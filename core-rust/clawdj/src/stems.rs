//! Classify vocals-only / instrumental-only stems and pick a bed for a dry vocal.
//!
//! Acapellas are not songs. They play at the same time as a beat-matched
//! instrumental (or a looped instrumental section of a full mix). Same-song
//! instrumental stacks are legal but not preferred — that stack is the original.

use serde::{Deserialize, Serialize};

/// How a track should be treated when planning a mix.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StemKind {
    VocalsOnly,
    InstrumentalOnly,
    FullMix,
}

/// One playlist row the pairer can see.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StemTrack {
    pub track_id: String,
    pub title: String,
    #[serde(default)]
    pub artist: String,
    #[serde(default)]
    pub bpm: Option<f64>,
    #[serde(default)]
    pub key: Option<String>,
    #[serde(default)]
    pub path: Option<String>,
    /// Effective dj_notes. `showcase_acapella` opts out of forced layering.
    #[serde(default)]
    pub dj_notes: String,
}

/// One vocals-only track assigned to a bed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StemPair {
    pub vocal_id: String,
    pub bed_id: String,
    pub score: f64,
    pub reason: String,
    pub same_song: bool,
    pub bed_kind: StemKind,
    pub loop_bed: bool,
}

/// JSON report for `clawdj stems pair`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StemPairReport {
    pub version: u32,
    pub pairs: Vec<StemPair>,
    pub unpaired_vocals: Vec<String>,
}

/// Classify a title/path. Version tags win; "Vocal Remix" of a produced
/// record is a full mix unless it is also tagged acapella.
#[must_use]
pub fn classify_stem(title: &str, path: &str) -> StemKind {
    let hay = format!("{title} {path}").to_ascii_lowercase();
    if is_vocals_only(&hay) {
        StemKind::VocalsOnly
    } else if is_instrumental_only(title, &hay) {
        StemKind::InstrumentalOnly
    } else {
        StemKind::FullMix
    }
}

/// True when a human note opts this vocal out of forced layering.
#[must_use]
pub fn is_showcase_acapella(notes: &str) -> bool {
    notes.to_ascii_lowercase().contains("showcase_acapella")
}

/// True when the vocal is already planned as a two-deck layer.
#[must_use]
pub fn is_vocal_over_bed(notes: &str) -> bool {
    notes.to_ascii_lowercase().contains("vocal_over_bed")
}

/// Pair each non-showcase vocals-only track with the best unused bed.
/// Prefers an instrumental-only track already in the set; a full mix is a
/// last-resort looped-section bed. Same-song instrumentals score lower than
/// a different interesting instrumental.
#[must_use]
pub fn pair_vocals(tracks: &[StemTrack]) -> StemPairReport {
    let mut used_beds = Vec::new();
    let mut pairs = Vec::new();
    let mut vocals = Vec::new();
    for (vocal_index, vocal) in tracks.iter().enumerate() {
        let path = vocal.path.as_deref().unwrap_or(vocal.track_id.as_str());
        if classify_stem(&vocal.title, path) != StemKind::VocalsOnly {
            continue;
        }
        if is_showcase_acapella(&vocal.dj_notes) {
            continue;
        }
        vocals.push((vocal_index, vocal));
    }
    let mut leftover = Vec::new();
    for &(vocal_index, vocal) in &vocals {
        if let Some(pair) = neighbor_instrumental(vocal, vocal_index, tracks, &used_beds) {
            used_beds.push(pair.bed_id.clone());
            pairs.push(pair);
        } else {
            leftover.push((vocal_index, vocal));
        }
    }
    for (vocal_index, vocal) in leftover {
        if let Some(pair) = best_bed(vocal, vocal_index, tracks, &used_beds) {
            used_beds.push(pair.bed_id.clone());
            pairs.push(pair);
        }
    }
    let claimed: std::collections::HashSet<&str> =
        pairs.iter().map(|pair| pair.vocal_id.as_str()).collect();
    let unpaired = vocals
        .iter()
        .filter(|(_, vocal)| !claimed.contains(vocal.track_id.as_str()))
        .map(|(_, vocal)| vocal.track_id.clone())
        .collect();
    StemPairReport {
        version: 1,
        pairs,
        unpaired_vocals: unpaired,
    }
}

