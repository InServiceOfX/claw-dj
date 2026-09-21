//! Original-source timeline executor. Mixxx owns audio/DSP; Rust owns timing.
//! The Python compiler validates musical constraints before invoking this layer.
use crate::control_api::{ControlApi, deck_group};
use anyhow::{Context, Result, bail, ensure};
use serde::Deserialize;
use std::{
    collections::HashMap,
    thread,
    time::{Duration, Instant},
};

#[derive(Clone, Debug, Deserialize)]
pub struct Segment {
    pub source_start: f64,
    pub source_end: f64,
    pub local_start: f64,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Gap {
    pub start: f64,
    pub end: f64,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Support {
    pub takeover_seconds: f64,
    pub transition_seconds: f64,
    pub low_gain: f64,
    pub high_gain: f64,
    pub pulse_gain: f64,
    pub pulse_width_seconds: f64,
    pub pulse_times: Vec<f64>,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Clip {
    pub id: String,
    pub path: String,
    pub deck: u8,
    pub load_at: f64,
    pub start: f64,
    pub length: f64,
    pub rate: f64,
    pub gain_db: f64,
    pub fade_in: f64,
    pub fade_out: f64,
    pub segments: Vec<Segment>,
    #[serde(default)]
    pub skip_fills: Vec<Gap>,
    pub live_eq: [f64; 3],
    pub support: Option<Support>,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Loop {
    pub source_start: f64,
    pub source_end: f64,
    pub rate: f64,
}
#[derive(Clone, Debug, Deserialize)]
pub struct Performance {
    pub tempo_bpm: f64,
    pub global_pattern_zero_seconds: f64,
    #[serde(rename = "loop")]
    pub loop_region: Option<Loop>,
    pub clips: Vec<Clip>,
}
#[derive(Clone, Copy, Debug)]
struct SourceState {
    position: f64,
    start: f64,
    end: f64,
    section: usize,
}
const LOOP: usize = usize::MAX;
fn smooth(x: f64) -> f64 {
    let x = x.clamp(0., 1.);
    x * x * (3. - 2. * x)
}

impl Performance {
    fn validate(&self) -> Result<()> {
        ensure!(
            !self.clips.is_empty() && self.tempo_bpm.is_finite() && self.tempo_bpm > 0.,
            "Invalid timeline"
        );
        let mut ids = std::collections::HashSet::new();
        for c in &self.clips {
            ensure!(ids.insert(&c.id), "Duplicate clip ID");
            ensure!(
                (1..=4).contains(&c.deck)
                    && c.start >= 0.
                    && c.length > 0.
                    && c.load_at >= 0.
                    && c.load_at <= c.start,
                "Invalid deck/placement"
            );
            ensure!(
                c.rate > 0. && c.rate <= 4. && 10_f64.powf(c.gain_db / 20.) <= 4.,
                "Invalid native gain/rate"
            );
            ensure!(
                c.live_eq.iter().all(|x| (0. ..=4.).contains(x)),
                "Invalid EQ gain"
            );
            ensure!(
                c.fade_in >= 0.
                    && c.fade_out >= 0.
                    && c.fade_in <= c.length
                    && c.fade_out <= c.length,
                "Invalid fades"
            );
            ensure!(
                !c.segments.is_empty() && c.segments[0].local_start == 0.,
                "Missing initial source segment"
            );
            for s in &c.segments {
                ensure!(
                    s.source_start >= 0. && s.source_end > s.source_start && s.local_start >= 0.,
                    "Invalid source span"
                );
            }
            if let Some(s) = &c.support {
                ensure!(
                    s.transition_seconds > 0.
                        && s.pulse_width_seconds > 0.
                        && s.takeover_seconds >= 0.,
                    "Invalid support envelope"
                );
                let l = self
                    .loop_region
                    .as_ref()
                    .context("Support requires a loop")?;
                ensure!(
                    l.source_start >= 0.
                        && l.source_end > l.source_start
                        && (l.rate - c.rate).abs() < 1e-8,
                    "Invalid support loop/rate"
                );
            }
        }
        for (i, a) in self.clips.iter().enumerate() {
            for b in &self.clips[i + 1..] {
                if a.deck == b.deck {
                    ensure!(
                        a.start + a.length <= b.load_at || b.start + b.length <= a.load_at,
                        "Deck preload overlaps an active source"
                    );
                }
            }
        }
        Ok(())
    }
    fn source(&self, c: &Clip, local: f64) -> Option<SourceState> {
        if c.support
            .as_ref()
            .is_some_and(|s| local >= s.takeover_seconds)
        {
            let l = self.loop_region.as_ref()?;
            return Some(SourceState {
                position: l.source_start
                    + ((c.start + local - self.global_pattern_zero_seconds) * l.rate)
                        .rem_euclid(l.source_end - l.source_start),
                start: l.source_start,
                end: l.source_end,
                section: LOOP,
            });
        }
        c.segments.iter().enumerate().find_map(|(i, s)| {
            (local >= s.local_start
                && local < s.local_start + (s.source_end - s.source_start) / c.rate)
                .then_some(SourceState {
                    position: s.source_start + (local - s.local_start) * c.rate,
                    start: s.source_start,
                    end: s.source_end,
                    section: i,
                })
        })
    }
    fn envelope(&self, c: &Clip, local: f64) -> f64 {
        if local < 0. || local >= c.length {
            return 0.;
        }
        let mut v = if c.fade_in > 0. {
            smooth(local / c.fade_in)
        } else {
            1.
        };
        if c.fade_out > 0. {
            v *= smooth((c.length - local) / c.fade_out);
        }
        let edge = 120. / self.tempo_bpm;
        for g in &c.skip_fills {
            v *= 1.
                - smooth((local - g.start + edge) / edge) * smooth((g.end + edge - local) / edge);
        }
        v
    }
    fn eq(&self, c: &Clip, local: f64) -> [f64; 3] {
        let Some(s) = &c.support else {
            return c.live_eq;
        };
        let alpha = smooth((local - s.takeover_seconds) / s.transition_seconds);
        let upper = s.high_gain
            + s.pulse_times
                .iter()
                .map(|t| {
                    s.pulse_gain
                        * (1. - (c.start + local - t).abs() / s.pulse_width_seconds).max(0.)
                })
                .sum::<f64>();
        let target = [s.low_gain, upper, upper];
        std::array::from_fn(|i| c.live_eq[i] + (target[i] - c.live_eq[i]) * alpha)
    }
}

#[derive(Clone, Copy)]
struct Asset {
    duration: f64,
    sample_rate: f64,
}
fn set_loop(api: &mut ControlApi, deck: u8, start: f64, end: f64, sr: f64) -> Result<()> {
    // Mixxx engine sample positions are stereo samples, not source frames.
    let a = (start * sr - 1e-7).ceil() * 2.;
    let b = (end * sr + 1e-7).floor() * 2.;
    ensure!(b > a, "Empty source guard loop");
    let g = deck_group(deck);
    api.set(&g, "loop_enabled", 0.)?;
    api.set(&g, "loop_start_position", a)?;
    api.set(&g, "loop_end_position", b)?;
    ensure!(
        (api.get(&g, "loop_start_position")? - a).abs() <= 2.
            && (api.get(&g, "loop_end_position")? - b).abs() <= 2.,
        "Mixxx rejected exact source guard bounds"
    );
    api.set(&g, "loop_enabled", 1.)?;
    ensure!(
        api.get(&g, "loop_enabled")? > 0.5,
        "Source guard loop inactive"
    );
    Ok(())
}
fn load(port: u16, p: &Performance, c: &Clip) -> Result<Asset> {
    let mut api = ControlApi::connect(port)?;
    let g = deck_group(c.deck);
    let t = Instant::now();
    for (k, v) in [("volume", 0.), ("play", 0.), ("loop_enabled", 0.)] {
        api.set(&g, k, v)?;
    }
    // Eject is a button edge; pressing it on an empty deck recalls old audio.
    if api.get(&g, "track_loaded")? > 0.5 {
        api.set(&g, "eject", 0.)?;
        api.set(&g, "eject", 1.)?;
        api.set(&g, "eject", 0.)?;
    }
    while api.get(&g, "track_loaded")? > 0.5 {
        ensure!(t.elapsed().as_secs_f64() < 25., "Source deck did not eject");
        thread::sleep(Duration::from_millis(20));
    }
    api.load(c.deck, &c.path, false)?;
    while api.get(&g, "track_loaded")? < 0.5 || api.get(&g, "duration")? <= 0. {
        ensure!(t.elapsed().as_secs_f64() < 25., "Source track did not load");
        thread::sleep(Duration::from_millis(20));
    }
    let asset = Asset {
        duration: api.get(&g, "duration")?,
        sample_rate: api.get(&g, "track_samplerate")?,
    };
    ensure!(
        asset.sample_rate > 0.
            && c.segments
                .iter()
                .all(|s| s.source_end <= asset.duration + 0.001),
        "Source span exceeds recording"
    );
    if c.support.is_some() {
        ensure!(
            p.loop_region.as_ref().unwrap().source_end <= asset.duration,
            "Loop exceeds recording"
        );
    }
    for (k, v) in [
        ("sync_enabled", 0.),
        ("keylock", 0.),
        ("quantize", 0.),
        ("pitch_adjust", 0.),
        ("rate_ratio", c.rate),
        ("volume", 0.),
        ("pregain", 10_f64.powf(c.gain_db / 20.)),
    ] {
        api.set(&g, k, v)?;
    }
    ensure!(
        (api.get(&g, "rate_ratio")? - c.rate).abs() < 1e-5,
        "Native rate rejected"
    );
    let source = p.source(c, 0.).context("Missing initial source position")?;
    set_loop(
        &mut api,
        c.deck,
        source.start,
        source.end,
        asset.sample_rate,
    )?;
    api.set(&g, "playposition", source.position / asset.duration)?;
    let mut stable = None;
    while t.elapsed().as_secs_f64() < 25. {
        if (api.get(&g, "playposition")? * asset.duration - source.position).abs() > 0.015 {
            api.set(&g, "playposition", source.position / asset.duration)?;
            stable = None;
        } else if stable.is_none() {
            stable = Some(Instant::now());
        } else if stable.unwrap().elapsed().as_secs_f64() >= 0.5 {
            return Ok(asset);
        }
        thread::sleep(Duration::from_millis(20));
    }
    bail!("Source cue did not settle after cue recall")
}
fn stop(api: &mut ControlApi, p: &Performance) {
    for d in 1..=4 {
        if p.clips.iter().any(|c| c.deck == d) {
            for (k, v) in [("volume", 0.), ("play", 0.), ("loop_enabled", 0.)] {
                let _ = api.set(&deck_group(d), k, v);
            }
        }
    }
}

/// Run a validated native timeline. The caller owns mixer setup/restoration.
pub fn run(port: u16, p: Performance) -> Result<()> {
    p.validate()?;
    let mut api = ControlApi::connect(port)?;
    for d in 1..=4 {
        if p.clips.iter().any(|c| c.deck == d) {
            ensure!(
                api.get(&deck_group(d), "play")? < 0.5,
                "Deck {d} is already playing"
            );
        }
    }
    let mut workers: HashMap<usize, thread::JoinHandle<Result<Asset>>> = HashMap::new();
    let outcome = (|| -> Result<()> {
        let n = p.clips.len();
        let mut assets = vec![None; n];
        let mut started = vec![false; n];
        let mut finished = vec![false; n];
        let mut section = vec![None; n];
        let mut volumes = vec![-1.; n];
        let mut eqs = vec![[-1.; 3]; n];
        let mut checks = vec![Instant::now(); n];
        let mut max_error: f64 = 0.;
        // Preload every initial deck before starting the shared monotonic clock.
        for (i, c) in p.clips.iter().enumerate() {
            if c.load_at == 0. {
                assets[i] = Some(load(port, &p, c)?);
            }
        }
        let origin = Instant::now();
        while finished.iter().any(|v| !*v) {
            let elapsed = origin.elapsed().as_secs_f64();
            for (i, c) in p.clips.iter().enumerate() {
                let g = deck_group(c.deck);
                if finished[i] {
                    continue;
                }
                if started[i] && elapsed >= c.start + c.length - 0.04 {
                    api.set(&g, "volume", 0.)?;
                    api.set(&g, "play", 0.)?;
                    finished[i] = true;
                    println!("stop deck {}: {}", c.deck, c.id);
                    continue;
                }
                if assets[i].is_none() && !workers.contains_key(&i) && elapsed >= c.load_at {
                    let pc = p.clone();
                    let cc = c.clone();
                    workers.insert(i, thread::spawn(move || load(port, &pc, &cc)));
                }
                if elapsed < c.start {
                    continue;
                }
                if !started[i] {
                    if assets[i].is_none() {
                        ensure!(
                            workers.get(&i).is_some_and(|w| w.is_finished()),
                            "{}: source preload missed start",
                            c.id
                        );
                        assets[i] = Some(
                            workers
                                .remove(&i)
                                .unwrap()
                                .join()
                                .map_err(|_| anyhow::anyhow!("Loader panicked"))??,
                        );
                    }
                    ensure!(
                        origin.elapsed().as_secs_f64() - c.start < 0.2,
                        "{}: missed start",
                        c.id
                    );
                    started[i] = true;
                    println!("start deck {}: {} (original source)", c.deck, c.id);
                }
                let asset = assets[i].unwrap();
                let local = origin.elapsed().as_secs_f64() - c.start;
                let desired = p.source(c, local);
                let approaching = desired.is_some_and(|s| {
                    s.section != LOOP
                        && s.section + 1 < c.segments.len()
                        && (s.end - s.position) / c.rate < 0.06
                });
                if desired.is_none() || approaching {
                    if section[i].is_some() {
                        api.set(&g, "volume", 0.)?;
                        api.set(&g, "play", 0.)?;
                        section[i] = None;
                        volumes[i] = -1.;
                    }
                    continue;
                }
                let s = desired.unwrap();
                if section[i] != Some(s.section) {
                    api.set(&g, "volume", 0.)?;
                    api.set(&g, "play", 0.)?;
                    volumes[i] = -1.;
                    set_loop(&mut api, c.deck, s.start, s.end, asset.sample_rate)?;
                    let Some(fresh) = p.source(c, origin.elapsed().as_secs_f64() - c.start) else {
                        continue;
                    };
                    api.set(&g, "playposition", fresh.position / asset.duration)?;
                    api.set(&g, "play", 1.)?;
                    let actual = api.get(&g, "playposition")? * asset.duration;
                    if let Some(fresh) = p.source(c, origin.elapsed().as_secs_f64() - c.start) {
                        if (actual - fresh.position).abs() > 0.015 {
                            api.set(&g, "playposition", fresh.position / asset.duration)?;
                        }
                    }
                    section[i] = Some(s.section);
                    checks[i] = Instant::now();
                    println!(
                        "  deck {}: source {:.3}s; guard {:.3}..{:.3}s",
                        c.deck, fresh.position, s.start, s.end
                    );
                }
                let local = origin.elapsed().as_secs_f64() - c.start;
                let volume = p.envelope(c, local);
                if (volume - volumes[i]).abs() > 0.002
                    || (volume == 0. || volume == 1.) && volume != volumes[i]
                {
                    api.set(&g, "volume", volume)?;
                    volumes[i] = volume;
                }
                let eq = p.eq(c, local);
                if eq.iter().zip(eqs[i]).any(|(a, b)| (a - b).abs() > 0.005) {
                    for (j, v) in eq.iter().enumerate() {
                        api.set(
                            &format!("[EqualizerRack1_{g}_Effect1]"),
                            &format!("parameter{}", j + 1),
                            *v,
                        )?;
                    }
                    eqs[i] = eq;
                }
                if checks[i].elapsed().as_secs_f64() > 0.5 {
                    let before = origin.elapsed().as_secs_f64();
                    let actual = api.get(&g, "playposition")? * asset.duration;
                    let after = origin.elapsed().as_secs_f64();
                    if let Some(target) = p.source(c, (before + after) / 2. - c.start) {
                        let mut error = (actual - target.position).abs() / c.rate;
                        if target.section == LOOP {
                            let period = (target.end - target.start) / c.rate;
                            error = error.min((period - error).abs());
                        }
                        max_error = max_error.max(error);
                        ensure!(
                            error < 0.08 && api.get(&g, "play")? > 0.5,
                            "{}: live source drift {error:.3}s or unexpected stop",
                            c.id
                        );
                    }
                    checks[i] = Instant::now();
                }
            }
            thread::sleep(Duration::from_millis(10));
        }
        println!("Native performance complete; maximum observed position error {max_error:.6}s");
        Ok(())
    })();
    // Silence immediately on failure, then wait for loaders and stop again.
    stop(&mut api, &p);
    for (_, w) in workers {
        let _ = w.join();
    }
    stop(&mut api, &p);
    outcome
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Performance {
        serde_json::from_value(serde_json::json!({"tempo_bpm":120.,"global_pattern_zero_seconds":0.,"loop":{"source_start":10.,"source_end":14.,"rate":1.},"clips":[{"id":"voice","path":"original.wav","deck":1,"load_at":0.,"start":0.,"length":8.,"rate":1.,"gain_db":0.,"fade_in":1.,"fade_out":1.,"segments":[{"source_start":10.,"source_end":13.,"local_start":0.},{"source_start":16.,"source_end":20.,"local_start":4.}],"skip_fills":[{"start":3.,"end":4.}],"live_eq":[0.4,1.,1.]}]})).unwrap()
    }
    #[test]
    fn excluded_regions_never_resolve_to_source() {
        let p = fixture();
        let c = &p.clips[0];
        assert!(p.source(c, 3.5).is_none());
        assert_eq!(p.source(c, 4.).unwrap().position, 16.);
        assert!(p.source(c, 8.).is_none());
    }
    #[test]
    fn skip_cover_and_fades_are_continuous() {
        let p = fixture();
        let c = &p.clips[0];
        assert_eq!(p.envelope(c, 0.), 0.);
        assert_eq!(p.envelope(c, 3.5), 0.);
        assert!((p.envelope(c, 2.5) - 0.5).abs() < 1e-12);
        assert_eq!(p.envelope(c, 5.), 1.);
        assert!((p.envelope(c, 7.5) - 0.5).abs() < 1e-12);
    }
    #[test]
    fn overlapping_deck_load_is_rejected() {
        let mut p = fixture();
        let mut c = p.clips[0].clone();
        c.id = "other".into();
        c.start = 4.;
        p.clips.push(c);
        assert!(p.validate().is_err());
    }
    #[test]
    fn loop_uses_common_clock_not_entry_time() {
        let mut p = fixture();
        p.clips[0].support = Some(Support {
            takeover_seconds: 0.,
            transition_seconds: 1.,
            low_gain: 0.8,
            high_gain: 0.1,
            pulse_gain: 0.,
            pulse_width_seconds: 1.,
            pulse_times: vec![],
        });
        assert_eq!(p.source(&p.clips[0], 5.5).unwrap().position, 11.5);
        assert!((p.eq(&p.clips[0], 2.)[0] - 0.8).abs() < 1e-12);
    }
}
