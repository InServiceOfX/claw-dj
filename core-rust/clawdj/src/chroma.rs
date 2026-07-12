//! Lightweight chromagram fingerprints for a *small* ordered playlist.
//!
//! Not for full-crate scanning. Decodes a short mono prefix of each file
//! (default ~45s) with Symphonia, folds a coarse STFT into 12 pitch-class
//! bins, L2-normalizes, and writes a cosine-similarity matrix as JSON.

use std::{
    fs::File,
    path::{Path, PathBuf},
};

use anyhow::{Context, Result, bail};
use realfft::RealFftPlanner;
use serde::Serialize;
use symphonia::core::{
    audio::SampleBuffer,
    codecs::DecoderOptions,
    formats::FormatOptions,
    io::MediaSourceStream,
    meta::MetadataOptions,
    probe::Hint,
};

const TARGET_SR: u32 = 11_025;
const FRAME: usize = 2048;
const HOP: usize = 1024;
const MAX_SECONDS: f32 = 45.0;

#[derive(Debug, Serialize)]
pub struct ChromaReport {
    pub version: u32,
    pub track_count: usize,
    pub sample_rate: u32,
    pub frame_size: usize,
    pub max_seconds: f32,
    pub paths: Vec<String>,
    pub fingerprints: Vec<Vec<f32>>,
    pub similarity: Vec<Vec<f32>>,
}

pub fn analyze_paths(paths: &[PathBuf]) -> Result<ChromaReport> {
    let mut fingerprints = Vec::with_capacity(paths.len());
    let mut ok_paths = Vec::with_capacity(paths.len());
    for path in paths {
        match fingerprint_file(path) {
            Ok(fp) => {
                fingerprints.push(fp);
                ok_paths.push(path.display().to_string());
            }
            Err(error) => {
                eprintln!("chroma skip {}: {error:#}", path.display());
            }
        }
    }
    if fingerprints.is_empty() {
        bail!("no tracks produced a chromagram fingerprint");
    }
    let n = fingerprints.len();
    let mut similarity = vec![vec![0.0_f32; n]; n];
    for i in 0..n {
        for j in 0..n {
            similarity[i][j] = if i == j {
                1.0
            } else {
                cosine(&fingerprints[i], &fingerprints[j])
            };
        }
    }
    Ok(ChromaReport {
        version: 1,
        track_count: n,
        sample_rate: TARGET_SR,
        frame_size: FRAME,
        max_seconds: MAX_SECONDS,
        paths: ok_paths,
        fingerprints,
        similarity,
    })
}

fn fingerprint_file(path: &Path) -> Result<Vec<f32>> {
    let samples = decode_mono_prefix(path, TARGET_SR, MAX_SECONDS)?;
    if samples.len() < FRAME {
        bail!("audio too short ({} samples)", samples.len());
    }
    let mut planner = RealFftPlanner::<f32>::new();
    let fft = planner.plan_fft_forward(FRAME);
    let mut scratch = fft.make_scratch_vec();
    let mut spectrum = fft.make_output_vec();
    let mut chroma = [0.0_f32; 12];
    let mut frames = 0_u32;

    let mut start = 0;
    while start + FRAME <= samples.len() {
        let mut input: Vec<f32> = samples[start..start + FRAME]
            .iter()
            .enumerate()
            .map(|(i, sample)| {
                // Hann window
                let w = 0.5
                    - 0.5 * (std::f32::consts::TAU * i as f32 / (FRAME as f32 - 1.0)).cos();
                sample * w
            })
            .collect();
        fft.process_with_scratch(&mut input, &mut spectrum, &mut scratch)
            .map_err(|error| anyhow::anyhow!("fft failed: {error:?}"))?;

        // Fold magnitude spectrum into pitch classes (ignore DC / very low bins).
        let bin_hz = TARGET_SR as f32 / FRAME as f32;
        for (bin, complex) in spectrum.iter().enumerate().skip(2) {
            let mag = (complex.re * complex.re + complex.im * complex.im).sqrt();
            if mag <= 0.0 {
                continue;
            }
            let freq = bin as f32 * bin_hz;
            if !(80.0..=4_000.0).contains(&freq) {
                continue;
            }
            let midi = 69.0 + 12.0 * (freq / 440.0).log2();
            if !midi.is_finite() {
                continue;
            }
            let pc = ((midi.round() as i32).rem_euclid(12)) as usize;
            chroma[pc] += mag;
        }
        frames += 1;
        start += HOP;
    }
    if frames == 0 {
        bail!("no analysis frames");
    }
    for value in &mut chroma {
        *value /= frames as f32;
    }
    let norm = chroma.iter().map(|v| v * v).sum::<f32>().sqrt().max(1e-9);
    Ok(chroma.iter().map(|v| v / norm).collect())
}

