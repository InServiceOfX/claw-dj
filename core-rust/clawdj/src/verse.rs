//! Respect verse start/stop when picking a mix-in cue or a mix-out ride.
//!
//! Automatic energy cues (`phrase_body`) land ~30–45s in — usually mid
//! first verse. A legal entry is the top of the record or a pre-roll that
//! finishes on bar 1 of the verse. A legal exit starts the blend at the
//! verse's end, not in the middle of a rap or sung verse.

use serde::{Deserialize, Serialize};

use crate::stems::{StemKind, classify_stem};

/// How far past a segment start still counts as "on the 1".
pub const START_TOLERANCE_SECONDS: f64 = 2.0;
/// A verse that begins after this has intro/hook before it.
pub const INTRO_BEFORE_VERSE_SECONDS: f64 = 8.0;
/// Detector sometimes labels a whole cut as one verse. Skip those.
pub const MAX_VERSE_SECONDS: f64 = 80.0;

/// One lyric-timeline segment (verse or chorus).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LyricSegment {
    pub kind: String,
    pub start: f64,
    pub end: f64,
}

/// Where a cue sits relative to lyric structure.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CuePlacement {
    Intro,
    VerseStart,
    MidVerse,
    Chorus,
    MidChorus,
    Unknown,
}

/// Rewrite of an illegal automatic cue.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerseCueDecision {
    pub legal: bool,
    pub placement: CuePlacement,
    pub cue_seconds: f64,
    pub reason: String,
    /// `unchanged` | `intro_top` | `verse_preroll`
    pub source: String,
}

/// JSON body for `clawdj verse cue`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerseCueRequest {
    pub proposed_cue: f64,
    #[serde(default)]
    pub bpm: Option<f64>,
    #[serde(default)]
    pub first_beat: Option<f64>,
    #[serde(default = "default_blend_beats")]
    pub blend_beats: u32,
    #[serde(default)]
    pub segments: Vec<LyricSegment>,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub path: String,
}

fn default_blend_beats() -> u32 {
    32
}

fn is_verse(kind: &str) -> bool {
    kind.eq_ignore_ascii_case("verse")
}

fn is_chorus(kind: &str) -> bool {
    kind.eq_ignore_ascii_case("chorus") || kind.eq_ignore_ascii_case("hook")
}

fn containing(cue: f64, segments: &[LyricSegment]) -> Option<&LyricSegment> {
    // A boundary timestamp belongs to the segment that starts there.
    segments
        .iter()
        .find(|segment| (segment.start - cue).abs() <= 1e-9)
        .or_else(|| {
            segments
                .iter()
                .find(|segment| cue + 1e-9 > segment.start && cue < segment.end - 1e-9)
        })
        .or_else(|| {
            segments
                .iter()
                .find(|segment| cue + 1e-9 >= segment.start && cue <= segment.end + 1e-9)
        })
}

/// Classify a cue against lyric segments. No segments → unknown.
#[must_use]
pub fn classify_cue(cue: f64, segments: &[LyricSegment]) -> CuePlacement {
    if segments.is_empty() {
        return CuePlacement::Unknown;
    }
    if cue <= START_TOLERANCE_SECONDS {
        let first = segments
            .iter()
            .min_by(|a, b| a.start.partial_cmp(&b.start).unwrap());
        if let Some(first) = first {
            if first.start >= INTRO_BEFORE_VERSE_SECONDS
                || cue + START_TOLERANCE_SECONDS < first.start
            {
                return CuePlacement::Intro;
            }
        } else {
            return CuePlacement::Intro;
        }
    }
    let Some(segment) = containing(cue, segments) else {
        let first_start = segments
            .iter()
            .map(|segment| segment.start)
            .fold(f64::INFINITY, f64::min);
        if cue + START_TOLERANCE_SECONDS < first_start {
            return CuePlacement::Intro;
        }
        return CuePlacement::Unknown;
    };
    let into = cue - segment.start;
    if is_verse(&segment.kind) {
        if into <= START_TOLERANCE_SECONDS {
            CuePlacement::VerseStart
        } else {
            CuePlacement::MidVerse
        }
    } else if is_chorus(&segment.kind) {
        if into <= START_TOLERANCE_SECONDS {
            CuePlacement::Chorus
        } else {
            CuePlacement::MidChorus
        }
    } else if cue <= START_TOLERANCE_SECONDS {
        CuePlacement::Intro
    } else {
        CuePlacement::Unknown
    }
}

fn verse_cut_by_window(start: f64, end: f64, segments: &[LyricSegment]) -> Option<&LyricSegment> {
    segments.iter().find(|item| {
        is_verse(&item.kind) && (item.end - item.start) <= MAX_VERSE_SECONDS && {
            let overlap_lo = start.max(item.start + START_TOLERANCE_SECONDS);
            let overlap_hi = end.min(item.end);
            overlap_hi > overlap_lo + 1e-9
        }
    })
}

