"""Mix to listen plays most of each song and blends out verse-safe."""
from unittest import TestCase

from brain.mix_profiles import PROFILES
from brain.verse import song_exit_seconds

SEGMENTS = [
    {"kind": "verse", "start": 20.0, "end": 60.0},
    {"kind": "chorus", "start": 60.0, "end": 80.0},
    {"kind": "verse", "start": 80.0, "end": 120.0},
    {"kind": "chorus", "start": 120.0, "end": 140.0},
    {"kind": "verse", "start": 140.0, "end": 200.0},
]


class ListenRideTest(TestCase):
    def test_mix_to_listen_rides_most_of_the_song(self) -> None:
        self.assertTrue(PROFILES["mix-to-listen"].ride_most_of_song)
        self.assertFalse(PROFILES["dj-showcase"].ride_most_of_song)
        self.assertFalse(PROFILES["club-set"].ride_most_of_song)

    def test_clear_ending_rides_to_latest(self) -> None:
        t, _ = song_exit_seconds(SEGMENTS[:4], earliest=100, latest=180, blend_seconds=20)
        self.assertEqual(t, 180)

    def test_verse_at_the_end_exits_on_the_last_safe_chorus(self) -> None:
        t, why = song_exit_seconds(SEGMENTS, earliest=100, latest=190, blend_seconds=20)
        self.assertEqual(t, 120.0)
        self.assertIn("chorus", why)

    def test_instrumental_rides_to_the_end(self) -> None:
        t, _ = song_exit_seconds(SEGMENTS, earliest=50, latest=190, blend_seconds=20,
                                 title="Song (Instrumental)")
        self.assertEqual(t, 190)

    def test_no_lyrics_rides_to_the_end(self) -> None:
        t, why = song_exit_seconds([], earliest=50, latest=190, blend_seconds=20)
        self.assertEqual(t, 190)
        self.assertIn("no lyric", why)


class ListenBlendLengthTest(TestCase):
    """2026-10-07: direction words must not stretch Mix to listen blends."""

    BRIEF = (
        "Smooth R&B listening mix. Play most of each song if it makes sense "
        "and let it breathe, with a long blend into the next song."
    )

    def test_mix_to_listen_keeps_its_blend_length(self) -> None:
        from brain.mix_profiles import apply_brief

        base = PROFILES["mix-to-listen"]
        profile, notes = apply_brief(base, self.BRIEF)
        self.assertEqual(profile.transition_scale, base.transition_scale)
        self.assertTrue(any("kept Mix to listen blend length" in n for n in notes))
        profile, _ = apply_brief(base, "quick short showcase")
        self.assertEqual(profile.transition_scale, base.transition_scale)

    def test_other_feels_still_follow_length_words(self) -> None:
        from brain.mix_profiles import apply_brief

        for name in ("dj-showcase", "club-set"):
            base = PROFILES[name]
            profile, _ = apply_brief(base, self.BRIEF)
            self.assertGreater(profile.transition_scale, base.transition_scale)
