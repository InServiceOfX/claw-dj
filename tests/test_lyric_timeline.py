import unittest

from brain.lyric_timeline import detect_segments, parse_lrc, snap_segments


def lrc_block(entries):
    return "\n".join(f"[{int(t // 60):02d}:{t % 60:05.2f}]{text}" for t, text in entries)


class LyricTimelineTests(unittest.TestCase):
    def test_parse_handles_multiple_stamps_and_sorting(self):
        lrc = "[00:30.00][01:30.00]shared hook line\n[00:10.00]first words\nno stamp line"
        lines = parse_lrc(lrc)
        self.assertEqual([round(l.t, 1) for l in lines], [10.0, 30.0, 90.0])
        self.assertEqual(lines[0].text, "first words")

    def test_detects_chorus_by_repetition_and_gap_boundaries(self):
        verse1 = [(10 + i * 3, f"unique verse one line {i}") for i in range(4)]
        chorus = [(25 + i * 3, f"this is the catchy chorus line {i % 2}") for i in range(4)]
        verse2 = [(40 + i * 3, f"different verse two bars {i}") for i in range(4)]
        chorus2 = [(55 + i * 3, f"this is the catchy chorus line {i % 2}") for i in range(4)]
        # long instrumental gap, then an outro verse
        outro = [(90 + i * 3, f"outro talking {i}") for i in range(2)]
        lines = parse_lrc(lrc_block(verse1 + chorus + verse2 + chorus2 + outro))
        segments = detect_segments(lines)
        kinds = [s.kind for s in segments]
        self.assertEqual(kinds, ["verse", "chorus", "verse", "chorus", "verse"])
        # gap boundary: outro starts at 90 even though label matches verse2
        self.assertEqual(segments[-1].start, 90.0)
        # verse 2 vocal onset preserved
        self.assertEqual(segments[2].start, 40.0)

    def test_snap_to_bars(self):
        lines = parse_lrc(lrc_block([(10.1, "unique a"), (30.4, "unique b c d")]))
        segments = detect_segments(lines)
        # 120 bpm -> bar = 2s, first beat at 0.1s
        snapped = snap_segments(segments, bpm=120.0, first_beat_seconds=0.1)
        self.assertEqual(snapped[0].bar_start, 10.1)   # exactly 5 bars in
        self.assertEqual(snapped[0].beat_index, 20)


if __name__ == "__main__":
    unittest.main()
