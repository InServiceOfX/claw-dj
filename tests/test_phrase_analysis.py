import struct
from unittest import TestCase

from brain.phrase_analysis import choose_phrase, decode_beat_grid


def varint(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


class PhraseAnalysisTest(TestCase):
    def test_decodes_mixxx_beatgrid_v2(self) -> None:
        bpm_message = b"\x09" + struct.pack("<d", 95.5)
        beat_message = b"\x08" + varint(44100)
        blob = b"\x0a" + varint(len(bpm_message)) + bpm_message
        blob += b"\x12" + varint(len(beat_message)) + beat_message
        self.assertEqual(decode_beat_grid(blob), (95.5, 44100))

    def test_phrase_picker_uses_aligned_energy_rise(self) -> None:
        energy = [0.1] * 16 + [0.9] * 16 + [0.4] * 32
        result = choose_phrase(
            energy,
            first_beat_seconds=0.25,
            bpm=120.0,
            phrase_beats=16,
        )
        self.assertEqual(result["beat_index"], 16)
        self.assertAlmostEqual(result["cue_seconds"], 8.25)
        self.assertGreater(result["confidence"], 0.6)
