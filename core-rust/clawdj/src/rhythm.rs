//! Section-local backbeat evidence. Scores are signal heuristics, not calibrated
//! instrument probabilities. Analysis never controls a deck or edits an audio file.
use anyhow::{Context, Result, bail};
use realfft::RealFftPlanner;
use serde::{Deserialize, Serialize};
use std::{path::Path, process::Command};

pub const VERSION: u32 = 1;
const SR: usize = 22050;
const FRAME: usize = 1024;
const HOP: usize = 220;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Onset {
    pub seconds: f64,
    pub strength: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Section {
    pub start_seconds: f64,
    pub end_seconds: f64,
    /// Backbeat cycle in source-grid beats; 4 also represents a half-time snare.
    pub cadence_beats: f64,
    /// Measured onset phase relative to first_beat_seconds, including microtiming.
    pub phase_beats: f64,
    pub confidence: f64,
    pub coverage: f64,
    pub spread_beats: f64,
    pub source: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub downbeat_seconds: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Rhythm {
    pub version: u32,
    pub bpm: f64,
    pub first_beat_seconds: f64,
    pub duration_seconds: f64,
    pub onsets: Vec<Onset>,
    pub sections: Vec<Section>,
    /// Only supplied by a reviewed marker or an independent downbeat model.
    #[serde(default)]
    pub downbeat_seconds: Option<f64>,
}

fn quantile(values: &[f64], q: f64) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f64::total_cmp);
    sorted[((sorted.len() - 1) as f64 * q).round() as usize]
}

