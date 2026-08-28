"""Verse start/stop: do not mix in or out mid-verse."""
from __future__ import annotations

from unittest import TestCase

from brain.verse import (
    classify_cue,
    has_vocal_verses,
    respect_verse_entry,
    respect_verse_exit,
)


ON_FIRE = [
    {"kind": "verse", "start": 3.60, "end": 12.92},
    {"kind": "chorus", "start": 12.92, "end": 27.75},
    {"kind": "verse", "start": 27.75, "end": 73.30},
    {"kind": "chorus", "start": 73.30, "end": 88.11},
]


class ClassifyCueTests(TestCase):
    def test_on_fire_phrase_body_is_mid_verse(self) -> None:
        self.assertEqual(classify_cue(41.35, ON_FIRE), "mid_verse")
        self.assertEqual(classify_cue(0.0, ON_FIRE), "intro")
        self.assertEqual(classify_cue(27.75, ON_FIRE), "verse_start")
        self.assertEqual(classify_cue(12.92, ON_FIRE), "chorus")

    def test_no_segments_is_unknown(self) -> None:
        self.assertEqual(classify_cue(41.35, []), "unknown")


class RespectVerseEntryTests(TestCase):
    def test_on_fire_rewrites_mid_verse_to_zero(self) -> None:
        decision = respect_verse_entry(41.35, ON_FIRE, first_beat=0.292, bpm=95.0)
        self.assertFalse(decision.legal)
        self.assertEqual(decision.cue_seconds, 0.0)
        self.assertEqual(decision.source, "intro_top")
        self.assertEqual(decision.placement, "mid_verse")

    def test_zero_stays_legal(self) -> None:
        decision = respect_verse_entry(0.0, ON_FIRE, bpm=95.0)
        self.assertTrue(decision.legal)
        self.assertEqual(decision.source, "unchanged")

    def test_no_intro_prerolls_onto_verse_start(self) -> None:
        segments = [{"kind": "verse", "start": 4.0, "end": 40.0}]
        decision = respect_verse_entry(20.0, segments, bpm=90.0, blend_beats=16)
        self.assertFalse(decision.legal)
        self.assertEqual(decision.source, "verse_preroll")
        self.assertEqual(decision.cue_seconds, 0.0)

    def test_unknown_without_lyrics(self) -> None:
        decision = respect_verse_entry(41.35, [], bpm=95.0)
        self.assertTrue(decision.legal)
        self.assertEqual(decision.cue_seconds, 41.35)


