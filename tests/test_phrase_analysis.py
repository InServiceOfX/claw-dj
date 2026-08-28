import struct
from unittest import TestCase

from brain.phrase_analysis import (
    choose_phrase,
    decode_beat_grid,
    seekable_cue_seconds,
    signed_protobuf_int64,
    usable_first_beat_seconds,
)


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

    def test_decodes_negative_first_beat_as_signed_int64(self) -> None:
        # Candy Shop / You Don't Know / Hands Up Instrumental: Mixxx placed
        # the first beat 77 frames before sample 0. Protobuf int64 stores
        # that as the two's-complement varint 2**64 - 77, not as -77.
        wrapped = (1 << 64) - 77
        self.assertEqual(signed_protobuf_int64(wrapped), -77)
        bpm_message = b"\x09" + struct.pack("<d", 98.0)
        beat_message = b"\x08" + varint(wrapped)
        blob = b"\x0a" + varint(len(bpm_message)) + bpm_message
        blob += b"\x12" + varint(len(beat_message)) + beat_message
        self.assertEqual(decode_beat_grid(blob), (98.0, -77))
        self.assertAlmostEqual((-77) / 44100, -0.001746, places=6)
        self.assertEqual(seekable_cue_seconds((-77) / 44100, 209.13), 0.0)
        self.assertEqual(
            seekable_cue_seconds(wrapped / 44100, 209.13),
            0.0,
        )

    def test_unsigned_wrap_is_not_a_usable_first_beat(self) -> None:
        self.assertEqual(
            usable_first_beat_seconds(18446744073709551539 / 44100),
            0.0,
        )
        self.assertAlmostEqual(usable_first_beat_seconds(-77 / 44100), -77 / 44100)

    def test_empty_energy_does_not_keep_wrapped_first_beat_as_cue(self) -> None:
        result = choose_phrase(
            [],
            first_beat_seconds=418293516410647.44,
            bpm=98.0,
            duration_seconds=209.13,
        )
        self.assertEqual(result["cue_seconds"], 0.0)
        self.assertEqual(result["confidence"], 0.0)

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