fn is_vocals_only(hay: &str) -> bool {
    hay.contains("acappella")
        || hay.contains("acapella")
        || hay.contains("a cappella")
        || hay.contains("a capella")
        || hay.contains("vocals only")
        || hay.contains("vocal only")
}

fn is_instrumental_only(title: &str, hay: &str) -> bool {
    let lower_title = title.to_ascii_lowercase();
    lower_title.contains("(instrumental)")
        || lower_title.contains("[instrumental]")
        || lower_title.contains("(instr.)")
        || lower_title.ends_with(" - instrumental")
        || hay.contains("/instrumental/")
        || version_tag_instrumental(&lower_title)
}

fn version_tag_instrumental(title: &str) -> bool {
    title.ends_with(" instrumental") && !title.contains("instrumental hip")
}

fn neighbor_instrumental(
    vocal: &StemTrack,
    vocal_index: usize,
    tracks: &[StemTrack],
    used_beds: &[String],
) -> Option<StemPair> {
    for delta in [-1_isize, 1] {
        let index = isize::try_from(vocal_index).ok()?.checked_add(delta)?;
        if index < 0 {
            continue;
        }
        let bed_index = usize::try_from(index).ok()?;
        let Some(bed) = tracks.get(bed_index) else {
            continue;
        };
        if used_beds.iter().any(|id| id == &bed.track_id) {
            continue;
        }
        let path = bed.path.as_deref().unwrap_or(bed.track_id.as_str());
        if classify_stem(&bed.title, path) == StemKind::InstrumentalOnly {
            return Some(score_bed(
                vocal,
                vocal_index,
                bed,
                bed_index,
                StemKind::InstrumentalOnly,
            ));
        }
    }
    None
}

fn best_bed(
    vocal: &StemTrack,
    vocal_index: usize,
    tracks: &[StemTrack],
    used_beds: &[String],
) -> Option<StemPair> {
    let mut best: Option<StemPair> = None;
    for (bed_index, bed) in tracks.iter().enumerate() {
        if bed.track_id == vocal.track_id {
            continue;
        }
        if used_beds.iter().any(|id| id == &bed.track_id) {
            continue;
        }
        let path = bed.path.as_deref().unwrap_or(bed.track_id.as_str());
        let kind = classify_stem(&bed.title, path);
        if kind == StemKind::VocalsOnly {
            continue;
        }
        let pair = score_bed(vocal, vocal_index, bed, bed_index, kind);
        let take = match &best {
            None => true,
            Some(current) => {
                pair.score > current.score
                    || (pair.score == current.score && pair.bed_id < current.bed_id)
            }
        };
        if take {
            best = Some(pair);
        }
    }
    best
}

fn score_bed(
    vocal: &StemTrack,
    vocal_index: usize,
    bed: &StemTrack,
    bed_index: usize,
    kind: StemKind,
) -> StemPair {
    let same_song =
        core_title(&vocal.title) == core_title(&bed.title) && !core_title(&vocal.title).is_empty();
    let adjacent = vocal_index.abs_diff(bed_index) == 1;
    let mut score = 0.0;
    let mut reasons = Vec::new();
    if kind == StemKind::InstrumentalOnly {
        score += 3.0;
        reasons.push("instrumental-only bed".to_string());
    } else {
        score += 0.5;
        reasons.push("full-mix looped section bed".to_string());
    }
    let (bpm_score, bpm_reason) = bpm_compatibility(vocal.bpm, bed.bpm);
    score += bpm_score * 2.0;
    reasons.push(bpm_reason);
    let (key_score, key_reason) = key_compatibility(vocal.key.as_deref(), bed.key.as_deref());
    score += key_score * 2.0;
    reasons.push(key_reason);
    if same_song {
        reasons.push("same-song stack (legal, not preferred)".to_string());
    } else if key_score >= 0.55 {
        score += 2.0;
        reasons.push("different song".to_string());
    }
    if adjacent {
        score += 1.0;
        reasons.push("already adjacent".to_string());
    }
    StemPair {
        vocal_id: vocal.track_id.clone(),
        bed_id: bed.track_id.clone(),
        score,
        reason: reasons.join("; "),
        same_song,
        bed_kind: kind,
        loop_bed: kind == StemKind::FullMix,
    }
}