class RespectVerseExitTests(TestCase):
    def test_extends_to_verse_end(self) -> None:
        ride, reason = respect_verse_exit(0.0, 80, 95.0, ON_FIRE)
        self.assertGreater(ride, 80)
        self.assertIn("extend ride", reason)
        fade = ride * 60.0 / 95.0
        self.assertLess(abs(fade - 73.30), 1.0)

    def test_empty_segments_do_not_rewrite(self) -> None:
        ride, reason = respect_verse_exit(0.0, 80, 95.0, [])
        self.assertEqual(ride, 80)
        self.assertEqual(reason, "unchanged")

    def test_whole_song_verse_is_not_extended(self) -> None:
        bogus = [{"kind": "verse", "start": 1.39, "end": 146.61}]
        ride, reason = respect_verse_exit(0.0, 39, 95.0, bogus)
        self.assertEqual(ride, 39)
        self.assertEqual(reason, "unchanged")

    def test_twenty_one_questions_blend_in_is_rewritten_to_zero(self) -> None:
        # Cue sits on the chorus/verse-2 boundary; 32-beat blend finishes
        # 20s into 50's "If I fell off tomorrow" verse.
        segments = [
            {"kind": "verse", "start": 2.66, "end": 32.77},
            {"kind": "chorus", "start": 32.77, "end": 53.02},
            {"kind": "verse", "start": 53.02, "end": 94.50},
        ]
        decision = respect_verse_entry(52.76, segments, bpm=93.05, blend_beats=32)
        self.assertFalse(decision.legal)
        self.assertEqual(decision.cue_seconds, 0.0)
        self.assertEqual(decision.source, "intro_top")

    def test_dont_need_em_blend_out_waits_for_verse_two(self) -> None:
        # 96 beats at 83 BPM fades in the hook; 32-beat blend then eats verse 2.
        segments = [
            {"kind": "verse", "start": 4.70, "end": 60.68},
            {"kind": "chorus", "start": 60.68, "end": 72.41},
            {"kind": "verse", "start": 72.41, "end": 130.08},
            {"kind": "chorus", "start": 130.08, "end": 142.07},
        ]
        ride, reason = respect_verse_exit(0.0, 96, 83.0, segments, blend_beats=32)
        self.assertGreaterEqual(ride, 179)
        self.assertIn("extend ride", reason)
        fade = ride * 60.0 / 83.0
        self.assertLess(abs(fade - 130.08), 1.5)

    def test_best_friend_opening_chorus_is_not_a_verse(self) -> None:
        # Opening hook "If I was your best friend" is chorus; 50's verse
        # starts at "First we get the talkin". A 96-beat ride from the
        # chorus landing dies inside verse 1.
        segments = [
            {"kind": "chorus", "start": 27.08, "end": 49.48},
            {"kind": "verse", "start": 49.48, "end": 109.65},
            {"kind": "chorus", "start": 109.65, "end": 133.93},
            {"kind": "verse", "start": 133.93, "end": 189.14},
            {"kind": "chorus", "start": 189.14, "end": 237.97},
        ]
        self.assertEqual(classify_cue(27.08, segments), "chorus")
        self.assertEqual(classify_cue(49.48, segments), "verse_start")
        cue = 49.48 - 24 * 60.0 / 90.80
        ride, reason = respect_verse_exit(cue, 96, 90.80, segments, blend_beats=24)
        self.assertGreaterEqual(ride, 115)
        self.assertIn("extend ride", reason)

    def test_god_pt_iii_skit_ride_eats_prodigy_verse(self) -> None:
        # Window skit is detector-"verse" 3.42–66.02. Cue 0 + ~102 live
        # beats fades on the hook; 32-beat blend cuts Prodigy at 1:28.
        segments = [
            {"kind": "verse", "start": 3.42, "end": 66.02},
            {"kind": "chorus", "start": 66.02, "end": 88.40},
            {"kind": "verse", "start": 88.40, "end": 162.17},
            {"kind": "chorus", "start": 162.17, "end": 183.11},
            {"kind": "verse", "start": 183.11, "end": 246.38},
            {"kind": "chorus", "start": 246.38, "end": 288.53},
        ]
        self.assertEqual(classify_cue(66.02, segments), "chorus")
        self.assertEqual(classify_cue(88.40, segments), "verse_start")
        cue = 87.05 - 32 * 60.0 / 91.15
        self.assertGreater(cue, 60.0)
        self.assertLess(cue, 66.1)
        # 160 beats from the hook fades in the post-v1 chorus; 32-beat
        # blend then sits in Havoc. Extend to Havoc's end / last hook.
        ride, reason = respect_verse_exit(cue, 160, 91.15, segments, blend_beats=32)
        self.assertGreaterEqual(ride, 273)
        self.assertIn("extend ride", reason)

    def test_if_i_cant_seventy_six_beats_eats_verse_two(self) -> None:
        # Cue 0 opening hook; v1 0:20–0:51, v2 1:02–1:42, v3 1:52–2:33.
        # 76 beats dies in v1; 32-beat blend eats v2.
        segments = [
            {"kind": "chorus", "start": 9.99, "end": 20.23},
            {"kind": "verse", "start": 20.23, "end": 50.80},
            {"kind": "chorus", "start": 50.80, "end": 61.69},
            {"kind": "verse", "start": 61.69, "end": 101.93},
            {"kind": "chorus", "start": 101.93, "end": 112.17},
            {"kind": "verse", "start": 112.17, "end": 153.06},
            {"kind": "chorus", "start": 153.06, "end": 183.20},
        ]
        self.assertEqual(classify_cue(20.23, segments), "verse_start")
        ride, reason = respect_verse_exit(0.18, 76, 94.0, segments, blend_beats=32)
        self.assertGreaterEqual(ride, 79)
        self.assertIn("extend ride", reason)
        ride, reason = respect_verse_exit(0.18, 160, 94.0, segments, blend_beats=32)
        self.assertGreaterEqual(ride, 239)
        self.assertIn("extend ride", reason)

    def test_bump_heads_seventy_two_beats_dies_in_eminem(self) -> None:
        # 50 hook 0:25, Eminem 0:34–2:16, Yayo 2:37–3:09, Banks 3:28–3:59.
        # 72 beats from 0 dies inside Eminem; Yayo/Banks never play.
        segments = [
            {"kind": "verse", "start": 25.01, "end": 136.85},
            {"kind": "chorus", "start": 136.85, "end": 157.35},
            {"kind": "verse", "start": 157.35, "end": 189.75},
            {"kind": "chorus", "start": 189.75, "end": 207.13},
            {"kind": "verse", "start": 207.13, "end": 239.51},
            {"kind": "chorus", "start": 239.51, "end": 260.70},
        ]
        fade = 72 * 60.0 / 93.49
        self.assertLess(fade, 80.0)
        ride, reason = respect_verse_exit(0.0, 72, 93.49, segments, blend_beats=24)
        # Eminem's verse is ~112s, over MAX_VERSE, so auto-extend will not
        # save this — the human ride lock has to.
        self.assertEqual(ride, 72)
        self.assertEqual(reason, "unchanged")

    def test_instrumental_skips_verse_rules_even_with_vocal_lrc(self) -> None:
        self.assertFalse(has_vocal_verses("On Fire (Instrumental)"))
        self.assertTrue(has_vocal_verses("On Fire (Feat. 50 Cent)"))
        decision = respect_verse_entry(
            41.35, ON_FIRE, bpm=95.0, title="On Fire (Instrumental)"
        )
        self.assertTrue(decision.legal)
        self.assertEqual(decision.cue_seconds, 41.35)
        ride, reason = respect_verse_exit(
            0.0, 80, 95.0, ON_FIRE, title="On Fire (Instrumental)"
        )
        self.assertEqual(ride, 80)
        self.assertEqual(reason, "unchanged")
