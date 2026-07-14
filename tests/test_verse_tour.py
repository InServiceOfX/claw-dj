import unittest

from brain.build_verse_tour import build_verse_tour_plan, tour_verses


def seg(kind, start, end, lines=8, bar=None, beat=None, first="line"):
    return {"kind": kind, "start": start, "end": end, "lines": lines,
            "bar_start": bar if bar is not None else start,
            "beat_index": beat, "first_line": first}


TRACK = {"track_id": "/music/song.mp3", "artist": "A", "title": "Song", "bpm": 120.0, "key": "Am"}

SEGMENTS = [
    seg("verse", 10.0, 40.0, beat=20, first="verse one"),
    seg("chorus", 40.0, 55.0, beat=80),
    seg("verse", 55.0, 85.0, beat=110, first="verse two"),
    seg("chorus", 85.0, 100.0, beat=170),
    seg("verse", 100.0, 130.0, beat=200, first="verse three"),
    seg("verse", 132.0, 135.0, lines=2, beat=264, first="short adlib"),
]


class VerseTourTests(unittest.TestCase):
    def test_short_blocks_excluded(self):
        verses = tour_verses(SEGMENTS)
        self.assertEqual([v["first_line"] for v in verses],
                         ["verse one", "verse two", "verse three"])

    def test_plan_alternates_decks_and_skips_choruses(self):
        plan = build_verse_tour_plan(TRACK, SEGMENTS)
        events = plan["events"]
        loads = [e for e in events if e["op"] in ("load", "preload_after_transition")]
        # decks cued at verse bar starts only — never a chorus time
        self.assertEqual([e["cue_seconds"] for e in loads], [10.0, 55.0, 100.0])
        cuts = [e for e in events if e["op"] == "transition"]
        self.assertTrue(all(e["technique"] == "verse_cut" and "hard_cut" in e["moves"] for e in cuts))
        self.assertEqual([(e["from_deck"], e["to_deck"]) for e in cuts], [(1, 2), (2, 1)])
        # 30s verse at 120bpm = 60 beats, minus the cut-anchor beat
        body = next(e for e in events if e["op"] == "play_body")
        self.assertEqual(body["beats"], 59)
        self.assertEqual(events[-1]["op"], "stop_all")
        self.assertEqual(events[-2]["op"], "finale")

    def test_requires_two_verses(self):
        with self.assertRaises(SystemExit):
            build_verse_tour_plan(TRACK, SEGMENTS[:2])


if __name__ == "__main__":
    unittest.main()