fn core_title(title: &str) -> String {
    let mut stripped = title.to_string();
    while let Some(start) = stripped.find('(') {
        if let Some(end) = stripped[start..].find(')') {
            stripped.replace_range(start..start + end + 1, " ");
        } else {
            break;
        }
    }
    while let Some(start) = stripped.find('[') {
        if let Some(end) = stripped[start..].find(']') {
            stripped.replace_range(start..start + end + 1, " ");
        } else {
            break;
        }
    }
    stripped
        .split_whitespace()
        .filter(|word| {
            let lower = word.to_ascii_lowercase();
            !matches!(
                lower.as_str(),
                "instrumental"
                    | "acapella"
                    | "acappella"
                    | "remix"
                    | "version"
                    | "dirty"
                    | "clean"
                    | "album"
                    | "feat."
                    | "ft."
                    | "-"
            )
        })
        .map(str::to_ascii_lowercase)
        .collect::<Vec<_>>()
        .join(" ")
}

fn bpm_compatibility(a: Option<f64>, b: Option<f64>) -> (f64, String) {
    match (a, b) {
        (Some(a), Some(b)) if a > 0.0 && b > 0.0 => {
            let lo = a.min(b);
            let hi = a.max(b);
            for factor in [1.0_f64, 2.0, 0.5] {
                let mut ratio = hi / (lo * factor);
                if ratio < 1.0 {
                    ratio = 1.0 / ratio;
                }
                if ratio <= 1.02 {
                    return (1.0, format!("bpm nearly identical ({a:.1}↔{b:.1})"));
                }
                if ratio <= 1.08 {
                    return (0.9, format!("bpm within ~8% ({a:.1}↔{b:.1})"));
                }
            }
            (0.15, format!("bpm far ({a:.1}↔{b:.1})"))
        }
        _ => (0.35, "bpm unknown".to_string()),
    }
}

fn key_compatibility(a: Option<&str>, b: Option<&str>) -> (f64, String) {
    let (Some(ka), Some(kb)) = (
        parse_camelot(a.unwrap_or("")),
        parse_camelot(b.unwrap_or("")),
    ) else {
        return (0.4, "key unknown".to_string());
    };
    if ka == kb {
        return (1.0, format!("same key ({})", a.unwrap_or("")));
    }
    if ka.0 == kb.0 {
        return (
            0.95,
            format!(
                "relative major/minor ({}↔{})",
                a.unwrap_or(""),
                b.unwrap_or("")
            ),
        );
    }
    let diff = (i32::from(ka.0) - i32::from(kb.0)).unsigned_abs() % 12;
    let wrapped = diff.min(12 - diff);
    if wrapped == 1 && ka.1 == kb.1 {
        return (
            0.85,
            format!("camelot neighbor ({}↔{})", a.unwrap_or(""), b.unwrap_or("")),
        );
    }
    (
        0.15,
        format!("key clash ({}↔{})", a.unwrap_or(""), b.unwrap_or("")),
    )
}

