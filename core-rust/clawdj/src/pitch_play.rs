//! Bounded monophonic cue instrument. Python owns original-source validation,
//! deck reservation/setup and final eject/restore; Mixxx owns pitch DSP.
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};

use crate::control_api::{ControlApi, deck_group};

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Note {
    pub beat: f64,
    pub semitones: f64,
    pub gate_beats: f64,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Score {
    pub deck: u8,
    pub bpm: f64,
    pub cue_seconds: f64,
    pub source_end_seconds: f64,
    pub duration_seconds: f64,
    pub sample_rate: f64,
    pub prepare_seconds: f64,
    pub max_late_seconds: f64,
    pub notes: Vec<Note>,
}
#[derive(Debug, Clone, Serialize)]
pub struct Attack {
    pub on_seconds: f64,
    pub off_seconds: f64,
    pub prepare_seconds: f64,
    pub semitones: f64,
    pub frequency_ratio: f64,
    pub cue_seconds: f64,
}
impl Score {
    pub fn compile(&self) -> Result<Vec<Attack>> {
        ensure!((1..=4).contains(&self.deck), "deck must be 1..4");
        ensure!(
            self.bpm.is_finite() && (40.0..=200.0).contains(&self.bpm),
            "bpm must be 40..200"
        );
        ensure!(
            self.duration_seconds.is_finite() && self.duration_seconds > 0.,
            "invalid duration"
        );
        ensure!(
            self.sample_rate.is_finite() && (8000.0..=192000.0).contains(&self.sample_rate),
            "invalid sample rate"
        );
        ensure!(
            self.cue_seconds.is_finite() && self.cue_seconds >= 0.,
            "invalid cue"
        );
        ensure!(
            self.source_end_seconds.is_finite()
                && self.source_end_seconds > self.cue_seconds
                && self.source_end_seconds <= self.duration_seconds,
            "invalid source bounds"
        );
        ensure!(
            self.prepare_seconds.is_finite() && (0.05..=1.0).contains(&self.prepare_seconds),
            "prepare must be 0.05..1 seconds"
        );
        ensure!(
            self.max_late_seconds.is_finite() && (0.001..=0.1).contains(&self.max_late_seconds),
            "lateness must be 0.001..0.1 seconds"
        );
        ensure!(
            !self.notes.is_empty() && self.notes.len() <= 64,
            "need 1..64 notes"
        );
        let beat = 60. / self.bpm;
        let mut previous_off = -1.;
        let mut result = Vec::new();
        for n in &self.notes {
            ensure!(
                n.beat.is_finite() && n.beat >= 0. && n.beat <= 128.,
                "invalid note beat"
            );
            ensure!(
                n.semitones.is_finite() && (-3.0..=3.0).contains(&n.semitones),
                "pitch must be within +/-3 semitones"
            );
            ensure!(
                n.gate_beats.is_finite() && n.gate_beats > 0.,
                "invalid gate"
            );
            let on = self.prepare_seconds + n.beat * beat;
            let off = on + n.gate_beats * beat;
            let prepare = on - self.prepare_seconds;
            ensure!(
                prepare >= previous_off,
                "notes overlap or leave insufficient pitch preparation time"
            );
            ensure!(off <= 200., "experiment exceeds 200 seconds");
            // Extra room for bounded transport lateness before hitting the guard.
            ensure!(
                self.cue_seconds + n.gate_beats * beat + self.max_late_seconds
                    < self.source_end_seconds,
                "gate reaches source boundary"
            );
            result.push(Attack {
                on_seconds: on,
                off_seconds: off,
                prepare_seconds: prepare,
                semitones: n.semitones,
                frequency_ratio: 2_f64.powf(n.semitones / 12.),
                cue_seconds: self.cue_seconds,
            });
            previous_off = off;
        }
        Ok(result)
    }
    pub fn loop_bounds(&self) -> (f64, f64) {
        (
            (self.cue_seconds * self.sample_rate).ceil() * 2.,
            (self.source_end_seconds * self.sample_rate).floor() * 2.,
        )
    }
}

pub trait Controls {
    fn get(&mut self, group: &str, key: &str) -> Result<f64>;
    fn set(&mut self, group: &str, key: &str, value: f64) -> Result<()>;
}
impl Controls for ControlApi {
    fn get(&mut self, g: &str, k: &str) -> Result<f64> {
        ControlApi::get(self, g, k)
    }
    fn set(&mut self, g: &str, k: &str, v: f64) -> Result<()> {
        ControlApi::set(self, g, k, v)
    }
}
pub trait Clock {
    fn now(&self) -> f64;
    fn sleep(&mut self, seconds: f64) -> Result<()>;
}
pub struct MonotonicClock(Instant);
impl Default for MonotonicClock {
    fn default() -> Self {
        Self(Instant::now())
    }
}
impl Clock for MonotonicClock {
    fn now(&self) -> f64 {
        self.0.elapsed().as_secs_f64()
    }
    fn sleep(&mut self, seconds: f64) -> Result<()> {
        std::thread::sleep(Duration::from_secs_f64(seconds));
        Ok(())
    }
}
fn wait(clock: &mut impl Clock, deadline: f64, late: f64) -> Result<()> {
    let remaining = deadline - clock.now();
    if remaining > 0. {
        clock.sleep(remaining)?;
    }
    ensure!(
        clock.now() - deadline <= late,
        "late note; aborting rather than bursting stale attacks"
    );
    Ok(())
}

/// No mutations on invalid score or failed preflight. Once owned, always try
/// both mute and stop even when a previous command/cleanup command fails.
/// Disconnect recovery and SIGINT child termination are the parent's job.
pub fn execute(api: &mut impl Controls, clock: &mut impl Clock, score: &Score) -> Result<()> {
    let attacks = score.compile()?;
    let g = deck_group(score.deck);
    ensure!(api.get("[AutoDJ]", "enabled")? == 0., "AutoDJ is enabled");
    for d in 1..=4 {
        ensure!(api.get(&deck_group(d), "play")? == 0., "a deck is playing");
    }
    for (key, expected) in [
        ("track_loaded", 1.),
        ("mute", 1.),
        ("loop_enabled", 1.),
        ("keylock", 1.),
        ("rate_ratio", 1.),
        ("sync_enabled", 0.),
        ("quantize", 0.),
        ("reverse", 0.),
        ("reverseroll", 0.),
        ("slip_enabled", 0.),
        ("scratch2_enable", 0.),
        ("vinylcontrol_enabled", 0.),
    ] {
        ensure!(
            (api.get(&g, key)? - expected).abs() < 1e-6,
            "unprepared deck control: {key}"
        );
    }
    ensure!(
        (api.get(&g, "duration")? - score.duration_seconds).abs() < 0.001,
        "source duration changed"
    );
    ensure!(
        (api.get(&g, "track_samplerate")? - score.sample_rate).abs() < 0.1,
        "sample rate changed"
    );
    let (a, b) = score.loop_bounds();
    for (key, expected) in [("loop_start_position", a), ("loop_end_position", b)] {
        ensure!(
            (api.get(&g, key)? - expected).abs() < 0.1,
            "source guard mismatch: {key}"
        );
    }
    let epoch = clock.now();
    let outcome = (|| {
        for n in attacks {
            wait(clock, epoch + n.prepare_seconds, score.max_late_seconds)?;
            api.set(&g, "pitch_adjust", n.semitones)?;
            ensure!(
                (api.get(&g, "pitch_adjust")? - n.semitones).abs() < 1e-6,
                "pitch readback mismatch"
            );
            api.set(
                &g,
                "playposition",
                score.cue_seconds / score.duration_seconds,
            )?;
            wait(clock, epoch + n.on_seconds, score.max_late_seconds)?;
            api.set(&g, "mute", 0.)?;
            // No stale attack if the unmute round trip overran its deadline.
            ensure!(
                clock.now() - epoch - n.on_seconds <= score.max_late_seconds,
                "late note-on"
            );
            api.set(&g, "play", 1.)?;
            ensure!(
                clock.now() - epoch - n.on_seconds <= score.max_late_seconds,
                "late play acknowledgement"
            );
            wait(clock, epoch + n.off_seconds, score.max_late_seconds)?;
            api.set(&g, "mute", 1.)?;
            api.set(&g, "play", 0.)?;
        }
        Ok(())
    })();
    let mute = api.set(&g, "mute", 1.);
    let stop = api.set(&g, "play", 0.);
    outcome.and(mute).and(stop)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    fn score() -> Score {
        Score {
            deck: 3,
            bpm: 120.,
            cue_seconds: 10.,
            source_end_seconds: 12.,
            duration_seconds: 100.,
            sample_rate: 44100.,
            prepare_seconds: 0.1,
            max_late_seconds: 0.05,
            notes: [0., 1., 2., 0.]
                .iter()
                .enumerate()
                .map(|(i, p)| Note {
                    beat: i as f64 * 2.,
                    semitones: *p,
                    gate_beats: 0.5,
                })
                .collect(),
        }
    }
    #[derive(Default)]
    struct Fake {
        values: HashMap<String, f64>,
        writes: Vec<(String, f64)>,
        fail_pitch: bool,
    }
    impl Fake {
        fn prepared(s: &Score) -> Self {
            let (a, b) = s.loop_bounds();
            let mut f = Self::default();
            for (k, v) in [
                ("track_loaded", 1.),
                ("mute", 1.),
                ("loop_enabled", 1.),
                ("keylock", 1.),
                ("rate_ratio", 1.),
                ("duration", s.duration_seconds),
                ("track_samplerate", s.sample_rate),
                ("loop_start_position", a),
                ("loop_end_position", b),
            ] {
                f.values.insert(k.into(), v);
            }
            f
        }
    }
    impl Controls for Fake {
        fn get(&mut self, _: &str, k: &str) -> Result<f64> {
            Ok(*self.values.get(k).unwrap_or(&0.))
        }
        fn set(&mut self, _: &str, k: &str, v: f64) -> Result<()> {
            self.writes.push((k.into(), v));
            ensure!(!(self.fail_pitch && k == "pitch_adjust"), "disconnect");
            self.values.insert(k.into(), v);
            Ok(())
        }
    }
    #[derive(Default)]
    struct FakeClock {
        time: f64,
        oversleep: f64,
        cancel: bool,
    }
    impl Clock for FakeClock {
        fn now(&self) -> f64 {
            self.time
        }
        fn sleep(&mut self, s: f64) -> Result<()> {
            ensure!(!self.cancel, "cancelled");
            self.time += s + self.oversleep;
            Ok(())
        }
    }
    #[test]
    fn score_math_and_absolute_pitch() {
        for bpm in [60., 90., 120.] {
            let mut s = score();
            s.bpm = bpm;
            let a = s.compile().unwrap();
            assert!((a[1].on_seconds - (0.1 + 120. / bpm)).abs() < 1e-10);
            assert_eq!(a[3].semitones, 0.);
            assert!((a[2].frequency_ratio - 2_f64.powf(2. / 12.)).abs() < 1e-10);
        }
    }
    #[test]
    fn reject_bad_scores() {
        for change in 0..10 {
            let mut s = score();
            match change {
                0 => s.bpm = f64::NAN,
                1 => s.notes[0].semitones = 4.,
                2 => s.notes[0].gate_beats = 0.,
                3 => s.notes[1].beat = 0.,
                4 => s.cue_seconds = -1.,
                5 => s.source_end_seconds = 10.1,
                6 => s.deck = 0,
                7 => s.notes[0].beat = f64::INFINITY,
                8 => s.notes.clear(),
                _ => s.notes[0].gate_beats = f64::NAN,
            }
            assert!(s.compile().is_err(), "case {change}");
        }
    }
    #[test]
    fn schedule_and_gate_pairing() {
        let s = score();
        let mut f = Fake::prepared(&s);
        let mut c = FakeClock::default();
        execute(&mut f, &mut c, &s).unwrap();
        let pitch: Vec<_> = f
            .writes
            .iter()
            .filter(|(k, _)| k == "pitch_adjust")
            .map(|(_, v)| *v)
            .collect();
        assert_eq!(pitch, vec![0., 1., 2., 0.]);
        assert_eq!(
            f.writes
                .iter()
                .filter(|(k, v)| k == "play" && *v == 1.)
                .count(),
            4
        );
        assert_eq!(f.values["play"], 0.);
        assert_eq!(f.values["mute"], 1.);
        assert!((c.time - 3.35).abs() < 1e-9);
    }
    #[test]
    fn refusal_has_no_writes() {
        for key in [
            "play",
            "loop_end_position",
            "mute",
            "duration",
            "rate_ratio",
        ] {
            let s = score();
            let mut f = Fake::prepared(&s);
            f.values.insert(key.into(), 999.);
            assert!(execute(&mut f, &mut FakeClock::default(), &s).is_err());
            assert!(f.writes.is_empty());
        }
    }
    #[test]
    fn lateness_cancellation_disconnect_cleanup_no_burst() {
        for mode in 0..3 {
            let s = score();
            let mut f = Fake::prepared(&s);
            let mut c = FakeClock::default();
            match mode {
                0 => c.oversleep = 0.2,
                1 => c.cancel = true,
                _ => f.fail_pitch = true,
            }
            assert!(execute(&mut f, &mut c, &s).is_err());
            assert!(!f.writes.iter().any(|(k, v)| k == "play" && *v == 1.));
            assert_eq!(
                f.writes[f.writes.len() - 2..],
                [("mute".into(), 1.), ("play".into(), 0.)]
            );
        }
    }
    #[test]
    fn slow_control_acknowledgements_abort_without_a_note_burst() {
        use std::{cell::Cell, rc::Rc};
        struct SharedClock(Rc<Cell<f64>>);
        impl Clock for SharedClock {
            fn now(&self) -> f64 {
                self.0.get()
            }
            fn sleep(&mut self, seconds: f64) -> Result<()> {
                self.0.set(self.0.get() + seconds);
                Ok(())
            }
        }
        struct Slow {
            inner: Fake,
            time: Rc<Cell<f64>>,
            delay_key: &'static str,
        }
        impl Controls for Slow {
            fn get(&mut self, g: &str, k: &str) -> Result<f64> {
                self.inner.get(g, k)
            }
            fn set(&mut self, g: &str, k: &str, v: f64) -> Result<()> {
                if k == self.delay_key && ((k == "mute" && v == 0.) || (k == "play" && v == 1.)) {
                    self.time.set(self.time.get() + 0.2);
                }
                self.inner.set(g, k, v)
            }
        }
        for key in ["mute", "play"] {
            let s = score();
            let time = Rc::new(Cell::new(0.));
            let mut api = Slow {
                inner: Fake::prepared(&s),
                time: time.clone(),
                delay_key: key,
            };
            assert!(execute(&mut api, &mut SharedClock(time), &s).is_err());
            let starts = api
                .inner
                .writes
                .iter()
                .filter(|(k, v)| k == "play" && *v == 1.)
                .count();
            assert_eq!(starts, usize::from(key == "play"));
            assert_eq!(api.inner.values["play"], 0.);
            assert_eq!(api.inner.values["mute"], 1.);
        }
    }
    #[test]
    fn failed_mute_cleanup_still_attempts_stop() {
        struct Broken(Fake);
        impl Controls for Broken {
            fn get(&mut self, g: &str, k: &str) -> Result<f64> {
                self.0.get(g, k)
            }
            fn set(&mut self, g: &str, k: &str, v: f64) -> Result<()> {
                if k == "mute" {
                    anyhow::bail!("mute disconnected");
                }
                self.0.set(g, k, v)
            }
        }
        let s = score();
        let mut api = Broken(Fake::prepared(&s));
        assert!(execute(&mut api, &mut FakeClock::default(), &s).is_err());
        assert_eq!(api.0.writes.last(), Some(&("play".into(), 0.)));
    }
    #[test]
    fn small_sleep_errors_do_not_accumulate() {
        let s = score();
        let mut f = Fake::prepared(&s);
        let mut c = FakeClock {
            oversleep: 0.005,
            ..Default::default()
        };
        execute(&mut f, &mut c, &s).unwrap();
        assert!((c.time - 3.355).abs() < 1e-9);
    }
}