/// False for instrumental-only / no-vocal beds — no artist verse exists.
#[must_use]
pub fn has_vocal_verses(title: &str, path: &str) -> bool {
    classify_stem(title, path) != StemKind::InstrumentalOnly
}

/// If `proposed_cue` is mid-verse, or the incoming blend *finishes* mid-verse,
/// move to 0:00 (iconic intro) or a pre-roll onto the verse start.
#[must_use]
pub fn respect_verse_entry(
    proposed_cue: f64,
    segments: &[LyricSegment],
    first_beat: f64,
    bpm: Option<f64>,
    blend_beats: u32,
    title: &str,
    path: &str,
) -> VerseCueDecision {
    let _ = first_beat;
    if (!title.is_empty() || !path.is_empty()) && !has_vocal_verses(title, path) {
        return VerseCueDecision {
            legal: true,
            placement: CuePlacement::Unknown,
            cue_seconds: proposed_cue.max(0.0),
            reason: "instrumental / no vocals — verse boundaries do not apply".to_string(),
            source: "unchanged".to_string(),
        };
    }
    let placement = classify_cue(proposed_cue, segments);
    let period = bpm.filter(|value| *value > 0.0).map(|value| 60.0 / value);
    let fader_at = period.map_or(proposed_cue, |p| {
        proposed_cue + f64::from(blend_beats.max(1)) * p
    });
    if proposed_cue <= START_TOLERANCE_SECONDS {
        return VerseCueDecision {
            legal: true,
            placement: if placement == CuePlacement::Unknown {
                CuePlacement::Intro
            } else {
                placement
            },
            cue_seconds: proposed_cue.max(0.0),
            reason: "starting from the top is a legal mix-in".to_string(),
            source: "unchanged".to_string(),
        };
    }
    let cut = verse_cut_by_window(proposed_cue, fader_at, segments);
    if cut.is_none() && placement != CuePlacement::MidVerse {
        return VerseCueDecision {
            legal: true,
            placement,
            cue_seconds: proposed_cue.max(0.0),
            reason: format!("{placement:?} is a legal mix-in"),
            source: "unchanged".to_string(),
        };
    }
    let Some(verse) = cut
        .or_else(|| containing(proposed_cue, segments).filter(|segment| is_verse(&segment.kind)))
    else {
        return VerseCueDecision {
            legal: true,
            placement,
            cue_seconds: proposed_cue.max(0.0),
            reason: "mid-verse but no containing verse segment".to_string(),
            source: "unchanged".to_string(),
        };
    };
    let has_intro = verse.start >= INTRO_BEFORE_VERSE_SECONDS
        || segments
            .iter()
            .any(|segment| segment.end <= verse.start + 1e-9 && segment.start < verse.start);
    if has_intro {
        return VerseCueDecision {
            legal: false,
            placement: CuePlacement::MidVerse,
            cue_seconds: 0.0,
            reason: format!(
                "incoming blend from {proposed_cue:.2}s finishes inside verse {:.2}–{:.2}; start from 0:00 so the blend covers the intro",
                verse.start, verse.end
            ),
            source: "intro_top".to_string(),
        };
    }
    let preroll = period.map_or(0.0, |p| f64::from(blend_beats.max(1)) * p);
    let cue = (verse.start - preroll).max(0.0);
    VerseCueDecision {
        legal: false,
        placement: CuePlacement::MidVerse,
        cue_seconds: cue,
        reason: format!(
            "incoming blend from {proposed_cue:.2}s finishes inside verse {:.2}–{:.2}; pre-roll onto verse start",
            verse.start, verse.end
        ),
        source: "verse_preroll".to_string(),
    }
}