fn parse_camelot(key: &str) -> Option<(u8, char)> {
    let raw = key.trim().replace(' ', "");
    if raw.is_empty() {
        return None;
    }
    if let Some(num) = raw
        .strip_suffix(['A', 'a', 'B', 'b'])
        .and_then(|digits| digits.parse::<u8>().ok())
    {
        if (1..=12).contains(&num) {
            let mode = raw.chars().last()?.to_ascii_uppercase();
            return Some((num, mode));
        }
    }
    let lowered = raw.to_ascii_lowercase();
    let minor = lowered.ends_with('m') || lowered.ends_with("min");
    let note = raw
        .trim_end_matches(|c: char| {
            c.eq_ignore_ascii_case(&'m')
                || c.eq_ignore_ascii_case(&'i')
                || c.eq_ignore_ascii_case(&'n')
        })
        .to_ascii_uppercase();
    let num = if minor {
        camelot_minor(&note)
    } else {
        camelot_major(&note)
    }?;
    Some((num, if minor { 'A' } else { 'B' }))
}

fn camelot_major(note: &str) -> Option<u8> {
    Some(match note {
        "C" => 8,
        "G" => 9,
        "D" => 10,
        "A" => 11,
        "E" => 12,
        "B" => 1,
        "F#" | "GB" => 2,
        "DB" | "C#" => 3,
        "AB" | "G#" => 4,
        "EB" | "D#" => 5,
        "BB" | "A#" => 6,
        "F" => 7,
        _ => return None,
    })
}

