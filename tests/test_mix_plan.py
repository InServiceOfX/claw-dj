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
        self.assertFalse(directives["no_flourish"])

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

    def test_no_flourish_directive_suppresses_showcase_moves(self) -> None:
        directives = track_directives({"dj_notes": "no_flourish"})
        self.assertTrue(directives["no_flourish"])

        # At index=1 the flourish rotation would normally land on
        # "scratch_preview" (rotation[1]) -- a track with no_flourish must
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
        self.assertNotIn("optional_scratch_in", transitions[1]["moves"])

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
            # A's snare on odd beats; A's own entry (beat 0) + ride_beats=10
            # lands its exit anchor on beat 10 (even) -- target parity
            # (10+1)%2=1.
            "/music/a.mp3": {
                "snare_parity": 1, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
            },
            # B's snare on EVEN beats; B's cue (beat 10, from cue_seconds=6.0
            # at 100bpm) gives current parity (10+0)%2=0 -- mismatched.
            "/music/b.mp3": {
                "snare_parity": 0, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
            },
        }
        plan = build_plan(
            tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup=beat_phase_lookup,
        )
        body = next(event for event in plan["events"] if event["op"] == "play_body")
        # 10 -> 11 flips A's exit anchor to odd parity, matching B's cue.
        self.assertEqual(body["beats"], 11)

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
            # Same parity as A this time -- already aligned, no nudge expected.
            "/music/b.mp3": {
                "snare_parity": 1, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0,
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
