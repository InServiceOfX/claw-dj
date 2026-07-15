from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.analyze_via_mixxx import key_from_control
from brain.build_mix_plan import (
    build_plan,
    compose_mix_plan,
    pick_technique,
    pitch_adjust_for_blend,
    plan_summary,
    track_directives,
)
from brain.lyrics import lyric_overlap, title_search_variants, tokens
from brain.mix_graph import key_compatibility
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

    def test_pick_technique_prefers_blend_over_hard_cut(self) -> None:
        # Same tempo, clashing key → filtered blend, not a slam cut.
        tech = pick_technique(
            {"bpm": 100.0, "key": "C"},
            {"bpm": 100.5, "key": "F#"},
            {"score": 0.4, "lyric_score": 0.0, "chroma_score": 0.0, "reasons": []},
        )
        self.assertEqual(tech["technique"], "key_adjusted_blend")
        self.assertIn("key_blend", tech["moves"])
        self.assertLessEqual(abs(tech["pitch_adjust_semitones"]), 2)
        adjusted_score, _ = key_compatibility("C", tech["pitch_adjust_target"])
        self.assertGreaterEqual(adjusted_score, 0.85)
        self.assertNotIn("hard_cut", tech["moves"])
        self.assertGreaterEqual(tech["transition_beats"], 12)
        # Moderate tempo gap → tempo_gap_blend, not hard cut.
        gap = pick_technique(
            {"bpm": 90.0, "key": "Am"},
            {"bpm": 140.0, "key": "Am"},
            {"score": 0.3, "lyric_score": 0.0, "chroma_score": 0.0, "reasons": []},
        )
        self.assertIn(gap["technique"], {"tempo_gap_blend", "half_time_or_cut"})
        if gap["technique"] == "tempo_gap_blend":
            self.assertNotIn("hard_cut", gap["moves"])

    def test_pitch_adjust_uses_smallest_harmonic_bridge(self) -> None:
        adjustment = pitch_adjust_for_blend("C", "F#")
        self.assertIsNotNone(adjustment)
        self.assertEqual(abs(adjustment["semitones"]), 1)
        self.assertGreaterEqual(adjustment["compatibility"], 0.85)
        camelot = pitch_adjust_for_blend("8B", "2B")
        self.assertIsNotNone(camelot)
        self.assertEqual(abs(camelot["semitones"]), 1)
        self.assertIsNone(pitch_adjust_for_blend("Am", "Am"))
        self.assertIsNone(pitch_adjust_for_blend(None, "F#"))

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

    def test_title_search_variants_fix_many_man(self) -> None:
        variants = title_search_variants("Many Man (Wish Death)")
        self.assertTrue(any("Many Men" in v for v in variants))
        self.assertEqual(key_from_control(17.0), "Em")

    def test_apply_brief_negation_beats_positive(self) -> None:
        profile, notes = apply_brief(PROFILES["dj-showcase"], "smooth, longer blends, no tricks")
        self.assertEqual(profile.flourish_every, 0)
        self.assertTrue(any("flourishes off" in note for note in notes))
        self.assertTrue(any("longer" in note for note in notes))
        # "no tricks" must not also fire the "tricks" positive branch.
        self.assertFalse(any("every transition" in note for note in notes))

    def test_dj_notes_directives_override_cue_and_ride(self) -> None:
        directives = track_directives(
            {
                "dj_notes": (
                    "Skip the spoken intro. cue_seconds=113.428; "
                    "ride_phrases=2; full_track"
                )
            }
        )
        self.assertEqual(directives["cue_seconds"], 113.428)
        self.assertEqual(directives["ride_phrases"], 2)
        self.assertIsNone(directives["ride_beats"])
        self.assertIsNone(directives["play_bpm"])
        self.assertIsNone(directives["entry_style"])
        self.assertIsNone(directives["opener_style"])
        self.assertIsNone(directives["landing_seconds"])
        self.assertIsNone(directives["landing_beats"])
        self.assertTrue(directives["full_track"])

    def test_track_entry_directives_override_transition(self) -> None:
        tracks = [
            {
                "track_id": "/music/out.mp3",
                "artist": "Out",
                "title": "Out",
                "bpm": 140.0,
                "key": "Am",
            },
            {
                "track_id": "/music/drop.mp3",
                "artist": "Drop",
                "title": "Drop",
                "bpm": 95.0,
                "key": "Am",
                "dj_notes": "cue_seconds=0; entry_style=beat_drop; play_bpm=100",
            },
            {
                "track_id": "/music/blend.mp3",
                "artist": "Blend",
                "title": "Blend",
                "bpm": 92.0,
                "key": "Am",
                "dj_notes": "entry_style=gentle_blend",
            },
        ]
        plan = build_plan(
            tracks,
            count=3,
            seconds_per_track=20.0,
            affinity_lookup={},
        )
        transitions = [
            event for event in plan["events"] if event["op"] == "transition"
        ]
        self.assertEqual(transitions[0]["technique"], "beat_drop_entry")
        self.assertEqual(transitions[0]["moves"], ["brake_out", "hard_cut"])
        self.assertEqual(transitions[0]["incoming_bpm_target"], 100.0)
        self.assertEqual(transitions[1]["technique"], "tempo_bridge_blend")
        self.assertEqual(transitions[1]["showcase_move"], "gentle_blend")
        self.assertGreaterEqual(transitions[1]["transition_beats"], 24)

    def test_opener_effect_and_verse_landing_cue(self) -> None:
        tracks = [
            {
                "track_id": "/music/opener.mp3",
                "artist": "Opener",
                "title": "Iconic Intro",
                "bpm": 93.4,
                "key": "Bbm",
                "dj_notes": "cue_seconds=0; opener_style=echo_tease_drop",
            },
            {
                "track_id": "/music/verse.mp3",
                "artist": "Rapper",
                "title": "Verse Track",
                "bpm": 91.3,
                "key": "Bb",
                "dj_notes": (
                    "entry_style=verse_landing; landing_seconds=28.740; "
                    "landing_beats=24; ride_beats=80"
                ),
            },
        ]
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=20.0,
            affinity_lookup={},
        )
        ops = [event["op"] for event in plan["events"]]
        self.assertIn("opener_effect", ops)
        # juggle_intro-style openers reuse deck 2 to juggle a second copy of
        # the opener track and leave it loaded there — a bare recue can only
        # re-seek whatever's currently loaded, not reload it, so this must be
        # an explicit "load" of the real second track or the first
        # transition would crossfade back into the opener instead.
        self.assertEqual(ops[ops.index("opener_effect") + 1], "load")
        verse = plan["tracks"][1]
        self.assertEqual(verse["cue_source"], "dj_notes_landing")
        self.assertAlmostEqual(verse["cue_seconds"], 12.968, places=3)
        transition = next(
            event for event in plan["events"] if event["op"] == "transition"
        )
        self.assertEqual(transition["technique"], "verse_landing_blend")
        self.assertEqual(transition["transition_beats"], 24)
        self.assertEqual(transition["landing_seconds"], 28.74)
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        self.assertEqual(body["beats"], 63)

    def test_smooth_opening_brief_builds_long_trick_free_blends(self) -> None:
        profile, notes = apply_brief(
            PROFILES["dj-showcase"],
            "smooth opening transitions",
        )
        self.assertEqual(profile.smooth_opening_transitions, 7)
        self.assertTrue(any("first 7 transitions" in note for note in notes))
        self.assertFalse(any("longer rides" in note for note in notes))

        tracks = [
            {
                "track_id": f"/music/{i}.mp3",
                "artist": f"Artist{i}",
                "title": f"Title{i}",
                "bpm": 88 + i,
                "key": "Am",
            }
            for i in range(9)
        ]
        plan = build_plan(
            tracks,
            count=len(tracks),
            seconds_per_track=20.0,
            affinity_lookup={},
            profile=profile,
        )
        forbidden = {
            "optional_scratch_in",
            "optional_loop_roll_out",
            "optional_transformer_cuts",
            "stutter_fill",
            "censor_fill",
            "brake_out",
            "spinback_out",
            "hard_cut",
        }
        transitions = [
            event for event in plan["events"] if event["op"] == "transition"
        ]
        for transition in transitions[:7]:
            self.assertGreaterEqual(transition["transition_beats"], 24)
            self.assertEqual(transition["showcase_move"], "smooth_opening")
            self.assertTrue(forbidden.isdisjoint(transition["moves"]))

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
                profile_name="mix-to-listen",
                mix_brief="clean, minimal",
                tracks=3,
                out=out,
            )
            self.assertTrue(out.exists())
            self.assertEqual(plan["track_count"], 3)
            self.assertEqual(plan["profile"]["name"], "mix-to-listen")
            self.assertIn("flourishes off", " ".join(plan["profile"]["brief_adjustments"]))
            summary = plan_summary(plan, plan_path=out)
            self.assertTrue(summary["dry_run_ok"])
            self.assertEqual(summary["track_count"], 3)
            self.assertEqual(summary["segment_count"], 2)
            self.assertGreater(summary["event_count"], 0)
            self.assertEqual(summary["plan_path"], str(out))
