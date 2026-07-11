use std::str::FromStr;

use anyhow::{Result, anyhow, bail};
use serde::Deserialize;

use crate::midi::MidiMessage;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Deserialize)]
#[serde(try_from = "u8")]
pub enum Deck {
    One,
    Two,
}

impl Deck {
    #[must_use]
    pub const fn as_u8(self) -> u8 {
        match self {
            Self::One => 1,
            Self::Two => 2,
        }
    }
}

impl TryFrom<u8> for Deck {
    type Error = anyhow::Error;

    fn try_from(value: u8) -> Result<Self> {
        match value {
            1 => Ok(Self::One),
            2 => Ok(Self::Two),
            _ => bail!("deck must be 1 or 2, got {value}"),
        }
    }
}

impl FromStr for Deck {
    type Err = anyhow::Error;

    fn from_str(value: &str) -> Result<Self> {
        value
            .parse::<u8>()
            .map_err(|error| anyhow!("invalid deck '{value}': {error}"))?
            .try_into()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Operation {
    Load { deck: Deck, track_id: i64 },
    Play { deck: Deck },
    Pause { deck: Deck },
    Cue { deck: Deck },
    Crossfade { value: u8 },
}

impl Operation {
    #[must_use]
    pub fn to_message(&self) -> MidiMessage {
        match *self {
            Self::Load { deck, .. } => MidiMessage::note_on(deck.load_note(), 0x7F),
            Self::Play { deck } => MidiMessage::note_on(deck.play_note(), 0x7F),
            Self::Pause { deck } => MidiMessage::note_on(deck.pause_note(), 0x7F),
            Self::Cue { deck } => MidiMessage::note_on(deck.cue_note(), 0x7F),
            Self::Crossfade { value } => MidiMessage::control_change(0x00, value),
        }
    }
}

impl Deck {
    const fn load_note(self) -> u8 {
        match self {
            Self::One => 0x00,
            Self::Two => 0x01,
        }
    }

    const fn play_note(self) -> u8 {
        match self {
            Self::One => 0x02,
            Self::Two => 0x03,
        }
    }

    const fn pause_note(self) -> u8 {
        match self {
            Self::One => 0x04,
            Self::Two => 0x05,
        }
    }

    const fn cue_note(self) -> u8 {
        match self {
            Self::One => 0x06,
            Self::Two => 0x07,
        }
    }
}

#[derive(Debug, Deserialize)]
pub struct JsonCommand {
    pub op: String,
    pub deck: Option<Deck>,
    pub track_id: Option<i64>,
    pub value: Option<u8>,
    pub position: Option<f64>,
}

impl JsonCommand {
    pub fn into_operation(self) -> Result<Operation> {
        match self.op.as_str() {
            "load" => Ok(Operation::Load {
                deck: self.deck.ok_or_else(|| anyhow!("load requires deck"))?,
                track_id: self
                    .track_id
                    .ok_or_else(|| anyhow!("load requires track_id"))?,
            }),
            "play" => Ok(Operation::Play {
                deck: self.deck.ok_or_else(|| anyhow!("play requires deck"))?,
            }),
            "pause" => Ok(Operation::Pause {
                deck: self.deck.ok_or_else(|| anyhow!("pause requires deck"))?,
            }),
            "cue" => Ok(Operation::Cue {
                deck: self.deck.ok_or_else(|| anyhow!("cue requires deck"))?,
            }),
            "crossfade" => Ok(Operation::Crossfade {
                value: self.crossfade_value()?,
            }),
            other => bail!("unsupported op '{other}'"),
        }
    }

    fn crossfade_value(&self) -> Result<u8> {
        if let Some(value) = self.value {
            return Ok(value);
        }
        if let Some(position) = self.position {
            if !(0.0..=1.0).contains(&position) {
                bail!("crossfade position must be between 0.0 and 1.0");
            }
            let scaled = (position * 127.0).round();
            return Ok(scaled as u8);
        }
        bail!("crossfade requires value or position")
    }
}

#[cfg(test)]
mod tests {
    use super::{Deck, JsonCommand, Operation};

    #[test]
    fn builds_expected_midi_bytes_for_ops() {
        let cases = [
            (
                Operation::Load {
                    deck: Deck::One,
                    track_id: 10,
                },
                [0x9F, 0x00, 0x7F],
            ),
            (
                Operation::Load {
                    deck: Deck::Two,
                    track_id: 20,
                },
                [0x9F, 0x01, 0x7F],
            ),
            (Operation::Play { deck: Deck::One }, [0x9F, 0x02, 0x7F]),
            (Operation::Play { deck: Deck::Two }, [0x9F, 0x03, 0x7F]),
            (Operation::Pause { deck: Deck::One }, [0x9F, 0x04, 0x7F]),
            (Operation::Pause { deck: Deck::Two }, [0x9F, 0x05, 0x7F]),
            (Operation::Cue { deck: Deck::One }, [0x9F, 0x06, 0x7F]),
            (Operation::Cue { deck: Deck::Two }, [0x9F, 0x07, 0x7F]),
            (Operation::Crossfade { value: 0x64 }, [0xBF, 0x00, 0x64]),
        ];

        for (operation, expected) in cases {
            assert_eq!(operation.to_message().to_bytes(), expected);
        }
    }

    #[test]
    fn parses_crossfade_position_from_json() {
        let command: JsonCommand =
            serde_json::from_str(r#"{"op":"crossfade","position":0.5}"#).unwrap();
        let operation = command.into_operation().unwrap();

        assert_eq!(operation, Operation::Crossfade { value: 64 });
    }
}
