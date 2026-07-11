use anyhow::{Context, Result, anyhow};
use midir::{
    Ignore, MidiInput, MidiInputConnection, MidiOutput, MidiOutputConnection, MidiOutputPort,
};
use once_cell::sync::Lazy;

use crate::command::Operation;

pub const MIDI_NOTE_ON_STATUS: u8 = 0x9F;
pub const MIDI_CONTROL_CHANGE_STATUS: u8 = 0xBF;
// Feedback notes the mapping's <outputs> emit on Mixxx's beat_active edge.
pub const BEAT_TICK_NOTE_DECK1: u8 = 0x40;
pub const BEAT_TICK_NOTE_DECK2: u8 = 0x41;

static MIDI_TARGET_HINTS: Lazy<Vec<&'static str>> =
    Lazy::new(|| vec!["IAC Driver clawdj", "clawdj"]);

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum MidiMessage {
    NoteOn { note: u8, velocity: u8 },
    ControlChange { controller: u8, value: u8 },
}

impl MidiMessage {
    #[must_use]
    pub const fn note_on(note: u8, velocity: u8) -> Self {
        Self::NoteOn { note, velocity }
    }

    #[must_use]
    pub const fn control_change(controller: u8, value: u8) -> Self {
        Self::ControlChange { controller, value }
    }

    #[must_use]
    pub const fn to_bytes(&self) -> [u8; 3] {
        match *self {
            Self::NoteOn { note, velocity } => [MIDI_NOTE_ON_STATUS, note, velocity],
            Self::ControlChange { controller, value } => {
                [MIDI_CONTROL_CHANGE_STATUS, controller, value]
            }
        }
    }
}

#[derive(Debug)]
pub struct PortPresenceSummary {
    pub input_ports: Vec<String>,
    pub output_ports: Vec<String>,
    pub clawdj_present: bool,
}

pub fn port_presence_summary() -> Result<PortPresenceSummary> {
    let midi_in = MidiInput::new("clawdj-setup-in").context("failed to initialize MIDI input")?;
    let midi_out =
        MidiOutput::new("clawdj-setup-out").context("failed to initialize MIDI output")?;

    let input_ports = midi_in
        .ports()
        .iter()
        .map(|port| midi_in.port_name(port))
        .collect::<std::result::Result<Vec<_>, _>>()
        .context("failed to enumerate MIDI input port names")?;

    let output_ports = midi_out
        .ports()
        .iter()
        .map(|port| midi_out.port_name(port))
        .collect::<std::result::Result<Vec<_>, _>>()
        .context("failed to enumerate MIDI output port names")?;

    let clawdj_present = input_ports.iter().any(|name| port_matches(name))
        || output_ports.iter().any(|name| port_matches(name));

    Ok(PortPresenceSummary {
        input_ports,
        output_ports,
        clawdj_present,
    })
}

#[must_use]
pub fn build_message(operation: &Operation) -> [u8; 3] {
    operation.to_message().to_bytes()
}

pub fn open_output_port() -> Result<MidiOutputConnection> {
    let midi_out = MidiOutput::new("clawdj-cli-out").context("failed to initialize MIDI output")?;
    let ports = midi_out.ports();

    let port = ports
        .iter()
        .find(|candidate| {
            midi_out
                .port_name(candidate)
                .map(|name| port_matches(&name))
                .unwrap_or(false)
        })
        .cloned()
        .ok_or_else(|| anyhow!("no MIDI output port matching clawdj was found"))?;

    connect_output_port(midi_out, &port)
}

/// Open the clawdj port for input and stream every incoming message to `callback`.
///
/// The IAC bus loops our own sent commands back to us alongside Mixxx's
/// feedback, so callers must filter (feedback notes/CCs live at 0x40+).
pub fn open_input_port<F>(callback: F) -> Result<MidiInputConnection<()>>
where
    F: FnMut(&[u8]) + Send + 'static,
{
    let mut midi_in = MidiInput::new("clawdj-cli-in").context("failed to initialize MIDI input")?;
    midi_in.ignore(Ignore::None);
    let ports = midi_in.ports();

    let port = ports
        .iter()
        .find(|candidate| {
            midi_in
                .port_name(candidate)
                .map(|name| port_matches(&name))
                .unwrap_or(false)
        })
        .cloned()
        .ok_or_else(|| anyhow!("no MIDI input port matching clawdj was found"))?;

    let mut callback = callback;
    midi_in
        .connect(
            &port,
            "clawdj-cli-in",
            move |_timestamp, bytes, ()| callback(bytes),
            (),
        )
        .map_err(|error| anyhow!("failed to open MIDI input port: {error}"))
}

pub fn send_message(connection: &mut MidiOutputConnection, message: &MidiMessage) -> Result<()> {
    connection
        .send(&message.to_bytes())
        .context("failed to send MIDI message")
}

fn connect_output_port(
    midi_out: MidiOutput,
    port: &MidiOutputPort,
) -> Result<MidiOutputConnection> {
    let port_name = midi_out
        .port_name(port)
        .context("failed to resolve MIDI output port name")?;
    midi_out
        .connect(port, "clawdj-cli")
        .map_err(|error| anyhow!("failed to open MIDI output port '{port_name}': {error}"))
}

fn port_matches(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    MIDI_TARGET_HINTS
        .iter()
        .any(|hint| lower.contains(&hint.to_ascii_lowercase()))
}

#[cfg(test)]
mod tests {
    use super::port_matches;

    #[test]
    fn matches_expected_port_names() {
        assert!(port_matches("IAC Driver clawdj"));
        assert!(port_matches("clawdj"));
        assert!(!port_matches("Scarlett 2i2 USB"));
    }
}
