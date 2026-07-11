#!/usr/bin/env python3
"""
clawdj MIDI bridge — minimal Python interface to drive the clawdj Mixxx mapping.

Uses `mido` (pip install mido python-rtmidi) to send Note On / CC messages
to the virtual MIDI port "IAC Driver clawdj" (macOS) or "clawdj" (Linux).

Channel 16 (0xF) is the control channel per clawdj.midi.xml.
"""

import mido
import time
from typing import Optional

# MIDI port name (macOS default; override via env or constructor)
DEFAULT_PORT = "IAC Driver clawdj"

# Note numbers (channel 16 = 0xF)
NOTE_LOAD_DECK1 = 0x00
NOTE_LOAD_DECK2 = 0x01
NOTE_PLAY_DECK1 = 0x02
NOTE_PLAY_DECK2 = 0x03
NOTE_PAUSE_DECK1 = 0x04
NOTE_PAUSE_DECK2 = 0x05
NOTE_CUE_DECK1 = 0x06
NOTE_CUE_DECK2 = 0x07
NOTE_SYNC_DECK1 = 0x08
NOTE_SYNC_DECK2 = 0x09

# CC numbers (7-bit, 0-127)
CC_CROSSFADER = 0x00
CC_DECK1_VOLUME = 0x01
CC_DECK2_VOLUME = 0x02
CC_DECK1_RATE = 0x03
CC_DECK2_RATE = 0x04
CC_DECK1_EQ_LOW = 0x05
CC_DECK1_EQ_MID = 0x06
CC_DECK1_EQ_HIGH = 0x07
CC_DECK2_EQ_LOW = 0x08
CC_DECK2_EQ_MID = 0x09
CC_DECK2_EQ_HIGH = 0x0A


class ClawDJMidi:
    def __init__(self, port_name: Optional[str] = None):
        self.port_name = port_name or DEFAULT_PORT
        self._outport = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        if self._outport is None:
            try:
                self._outport = mido.open_output(self.port_name)
            except OSError as e:
                raise RuntimeError(
                    f"Could not open MIDI port '{self.port_name}'. "
                    f"Create the IAC Driver 'clawdj' bus in Audio MIDI Setup (macOS) "
                    f"or equivalent virtual port on Linux."
                ) from e
        return self

    def close(self):
        if self._outport:
            self._outport.close()
            self._outport = None

    def _note_on(self, note: int, velocity: int = 127):
        if self._outport:
            msg = mido.Message('note_on', channel=15, note=note, velocity=velocity)
            self._outport.send(msg)

    def _cc(self, control: int, value: int):
        if self._outport:
            # Clamp to 0-127
            value = max(0, min(127, int(value)))
            msg = mido.Message('control_change', channel=15, control=control, value=value)
            self._outport.send(msg)

    # --- High-level API (matches clawdj.midi.xml) ---
    def load_deck1(self):
        self._note_on(NOTE_LOAD_DECK1)

    def load_deck2(self):
        self._note_on(NOTE_LOAD_DECK2)

    def play_deck1(self):
        self._note_on(NOTE_PLAY_DECK1)

    def play_deck2(self):
        self._note_on(NOTE_PLAY_DECK2)

    def pause_deck1(self):
        self._note_on(NOTE_PAUSE_DECK1)

    def pause_deck2(self):
        self._note_on(NOTE_PAUSE_DECK2)

    def cue_deck1(self):
        self._note_on(NOTE_CUE_DECK1)

    def cue_deck2(self):
        self._note_on(NOTE_CUE_DECK2)

    def sync_deck1(self):
        self._note_on(NOTE_SYNC_DECK1)

    def sync_deck2(self):
        self._note_on(NOTE_SYNC_DECK2)

    def set_crossfader(self, value: float):
        """value: -1.0 (full left) .. +1.0 (full right)"""
        midi_val = int((value + 1.0) * 63.5)
        self._cc(CC_CROSSFADER, midi_val)

    def set_deck_volume(self, deck: int, value: float):
        """deck: 1 or 2, value: 0.0 .. 1.0"""
        cc = CC_DECK1_VOLUME if deck == 1 else CC_DECK2_VOLUME
        midi_val = int(value * 127)
        self._cc(cc, midi_val)

    def set_deck_rate(self, deck: int, value: float):
        """deck: 1 or 2, value: -1.0 .. +1.0 (pitch bend style)"""
        cc = CC_DECK1_RATE if deck == 1 else CC_DECK2_RATE
        midi_val = int((value + 1.0) * 63.5)
        self._cc(cc, midi_val)

    def set_deck_eq(self, deck: int, band: str, value: float):
        """band: 'low', 'mid', or 'high'"""
        if deck not in (1, 2):
            raise ValueError("deck must be 1 or 2")
        band_map = {'low': 0, 'mid': 1, 'high': 2}
        if band not in band_map:
            raise ValueError("band must be low/mid/high")
        base_cc = CC_DECK1_EQ_LOW if deck == 1 else CC_DECK2_EQ_LOW
        cc = base_cc + band_map[band]
        midi_val = int(value * 127)
        self._cc(cc, midi_val)


if __name__ == "__main__":
    # Quick smoke test
    print("clawdj MIDI bridge smoke test")
    with ClawDJMidi() as dj:
        print(f"Connected to {dj.port_name}")
        dj.play_deck1()
        time.sleep(0.1)
        dj.set_crossfader(0.0)
        print("Sent play + center crossfader")
