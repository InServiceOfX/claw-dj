from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.build_mix_plan import build_plan, compose_mix_plan, pick_technique, plan_summary
from brain.lyrics import lyric_overlap, tokens
from brain.mix_profiles import PROFILES, apply_brief


class MixPlanTest(TestCase):
    def test_lyric_overlap_finds_shared_hooks(self) -> None:
        a = "it was all a dream I used to read word up magazine"
        b = "all a dream nothing but a g thang baby"
        result = lyric_overlap(a, b)
        self.assertGreater(result["score"], 0)
        self.assertTrue(any("dream" in t for t in result["shared_tokens"]))

    def test_pick_technique_lineage_prefers_callback(self) -> None:
        left = {"bpm": 95.0, "key": "D"}
        right = {"bpm": 95.4, "key": "D"}
        tech = pick_technique(
            left,
            right,
            {"score": 0.9, "lyric_score": 0.0, "chroma_score": 0.0, "reasons": ["sample/cover lineage"]},
        )
        self.assertEqual(tech["technique"], "sample_callback_blend")
        self.assertGreaterEqual(tech["transition_beats"], 16)

    def test_build_plan_has_instrument_map_and_transitions(self) -> None:
        tracks = [
            {
                "track_id": f"/music/{i}.mp3",
                "artist": f"Artist{i}",
                "title": f"Title{i}",
                "bpm": 90 + i,
                "key": "Am",
            }
            for i in range(4)
        ]
        plan = build_plan(tracks, count=4, seconds_per_track=20.0, affinity_lookup={})
        self.assertEqual(plan["track_count"], 4)
        self.assertEqual(plan["version"], 2)
        self.assertEqual(plan["phrase_interval_beats"], 32)
        self.assertIn("crossfader", plan["instrument_map"]["levels"])
        ops = [event["op"] for event in plan["events"]]
        self.assertIn("reset_instrument", ops)
        self.assertIn("transition", ops)
        self.assertIn("stop_all", ops)
        self.assertEqual(len(plan["segments"]), 3)
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        # The opener now rides two phrases; varied segment lengths are an
        # intentional part of the current plan defaults.
        self.assertEqual(body["beats"], 63)

    def test_apply_brief_negation_beats_positive(self) -> None:
        profile, notes = apply_brief(PROFILES["dj-showcase"], "smooth, longer blends, no tricks")
        self.assertEqual(profile.flourish_every, 0)
        self.assertTrue(any("flourishes off" in note for note in notes))
        self.assertTrue(any("longer" in note for note in notes))
        # "no tricks" must not also fire the "tricks" positive branch.
        self.assertFalse(any("every transition" in note for note in notes))

    def test_compose_mix_plan_and_summary(self) -> None:
        tracks = [
            {
                "track_id": f"/music/{i}.mp3",
                "artist": f"Artist{i}",
                "title": f"Title{i}",
                "bpm": 90 + i,
                "key": "Am",
            }
            for i in range(4)
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            playlist = root / "playlist.json"
            out = root / "mix_plan.json"
            playlist.write_text(__import__("json").dumps(tracks))
            plan = compose_mix_plan(
                playlist=playlist,
                profile_name="warm-up",
                mix_brief="clean, minimal",
                tracks=3,
                out=out,
            )
            self.assertTrue(out.exists())
            self.assertEqual(plan["track_count"], 3)
            self.assertEqual(plan["profile"]["name"], "warm-up")
            self.assertIn("flourishes off", " ".join(plan["profile"]["brief_adjustments"]))
            summary = plan_summary(plan, plan_path=out)
            self.assertTrue(summary["dry_run_ok"])
            self.assertEqual(summary["track_count"], 3)
            self.assertEqual(summary["segment_count"], 2)
            self.assertGreater(summary["event_count"], 0)
            self.assertEqual(summary["plan_path"], str(out))
