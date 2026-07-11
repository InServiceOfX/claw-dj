//! Real-time layer: listen to Mixxx's live beat ticks and execute
//! beat-anchored moves, instead of the canned sleep-based demo scripts.
//!
//! Feedback path (verified live 2026-07-11): the clawdj mapping's `<outputs>`
//! make Mixxx emit Note On `0x40 + (deck-1)` velocity 127 on channel 16 for
//! every beat (`beat_active` edge), onto the same IAC bus we send commands
//! into. The bus loops our own commands back too, so everything below
//! filters to the 0x40+ feedback range.

use std::{
    sync::mpsc::{Receiver, channel},
    thread,
    time::{Duration, Instant},
};

use anyhow::{Context, Result, anyhow};
use midir::{MidiInputConnection, MidiOutputConnection};

use crate::{
    command::{Deck, Operation},
    midi::{BEAT_TICK_NOTE_DECK1, MIDI_NOTE_ON_STATUS, open_input_port, send_message},
};

#[derive(Clone, Copy, Debug)]
pub struct BeatTick {
    pub deck: u8,
    pub at: Instant,
}

/// Subscribes to the clawdj port and turns Mixxx's beat_active feedback
/// notes into a stream of timestamped ticks.
pub struct BeatClock {
    receiver: Receiver<BeatTick>,
    // Dropping the connection closes the port; hold it for the clock's lifetime.
    _connection: MidiInputConnection<()>,
}

impl BeatClock {
    pub fn start() -> Result<Self> {
        let (sender, receiver) = channel();
        let connection = open_input_port(move |bytes| {
            if let [MIDI_NOTE_ON_STATUS, note @ (0x40 | 0x41), velocity] = *bytes
                && velocity > 0
            {
                let tick = BeatTick {
                    deck: note - BEAT_TICK_NOTE_DECK1 + 1,
                    at: Instant::now(),
                };
                // The receiver disappearing just means the clock is shutting down.
                let _ = sender.send(tick);
            }
        })?;
        Ok(Self {
            receiver,
            _connection: connection,
        })
    }

    /// Block until the next beat from either deck.
    pub fn next_any(&self, timeout: Duration) -> Result<BeatTick> {
        self.receiver
            .recv_timeout(timeout)
            .context("no beat tick from any deck — is one playing?")
    }

    /// Block until the next beat of `deck`, discarding other decks' ticks.
    pub fn next_beat(&self, deck: Deck, timeout: Duration) -> Result<BeatTick> {
        let deadline = Instant::now() + timeout;
        loop {
            let remaining = deadline
                .checked_duration_since(Instant::now())
                .ok_or_else(|| {
                    anyhow!(
                        "no beat tick from deck {} within {timeout:?} — is it playing?",
                        deck.as_u8()
                    )
                })?;
            let tick = self.receiver.recv_timeout(remaining).with_context(|| {
                format!("no beat tick from deck {} — is it playing?", deck.as_u8())
            })?;
            if tick.deck == deck.as_u8() {
                return Ok(tick);
            }
        }
    }

    /// Measure the deck's live BPM from `intervals` consecutive beat gaps.
    pub fn measure_bpm(&self, deck: Deck, intervals: usize, timeout: Duration) -> Result<f64> {
        let first = self.next_beat(deck, timeout)?;
        let mut previous = first.at;
        let mut total = Duration::ZERO;
        for _ in 0..intervals {
            let tick = self.next_beat(deck, timeout)?;
            total += tick.at.duration_since(previous);
            previous = tick.at;
        }
        let mean = total.as_secs_f64() / intervals as f64;
        Ok(60.0 / mean)
    }
}

const CROSSFADE_STEP: Duration = Duration::from_millis(25);

/// Beat-anchored transition: measure the outgoing deck's live BPM, start the
/// incoming deck on a beat, beat-sync it, and crossfade over `beats` beats
/// of real measured time. Assumes the incoming deck already has a track
/// loaded (that's the Brain's job).
pub fn transition(
    connection: &mut MidiOutputConnection,
    clock: &BeatClock,
    from: Deck,
    to: Deck,
    beats: u32,
) -> Result<TransitionReport> {
    // Full channel volumes: the blend lives on the crossfader alone.
    send_message(
        &mut *connection,
        &Operation::Volume {
            deck: from,
            value: 0x7F,
        }
        .to_message(),
    )?;
    send_message(
        &mut *connection,
        &Operation::Volume {
            deck: to,
            value: 0x7F,
        }
        .to_message(),
    )?;

    let bpm = clock.measure_bpm(from, 4, Duration::from_secs(15))?;

    // Drop the incoming deck in on a live beat, then let Mixxx's own
    // beat-sync engine pull its tempo/phase into line.
    clock.next_beat(from, Duration::from_secs(10))?;
    send_message(&mut *connection, &Operation::Play { deck: to }.to_message())?;
    send_message(&mut *connection, &Operation::Sync { deck: to }.to_message())?;

    let (start, end) = match from {
        Deck::One => (0.0_f64, 127.0_f64),
        Deck::Two => (127.0, 0.0),
    };
    let fade = Duration::from_secs_f64(f64::from(beats) * 60.0 / bpm);
    let started = Instant::now();
    loop {
        let progress = (started.elapsed().as_secs_f64() / fade.as_secs_f64()).min(1.0);
        // Smoothstep: gentle at the edges, no audible jump at either end.
        let eased = progress * progress * (3.0 - 2.0 * progress);
        let value = (start + (end - start) * eased).round().clamp(0.0, 127.0) as u8;
        send_message(
            &mut *connection,
            &Operation::Crossfade { value }.to_message(),
        )?;
        if progress >= 1.0 {
            break;
        }
        thread::sleep(CROSSFADE_STEP);
    }

    send_message(
        &mut *connection,
        &Operation::Pause { deck: from }.to_message(),
    )?;

    Ok(TransitionReport {
        measured_bpm: bpm,
        fade: started.elapsed(),
    })
}

#[derive(Debug)]
pub struct TransitionReport {
    pub measured_bpm: f64,
    pub fade: Duration,
}