fn camelot_minor(note: &str) -> Option<u8> {
    Some(match note {
        "A" => 8,
        "E" => 9,
        "B" => 10,
        "F#" | "GB" => 11,
        "C#" | "DB" => 12,
        "G#" | "AB" => 1,
        "D#" | "EB" => 2,
        "A#" | "BB" => 3,
        "F" => 4,
        "C" => 5,
        "G" => 6,
        "D" => 7,
        _ => return None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn track(id: &str, title: &str, bpm: f64, key: &str) -> StemTrack {
        StemTrack {
            track_id: id.to_string(),
            title: title.to_string(),
            artist: "50 Cent".to_string(),
            bpm: Some(bpm),
            key: Some(key.to_string()),
            path: Some(id.to_string()),
            dj_notes: String::new(),
        }
    }

    #[test]
    fn acapella_is_vocals_only_vocal_remix_is_not() {
        assert_eq!(
            classify_stem(
                "Get Up (Acapella)",
                "/x/04 - 50 Cent - Get Up (Acapella).mp3"
            ),
            StemKind::VocalsOnly
        );
        assert_eq!(
            classify_stem("Jimmy Crack Corn (Vocal Remix)", "/x/vocal-remix.mp3"),
            StemKind::FullMix
        );
        assert_eq!(
            classify_stem(
                "Jimmy Crack Corn (Vocal Remix) (Feat. Cashis) (Acapella)",
                "/x/a.mp3"
            ),
            StemKind::VocalsOnly
        );
    }

    #[test]
    fn dashed_instrumental_title_is_a_stem() {
        assert_eq!(
            classify_stem("Outta Control - Instrumental", "/x/outta.mp3"),
            StemKind::InstrumentalOnly
        );
        assert_eq!(
            classify_stem("Get Up (Instrumental)", "/x/get-up-inst.mp3"),
            StemKind::InstrumentalOnly
        );
    }

    #[test]
    fn neighbor_instrumental_wins_over_a_distant_mash() {
        let tracks = vec![
            track(
                "/jcc-inst",
                "Jimmy Crack Corn (Vocal Remix) (Instrumental)",
                95.86,
                "Fm",
            ),
            track(
                "/jcc-acapella",
                "Jimmy Crack Corn (Vocal Remix) (Feat. Cashis) (Acapella)",
                97.0,
                "Fm",
            ),
            track(
                "/jcc-full",
                "Eminem & 50 Cent - Jimmy Crack Corn",
                95.86,
                "Fm",
            ),
            track("/hands-up-inst", "Hands Up (Instrumental)", 95.0, "Fm"),
        ];
        let report = pair_vocals(&tracks);
        assert_eq!(report.pairs[0].bed_id, "/jcc-inst");
    }

    #[test]
    fn get_up_prefers_adjacent_different_song_instrumental() {
        let tracks = vec![
            track("/best-friend", "Best Friend", 90.8, "Db"),
            track("/get-up-acapella", "Get Up (Acapella)", 186.0, "F#"),
            track("/outta-inst", "Outta Control - Instrumental", 92.0, "Ebm"),
            track("/get-up-inst", "Get Up (Instrumental)", 93.0, "F#"),
        ];
        let report = pair_vocals(&tracks);
        assert_eq!(report.pairs.len(), 1);
        assert_eq!(report.pairs[0].vocal_id, "/get-up-acapella");
        assert_eq!(report.pairs[0].bed_id, "/outta-inst");
        assert!(!report.pairs[0].same_song);
        assert!(!report.pairs[0].loop_bed);
    }

    #[test]
    fn vocal_over_bed_note_is_detected() {
        assert!(is_vocal_over_bed(
            "entry_style=vocal_over_bed; ride_beats=96"
        ));
        assert!(!is_vocal_over_bed("showcase_acapella"));
    }

    #[test]
    fn showcase_acapella_is_not_paired() {
        let mut vocal = track("/banks", "On Fire (Acapella)", 94.0, "F#m");
        vocal.dj_notes = "showcase_acapella".to_string();
        let tracks = vec![vocal, track("/inst", "On Fire (Instrumental)", 94.0, "F#m")];
        let report = pair_vocals(&tracks);
        assert!(report.pairs.is_empty());
    }

    #[test]
    fn key_clash_does_not_beat_same_song_instrumental() {
        let tracks = vec![
            track("/cream-acapella", "C.R.E.A.M. (A Cappella)", 141.0, "Ab"),
            track("/cream-inst", "C.R.E.A.M. (Instrumental)", 93.0, "Ab"),
            track(
                "/patiently-inst",
                "Patiently Waiting (Instrumental)",
                79.0,
                "Bm",
            ),
        ];
        let report = pair_vocals(&tracks);
        assert_eq!(report.pairs[0].bed_id, "/cream-inst");
    }

    #[test]
    fn already_noted_vocal_still_pairs_onto_its_bed() {
        let mut vocal = track(
            "/still-kill-acapella",
            "I'll Still Kill (Acappella)",
            110.0,
            "F",
        );
        vocal.dj_notes = "entry_style=vocal_over_bed; ride_beats=192".to_string();
        let tracks = vec![
            track(
                "/still-kill-inst",
                "I'll Still Kill (Instrumental)",
                88.0,
                "Dm",
            ),
            vocal,
        ];
        let report = pair_vocals(&tracks);
        assert_eq!(report.pairs.len(), 1);
        assert_eq!(report.pairs[0].bed_id, "/still-kill-inst");
    }

    #[test]
    fn already_layered_neighbor_is_not_stolen() {
        let mut jcc = track(
            "/jcc-acapella",
            "Jimmy Crack Corn (Vocal Remix) (Feat. Cashis) (Acapella)",
            97.0,
            "Fm",
        );
        jcc.dj_notes = "entry_style=vocal_over_bed; ride_beats=96".to_string();
        let tracks = vec![
            track(
                "/jcc-inst",
                "Jimmy Crack Corn (Vocal Remix) (Instrumental)",
                95.86,
                "Fm",
            ),
            jcc,
            track("/ydk-acapella", "You Don't Know [Acapella]", 85.7, "Ab"),
            track("/ydk-inst", "You Don't Know [Instrumental]", 85.7, "Ab"),
        ];
        let report = pair_vocals(&tracks);
        let jcc_bed = report
            .pairs
            .iter()
            .find(|pair| pair.vocal_id == "/jcc-acapella")
            .unwrap();
        let ydk_bed = report
            .pairs
            .iter()
            .find(|pair| pair.vocal_id == "/ydk-acapella")
            .unwrap();
        assert_eq!(jcc_bed.bed_id, "/jcc-inst");
        assert_eq!(ydk_bed.bed_id, "/ydk-inst");
    }
}