pub fn analyze_file(path: &Path, bpm: f64, first_beat: f64) -> Result<Rhythm> {
    if !path.is_file() {
        bail!("rhythm input must be an existing local audio file");
    }
    let output = Command::new("ffmpeg")
        .args(["-v", "error", "-nostdin", "-i"])
        .arg(path)
        .args([
            "-vn", "-t", "1800", "-ac", "1", "-ar", "22050", "-f", "f32le", "pipe:1",
        ])
        .output()
        .context("rhythm analysis requires ffmpeg on PATH")?;
    if !output.status.success() {
        bail!(
            "audio decode failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let samples: Vec<f32> = output
        .stdout
        .chunks_exact(4)
        .map(|v| f32::from_le_bytes([v[0], v[1], v[2], v[3]]))
        .collect();
    analyze_samples(&samples, bpm, first_beat)
}

pub fn analyze_samples(samples: &[f32], bpm: f64, first_beat: f64) -> Result<Rhythm> {
    if !bpm.is_finite() || !(35.0..=300.0).contains(&bpm) || !first_beat.is_finite() {
        bail!("rhythm requires a finite 35..300 BPM grid and finite first beat");
    }
    if samples.len() < FRAME || samples.iter().any(|v| !v.is_finite()) {
        bail!("audio is too short or contains non-finite samples");
    }
    let mut planner = RealFftPlanner::<f32>::new();
    let fft = planner.plan_fft_forward(FRAME);
    let mut spectrum = fft.make_output_vec();
    let mut scratch = fft.make_scratch_vec();
    let mut previous = vec![0.0_f64; spectrum.len()];
    let mut fluxes = Vec::new();
    let mut ratios = Vec::new();
    for frame in samples.windows(FRAME).step_by(HOP) {
        let mut input: Vec<f32> = frame
            .iter()
            .enumerate()
            .map(|(i, v)| v * (0.5 - 0.5 * (std::f32::consts::TAU * i as f32 / FRAME as f32).cos()))
            .collect();
        fft.process_with_scratch(&mut input, &mut spectrum, &mut scratch)?;
        let mut flux = [0.0_f64; 5];
        let mut energy = [0.0_f64; 5];
        for (i, c) in spectrum.iter().enumerate().skip(1) {
            let hz = i as f64 * SR as f64 / FRAME as f64;
            let band = if hz < 180.0 {
                0
            } else if hz < 700.0 {
                1
            } else if hz < 1500.0 {
                2
            } else if hz < 6000.0 {
                3
            } else {
                4
            };
            let magnitude = f64::from(c.norm());
            flux[band] += (magnitude - previous[i]).max(0.0);
            energy[band] += magnitude;
            previous[i] = magnitude;
        }
        // Hats alone have little low/mid body. Do not normalize that absence
        // into apparent snare evidence when whitening the individual bands.
        ratios.push(((energy[1] + energy[2]) / (energy[3] + energy[4] + 1e-9)).min(1.0));
        fluxes.push(flux);
    }
    let mut scores = vec![0.0; fluxes.len()];
    // Local normalization accommodates quiet intros, loud choruses and fades.
    let block = SR * 8 / HOP;
    for start in (0..fluxes.len()).step_by(block) {
        let end = (start + block).min(fluxes.len());
        let scales: Vec<f64> = (0..5)
            .map(|b| {
                quantile(
                    &fluxes[start..end].iter().map(|f| f[b]).collect::<Vec<_>>(),
                    0.9,
                )
                .max(1e-6)
            })
            .collect();
        for i in start..end {
            let body = (fluxes[i][1] / scales[1] + fluxes[i][2] / scales[2]) / 2.0;
            let snap = fluxes[i][3] / scales[3];
            let hat = fluxes[i][4] / scales[4];
            scores[i] = snap * (0.8 + 0.2 * body.min(2.0)) / (1.0 + 0.25 * hat)
                * (ratios[i] / 0.12).min(1.0);
        }
    }
    let mut onsets: Vec<Onset> = Vec::new();
    for i in 2..scores.len().saturating_sub(2) {
        let lo = i.saturating_sub(block / 2);
        let hi = (i + block / 2).min(scores.len());
        // Peak threshold uses the nearby average; a strong hat must also pass
        // the independent body/snap gate above.
        let mean = scores[lo..hi].iter().sum::<f64>() / (hi - lo).max(1) as f64;
        if scores[i] < (mean * 2.3).max(0.35) || scores[i - 2..i + 3].iter().any(|v| *v > scores[i])
        {
            continue;
        }
        let seconds = (i * HOP + FRAME / 2) as f64 / SR as f64;
        let candidate = Onset {
            seconds,
            strength: scores[i].min(8.0),
        };
        if let Some(last) = onsets.last_mut() {
            if seconds - last.seconds < 0.10 {
                if candidate.strength > last.strength {
                    *last = candidate;
                }
                continue;
            }
        }
        onsets.push(candidate);
    }
    let duration = samples.len() as f64 / SR as f64;
    let sections = fit_sections(&onsets, bpm, first_beat, duration);
    Ok(Rhythm {
        version: VERSION,
        bpm,
        first_beat_seconds: first_beat,
        duration_seconds: duration,
        onsets,
        sections,
        downbeat_seconds: None,
    })
}

pub fn fit_sections(onsets: &[Onset], bpm: f64, first: f64, duration: f64) -> Vec<Section> {
    let beat_s = 60.0 / bpm;
    let mut sections = Vec::new();
    let total_beats = ((duration - first) / beat_s).ceil().max(0.0) as usize;
    for start in (0..total_beats).step_by(16) {
        let end = (start + 32).min(total_beats);
        // The preceding overlapping window already covers a short tail.
        // Do not replace its measured context with a tiny, unfit duplicate.
        if start > 0 && end - start < 16 {
            continue;
        }
        let mut slots = [0.0_f64; 4];
        let mut per_beat = vec![0.0_f64; end - start];
        let mut best_hits = vec![None; end - start];
        for hit in onsets {
            let beat = (hit.seconds - first) / beat_s;
            let index = beat.round() as i64;
            if index < start as i64 || index >= end as i64 || (beat - index as f64).abs() > 0.20 {
                continue;
            }
            let local = index as usize - start;
            if hit.strength > per_beat[local] {
                per_beat[local] = hit.strength;
                best_hits[local] = Some((index as usize, beat - index as f64, hit.strength));
            }
        }
        for (i, energy) in per_beat.iter().enumerate() {
            slots[(i + start) % 4] += energy;
        }
        let even = slots[0] + slots[2];
        let odd = slots[1] + slots[3];
        let parity = usize::from(odd > even);
        let pair = [slots[parity], slots[parity + 2]];
        let cadence = if pair[0].min(pair[1]) >= pair[0].max(pair[1]) * 0.38 {
            2
        } else {
            4
        };
        let phase = if cadence == 2 || pair[0] >= pair[1] {
            parity
        } else {
            parity + 2
        };
        let selected: Vec<_> = best_hits
            .iter()
            .flatten()
            .filter(|(b, _, _)| b % cadence == phase)
            .collect();
        let offsets: Vec<_> = selected.iter().map(|(_, offset, _)| *offset).collect();
        let offset = quantile(&offsets, 0.5);
        let spread = quantile(
            &offsets
                .iter()
                .map(|v| (v - offset).abs())
                .collect::<Vec<_>>(),
            0.8,
        );
        let occupied = per_beat
            .iter()
            .enumerate()
            .filter(|(i, v)| (i + start) % cadence == phase && **v > 0.0)
            .count();
        let expected = ((end - start) as f64 / cadence as f64).max(1.0);
        let coverage = (occupied as f64 / expected).min(1.0);
        let signal = if cadence == 2 {
            even.max(odd) / 2.0
        } else {
            slots[phase]
        };
        let noise = if cadence == 2 {
            even.min(odd) / 2.0
        } else {
            (slots.iter().sum::<f64>() - signal) / 3.0
        };
        let mean = per_beat.iter().sum::<f64>() / per_beat.len().max(1) as f64;
        let centered: Vec<_> = per_beat.iter().map(|v| v - mean).collect();
        let alternating = centered
            .iter()
            .enumerate()
            .map(|(i, v)| if (i + start) % 2 == parity { *v } else { -*v })
            .sum::<f64>()
            .abs()
            / (centered.iter().map(|v| v.abs()).sum::<f64>() + 1e-9);
        let dominance = if cadence == 2 {
            alternating
        } else {
            ((signal - noise) / (signal + noise + 1e-9)).max(0.0)
        };
        let confidence = if occupied < 4 || end - start < 16 {
            0.0
        } else {
            dominance * coverage * (1.0 - spread / 0.20).clamp(0.0, 1.0)
        };
        sections.push(Section {
            start_seconds: if start == 0 {
                0.0
            } else {
                (first + start as f64 * beat_s).max(0.0)
            },
            end_seconds: (first + end as f64 * beat_s).min(duration),
            cadence_beats: cadence as f64,
            phase_beats: phase as f64 + offset,
            confidence,
            coverage,
            spread_beats: spread,
            source: "multiband_transients".into(),
            downbeat_seconds: None,
        });
    }
    sections
}

/// Fit explicit snare/clap transcription timestamps, from a reviewed or
/// independently learned source. Beat/downbeat timestamps are not drum hits.
pub fn refit(mut rhythm: Rhythm) -> Result<Rhythm> {
    if rhythm.version != VERSION
        || !(35.0..=300.0).contains(&rhythm.bpm)
        || !rhythm.first_beat_seconds.is_finite()
        || !rhythm.duration_seconds.is_finite()
        || rhythm.duration_seconds <= 0.0
        || rhythm.onsets.iter().any(|h| {
            !h.seconds.is_finite()
                || h.seconds < 0.0
                || h.seconds > rhythm.duration_seconds
                || !h.strength.is_finite()
                || h.strength <= 0.0
        })
    {
        bail!("invalid drum onset evidence");
    }
    rhythm
        .onsets
        .sort_by(|a, b| a.seconds.total_cmp(&b.seconds));
    rhythm.sections = fit_sections(
        &rhythm.onsets,
        rhythm.bpm,
        rhythm.first_beat_seconds,
        rhythm.duration_seconds,
    );
    Ok(rhythm)
}

pub fn section_at(rhythm: &Rhythm, seconds: f64) -> Option<&Section> {
    // Prefer the window with the most context around the position. Never use
    // a distant confident chorus to certify a different, drumless breakdown.
    rhythm
        .sections
        .iter()
        .filter(|s| seconds >= s.start_seconds && seconds < s.end_seconds)
        .min_by(|a, b| {
            let da = (seconds - (a.start_seconds + a.end_seconds) / 2.0).abs();
            let db = (seconds - (b.start_seconds + b.end_seconds) / 2.0).abs();
            da.total_cmp(&db)
        })
}

#[derive(Debug, Deserialize)]
pub struct AlignmentRequest {
    pub outgoing: Rhythm,
    pub incoming: Rhythm,
    pub outgoing_seconds: f64,
    pub incoming_seconds: f64,
    pub outgoing_rate: f64,
    pub incoming_rate: f64,
    pub overlap_seconds: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Alignment {
    pub status: String,
    pub reason: String,
    pub delay_seconds: f64,
    pub cycle_seconds: f64,
    pub confidence: f64,
    pub matched_hits: usize,
    pub median_error_ms: Option<f64>,
    pub p90_error_ms: Option<f64>,
    /// A reliable suffix may time an uncertain entrance, never certify it.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub evidence_window_start_seconds: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub evidence_window_duration_seconds: Option<f64>,
}

fn primary_hits(
    rhythm: &Rhythm,
    section: &Section,
    start: f64,
    rate: f64,
    overlap: f64,
) -> Vec<f64> {
    let beat_s = 60.0 / rhythm.bpm;
    let mut cycles = std::collections::BTreeMap::<i64, (f64, f64)>::new();
    for hit in &rhythm.onsets {
        let beat = (hit.seconds - rhythm.first_beat_seconds) / beat_s - section.phase_beats;
        let cycle = (beat / section.cadence_beats).round() as i64;
        let time = (hit.seconds - start) / rate;
        if time < 0.0
            || time > overlap
            || (beat - cycle as f64 * section.cadence_beats).abs() > 0.20
        {
            continue;
        }
        let entry = cycles.entry(cycle).or_insert((time, hit.strength));
        if hit.strength > entry.1 {
            *entry = (time, hit.strength);
        }
    }
    cycles.values().map(|(time, _)| *time).collect()
}

pub fn align(r: &AlignmentRequest) -> Result<Alignment> {
    let direct = align_local(r)?;
    if direct.status != "uncertain"
        || !matches!(
            direct.reason.as_str(),
            "no local backbeat evidence" | "weak or inconsistent local snare/clap evidence"
        )
    {
        return Ok(direct);
    }
    // Do not collapse an alternating backbeat onto an arbitrary grid tick just
    // because the first window is weak. Look ONLY inside this actual overlap
    // for a suffix with repeated corresponding hits. Keep the entrance marked
    // uncertain, and do not extrapolate through contradictory confident drums.
    let step = 0.5 * 60.0 / r.outgoing.bpm / r.outgoing_rate;
    for index in 1..=(r.overlap_seconds / step).ceil().min(256.0) as usize {
        let time = index as f64 * step;
        if time >= r.overlap_seconds {
            break;
        }
        let future = AlignmentRequest {
            outgoing: r.outgoing.clone(),
            incoming: r.incoming.clone(),
            // The outgoing song advances while the incoming cue waits. Search
            // the audible overlap after the nominal grid entrance, not the
            // earlier pre-launch position (which may still be weak).
            outgoing_seconds: r.outgoing_seconds + (time + direct.delay_seconds) * r.outgoing_rate,
            incoming_seconds: r.incoming_seconds + time * r.incoming_rate,
            outgoing_rate: r.outgoing_rate,
            incoming_rate: r.incoming_rate,
            overlap_seconds: r.overlap_seconds - time,
        };
        let mut candidate = align_local(&future)?;
        if candidate.status != "ready" {
            continue;
        }
        candidate.delay_seconds += direct.delay_seconds;
        let out_start = r.outgoing_seconds + candidate.delay_seconds * r.outgoing_rate;
        if out_start + r.overlap_seconds * r.outgoing_rate > r.outgoing.duration_seconds - 0.15 {
            continue; // Never obtain parity by consuming the full fade's bed.
        }
        let out_anchor = section_at(&r.outgoing, future.outgoing_seconds).unwrap();
        let in_anchor = section_at(&r.incoming, future.incoming_seconds).unwrap();
        if !consistent_confident_sections(
            &r.outgoing,
            out_anchor,
            out_start,
            r.outgoing_rate,
            r.overlap_seconds,
        ) || !consistent_confident_sections(
            &r.incoming,
            in_anchor,
            r.incoming_seconds,
            r.incoming_rate,
            r.overlap_seconds,
        ) {
            continue;
        }
        candidate.status = "uncertain".into();
        candidate.reason = "entrance timed from reliable later overlap backbeats; entrance evidence remains unverified".into();
        candidate.evidence_window_start_seconds = Some(time);
        candidate.evidence_window_duration_seconds = Some(future.overlap_seconds);
        return Ok(candidate);
    }
    Ok(direct)
}

fn consistent_confident_sections(
    rhythm: &Rhythm,
    anchor: &Section,
    start: f64,
    rate: f64,
    overlap: f64,
) -> bool {
    // section_at changes at starts/ends AND halfway between window centers.
    // Partition its exact piecewise-constant selection, rather than sampling
    // a brief contradictory window away between two arbitrary time ticks.
    let end = start + overlap * rate;
    let local = rhythm
        .sections
        .iter()
        .filter(|s| s.start_seconds < end && s.end_seconds > start)
        .collect::<Vec<_>>();
    let mut boundaries = vec![start, end];
    for (i, section) in local.iter().enumerate() {
        boundaries.extend([section.start_seconds, section.end_seconds]);
        for other in &local[i + 1..] {
            let halfway = (section.start_seconds
                + section.end_seconds
                + other.start_seconds
                + other.end_seconds)
                / 4.0;
            if halfway >= section.start_seconds.max(other.start_seconds)
                && halfway < section.end_seconds.min(other.end_seconds)
            {
                boundaries.push(halfway);
            }
        }
    }
    boundaries.retain(|t| *t >= start && *t <= end);
    boundaries.sort_by(f64::total_cmp);
    boundaries.dedup();
    boundaries.windows(2).all(|interval| {
        let Some(section) =
            section_at(rhythm, (interval[0] + interval[1]) / 2.0).filter(|s| s.confidence >= 0.45)
        else {
            return true;
        };
        let difference = (section.phase_beats - anchor.phase_beats + anchor.cadence_beats / 2.0)
            .rem_euclid(anchor.cadence_beats)
            - anchor.cadence_beats / 2.0;
        section.cadence_beats == anchor.cadence_beats && difference.abs() < 0.15
    })
}

fn align_local(r: &AlignmentRequest) -> Result<Alignment> {
    for v in [
        r.outgoing_seconds,
        r.incoming_seconds,
        r.outgoing_rate,
        r.incoming_rate,
        r.overlap_seconds,
    ] {
        if !v.is_finite() {
            bail!("alignment inputs must be finite");
        }
    }
    if r.outgoing_rate <= 0.0 || r.incoming_rate <= 0.0 || r.overlap_seconds <= 0.0 {
        bail!("rates and overlap must be positive");
    }
    for rhythm in [&r.outgoing, &r.incoming] {
        if rhythm.version != VERSION
            || !(35.0..=300.0).contains(&rhythm.bpm)
            || rhythm
                .sections
                .iter()
                .any(|s| ![1.0, 2.0, 4.0].contains(&s.cadence_beats))
        {
            bail!("unsupported rhythm version, BPM or cadence");
        }
    }
    let mut result = Alignment {
        status: "uncertain".into(),
        reason: "no local backbeat evidence".into(),
        delay_seconds: 0.0,
        cycle_seconds: 0.0,
        confidence: 0.0,
        matched_hits: 0,
        median_error_ms: None,
        p90_error_ms: None,
        evidence_window_start_seconds: None,
        evidence_window_duration_seconds: None,
    };
    // Even without classified snares, a source grid supports a cue-preserving
    // beat entrance. This is a best-effort launch, NOT backbeat certification.
    let out_beat = 60.0 / r.outgoing.bpm;
    let in_beat = 60.0 / r.incoming.bpm;
    let grid_cycle = out_beat / r.outgoing_rate;
    result.cycle_seconds = grid_cycle;
    result.delay_seconds = ((r.outgoing.first_beat_seconds - r.outgoing_seconds) / r.outgoing_rate
        - (r.incoming.first_beat_seconds - r.incoming_seconds) / r.incoming_rate)
        .rem_euclid(grid_cycle);
    if result.delay_seconds < 0.005 || grid_cycle - result.delay_seconds < 0.005 {
        result.delay_seconds = 0.0;
    }
    let (Some(out), Some(inc)) = (
        section_at(&r.outgoing, r.outgoing_seconds),
        section_at(&r.incoming, r.incoming_seconds),
    ) else {
        return Ok(result);
    };
    result.confidence = out.confidence.min(inc.confidence);
    if result.confidence < 0.45 {
        result.reason = "weak or inconsistent local snare/clap evidence".into();
        return Ok(result);
    }
    let out_cycle = out.cadence_beats * out_beat / r.outgoing_rate;
    let in_cycle = inc.cadence_beats * in_beat / r.incoming_rate;
    result.cycle_seconds = out_cycle;
    if (out_cycle - in_cycle).abs() * (r.overlap_seconds / out_cycle) > 0.070 {
        result.status = "incompatible".into();
        result.reason = "backbeat cadence/tempo would drift during this overlap".into();
        return Ok(result);
    }
    let out_next = ((r.outgoing.first_beat_seconds + out.phase_beats * out_beat
        - r.outgoing_seconds)
        / r.outgoing_rate)
        .rem_euclid(out_cycle);
    let in_next = ((r.incoming.first_beat_seconds + inc.phase_beats * in_beat
        - r.incoming_seconds)
        / r.incoming_rate)
        .rem_euclid(in_cycle);
    let mut delay = (out_next - in_next).rem_euclid(out_cycle);
    // Floating-point zero must not turn an already-aligned entrance into
    // an unnecessary complete-cycle wait.
    if out_cycle - delay < 0.005 || delay < 0.005 {
        delay = 0.0;
    }
    if let (Some(out_down), Some(in_down)) = (
        out.downbeat_seconds.or(r.outgoing.downbeat_seconds),
        inc.downbeat_seconds.or(r.incoming.downbeat_seconds),
    ) {
        let mut candidates = Vec::new();
        for extra in 0..4 {
            let candidate = delay + extra as f64 * out_cycle;
            if candidate > 4.0 * out_beat / r.outgoing_rate + 0.01 {
                break;
            }
            let out_bar = ((r.outgoing_seconds + candidate * r.outgoing_rate - out_down)
                / out_beat)
                .rem_euclid(4.0);
            let in_bar = ((r.incoming_seconds - in_down) / in_beat).rem_euclid(4.0);
            let difference = (out_bar - in_bar + 2.0).rem_euclid(4.0) - 2.0;
            candidates.push((difference.abs(), candidate));
        }
        if let Some((error, candidate)) = candidates.into_iter().min_by(|a, b| a.0.total_cmp(&b.0))
        {
            if error > 0.20 {
                result.status = "incompatible".into();
                result.reason = "verified downbeats conflict with backbeat alignment".into();
                return Ok(result);
            }
            delay = candidate;
        }
    }
    result.delay_seconds = delay;
    let out_start = r.outgoing_seconds + delay * r.outgoing_rate;
    let mut errors = Vec::new();
    let out_hits = primary_hits(
        &r.outgoing,
        out,
        out_start,
        r.outgoing_rate,
        r.overlap_seconds,
    );
    let in_hits = primary_hits(
        &r.incoming,
        inc,
        r.incoming_seconds,
        r.incoming_rate,
        r.overlap_seconds,
    );
    for t in in_hits {
        if let Some(error) = out_hits
            .iter()
            .map(|other| (other - t).abs())
            .min_by(f64::total_cmp)
        {
            // Missing beats are missing coverage, not a nearest-neighbor
            // match to a snare an entire bar away.
            if error < out_cycle * 0.35 {
                errors.push(error * 1000.0);
            }
        }
    }
    result.matched_hits = errors.len();
    if errors.len() < 3 || (errors.len() as f64) < (r.overlap_seconds / out_cycle).floor() * 0.60 {
        result.reason = "insufficient corresponding backbeats across overlap".into();
        return Ok(result);
    }
    // Check each local window, not just the entrance. A confident intro cannot
    // certify a drumless breakdown or a different cadence later in the blend.
    let mut time = 0.0;
    while time < r.overlap_seconds {
        for (rhythm, initial, start, rate) in [
            (&r.outgoing, out, out_start, r.outgoing_rate),
            (&r.incoming, inc, r.incoming_seconds, r.incoming_rate),
        ] {
            let Some(section) =
                section_at(rhythm, start + time * rate).filter(|s| s.confidence >= 0.45)
            else {
                result.reason = "local backbeat evidence unavailable within overlap".into();
                return Ok(result);
            };
            let difference = (section.phase_beats - initial.phase_beats
                + initial.cadence_beats / 2.0)
                .rem_euclid(initial.cadence_beats)
                - initial.cadence_beats / 2.0;
            if section.cadence_beats != initial.cadence_beats || difference.abs() >= 0.15 {
                result.status = "incompatible".into();
                result.reason = "confident local backbeat changes within overlap".into();
                return Ok(result);
            }
        }
        time += out_cycle;
    }
    let median = quantile(&errors, 0.5);
    let p90 = quantile(&errors, 0.9);
    result.median_error_ms = Some(median);
    result.p90_error_ms = Some(p90);
    if median > 45.0 || p90 > 85.0 {
        result.status = "incompatible".into();
        result.reason = "measured hits disagree or drift across the overlap".into();
    } else {
        result.status = "ready".into();
        result.reason = "local backbeats agree; verify live positions before opening fader".into();
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn pattern(phase: f64, cadence: f64) -> Rhythm {
        let onsets = (0..64)
            .map(|i| Onset {
                seconds: (phase + i as f64 * cadence) * 0.5,
                strength: 2.0,
            })
            .collect::<Vec<_>>();
        Rhythm {
            version: VERSION,
            bpm: 120.0,
            first_beat_seconds: 0.0,
            duration_seconds: 64.0,
            sections: fit_sections(&onsets, 120.0, 0.0, 64.0),
            onsets,
            downbeat_seconds: None,
        }
    }
    #[test]
    fn resolves_parity_without_jumping_or_moving_cue() {
        let request = AlignmentRequest {
            outgoing: pattern(0.0, 2.0),
            incoming: pattern(1.0, 2.0),
            outgoing_seconds: 8.0,
            incoming_seconds: 0.0,
            outgoing_rate: 1.0,
            incoming_rate: 1.0,
            overlap_seconds: 8.0,
        };
        let aligned = align(&request).unwrap();
        assert_eq!(aligned.status, "ready");
        assert!((aligned.delay_seconds - 0.5).abs() < 0.01);
        let again = align(&AlignmentRequest {
            outgoing_seconds: 8.5,
            ..request
        })
        .unwrap();
        assert_eq!(again.delay_seconds, 0.0);
    }
    #[test]
    fn half_time_is_not_misrepresented_as_parity() {
        let half = pattern(2.0, 4.0);
        assert_eq!(half.sections[0].cadence_beats, 4.0);
        let r = AlignmentRequest {
            outgoing: pattern(1.0, 2.0),
            incoming: half,
            outgoing_seconds: 8.0,
            incoming_seconds: 0.0,
            outgoing_rate: 1.0,
            incoming_rate: 1.0,
            overlap_seconds: 8.0,
        };
        assert_eq!(align(&r).unwrap().status, "incompatible");
    }
    #[test]
    fn half_double_grid_families_can_have_matching_backbeats() {
        for reverse in [false, true] {
            let slow = pattern(1.0, 2.0);
            let mut fast = pattern(2.0, 4.0);
            fast.bpm = 240.0;
            for onset in &mut fast.onsets {
                onset.seconds /= 2.0;
            }
            for section in &mut fast.sections {
                section.start_seconds /= 2.0;
                section.end_seconds /= 2.0;
            }
            let (outgoing, incoming) = if reverse { (fast, slow) } else { (slow, fast) };
            let mut r = AlignmentRequest {
                outgoing,
                incoming,
                outgoing_seconds: 8.0,
                incoming_seconds: 0.0,
                outgoing_rate: 1.0,
                incoming_rate: 1.0,
                overlap_seconds: 8.0,
            };
            assert_eq!(align(&r).unwrap().status, "ready");
            for section in &mut r.incoming.sections {
                section.confidence = 0.1;
            }
            let result = align(&r).unwrap();
            assert_eq!(result.status, "uncertain");
            assert!(result.cycle_seconds > 0.0);
        }
    }

    #[test]
    fn weak_evidence_still_provides_a_cue_preserving_grid_entrance() {
        let mut incoming = pattern(1.0, 2.0);
        for s in &mut incoming.sections {
            s.confidence = 0.1;
        }
        let r = AlignmentRequest {
            outgoing: pattern(0.0, 2.0),
            incoming,
            outgoing_seconds: 8.1,
            incoming_seconds: 0.12,
            outgoing_rate: 1.0,
            incoming_rate: 1.0,
            overlap_seconds: 8.0,
        };
        let result = align(&r).unwrap();
        assert_eq!(result.status, "uncertain");
        assert!((result.delay_seconds - 0.02).abs() < 0.001);
        assert_eq!(r.incoming_seconds, 0.12);
    }
    fn weak_entrance_request() -> AlignmentRequest {
        let mut outgoing = pattern(0.0, 2.0);
        let strong = outgoing.sections[0].clone();
        outgoing.sections = vec![
            Section {
                start_seconds: 0.0,
                end_seconds: 12.0,
                confidence: 0.40,
                ..strong.clone()
            },
            Section {
                start_seconds: 12.0,
                end_seconds: 64.0,
                ..strong
            },
        ];
        AlignmentRequest {
            outgoing,
            incoming: pattern(1.0, 2.0),
            outgoing_seconds: 8.0,
            incoming_seconds: 0.0,
            outgoing_rate: 1.0,
            incoming_rate: 1.0,
            overlap_seconds: 8.0,
        }
    }
    #[test]
    fn reliable_later_overlap_preserves_backbeat_parity_at_weak_entrance() {
        // A weak first section must not throw away the count relationship
        // established by repeated hits later in the SAME audible overlap.
        for anchor in [8.0, 8.2, 8.6, 9.1] {
            let mut r = weak_entrance_request();
            r.outgoing_seconds = anchor;
            let result = align(&r).unwrap();
            let expected = (0.5_f64 - anchor).rem_euclid(1.0);
            assert!(
                (result.delay_seconds - expected).abs() < 0.005,
                "{anchor}: {result:?}"
            );
            assert_eq!(result.cycle_seconds, 1.0);
            assert_eq!(result.status, "uncertain"); // Not whole-overlap certification.
            assert!(result.matched_hits >= 3);
            assert_eq!(r.incoming_seconds, 0.0);
            assert_eq!(r.overlap_seconds, 8.0);
        }
    }
    #[test]
    fn later_evidence_does_not_borrow_drums_outside_the_blend_or_rush_eof() {
        let mut r = weak_entrance_request();
        r.overlap_seconds = 2.0;
        assert_eq!(align(&r).unwrap().delay_seconds, 0.0);
        r.overlap_seconds = 8.0;
        r.outgoing.duration_seconds = 16.1;
        assert_eq!(align(&r).unwrap().delay_seconds, 0.0);
    }
    #[test]
    fn suffix_search_accounts_for_outgoing_audio_during_launch_wait() {
        let mut r = weak_entrance_request();
        r.outgoing_seconds = 8.6;
        r.outgoing.sections[0].end_seconds = 14.25;
        r.outgoing.sections[1].start_seconds = 14.25;
        // Only three matched hits fit: ignoring the outgoing grid wait would
        // discard one and silently select the wrong alternating grid count.
        let result = align(&r).unwrap();
        assert!((result.delay_seconds - 0.9).abs() < 0.005, "{result:?}");
        assert_eq!(result.matched_hits, 3);
        assert_eq!(result.status, "uncertain");
    }
    #[test]
    fn conflicting_confident_counts_are_not_overruled_by_later_drums() {
        let mut r = weak_entrance_request();
        let strong = r.outgoing.sections[1].clone();
        r.outgoing.sections[0].end_seconds = 9.0;
        r.outgoing.sections.insert(
            1,
            Section {
                start_seconds: 9.0,
                end_seconds: 11.0,
                phase_beats: 1.0,
                ..strong
            },
        );
        let result = align(&r).unwrap();
        assert_eq!(result.delay_seconds, 0.0);
        assert_eq!(result.status, "uncertain");
    }
    #[test]
    fn a_short_selected_conflicting_window_is_not_skipped_by_time_sampling() {
        let mut r = weak_entrance_request();
        r.outgoing_seconds = 0.0;
        r.overlap_seconds = 20.0;
        let strong = r.outgoing.sections[1].clone();
        r.outgoing.sections = vec![
            Section {
                start_seconds: 0.0,
                end_seconds: 8.62,
                confidence: 0.1,
                ..strong.clone()
            },
            Section {
                start_seconds: 0.0,
                end_seconds: 8.64,
                phase_beats: 1.0,
                ..strong.clone()
            },
            Section {
                start_seconds: 0.0,
                end_seconds: 8.66,
                confidence: 0.1,
                ..strong.clone()
            },
            Section {
                start_seconds: 8.66,
                end_seconds: 64.0,
                ..strong
            },
        ];
        assert_eq!(section_at(&r.outgoing, 4.32).unwrap().phase_beats, 1.0);
        let result = align(&r).unwrap();
        assert_eq!(result.delay_seconds, 0.0, "{result:?}");
        assert_eq!(result.status, "uncertain");
    }
    #[test]
    fn all_beats_and_drumless_sections_are_uncertain() {
        assert!(pattern(0.0, 1.0).sections[0].confidence < 0.45);
        assert!(
            fit_sections(&[], 120.0, 0.0, 30.0)
                .iter()
                .all(|s| s.confidence == 0.0)
        );
    }
    #[test]
    fn microtiming_is_retained() {
        let r = pattern(1.10, 2.0);
        assert!((r.sections[0].phase_beats - 1.10).abs() < 0.001);
    }
    #[test]
    fn a_single_snare_on_two_is_distinct_from_four() {
        assert!((pattern(1.0, 4.0).sections[0].phase_beats - 1.0).abs() < 0.001);
        assert!((pattern(3.0, 4.0).sections[0].phase_beats - 3.0).abs() < 0.001);
    }

    #[test]
    fn detector_finds_backbeat_beneath_louder_hats_in_pcm() {
        let mut samples = vec![0.0_f32; SR * 40];
        let mut seed = 7_u32;
        for tick in 0..156 {
            let start = SR / 2 + tick * SR / 4;
            for j in 0..SR / 8 {
                let t = j as f32 / SR as f32;
                let tau = std::f32::consts::TAU;
                // Louder hats every eighth-note, kick on 1/3, snare on 2/4.
                let mut value = 2.0 * (tau * 8500.0 * t).sin() * (-t * 100.0).exp();
                if tick % 4 == 0 {
                    value += (tau * 90.0 * t).sin() * (-t * 30.0).exp();
                }
                if tick % 4 == 2 {
                    seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
                    let noise = (seed as f32 / u32::MAX as f32) * 2.0 - 1.0;
                    value += (noise + 0.6 * (tau * 300.0 * t).sin()) * (-t * 45.0).exp();
                }
                samples[start + j] += value;
            }
        }
        let r = analyze_samples(&samples, 120.0, 0.5).unwrap();
        let s = section_at(&r, 10.0).unwrap();
        assert_eq!(s.cadence_beats, 2.0);
        assert!((s.phase_beats - 1.0).abs() < 0.08, "{s:?}");
        assert!(s.confidence > 0.45, "{s:?}");
    }

    #[test]
    fn ghosts_do_not_count_as_a_second_primary_backbeat() {
        let mut r = pattern(1.0, 2.0);
        r.onsets.extend(r.onsets.clone().into_iter().map(|h| Onset {
            seconds: h.seconds + 0.08,
            strength: 0.2,
        }));
        let hits = primary_hits(&r, &r.sections[0], 0.0, 1.0, 8.0);
        assert_eq!(hits.len(), 8);
        assert_eq!(hits[0], 0.5);
    }

    #[test]
    fn losing_drums_mid_blend_is_not_ready() {
        let mut inc = pattern(1.0, 2.0);
        for s in &mut inc.sections {
            if s.start_seconds >= 8.0 {
                s.confidence = 0.0;
            }
        }
        let r = AlignmentRequest {
            outgoing: pattern(1.0, 2.0),
            incoming: inc,
            outgoing_seconds: 0.0,
            incoming_seconds: 0.0,
            outgoing_rate: 1.0,
            incoming_rate: 1.0,
            overlap_seconds: 30.0,
        };
        assert_eq!(align(&r).unwrap().status, "uncertain");
    }

    #[test]
    fn reviewed_downbeats_choose_same_bar_phase() {
        let mut out = pattern(1.0, 2.0);
        let mut inc = pattern(1.0, 2.0);
        out.downbeat_seconds = Some(0.0);
        inc.downbeat_seconds = Some(1.0);
        let r = AlignmentRequest {
            outgoing: out,
            incoming: inc,
            outgoing_seconds: 8.0,
            incoming_seconds: 0.0,
            outgoing_rate: 1.0,
            incoming_rate: 1.0,
            overlap_seconds: 8.0,
        };
        assert!((align(&r).unwrap().delay_seconds - 1.0).abs() < 0.001);
    }
}
