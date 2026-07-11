"""Executes shared.commands.Command objects against Mixxx over MIDI, using
the claw-dj controller mapping in hands/mixxx_mapping/. No vision model, no
screenshots, no network round-trip in this path — timing comes from
hands/beatgrid.py plus a local scheduler.
"""
import time

import rtmidi

from hands.beatgrid import Beatgrid, beat_to_seconds
from shared.commands import BeatJump, Command, Crossfade, Loop, SetHotcue, TriggerHotcue

# TODO: fill in against hands/mixxx_mapping/claw-dj.midi.xml once the mapping
# is written and loaded in Mixxx's Controller preferences.
HOTCUE_NOTE_BASE = 0x10
LOOP_CC = 0x20
BEATJUMP_CC = 0x21
CROSSFADER_CC = 0x22


class MidiEngine:
    def __init__(self, port_name: str = "claw-dj"):
        self._out = rtmidi.MidiOut()
        ports = self._out.get_ports()
        matches = [i for i, p in enumerate(ports) if port_name in p]
        if not matches:
            raise RuntimeError(
                f"no MIDI port matching {port_name!r}; open ports: {ports}"
            )
        self._out.open_port(matches[0])

    def execute(self, command: Command, grid: Beatgrid | None = None) -> None:
        match command:
            case TriggerHotcue(deck, slot):
                self._out.send_message([0x90 | deck, HOTCUE_NOTE_BASE + slot, 127])
            case SetHotcue(deck, slot, position_beats):
                # TODO: Mixxx hotcue-set is normally "play to position, hit
                # set" rather than a direct seek — revisit once mapping exists.
                raise NotImplementedError
            case Loop(deck, beats, action):
                self._out.send_message([0xB0 | deck, LOOP_CC, beats])
            case BeatJump(deck, beats):
                self._out.send_message([0xB0 | deck, BEATJUMP_CC, beats & 0x7F])
            case Crossfade(from_deck, to_deck, duration_ms, curve):
                self._ramp_crossfader(duration_ms)
            case _:
                raise ValueError(f"unhandled command: {command!r}")

    def _ramp_crossfader(self, duration_ms: int, steps: int = 32) -> None:
        interval = duration_ms / 1000 / steps
        for i in range(steps + 1):
            value = int(127 * i / steps)
            self._out.send_message([0xB0, CROSSFADER_CC, value])
            time.sleep(interval)

    def wait_for_beat(self, grid: Beatgrid, beat: float) -> None:
        target = beat_to_seconds(grid, beat)
        # TODO: needs a real reference clock (deck playback start time), not
        # wall-clock time.time() — placeholder until that's wired up.
        time.sleep(max(0.0, target - time.time()))
