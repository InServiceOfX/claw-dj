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
    snap_to_lyric_line,
    track_directives,
)
from brain.dj_formats import get_format
from brain.lyrics import lyric_overlap, title_search_variants, tokens
from brain.mix_graph import key_compatibility
from brain.mix_profiles import PROFILES, apply_brief


class MixPlanTest(TestCase):
    def test_hiphop_rnb_format_lands_chorus_and_intro_on_the_one(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3",
                "artist": "Song A",
                "title": "Outgoing",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": "cue_seconds=0",
            },
            {
                "track_id": "/music/b.mp3",
                "artist": "Song B",
                "title": "Incoming",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": "intro_seconds=0",
            },
        ]
        phrases = {
            track["track_id"]: {
                "bpm": 120.0,
                "first_beat_seconds": 0.0,
                "intro": {
                    "cue_seconds": 0.0,
                    "beat_index": 0,
                    "confidence": 1.0,
                },
            }
            for track in tracks
        }
        timeline = {
            "/music/a.mp3": [
                {
                    "kind": "chorus",
                    "start": 32.0,
                    "end": 48.0,
                    "bar_start": 32.0,
                    "beat_index": 64,
                }
            ]
        }
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=20.0,
            affinity_lookup={},
            phrase_lookup=phrases,
            lyric_segment_lookup=timeline,
            dj_format=get_format("hiphop-rnb-8bar"),
        )
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        body = next(e for e in plan["events"] if e["op"] == "play_body")
        self.assertEqual(plan["dj_format"]["name"], "hiphop-rnb-8bar")
        self.assertEqual(transition["technique"], "dj_format_chorus_to_intro")
        self.assertEqual(transition["transition_beats"], 32)
        self.assertEqual(transition["format_exit_beat_index"] % 4, 0)
        self.assertEqual(transition["format_entry_beat_index"] % 4, 0)
        self.assertEqual(body["beats"], 63)
        self.assertEqual(plan["tracks"][1]["cue_source"], "dj_format_human_intro")

    def test_hiphop_rnb_format_fails_closed_without_acapella_hook_marker(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3",
                "artist": "Song A",
                "title": "Outgoing",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": (
                    "cue_seconds=0; format_recipe=acapella_hook_swap"
                ),
            },
            {
                "track_id": "/music/b.mp3",
                "artist": "Song B",
                "title": "Incoming",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": "intro_seconds=0",
            },
        ]
        phrases = {
            track["track_id"]: {
                "bpm": 120.0,
                "first_beat_seconds": 0.0,
                "intro": {"cue_seconds": 0.0, "beat_index": 0},
            }
            for track in tracks
        }
        with self.assertRaisesRegex(ValueError, "hook_acapella_seconds"):
            build_plan(
                tracks,
                count=2,
                seconds_per_track=20.0,
                affinity_lookup={},
                phrase_lookup=phrases,
                dj_format=get_format("hiphop-rnb-8bar"),
            )

    def test_hiphop_rnb_intro_loop_recipe_is_declarative_and_8_bars(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3",
                "artist": "Song A",
                "title": "Outgoing",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": (
                    "cue_seconds=0; chorus_seconds=32; "
                    "format_recipe=intro_loop_under_entry; "
                    "intro_loop_seconds=0"
                ),
            },
            {
                "track_id": "/music/b.mp3",
                "artist": "Song B",
                "title": "Incoming",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": "intro_seconds=0",
            },
        ]
        phrases = {
            track["track_id"]: {
                "bpm": 120.0,
                "first_beat_seconds": 0.0,
                "intro": {"cue_seconds": 0.0, "beat_index": 0},
            }
            for track in tracks
        }
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=20.0,
            affinity_lookup={},
            phrase_lookup=phrases,
            dj_format=get_format("hiphop-rnb-8bar"),
        )
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        self.assertEqual(
            transition["technique"],
            "dj_format_intro_loop_under_entry",
        )
        self.assertEqual(transition["outgoing_loop_beats"], 32)
        self.assertIn("outgoing_intro_loop_8_bars", transition["moves"])

    def test_guided_format_keeps_beat_one_and_labels_fallback(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3",
                "artist": "Song A",
                "title": "No Detected Chorus",
                "bpm": 120.0,
                "key": "Am",
            },
            {
                "track_id": "/music/b.mp3",
                "artist": "Song B",
                "title": "Unverified Intro",
                "bpm": 120.0,
                "key": "Am",
            },
        ]
        phrases = {
            "/music/a.mp3": {
                "bpm": 120.0,
                "first_beat_seconds": 0.0,
                "intro": {
                    "cue_seconds": 8.0,
                    "beat_index": 16,
                    "confidence": 0.6,
                },
            },
            "/music/b.mp3": {
                "bpm": 120.0,
                "first_beat_seconds": 0.0,
                "intro": {
                    "cue_seconds": 11.0,
                    "beat_index": 22,
                    "confidence": 0.5,
                },
            },
        }
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=20.0,
            affinity_lookup={},
            phrase_lookup=phrases,
            dj_format=get_format("hiphop-rnb-guided"),
        )
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        incoming = plan["tracks"][1]
        self.assertEqual(plan["dj_format"]["enforcement"], "guided")
        self.assertEqual(transition["format_compliance"], "guided_fallback")
        self.assertEqual(transition["format_recipe"], "phrase_aligned_fallback")
        self.assertEqual(transition["format_exit_beat_index"] % 4, 0)
        self.assertEqual(transition["format_entry_beat_index"] % 4, 0)
        # The raw intro candidate was beat 22 (not a downbeat); guided mode
        # moves forward to beat 24 and derives the corresponding time.
        self.assertEqual(incoming["cue_beat_index"], 24)
        self.assertEqual(incoming["cue_seconds"], 12.0)

    def test_guided_format_promotes_complete_evidence_to_expert_recipe(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3",
                "artist": "Song A",
                "title": "Verified Chorus",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": "cue_seconds=0; chorus_seconds=32",
            },
            {
                "track_id": "/music/b.mp3",
                "artist": "Song B",
                "title": "Verified Intro",
                "bpm": 120.0,
                "key": "Am",
                "dj_notes": "intro_seconds=0",
            },
        ]
        phrases = {
            track["track_id"]: {
                "bpm": 120.0,
                "first_beat_seconds": 0.0,
                "intro": {"cue_seconds": 0.0, "beat_index": 0},
            }
            for track in tracks
        }
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=20.0,
            affinity_lookup={},
            phrase_lookup=phrases,
            dj_format=get_format("hiphop-rnb-guided"),
        )
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        self.assertEqual(transition["format_compliance"], "expert_recipe")
        self.assertEqual(transition["format_recipe"], "chorus_to_intro")
        self.assertEqual(transition["technique"], "dj_format_chorus_to_intro")
        summary = plan_summary(plan)
        self.assertEqual(summary["format_compliance"], {"expert_recipe": 1})

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

    def test_hard_cuts_are_capped_at_one_per_mix_and_never_back_to_back(self) -> None:
        """"Use sparingly" is enforced by the planner, not left to the recipe.

        Four tracks whose tempos alternate wildly with no lineage or chroma
        support: every pairing is exactly what pick_technique answers with
        half_time_or_cut. Without a budget the plan would brake the platter
        to a stop three times, twice of them back to back (heard live,
        2026-08-03). At most the first survives; the rest downgrade.
        """
        tracks = [
            {"track_id": "/music/a.mp3", "artist": "A", "title": "A",
             "bpm": 90.0, "key": "C", "duration_seconds": 300.0},
            {"track_id": "/music/b.mp3", "artist": "B", "title": "B",
             "bpm": 150.0, "key": "F#", "duration_seconds": 300.0},
            {"track_id": "/music/c.mp3", "artist": "C", "title": "C",
             "bpm": 92.0, "key": "C", "duration_seconds": 300.0},
            {"track_id": "/music/d.mp3", "artist": "D", "title": "D",
             "bpm": 152.0, "key": "F#", "duration_seconds": 300.0},
        ]
        plan = build_plan(
            tracks,
            count=4,
            seconds_per_track=20.0,
            affinity_lookup={},
            phrase_lookup={},
        )
        techniques = [e["technique"] for e in plan["events"] if e["op"] == "transition"]
        hard_cuts = [t for t in techniques if t == "half_time_or_cut"]
        self.assertGreaterEqual(len(techniques), 3, techniques)
        self.assertLessEqual(len(hard_cuts), 1, techniques)
        # And never two in a row, whatever the budget allowed.
        for earlier, later in zip(techniques, techniques[1:]):
            self.assertFalse(
                earlier == "half_time_or_cut" and later == "half_time_or_cut",
                f"back-to-back hard cuts in {techniques}",
            )
        # A declined hard cut must become a real blend, not silently keep
        # brake_out/hard_cut moves under a different technique name.
        for event in plan["events"]:
            if event["op"] == "transition" and event["technique"] == "tempo_gap_blend":
                self.assertNotIn("hard_cut", event["moves"])
                self.assertNotIn("brake_out", event["moves"])

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

    def test_tempo_gap_blend_never_forces_a_hard_sync(self) -> None:
        # avoid_silence=True guarantees tempo_gap_blend over half_time_or_cut
        # for a deterministic assertion. "sync" fully snaps the incoming
        # deck to whatever the outgoing deck is ACTUALLY playing at, which
        # for a gap this large means an audible, jarring speed change —
        # heard live, 2026-07-16, on Sade — The Sweetest Taboo entering
        # from a track held at a much higher bumped tempo: "the speed up...
        # shouldn't be that fast, it sounds terrible." rate_nudge_in already
        # gives a small bounded taste of movement without a full sync-lock.
        tech = pick_technique(
            {"bpm": 90.0, "key": "Am"},
            {"bpm": 140.0, "key": "Am"},
            {"score": 0.3, "lyric_score": 0.0, "chroma_score": 0.0, "reasons": []},
            avoid_silence=True,
        )
        self.assertEqual(tech["technique"], "tempo_gap_blend")
        self.assertNotIn("sync", tech["moves"])
        self.assertIn("rate_nudge_in", tech["moves"])

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

    def test_snap_to_lyric_line_moves_forward_to_next_word(self) -> None:
        lookup = {"/music/a.mp3": [2.38, 37.18, 44.26, 49.00, 59.87]}
        # Cassie — Me&U's real case: beatgrid/energy picker landed at 48.2s,
        # mid-line ("...wanna see if it's true", 44.26-49.00) — must snap
        # forward to the next line, never backward into content already
        # implicitly skipped.
        snapped, did_snap = snap_to_lyric_line(48.2053, "/music/a.mp3", lookup)
        self.assertTrue(did_snap)
        self.assertAlmostEqual(snapped, 49.00)

    def test_snap_to_lyric_line_exact_hit_is_a_noop(self) -> None:
        lookup = {"/music/a.mp3": [2.38, 37.18]}
        snapped, did_snap = snap_to_lyric_line(37.18, "/music/a.mp3", lookup)
        self.assertTrue(did_snap)
        self.assertAlmostEqual(snapped, 37.18)

    def test_snap_to_lyric_line_gives_up_beyond_cap(self) -> None:
        lookup = {"/music/a.mp3": [2.38, 60.0]}
        snapped, did_snap = snap_to_lyric_line(48.2, "/music/a.mp3", lookup, max_snap_s=6.0)
        self.assertFalse(did_snap)
        self.assertEqual(snapped, 48.2)

    def test_snap_to_lyric_line_no_data_is_a_noop(self) -> None:
        snapped, did_snap = snap_to_lyric_line(48.2, "/music/unknown.mp3", {})
        self.assertFalse(did_snap)
        self.assertEqual(snapped, 48.2)

    def test_snap_to_lyric_line_never_snaps_backward(self) -> None:
        # Every candidate line is behind the cue point -> nothing to snap to.
        lookup = {"/music/a.mp3": [2.38, 10.0, 20.0]}
        snapped, did_snap = snap_to_lyric_line(48.2, "/music/a.mp3", lookup)
        self.assertFalse(did_snap)
        self.assertEqual(snapped, 48.2)

    def test_build_plan_snaps_phrase_body_cue_off_a_mid_word_landing(self) -> None:
        tracks = [
            {
                "track_id": "/music/opener.mp3", "artist": "Cassie", "title": "Me&U",
                "bpm": 100.0, "key": "Am", "duration_seconds": 192.4,
            },
            {
                "track_id": "/music/next.mp3", "artist": "Someone", "title": "Else",
                "bpm": 100.0, "key": "Am",
            },
        ]
        phrase_lookup = {
            "/music/opener.mp3": {
                "intro": {"cue_seconds": 0.2, "beat_index": 0, "confidence": 0.7, "score": 1.1},
                "body": {"cue_seconds": 48.2053, "beat_index": 80, "confidence": 0.53, "score": 0.68},
            }
        }
        lyric_line_lookup = {"/music/opener.mp3": [2.38, 37.18, 44.26, 49.00, 59.87]}
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            phrase_lookup=phrase_lookup, lyric_line_lookup=lyric_line_lookup,
        )
        load_event = next(
            e for e in plan["events"] if e["op"] == "load" and e["track_id"] == "/music/opener.mp3"
        )
        self.assertAlmostEqual(load_event["cue_seconds"], 49.00)
        self.assertEqual(load_event["cue_source"], "phrase_body+lyric_snap")

    def test_pickup_beats_starts_early_so_the_downbeat_is_on_one(self) -> None:
        # Remix Report ep.12: brake + Jay-Z sample is one bar before the
        # In Da Club beat. Cue 0, land on beat 4.
        tracks = [
            {
                "track_id": "/music/out.mp3",
                "artist": "Out",
                "title": "Outgoing",
                "bpm": 92.0,
                "key": "C#m",
                "dj_notes": "cue_seconds=0",
            },
            {
                "track_id": "/music/break.mp3",
                "artist": "Holla Boyz",
                "title": "Show Me Love In Da Club",
                "bpm": 92.0,
                "key": "C#m",
                "dj_notes": "pickup_beats=4",
            },
        ]
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={}
        )
        incoming = next(
            event
            for event in plan["events"]
            if event.get("track_id") == "/music/break.mp3"
            and event["op"] in {"load", "preload_after_transition"}
        )
        self.assertEqual(incoming["cue_seconds"], 0.0)
        self.assertEqual(incoming["cue_source"], "dj_notes_pickup")
        self.assertEqual(incoming["pickup_beats"], 4)
        self.assertAlmostEqual(incoming["landing_seconds"], 4 * 60.0 / 92.0, places=3)
        transition = next(
            event for event in plan["events"] if event["op"] == "transition"
        )
        self.assertEqual(transition["technique"], "pickup_on_one_blend")
        self.assertGreaterEqual(transition["transition_beats"], 4)

    def test_ten_bar_chorus_waits_two_bars_before_eight_bar_intro(self) -> None:
        tracks = [
            {
                "track_id": "/music/over.mp3",
                "artist": "Drake",
                "title": "Over",
                "bpm": 76.0,
                "key": "Am",
                "dj_notes": "cue_seconds=0; ride_beats=32; chorus_bars=10",
            },
            {
                "track_id": "/music/next.mp3",
                "artist": "Jay-Z",
                "title": "You Don't Know",
                "bpm": 87.0,
                "key": "Am",
                "dj_notes": "cue_seconds=0",
            },
        ]
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={}
        )
        body = next(e for e in plan["events"] if e["op"] == "play_body")
        self.assertEqual(body["beats"], 40)
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        self.assertEqual(transition["outgoing_chorus_bars"], 10)
        self.assertIn("wait 2 bars", transition["notes"])

    def test_six_bar_chorus_skips_two_bars_of_incoming_intro(self) -> None:
        tracks = [
            {
                "track_id": "/music/stick.mp3",
                "artist": "50 Cent",
                "title": "Magic Stick",
                "bpm": 93.0,
                "key": "Am",
                "dj_notes": "cue_seconds=0; ride_beats=32; chorus_bars=6",
            },
            {
                "track_id": "/music/next.mp3",
                "artist": "Next",
                "title": "Eight Bar Intro",
                "bpm": 93.0,
                "key": "Am",
                "dj_notes": "cue_seconds=0",
            },
        ]
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={}
        )
        incoming = next(
            e
            for e in plan["events"]
            if e.get("track_id") == "/music/next.mp3"
            and e["op"] in {"load", "preload_after_transition"}
        )
        self.assertEqual(incoming["chorus_intro_skip_bars"], 2)
        self.assertAlmostEqual(incoming["cue_seconds"], 2 * 4 * 60.0 / 93.0, places=3)

    def test_wrapped_beatgrid_cue_is_not_copied_into_the_plan(self) -> None:
        # 2**64-77 frames / 44100 Hz — Candy Shop's unsigned Mixxx first beat.
        wrapped = 418293516410647.44
        tracks = [
            {
                "track_id": "/music/candy.mp3",
                "artist": "50 Cent",
                "title": "Candy Shop",
                "bpm": 98.0,
                "key": "Bm",
                "duration_seconds": 209.13,
            },
            {
                "track_id": "/music/next.mp3",
                "artist": "Someone",
                "title": "Else",
                "bpm": 98.0,
                "key": "Bm",
                "duration_seconds": 200.0,
            },
        ]
        phrase_lookup = {
            "/music/candy.mp3": {
                "bpm": 98.0,
                "first_beat_seconds": wrapped,
                "cue_seconds": wrapped,
                "beat_index": 0,
                "confidence": 0.0,
                "duration": 209.13,
            }
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            phrase_lookup=phrase_lookup,
        )
        load_event = next(
            e for e in plan["events"]
            if e["op"] == "load" and e["track_id"] == "/music/candy.mp3"
        )
        self.assertEqual(load_event["cue_seconds"], 0.0)
        self.assertIn("sanitized", load_event["cue_source"])
        body = next(
            e for e in plan["events"]
            if e.get("track") == "50 Cent — Candy Shop" and e["op"] == "play_body"
        )
        self.assertEqual(body["phase_anchor"]["first_beat_seconds"], 0.0)

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

    def test_apply_brief_avoid_hard_cuts(self) -> None:
        profile, notes = apply_brief(
            PROFILES["dj-showcase"], "great song choices, just use hard cuts sparingly"
        )
        self.assertTrue(profile.avoid_silence)
        self.assertTrue(any("hard cut" in note for note in notes))

    def test_apply_brief_default_profile_keeps_hard_cuts_available(self) -> None:
        profile, _ = apply_brief(PROFILES["dj-showcase"], "smooth, longer blends")
        self.assertFalse(profile.avoid_silence)

    def test_dj_notes_directives_override_cue_and_ride(self) -> None:
        directives = track_directives(
            {
                "dj_notes": (
                    "Skip the spoken intro. cue_seconds=113.428; "
                    "ride_phrases=2; juggle_chops=3; full_track"
                )
            }
        )
        self.assertEqual(directives["cue_seconds"], 113.428)
        self.assertEqual(directives["ride_phrases"], 2)
        self.assertIsNone(directives["ride_beats"])
        self.assertIsNone(directives["play_bpm"])
        self.assertIsNone(directives["entry_style"])
        self.assertIsNone(directives["opener_style"])
        self.assertEqual(directives["juggle_chops"], 3)
        self.assertIsNone(directives["landing_seconds"])
        self.assertIsNone(directives["landing_beats"])
        self.assertTrue(directives["full_track"])
        self.assertFalse(directives["no_flourish"])
        self.assertFalse(directives["trust_cue_seconds"])

    def test_ordinary_explicit_cue_is_snapped_to_analyzed_beat(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3", "artist": "A", "title": "A",
                "bpm": 100.0, "key": "Am", "duration_seconds": 180.0,
                "dj_notes": "cue_seconds=0",
            },
            {
                "track_id": "/music/b.mp3", "artist": "B", "title": "B",
                "bpm": 100.0, "key": "Am", "duration_seconds": 180.0,
                "dj_notes": "cue_seconds=6",
            },
        ]
        phases = {
            track["track_id"]: {
                "bpm": 100.0, "first_beat_seconds": 0.3,
                "snare_parity": 1, "confidence": 0.8,
            }
            for track in tracks
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=phases,
        )
        opener = plan["tracks"][0]
        self.assertEqual(opener["cue_seconds_requested"], 0.0)
        self.assertEqual(opener["cue_seconds"], 0.3)
        self.assertEqual(opener["cue_beat_index"], 0)
        self.assertEqual(opener["cue_source"], "dj_notes+beat_snap")

    def test_trusted_off_grid_cue_is_preserved_and_not_given_fake_index(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3", "artist": "A", "title": "A",
                "bpm": 100.0, "key": "Am", "duration_seconds": 180.0,
                "dj_notes": "cue_seconds=0; trust_cue_seconds; trust_ride_beats; ride_beats=32",
            },
            {
                "track_id": "/music/b.mp3", "artist": "B", "title": "B",
                "bpm": 100.0, "key": "Am", "duration_seconds": 180.0,
            },
        ]
        phases = {
            track["track_id"]: {
                "bpm": 100.0, "first_beat_seconds": 0.3,
                "snare_parity": 1, "confidence": 0.8,
            }
            for track in tracks
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=phases,
        )
        opener = plan["tracks"][0]
        self.assertEqual(opener["cue_seconds"], 0.0)
        self.assertNotIn("cue_beat_index", opener)
        self.assertAlmostEqual(opener["cue_grid_offset_beats"], -0.5)

    def test_guided_format_does_not_fail_trusted_file_head_opener(self) -> None:
        # Live 50centgunitera GUI: What Up Gangsta cue_seconds=0 +
        # trust_cue_seconds, Mixxx first_beat ~45ms later. Guided format
        # used to abort the whole 148-track build.
        tracks = [
            {
                "track_id": "/music/gangsta.mp3",
                "artist": "50 Cent",
                "title": "What Up Gangsta",
                "bpm": 82.5,
                "key": "C#m",
                "dj_notes": (
                    "cue_seconds=0; trust_cue_seconds; "
                    "opener_style=juggle_intro; ride_beats=200; trust_ride_beats"
                ),
            },
            {
                "track_id": "/music/needem.mp3",
                "artist": "50 Cent",
                "title": "I Don't Need 'Em",
                "bpm": 83.0,
                "key": "G#m",
                "dj_notes": "cue_seconds=0",
            },
        ]
        phrases = {
            "/music/gangsta.mp3": {
                "bpm": 82.51467955526623,
                "first_beat_seconds": 0.044853,
            },
            "/music/needem.mp3": {
                "bpm": 83.0,
                "first_beat_seconds": 0.0,
            },
        }
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=20.0,
            affinity_lookup={},
            phrase_lookup=phrases,
            dj_format=get_format("hiphop-rnb-guided"),
        )
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        self.assertEqual(plan["tracks"][0]["cue_seconds"], 0.0)
        self.assertNotIn("cue_beat_index", plan["tracks"][0])
        self.assertIn(transition["format_compliance"], {"guided_fallback", "expert_recipe"})

    def test_guided_format_honors_trust_ride_beats_and_verse_landing(self) -> None:
        # Guided exit-anchor math used to overwrite ride_beats even when the
        # DJ note locked the length (Compton → Southside interpolation).
        tracks = [
            {
                "track_id": "/music/compton.mp3",
                "artist": "N.W.A",
                "title": "Straight Outta Compton",
                "bpm": 102.83333333333333,
                "key": "Ab",
                "duration_seconds": 258.4,
                "dj_notes": (
                    "cue_seconds=12.24; trust_cue_seconds; "
                    "ride_beats=92; trust_ride_beats; play_bpm=102.83; no_flourish"
                ),
            },
            {
                "track_id": "/music/southside.mp3",
                "artist": "G-Unit",
                "title": "Straight Outta Southside",
                "bpm": 92.21986528181748,
                "key": "Em",
                "duration_seconds": 156.1,
                "dj_notes": (
                    "entry_style=verse_landing; landing_seconds=11.36; "
                    "landing_beats=16; play_bpm=92.22; ride_beats=192; "
                    "trust_ride_beats; no_flourish"
                ),
            },
        ]
        phrases = {
            "/music/compton.mp3": {
                "bpm": 102.83333333333333,
                "first_beat_seconds": 0.56873,
                "intro": {"beat_index": 32, "cue_seconds": 19.24},
            },
            "/music/southside.mp3": {
                "bpm": 92.21986528181748,
                "first_beat_seconds": 0.079909,
                "intro": {"beat_index": 16, "cue_seconds": 10.49},
            },
        }
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=40.0,
            affinity_lookup={},
            phrase_lookup=phrases,
            dj_format=get_format("hiphop-rnb-guided"),
        )
        incoming = plan["tracks"][1]
        self.assertEqual(incoming["cue_source"], "guided_human_landing_downbeat")
        self.assertEqual(incoming["cue_beat_index"], 0)
        self.assertAlmostEqual(incoming["cue_seconds"], 0.08, places=2)
        self.assertAlmostEqual(incoming["landing_seconds"], 11.36, places=2)
        body = next(e for e in plan["events"] if e["op"] == "play_body")
        self.assertEqual(body["beats"], 92)
        self.assertTrue(body.get("trust_ride_beats"))
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        self.assertEqual(transition["technique"], "verse_landing_blend")
        self.assertEqual(transition["transition_beats"], 16)
        self.assertAlmostEqual(transition["landing_seconds"], 11.36, places=2)
        self.assertAlmostEqual(transition["incoming_bpm_target"], 92.22, places=2)

    def test_file_head_cue_never_gets_a_hypothetical_negative_beat(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3", "artist": "A", "title": "A",
                "bpm": 100.0, "key": "Am", "duration_seconds": 180.0,
                "dj_notes": "cue_seconds=0; ride_beats=32",
            },
            {
                "track_id": "/music/b.mp3", "artist": "B", "title": "B",
                "bpm": 100.0, "key": "Am", "duration_seconds": 180.0,
            },
        ]
        phases = {
            track["track_id"]: {
                "bpm": 100.0, "first_beat_seconds": 0.5,
                "snare_parity": 1, "confidence": 0.8,
            }
            for track in tracks
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=phases,
        )
        opener = plan["tracks"][0]
        self.assertEqual(opener["cue_beat_index"], 0)
        self.assertEqual(opener["cue_seconds"], 0.5)

    def test_fraction_fallback_becomes_a_grid_aligned_absolute_cue(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3", "artist": "A", "title": "A",
                "bpm": 100.0, "key": "Am", "duration_seconds": 180.0,
                "dj_notes": "ride_beats=32",
            },
            {
                "track_id": "/music/b.mp3", "artist": "B", "title": "B",
                "bpm": 100.0, "key": "Am", "duration_seconds": 322.5,
            },
        ]
        phases = {
            track["track_id"]: {
                "bpm": 100.0, "first_beat_seconds": 0.1,
                "snare_parity": 1, "confidence": 0.8,
            }
            for track in tracks
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=phases,
        )
        incoming = plan["tracks"][1]
        self.assertNotIn("cue_fraction", incoming)
        self.assertEqual(incoming["cue_seconds_requested"], 32.25)
        self.assertEqual(incoming["cue_seconds"], 32.5)
        self.assertEqual(incoming["cue_beat_index"], 54)
        self.assertEqual(incoming["cue_source"], "fraction_fallback+beat_snap")

    def test_dj_notes_last_directive_wins_over_stale_prose_mentions(self) -> None:
        # A note narrating its own history ("was ride_beats=128, trimmed to
        # ride_beats=112...") before the real final directive must not let
        # an earlier, stale number win -- found live twice in one session
        # before the parser itself was fixed to always prefer the last match.
        directives = track_directives(
            {
                "dj_notes": (
                    "Ride length trimmed twice already, first the full "
                    "third verse (ride_beats=128), then partway into it "
                    "(ride_beats=112) -- still too long, trim further. "
                    "cue_seconds=61.97; ride_beats=96"
                )
            }
        )
        self.assertEqual(directives["ride_beats"], 96)
        self.assertEqual(directives["cue_seconds"], 61.97)

    def test_skip_from_to_emits_a_64_beat_in_play_jump(self) -> None:
        tracks = [
            {
                "track_id": "/music/igetmoney.mp3",
                "artist": "50 Cent",
                "title": "I Get Money (1, 2, 3 Remix) (Album)",
                "bpm": 92.3,
                "key": "A",
                "duration_seconds": 272.8,
                "dj_notes": (
                    "cue_seconds=0.36; trust_cue_seconds; "
                    "skip_from_seconds=91.34; skip_to_seconds=132.93; "
                    "ride_beats=268; trust_ride_beats"
                ),
            },
            {
                "track_id": "/music/next.mp3",
                "artist": "50 Cent",
                "title": "Heat Ja Diss (feat. G-Unit)",
                "bpm": 93.8,
                "key": "D",
                "duration_seconds": 178.0,
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        body = next(
            event
            for event in plan["events"]
            if event.get("op") == "play_body" and "I Get Money" in event.get("track", "")
        )
        self.assertEqual(body.get("skip_beats"), 64)
        self.assertGreaterEqual(body.get("skip_after_beats"), 140)
        self.assertLessEqual(body.get("skip_after_beats"), 142)
        self.assertEqual(body.get("beats"), 268)
        self.assertAlmostEqual(body.get("skip_from_seconds"), 91.34, places=2)
        self.assertAlmostEqual(body.get("skip_to_seconds"), 132.93, places=2)

    def test_skip_after_subtracts_incoming_blend_beats(self) -> None:
        tracks = [
            {
                "track_id": "/music/ludacris.mp3",
                "artist": "50 Cent",
                "title": "I Get Money (Feat. Ludacris) (Remix) (Exclu)",
                "bpm": 92.3,
                "key": "A",
                "duration_seconds": 200.0,
                "dj_notes": "cue_seconds=0; ride_beats=96; trust_ride_beats",
            },
            {
                "track_id": "/music/igetmoney.mp3",
                "artist": "50 Cent",
                "title": "I Get Money (1, 2, 3 Remix) (Album)",
                "bpm": 92.3,
                "key": "A",
                "duration_seconds": 272.8,
                "dj_notes": (
                    "cue_seconds=0.36; trust_cue_seconds; "
                    "skip_from_seconds=91.34; skip_to_seconds=132.93; "
                    "ride_beats=268; trust_ride_beats"
                ),
            },
            {
                "track_id": "/music/next.mp3",
                "artist": "50 Cent",
                "title": "Heat Ja Diss (feat. G-Unit)",
                "bpm": 93.8,
                "key": "D",
                "duration_seconds": 178.0,
            },
        ]
        plan = build_plan(
            tracks,
            count=3,
            seconds_per_track=20.0,
            affinity_lookup={},
            transition_beats_by_pair={("/music/ludacris.mp3", "/music/igetmoney.mp3"): 32},
        )
        body = next(
            event
            for event in plan["events"]
            if event.get("op") == "play_body" and "1, 2, 3 Remix" in event.get("track", "")
        )
        # 141 file beats from cue to skip_from, minus the 32-beat landing.
        self.assertGreaterEqual(body.get("skip_after_beats"), 108)
        self.assertLessEqual(body.get("skip_after_beats"), 110)
        self.assertEqual(body.get("skip_beats"), 64)

    def test_keep_blend_tempo_does_not_pin_native_or_settle(self) -> None:
        tracks = [
            {
                "track_id": "/music/compton.mp3",
                "artist": "N.W.A",
                "title": "Straight Outta Compton",
                "bpm": 102.83,
                "key": "Ab",
                "duration_seconds": 258.0,
                "dj_notes": "cue_seconds=2.9; ride_beats=108; trust_ride_beats",
            },
            {
                "track_id": "/music/southside.mp3",
                "artist": "G-Unit",
                "title": "Straight Outta Southside",
                "bpm": 92.22,
                "key": "Em",
                "duration_seconds": 200.0,
                "dj_notes": "keep_blend_tempo; no_flourish",
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        self.assertTrue(transition.get("keep_blend_tempo"))
        self.assertIsNone(transition.get("incoming_bpm_target"))
        self.assertIsNone(transition.get("incoming_settle_bpm"))
        self.assertIn("sync", transition.get("moves") or [])

    def test_vocal_over_bed_keeps_instrumental_live(self) -> None:
        tracks = [
            {
                "track_id": "/music/bed.mp3",
                "artist": "50 Cent",
                "title": "I'll Still Kill (Instrumental)",
                "bpm": 88.0,
                "key": "Dm",
                "duration_seconds": 218.0,
                "dj_notes": "cue_seconds=0.3; ride_beats=16; trust_ride_beats",
            },
            {
                "track_id": "/music/vocal.mp3",
                "artist": "50 Cent",
                "title": "Still Will (Acapella)",
                "bpm": 88.7,
                "key": "F",
                "duration_seconds": 220.0,
                "dj_notes": (
                    "entry_style=vocal_over_bed; ride_beats=96; "
                    "trust_ride_beats; no_flourish"
                ),
            },
            {
                "track_id": "/music/next.mp3",
                "artist": "Lloyd Banks",
                "title": "Ain't No Click",
                "bpm": 93.0,
                "key": "Dm",
                "duration_seconds": 200.0,
            },
        ]
        plan = build_plan(tracks, count=3, seconds_per_track=20.0, affinity_lookup={})
        transitions = [e for e in plan["events"] if e["op"] == "transition"]
        self.assertEqual(transitions[0]["technique"], "vocal_over_bed")
        self.assertEqual(transitions[0]["transition_beats"], 96)
        self.assertTrue(transitions[0].get("keep_outgoing_live"))
        self.assertEqual(transitions[0]["bed_track_id"], "/music/bed.mp3")
        self.assertEqual(transitions[0]["vocal_track_id"], "/music/vocal.mp3")
        bodies = [e for e in plan["events"] if e["op"] == "play_body"]
        self.assertEqual(len(bodies), 1)
        self.assertIn("I'll Still Kill (Instrumental)", bodies[0]["track"])
        self.assertEqual(transitions[1]["from_deck"], transitions[0]["from_deck"])
        self.assertIn("I'll Still Kill (Instrumental)", transitions[1]["from_track"])
        self.assertIn("Ain't No Click", transitions[1]["to_track"])
        vocal_over_idx = next(
            i for i, event in enumerate(plan["events"]) if event.get("technique") == "vocal_over_bed"
        )
        preloads_before = [
            event
            for event in plan["events"][:vocal_over_idx]
            if event.get("op") == "preload_after_transition"
        ]
        self.assertEqual(preloads_before, [])
        loads_after = [
            event
            for event in plan["events"][vocal_over_idx + 1 :]
            if event.get("op") == "load" and event.get("track_id") == "/music/next.mp3"
        ]
        self.assertEqual(len(loads_after), 1)
        self.assertEqual(loads_after[0]["deck"], transitions[0]["to_deck"])

    def test_get_up_over_outta_control_is_the_canonical_layer(self) -> None:
        from brain.stems import apply_vocal_layers, assert_vocals_layered

        tracks = [
            {
                "track_id": "/music/best-friend.mp3",
                "artist": "50 Cent",
                "title": "Best Friend",
                "bpm": 90.8,
                "key": "Db",
                "duration_seconds": 251.0,
            },
            {
                "track_id": "/music/get-up-acapella.mp3",
                "artist": "50 Cent",
                "title": "Get Up (Acapella)",
                "bpm": 186.0,
                "key": "F#",
                "duration_seconds": 166.0,
                "dj_notes": (
                    "entry_style=vocal_over_bed; ride_beats=96; "
                    "trust_ride_beats; no_flourish"
                ),
            },
            {
                "track_id": "/music/outta-inst.mp3",
                "artist": "50 Cent",
                "title": "Outta Control - Instrumental",
                "bpm": 92.0,
                "key": "Ebm",
                "duration_seconds": 249.0,
                "dj_notes": "cue_seconds=0.26; trust_cue_seconds; ride_beats=16; trust_ride_beats",
            },
            {
                "track_id": "/music/remix.mp3",
                "artist": "50 Cent",
                "title": "Out Of Control (Remix) (ft. Mobb Deep)",
                "bpm": 92.0,
                "key": "Ebm",
                "duration_seconds": 250.0,
            },
        ]
        layered, _ = apply_vocal_layers(tracks)
        self.assertEqual(
            [row["title"] for row in layered],
            [
                "Best Friend",
                "Outta Control - Instrumental",
                "Get Up (Acapella)",
                "Out Of Control (Remix) (ft. Mobb Deep)",
            ],
        )
        plan = build_plan(layered, count=4, seconds_per_track=20.0, affinity_lookup={})
        assert_vocals_layered(plan)
        layer = next(e for e in plan["events"] if e.get("technique") == "vocal_over_bed")
        self.assertTrue(layer.get("keep_outgoing_live"))
        self.assertEqual(layer["bed_track_id"], "/music/outta-inst.mp3")
        self.assertEqual(layer["vocal_track_id"], "/music/get-up-acapella.mp3")
        self.assertEqual(layer["transition_beats"], 96)
        bodies = [e["track"] for e in plan["events"] if e.get("op") == "play_body"]
        self.assertTrue(any("Outta Control - Instrumental" in track for track in bodies))
        self.assertFalse(any("Get Up (Acapella)" in track for track in bodies))

    def test_phrase_body_mid_verse_rewrites_to_zero(self) -> None:
        tracks = [
            {
                "track_id": "/music/on-fire.mp3",
                "artist": "Lloyd Banks",
                "title": "On Fire (Feat. 50 Cent)",
                "bpm": 95.0,
                "key": "Gm",
                "duration_seconds": 187.3,
            },
            {
                "track_id": "/music/next.mp3",
                "artist": "50 Cent",
                "title": "Disco Inferno",
                "bpm": 97.0,
                "key": "Gm",
                "duration_seconds": 200.0,
            },
        ]
        phrases = {
            "/music/on-fire.mp3": {
                "intro": {"cue_seconds": 0.2, "beat_index": 0, "confidence": 0.7, "score": 1.1},
                "body": {"cue_seconds": 41.35, "beat_index": 65, "confidence": 0.54, "score": 0.68},
            }
        }
        segments = {
            "/music/on-fire.mp3": [
                {"kind": "verse", "start": 3.60, "end": 12.92},
                {"kind": "chorus", "start": 12.92, "end": 27.75},
                {"kind": "verse", "start": 27.75, "end": 73.30},
                {"kind": "chorus", "start": 73.30, "end": 88.11},
            ]
        }
        plan = build_plan(
            tracks,
            count=2,
            seconds_per_track=40.0,
            affinity_lookup={},
            phrase_lookup=phrases,
            lyric_segment_lookup=segments,
        )
        load_event = next(
            event
            for event in plan["events"]
            if event.get("op") == "load" and event.get("track_id") == "/music/on-fire.mp3"
        )
        self.assertEqual(load_event["cue_seconds"], 0.0)
        self.assertIn("verse_guard_intro_top", str(load_event.get("cue_source")))

    def test_consecutive_vocals_layer_on_the_same_bed(self) -> None:
        tracks = [
            {
                "track_id": "/music/bed.mp3",
                "artist": "Lloyd Banks",
                "title": "On Fire (Instrumental)",
                "bpm": 94.83,
                "key": "Gm",
                "duration_seconds": 186.0,
                "dj_notes": "cue_seconds=0; ride_beats=16; trust_ride_beats",
            },
            {
                "track_id": "/music/on-fire-acapella.mp3",
                "artist": "Lloyd Banks",
                "title": "On Fire (Acapella)",
                "bpm": 95.0,
                "key": "Bb",
                "duration_seconds": 150.0,
                "dj_notes": "entry_style=vocal_over_bed; ride_beats=80; trust_ride_beats; no_flourish",
            },
            {
                "track_id": "/music/warrior-acapella.mp3",
                "artist": "Lloyd Banks",
                "title": "Warrior (Acapella)",
                "bpm": 187.0,
                "key": "Bb",
                "duration_seconds": 153.0,
                "dj_notes": "entry_style=vocal_over_bed; ride_beats=80; trust_ride_beats; no_flourish",
            },
            {
                "track_id": "/music/disco.mp3",
                "artist": "50 Cent",
                "title": "Disco Inferno",
                "bpm": 97.0,
                "key": "Gm",
                "duration_seconds": 214.0,
            },
        ]
        plan = build_plan(
            tracks,
            count=4,
            seconds_per_track=20.0,
            affinity_lookup={},
            transition_beats_by_pair={("/music/bed.mp3", "/music/disco.mp3"): 32},
        )
        transitions = [event for event in plan["events"] if event.get("op") == "transition"]
        self.assertEqual(transitions[0]["technique"], "vocal_over_bed")
        self.assertEqual(transitions[1]["technique"], "vocal_over_bed")
        self.assertIn("On Fire (Instrumental)", transitions[0]["from_track"])
        self.assertIn("On Fire (Instrumental)", transitions[1]["from_track"])
        self.assertIn("Warrior (Acapella)", transitions[1]["to_track"])
        self.assertIn("On Fire (Instrumental)", transitions[2]["from_track"])
        self.assertIn("Disco Inferno", transitions[2]["to_track"])
        self.assertEqual(transitions[2]["transition_beats"], 32)
        bodies = [event["track"] for event in plan["events"] if event.get("op") == "play_body"]
        self.assertTrue(all("Acapella" not in track for track in bodies))

    def test_no_flourish_directive_suppresses_showcase_moves(self) -> None:
        directives = track_directives({"dj_notes": "no_flourish"})
        self.assertTrue(directives["no_flourish"])

        # At index=1 the flourish rotation would normally land on
        # "stutter_fill" (rotation[1]) -- a track with no_flourish must
        # fall back to the plain "bass_swap" default instead.
        tracks = [
            {"track_id": "/music/a.mp3", "artist": "A", "title": "A", "bpm": 100.0, "key": "Am"},
            {"track_id": "/music/b.mp3", "artist": "B", "title": "B", "bpm": 100.5, "key": "Am"},
            {
                "track_id": "/music/c.mp3", "artist": "C", "title": "C", "bpm": 101.0, "key": "Am",
                "dj_notes": "no_flourish",
            },
        ]
        from dataclasses import replace

        profile = replace(PROFILES["dj-showcase"], flourish_every=1)
        plan = build_plan(tracks, count=3, seconds_per_track=20.0, affinity_lookup={}, profile=profile)
        transitions = [e for e in plan["events"] if e["op"] == "transition"]
        self.assertEqual(transitions[1]["showcase_move"], "bass_swap")
        self.assertNotIn("stutter_fill", transitions[1]["moves"])

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
                "dj_notes": (
                    "cue_seconds=0; opener_style=juggle_intro; "
                    "juggle_chops=4; juggle_hold_beats=4"
                ),
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
        opener = next(event for event in plan["events"] if event["op"] == "opener_effect")
        self.assertEqual(opener["juggle_chops"], 4)
        self.assertEqual(opener["juggle_hold_beats"], 4)
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

    def test_opener_play_bpm_reaches_the_start_event(self) -> None:
        # play_bpm only ever applied via pick_technique's incoming_bpm_target,
        # which fires on a transition INTO a track — the opener has no
        # incoming transition, so a play_bpm directive on track 0 silently
        # did nothing. Must reach the "start" event instead.
        tracks = [
            {
                "track_id": "/music/opener.mp3", "artist": "Cassie", "title": "Me&U",
                "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=0; play_bpm=103.0",
            },
            {
                "track_id": "/music/next.mp3", "artist": "Someone", "title": "Else",
                "bpm": 94.0, "key": "Am",
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        start_event = next(e for e in plan["events"] if e["op"] == "start")
        self.assertEqual(start_event["bpm_target"], 103.0)

    def test_exit_style_echo_out_overrides_technique(self) -> None:
        # docs/DJ_TRANSITIONS_PLAYBOOK.md #4: an echo-out exit is the gentle
        # large-gap escape -- no tempo bridging at all, so sync must be gone
        # from the moves and the incoming enters clean.
        tracks = [
            {
                "track_id": "/m/a.mp3", "artist": "A", "title": "Out",
                "bpm": 92.0, "key": "Db",
                "dj_notes": "cue_seconds=0; ride_beats=32; exit_style=echo_out",
            },
            {
                "track_id": "/m/b.mp3", "artist": "B", "title": "In",
                "bpm": 78.0, "key": "F#", "dj_notes": "cue_seconds=5",
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        transition = next(e for e in plan["events"] if e["op"] == "transition")
        self.assertEqual(transition["technique"], "echo_out_exit")
        self.assertEqual(transition["moves"], ["echo_out_exit"])
        self.assertNotIn("sync", transition["moves"])
        self.assertIsNone(transition.get("incoming_bpm_target"))

    def test_beat_phase_mismatch_auto_corrects_ride_beats(self) -> None:
        # Ernest, 2026-07-17: three separate "beats don't match" complaints
        # traced to real, confirmed snare-parity mismatches (see
        # brain.onset_analysis) that pure bar-count arithmetic missed. This
        # wires the check into build_plan() itself so future builds catch
        # it automatically instead of needing another manual investigation.
        tracks = [
            {
                "track_id": "/music/a.mp3", "artist": "A", "title": "Outgoing",
                "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=0; ride_beats=10",
            },
            {
                "track_id": "/music/b.mp3", "artist": "B", "title": "Incoming",
                "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=6.0",
            },
        ]
        beat_phase_lookup = {
            # Execution counts 10 body beat edges and perform_transition then
            # anchors on the NEXT edge: beat 11, not beat 10. A's odd snare
            # therefore gives target parity (11+1)%2=0.
            "/music/a.mp3": {
                "snare_parity": 1, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
            },
            # B's odd snare at cue beat 10 gives current parity 1, so the
            # requested body is mismatched against the real N+1 anchor.
            "/music/b.mp3": {
                "snare_parity": 1, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
            },
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=beat_phase_lookup,
        )
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        # 10 -> 9 makes the actual next-beat anchor beat 10, matching B.
        self.assertEqual(body["beats"], 9)

    def test_trust_ride_beats_blocks_the_auto_nudge(self) -> None:
        # Ear override (Ernest, 2026-07-19): the parity measurement driving
        # a nudge can be a near-coin-flip (confidence 0.015 seen live), and
        # a human-certified ride length must never be silently shifted.
        tracks = [
            {
                "track_id": "/m/a.mp3", "artist": "A", "title": "Outgoing",
                "bpm": 100.0, "key": "Am",
                "dj_notes": "cue_seconds=0; ride_beats=10; trust_ride_beats",
            },
            {
                "track_id": "/m/b.mp3", "artist": "B", "title": "Incoming",
                "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=6.0",
            },
        ]
        beat_phase_lookup = {
            # Deliberately mismatched parities: the nudge WOULD fire.
            "/m/a.mp3": {"snare_parity": 1, "confidence": 0.5, "bpm": 100.0,
                         "first_beat_seconds": 0.0},
            "/m/b.mp3": {"snare_parity": 0, "confidence": 0.5, "bpm": 100.0,
                         "first_beat_seconds": 0.0},
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=beat_phase_lookup,
        )
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        self.assertEqual(body["beats"], 10)
        self.assertTrue(body["trust_ride_beats"])
        # Planner must not auto-nudge a trusted count, but the count still
        # defines a planned anchor so runtime can absorb load jitter.
        self.assertIn("phase_anchor", body)
        # entry 0 + prev_fade 0 + body 10 + 1 = 11
        self.assertEqual(body["phase_anchor"]["planned_anchor_beat_index"], 11)
        self.assertEqual(body["phase_anchor"]["target_beat_mod4"], 11 % 4)

    def test_double_time_grid_allows_long_trusted_ride(self) -> None:
        # Wanna Get To Know is tagged 168 (double-time of ~84). All three
        # verses plus Joe's last chorus need ~640 grid beats; the old 512
        # cap cut 50's verse off.
        tracks = [
            {
                "track_id": "/m/wanna.mp3",
                "artist": "G-Unit",
                "title": "Wanna Get To Know You",
                "bpm": 168.0,
                "key": "Cm",
                "duration_seconds": 265.0,
                "dj_notes": (
                    "cue_seconds=0.3; trust_cue_seconds; ride_beats=640; "
                    "trust_ride_beats; play_bpm=168.0; no_flourish"
                ),
            },
            {
                "track_id": "/m/next.mp3",
                "artist": "G-Unit",
                "title": "G-Unit Soldiers",
                "bpm": 90.0,
                "key": "Fm",
                "duration_seconds": 189.0,
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        self.assertEqual(body["beats"], 640)
        self.assertTrue(body.get("trust_ride_beats"))

    def test_transition_beat_overrides_feed_next_phase_anchor(self) -> None:
        # Post-build patching used to set transition_beats=64 while the next
        # body's phase_anchor still assumed the default ~24-beat previous fade.
        tracks = [
            {
                "track_id": "/m/a.mp3", "artist": "A", "title": "One",
                "bpm": 100.0, "key": "Am",
                "dj_notes": "cue_seconds=0; ride_beats=32; trust_ride_beats",
            },
            {
                "track_id": "/m/b.mp3", "artist": "B", "title": "Two",
                "bpm": 100.0, "key": "Am",
                "dj_notes": "cue_seconds=0; ride_beats=40; trust_ride_beats",
            },
            {
                "track_id": "/m/c.mp3", "artist": "C", "title": "Three",
                "bpm": 100.0, "key": "Am",
                "dj_notes": "cue_seconds=0",
            },
        ]
        beat_phase_lookup = {
            tid: {
                "snare_parity": 1, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
            }
            for tid in ("/m/a.mp3", "/m/b.mp3", "/m/c.mp3")
        }
        plan = build_plan(
            tracks,
            count=3,
            seconds_per_track=20.0,
            affinity_lookup={},
            beat_phase_lookup=beat_phase_lookup,
            transition_beats_by_pair={("/m/a.mp3", "/m/b.mp3"): 64},
        )
        bodies = [event for event in plan["events"] if event["op"] == "play_body"]
        transitions = [event for event in plan["events"] if event["op"] == "transition"]
        self.assertEqual(transitions[0]["transition_beats"], 64)
        # B's body: entry 0 + previous fade 64 + ride 40 + 1 = 105
        self.assertEqual(bodies[1]["beats"], 40)
        self.assertEqual(bodies[1]["phase_anchor"]["planned_anchor_beat_index"], 105)
        self.assertEqual(bodies[1]["phase_anchor"]["target_beat_mod4"], 105 % 4)

    def test_tempo_ramp_exit_shapes_outgoing_before_native_bpm_blend(self) -> None:
        tracks = [
            {
                "track_id": "/m/fiesta.mp3", "artist": "R. Kelly", "title": "Fiesta",
                "bpm": 92.86, "key": "Bbm",
                "dj_notes": (
                    "ride_beats=72; trust_ride_beats; "
                    "exit_style=tempo_ramp_blend; exit_bpm=100; tempo_ramp_beats=32"
                ),
            },
            {
                "track_id": "/m/me-u.mp3", "artist": "Cassie", "title": "Me&U",
                "bpm": 100.0, "key": "G#m",
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        transition = next(event for event in plan["events"] if event["op"] == "transition")
        self.assertEqual(body["beats"], 72)
        self.assertEqual(body["exit_bpm_target"], 100.0)
        self.assertEqual(body["tempo_ramp_beats"], 32)
        self.assertEqual(transition["technique"], "tempo_ramp_blend")
        self.assertIn("sync", transition["moves"])
        self.assertNotIn("incoming_bpm_target", transition)

    def test_new_transition_features_are_opt_in_for_ordinary_tracks(self) -> None:
        tracks = [
            {
                "track_id": "/m/a.mp3", "artist": "A", "title": "A",
                "bpm": 100.0, "key": "Am", "dj_notes": "ride_beats=32",
            },
            {
                "track_id": "/m/b.mp3", "artist": "B", "title": "B",
                "bpm": 101.0, "key": "Am", "dj_notes": "",
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        transition = next(event for event in plan["events"] if event["op"] == "transition")
        self.assertNotIn("exit_bpm_target", body)
        self.assertNotIn("tempo_ramp_beats", body)
        self.assertNotIn(
            transition["technique"],
            {"tempo_ramp_blend", "halftime_backbeat_blend", "filter_drop_exit"},
        )
        self.assertNotIn("filter_drop_exit", transition["moves"])

    def test_halftime_backbeat_blend_and_filter_drop_directives(self) -> None:
        tracks = [
            {
                "track_id": "/m/original.mp3", "artist": "Aaliyah", "title": "Original",
                "bpm": 121.93, "key": "A", "dj_notes": "ride_beats=40; trust_ride_beats",
            },
            {
                "track_id": "/m/dark.mp3", "artist": "Aaliyah", "title": "Dark Child",
                "bpm": 121.97, "key": "A",
                "dj_notes": (
                    "entry_style=halftime_blend; ride_beats=80; trust_ride_beats; "
                    "exit_style=filter_drop"
                ),
            },
            {
                "track_id": "/m/top.mp3", "artist": "Big Pun", "title": "Top",
                "bpm": 100.83, "key": "G#m",
            },
        ]
        plan = build_plan(tracks, count=3, seconds_per_track=20.0, affinity_lookup={})
        transitions = [event for event in plan["events"] if event["op"] == "transition"]
        self.assertEqual(transitions[0]["technique"], "halftime_backbeat_blend")
        self.assertIn("sync", transitions[0]["moves"])
        self.assertEqual(transitions[1]["technique"], "filter_drop_exit")
        self.assertEqual(transitions[1]["moves"], ["filter_drop_exit"])

    def test_beat_phase_match_leaves_ride_beats_untouched(self) -> None:
        tracks = [
            {
                "track_id": "/music/a.mp3", "artist": "A", "title": "Outgoing",
                "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=0; ride_beats=10",
            },
            {
                "track_id": "/music/b.mp3", "artist": "B", "title": "Incoming",
                "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=6.0",
            },
        ]
        beat_phase_lookup = {
            "/music/a.mp3": {
                "snare_parity": 1, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
            },
            # Even incoming snare at cue beat 10 matches A's odd snare at the
            # actual next-beat anchor 11; no nudge expected.
            "/music/b.mp3": {
                "snare_parity": 0, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
            },
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=beat_phase_lookup,
        )
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        self.assertEqual(body["beats"], 10)

    def test_non_opener_play_bpm_does_not_leak_onto_start_event(self) -> None:
        tracks = [
            {
                "track_id": "/music/opener.mp3", "artist": "A", "title": "A",
                "bpm": 100.0, "key": "Am",
            },
            {
                "track_id": "/music/next.mp3", "artist": "B", "title": "B",
                "bpm": 94.0, "key": "Am", "dj_notes": "play_bpm=98.0",
            },
        ]
        plan = build_plan(tracks, count=2, seconds_per_track=20.0, affinity_lookup={})
        start_event = next(e for e in plan["events"] if e["op"] == "start")
        self.assertNotIn("bpm_target", start_event)

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