/// Stretch an automatic ride so the whole outgoing blend sits after the verse.
/// Returns `(ride_beats, reason)`.
#[must_use]
pub fn respect_verse_exit(
    cue_seconds: f64,
    ride_beats: u32,
    bpm: f64,
    segments: &[LyricSegment],
    blend_beats: u32,
    title: &str,
    path: &str,
) -> (u32, String) {
    if (!title.is_empty() || !path.is_empty()) && !has_vocal_verses(title, path) {
        return (ride_beats, "unchanged".to_string());
    }
    if segments.is_empty() || bpm <= 0.0 {
        return (ride_beats, "unchanged".to_string());
    }
    let period = 60.0 / bpm;
    let fade_at = cue_seconds + f64::from(ride_beats) * period;
    let fade_done = fade_at + f64::from(blend_beats.max(1)) * period;
    let Some(verse) = verse_cut_by_window(fade_at, fade_done, segments) else {
        return (ride_beats, "unchanged".to_string());
    };
    let needed = ((verse.end - cue_seconds) / period).ceil().max(0.0) as u32;
    if needed <= ride_beats {
        return (ride_beats, "unchanged".to_string());
    }
    let capped = needed.min(ride_beats.saturating_add(128));
    (
        capped,
        format!(
            "blend {fade_at:.2}–{fade_done:.2}s eats verse {:.2}–{:.2}; extend ride {ride_beats} -> {capped} so the fade starts at the verse end",
            verse.start, verse.end
        ),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn verse(start: f64, end: f64) -> LyricSegment {
        LyricSegment {
            kind: "verse".to_string(),
            start,
            end,
        }
    }

    fn chorus(start: f64, end: f64) -> LyricSegment {
        LyricSegment {
            kind: "chorus".to_string(),
            start,
            end,
        }
    }

    #[test]
    fn on_fire_phrase_body_is_mid_verse_and_rewrites_to_zero() {
        let segments = vec![
            verse(3.60, 12.92),
            chorus(12.92, 27.75),
            verse(27.75, 73.30),
            chorus(73.30, 88.11),
        ];
        assert_eq!(classify_cue(41.35, &segments), CuePlacement::MidVerse);
        let decision = respect_verse_entry(41.35, &segments, 0.292, Some(95.0), 32, "", "");
        assert!(!decision.legal);
        assert_eq!(decision.cue_seconds, 0.0);
        assert_eq!(decision.source, "intro_top");
    }

    #[test]
    fn cue_at_zero_is_intro() {
        let segments = vec![chorus(12.92, 27.75), verse(32.88, 73.30)];
        assert_eq!(classify_cue(0.0, &segments), CuePlacement::Intro);
        let decision = respect_verse_entry(0.0, &segments, 0.0, Some(95.0), 32, "", "");
        assert!(decision.legal);
        assert_eq!(decision.source, "unchanged");
    }

    #[test]
    fn verse_start_within_tolerance_is_legal() {
        let segments = vec![verse(32.88, 73.30)];
        assert_eq!(classify_cue(32.88, &segments), CuePlacement::VerseStart);
        assert_eq!(classify_cue(34.0, &segments), CuePlacement::VerseStart);
        assert_eq!(classify_cue(36.0, &segments), CuePlacement::MidVerse);
    }

    #[test]
    fn no_intro_prerolls_onto_verse_start() {
        let segments = vec![verse(4.0, 40.0)];
        let decision = respect_verse_entry(20.0, &segments, 0.0, Some(90.0), 16, "", "");
        assert!(!decision.legal);
        assert_eq!(decision.source, "verse_preroll");
        // 16 beats at 90 BPM = 10.67s; 4.0 - 10.67 → 0
        assert_eq!(decision.cue_seconds, 0.0);
    }

    #[test]
    fn exit_extends_to_verse_end() {
        let segments = vec![verse(32.88, 73.30), chorus(73.30, 88.11)];
        // cue 0, 80 beats at 95 BPM = 50.53s, still in verse 1
        let (ride, reason) = respect_verse_exit(0.0, 80, 95.0, &segments, 32, "", "");
        assert!(ride > 80, "{ride} {reason}");
        assert!(reason.contains("extend ride"));
        let fade = f64::from(ride) * 60.0 / 95.0;
        assert!((fade - 73.30).abs() < 1.0, "fade {fade}");
    }

    #[test]
    fn twenty_one_questions_blend_in_rewrites_to_zero() {
        let segments = vec![
            verse(2.66, 32.77),
            chorus(32.77, 53.02),
            verse(53.02, 94.50),
        ];
        let decision = respect_verse_entry(52.76, &segments, 0.0, Some(93.05), 32, "", "");
        assert!(!decision.legal);
        assert_eq!(decision.cue_seconds, 0.0);
        assert_eq!(decision.source, "intro_top");
    }

    #[test]
    fn empty_segments_do_not_rewrite() {
        assert_eq!(classify_cue(41.35, &[]), CuePlacement::Unknown);
        let decision = respect_verse_entry(41.35, &[], 0.0, Some(95.0), 32, "", "");
        assert!(decision.legal);
        assert_eq!(decision.cue_seconds, 41.35);
        let (ride, reason) = respect_verse_exit(0.0, 80, 95.0, &[], 32, "", "");
        assert_eq!(ride, 80);
        assert_eq!(reason, "unchanged");
    }

    #[test]
    fn instrumental_skips_verse_rules_even_with_vocal_lrc() {
        let segments = vec![verse(27.75, 73.30), chorus(73.30, 88.11)];
        let decision = respect_verse_entry(
            41.35,
            &segments,
            0.0,
            Some(95.0),
            32,
            "On Fire (Instrumental)",
            "",
        );
        assert!(decision.legal);
        assert_eq!(decision.cue_seconds, 41.35);
        let (ride, reason) =
            respect_verse_exit(0.0, 80, 95.0, &segments, 32, "On Fire (Instrumental)", "");
        assert_eq!(ride, 80);
        assert_eq!(reason, "unchanged");
        assert!(!has_vocal_verses("On Fire (Instrumental)", ""));
        assert!(has_vocal_verses("On Fire (Feat. 50 Cent)", ""));
    }
}