fn decode_mono_prefix(path: &Path, target_sr: u32, max_seconds: f32) -> Result<Vec<f32>> {
    let file = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mss = MediaSourceStream::new(Box::new(file), Default::default());
    let mut hint = Hint::new();
    if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
        hint.with_extension(ext);
    }
    let probed = symphonia::default::get_probe()
        .format(
            &hint,
            mss,
            &FormatOptions::default(),
            &MetadataOptions::default(),
        )
        .context("probe audio")?;
    let mut format = probed.format;
    let track = format
        .default_track()
        .context("no default audio track")?
        .clone();
    let mut decoder = symphonia::default::get_codecs()
        .make(&track.codec_params, &DecoderOptions::default())
        .context("create decoder")?;
    let sr = track
        .codec_params
        .sample_rate
        .context("missing sample rate")?;
    let channels = track
        .codec_params
        .channels
        .context("missing channel layout")?
        .count();
    let max_samples = (max_seconds * target_sr as f32) as usize;
    let mut mono: Vec<f32> = Vec::with_capacity(max_samples);
    let mut sample_buf: Option<SampleBuffer<f32>> = None;

    loop {
        if mono.len() >= max_samples {
            break;
        }
        let packet = match format.next_packet() {
            Ok(packet) => packet,
            Err(_) => break,
        };
        if packet.track_id() != track.id {
            continue;
        }
        let decoded = match decoder.decode(&packet) {
            Ok(audio) => audio,
            Err(_) => continue,
        };
        if sample_buf.is_none() {
            let spec = *decoded.spec();
            let duration = decoded.capacity() as u64;
            sample_buf = Some(SampleBuffer::<f32>::new(duration, spec));
        }
        let buf = sample_buf.as_mut().unwrap();
        buf.copy_interleaved_ref(decoded);
        let samples = buf.samples();
        // Downmix + crude integer decimation toward target_sr.
        let decim = (sr / target_sr).max(1) as usize;
        let mut i = 0;
        while i + channels <= samples.len() {
            if (i / channels) % decim == 0 {
                let mut acc = 0.0_f32;
                for c in 0..channels {
                    acc += samples[i + c];
                }
                mono.push(acc / channels as f32);
                if mono.len() >= max_samples {
                    break;
                }
            }
            i += channels;
        }
    }
    Ok(mono)
}

fn cosine(a: &[f32], b: &[f32]) -> f32 {
    let mut dot = 0.0;
    let mut na = 0.0;
    let mut nb = 0.0;
    for (x, y) in a.iter().zip(b.iter()) {
        dot += x * y;
        na += x * x;
        nb += y * y;
    }
    let denom = na.sqrt() * nb.sqrt();
    if denom <= 1e-9 {
        0.0
    } else {
        (dot / denom).clamp(0.0, 1.0)
    }
}

#[cfg(test)]
mod tests {
    use super::cosine;

    #[test]
    fn cosine_identical() {
        assert!((cosine(&[1.0, 0.0], &[1.0, 0.0]) - 1.0).abs() < 1e-5);
    }
}
