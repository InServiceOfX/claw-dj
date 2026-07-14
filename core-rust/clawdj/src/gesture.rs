//! Beat-accurate DJ gestures over the Mixxx control API — the inner timing
//! loops where Rust earns its keep (sub-beat resolution, no GC jitter).
//!
//! Each gesture is deterministic and self-contained: given a connected
//! `ControlApi` it performs one audible move and restores any state it
//! toggled. The Python plan runner (or `clawdj gesture …`) orchestrates.
//! Vocabulary and control references: docs/MIXXX_CONTROL_SURFACE.md.

use std::thread::sleep;
use std::time::{Duration, Instant};

use anyhow::Result;

use crate::control_api::{BeatWaiter, ControlApi, deck_group};

const STEP: Duration = Duration::from_millis(10);

fn eq_group(deck: u8) -> String {
    format!("[EqualizerRack1_[Channel{deck}]_Effect1]")
}

/// Turntable brake: the platter slows to a stop over `seconds`.
/// Leaves the deck paused (that's the point of a brake).
pub fn brake(api: &mut ControlApi, deck: u8, seconds: f64) -> Result<()> {
    let group = deck_group(deck);
    api.set(&group, "scratch2_enable", 1.0)?;
    let t0 = Instant::now();
    loop {
        let progress = (t0.elapsed().as_secs_f64() / seconds).min(1.0);
        // Quadratic ease-out reads as a heavy platter, not a linear fade.
        let velocity = (1.0 - progress) * (1.0 - progress);
        api.set(&group, "scratch2", velocity)?;
        if progress >= 1.0 {
            break;
        }
        sleep(STEP);
    }
    api.set(&group, "play", 0.0)?;
    api.set(&group, "scratch2_enable", 0.0)?;
    api.set(&group, "scratch2", 0.0)?;
    Ok(())
}

/// Spinback: the platter is thrown backwards, accelerating in reverse,
/// then stops. `intensity` is the peak reverse speed (3–6 sounds classic).
pub fn spinback(api: &mut ControlApi, deck: u8, seconds: f64, intensity: f64) -> Result<()> {
    let group = deck_group(deck);
    api.set(&group, "scratch2_enable", 1.0)?;
    let t0 = Instant::now();
    loop {
        let progress = (t0.elapsed().as_secs_f64() / seconds).min(1.0);
        // Fast flip into reverse, then decay back toward zero.
        let velocity = if progress < 0.25 {
            1.0 - progress / 0.25 * (1.0 + intensity)
        } else {
            -intensity * (1.0 - (progress - 0.25) / 0.75)
        };
        api.set(&group, "scratch2", velocity)?;
        if progress >= 1.0 {
            break;
        }
        sleep(STEP);
    }
    api.set(&group, "play", 0.0)?;
    api.set(&group, "scratch2_enable", 0.0)?;
    api.set(&group, "scratch2", 0.0)?;
    Ok(())
}

/// Kill-switch bass swap, anchored on the outgoing deck's next beat:
/// the incoming deck takes the low end in one instant toggle.
pub fn kill_swap(api: &mut ControlApi, from_deck: u8, to_deck: u8, port: u16) -> Result<()> {
    // Pre-kill the incoming lows so both basses never stack.
    api.set(&eq_group(to_deck), "button_parameter1", 1.0)?;
    let mut beats = BeatWaiter::new(port, from_deck)?;
    beats.wait_next_beat()?;
    api.set(&eq_group(from_deck), "button_parameter1", 1.0)?;
    api.set(&eq_group(to_deck), "button_parameter1", 0.0)?;
    Ok(())
}

/// Undo any kill switches on a deck (restore full EQ).
pub fn kill_restore(api: &mut ControlApi, deck: u8) -> Result<()> {
    let group = eq_group(deck);
    for key in [
        "button_parameter1",
        "button_parameter2",
        "button_parameter3",
    ] {
        api.set(&group, key, 0.0)?;
    }
    Ok(())
}

/// Censor fill: slip-reverse for `beats` beats, then snap back on grid.
/// Playback position keeps advancing underneath (reverseroll is slip-based).
pub fn censor(api: &mut ControlApi, deck: u8, beats: u32, port: u16) -> Result<()> {
    let group = deck_group(deck);
    let mut waiter = BeatWaiter::new(port, deck)?;
    waiter.wait_next_beat()?;
    api.set(&group, "reverseroll", 1.0)?;
    waiter.wait_beats(beats)?;
    api.set(&group, "reverseroll", 0.0)?;
    Ok(())
}

/// Slip stutter: `rolls` beat-anchored loop rolls of `size` beats each,
/// position advancing underneath — the fill before a landing.
pub fn stutter(api: &mut ControlApi, deck: u8, rolls: u32, size: f64, port: u16) -> Result<()> {
    let group = deck_group(deck);
    let key = format!("beatlooproll_{}_activate", format_size(size));
    api.set(&group, "slip_enabled", 1.0)?;
    let mut waiter = BeatWaiter::new(port, deck)?;
    for _ in 0..rolls {
        waiter.wait_next_beat()?;
        api.set(&group, &key, 1.0)?;
        waiter.wait_next_beat()?;
        api.set(&group, &key, 0.0)?;
    }
    api.set(&group, "slip_enabled", 0.0)?;
    Ok(())
}

fn format_size(size: f64) -> String {
    // Mixxx control names use 0.0625..64 with fractions like 0.5.
    if size.fract() == 0.0 {
        format!("{}", size as i64)
    } else {
        format!("{size}")
    }
}

/// Smoothstep crossfade over `beats` beats of the outgoing deck's live
/// tempo — the Rust port of the runner's fade loop.
pub fn fade(api: &mut ControlApi, from_deck: u8, to_deck: u8, beats: u32, port: u16) -> Result<()> {
    let out_group = deck_group(from_deck);
    let bpm = api.get(&out_group, "bpm")?;
    anyhow::ensure!(bpm > 0.0, "{out_group} reports no BPM");
    let seconds = f64::from(beats) * 60.0 / bpm;
    let start = api.get("[Master]", "crossfader")?;
    let end = if to_deck % 2 == 1 { -1.0 } else { 1.0 };

    let mut waiter = BeatWaiter::new(port, from_deck)?;
    waiter.wait_next_beat()?;
    api.set(&deck_group(to_deck), "play", 1.0)?;

    let t0 = Instant::now();
    loop {
        let progress = (t0.elapsed().as_secs_f64() / seconds).min(1.0);
        let curve = progress * progress * (3.0 - 2.0 * progress);
        api.set("[Master]", "crossfader", start + (end - start) * curve)?;
        if progress >= 1.0 {
            break;
        }
        sleep(STEP);
    }
    api.set(&out_group, "play", 0.0)?;
    Ok(())
}
