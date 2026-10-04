"""hands.live_kit: reusable live Mixxx moves, tested against a fake Mixxx whose
play position advances while a deck plays (no live Mixxx, no audio)."""
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from brain.library_index import connect as library_connect
from hands import live_kit
from hands.live_kit import (
    Live,
    Track,
    eq_split_crossover,
    exact_loop,
    library_track,
    play_bar_pattern,
    same_song_handoff,
    track_from_library,
)

EQ = "[EqualizerRack1_[Channel{d}]_Effect1]"
FILTER = "[QuickEffectRack1_[Channel{d}]]"


class ClockMixxx:
    """Each playposition read advances a playing deck by `step` seconds."""

    def __init__(self, step: float = 0.05, duration: float = 300.0):
        self.values: dict[tuple[str, str], float] = {}
        self.seconds: dict[str, float] = {}
        self.writes: list[tuple[str, str, float]] = []
        self.step, self.duration = step, duration

    def get(self, group: str, key: str) -> float:
        if key == "duration":
            return self.duration
        if key == "playposition":
            if self.values.get((group, "play"), 0.0) >= 0.5:
                self.seconds[group] = self.seconds.get(group, 0.0) + self.step
            return self.seconds.get(group, 0.0) / self.duration
        return self.values.get((group, key), 0.0)

    def set(self, group: str, key: str, value: float) -> None:
        self.values[(group, key)] = value
        self.writes.append((group, key, value))

    def cue(self, deck: int, seconds: float) -> None:
        self.seconds[f"[Channel{deck}]"] = seconds


TRACK = Track("Artist", "Song", 120.0, 0.25)       # beat b at 0.25 + 0.5*b seconds


def no_sleep():
    return patch("hands.live_kit.time.sleep", lambda _s: None)


class LibraryLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.index = Path(self._tmp.name) / "library.sqlite3"
        with closing(library_connect(self.index)) as db:
            for tid, available in (("/v/Album A/01 Song.mp3", 1), ("/v/Deluxe B/01 Song.mp3", 1),
                                   ("/v/Gone/01 Song.mp3", 0), ("/v/Solo/02 Other.mp3", 1)):
                title = "Other" if "Other" in tid else "Song"
                db.execute(
                    """INSERT INTO tracks (track_id, root, size_bytes, mtime_ns, title, artist, album, genre,
                       duration_seconds, bpm, key, energy, first_seen_at, last_seen_at, available, tag_status, dj_notes)
                       VALUES (?, '/v', 1, 1, ?, 'Some Artist', NULL, NULL, 200.0, 100.0, 'Am', NULL, 0, 0, ?, 'ok', '')""",
                    (tid, title, available))
            db.execute("INSERT INTO beat_phase(track_id, analyzed_at, snare_parity, confidence, bpm, first_beat_seconds)"
                       " VALUES ('/v/Solo/02 Other.mp3', 0, 0, 0.5, 104.37, 0.39)")
            db.commit()

    def test_one_available_copy_is_returned(self) -> None:
        self.assertEqual(library_track("Some Artist", "Other", index_path=self.index), "/v/Solo/02 Other.mp3")

    def test_several_copies_need_a_hint_and_the_hint_picks_one(self) -> None:
        with self.assertRaises(SystemExit):
            library_track("Some Artist", "Song", index_path=self.index)
        self.assertEqual(library_track("Some Artist", "Song", "Deluxe B", index_path=self.index),
                         "/v/Deluxe B/01 Song.mp3")

    def test_unavailable_or_missing_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            library_track("Some Artist", "Song", "Gone", index_path=self.index)
        with self.assertRaises(SystemExit):
            library_track("Nobody", "Nothing", index_path=self.index)

    def test_track_from_library_reads_the_beat_grid(self) -> None:
        track = track_from_library("Some Artist", "Other", index_path=self.index)
        self.assertAlmostEqual(track.bpm, 104.37)
        self.assertAlmostEqual(track.first_beat, 0.39)
        self.assertEqual(track.path(), "/v/Solo/02 Other.mp3")


class GridAndSessionTests(unittest.TestCase):
    def test_grid_math_round_trips(self) -> None:
        self.assertAlmostEqual(TRACK.at(8), 4.25)
        self.assertAlmostEqual(TRACK.beat_at(TRACK.at(37.5)), 37.5)

    def test_prepare_refuses_a_playing_deck(self) -> None:
        mixxx = ClockMixxx()
        mixxx.values[("[Channel2]", "play")] = 1.0
        with self.assertRaises(SystemExit):
            Live(mixxx).prepare((1, 2))

    def test_prepare_sets_a_clean_slate_and_restore_puts_it_back(self) -> None:
        mixxx = ClockMixxx()
        mixxx.values[(FILTER.format(d=1), "super1")] = 0.13          # left closed by an interrupted mix
        mixxx.values[(EQ.format(d=1), "parameter1")] = 0.5
        live = Live(mixxx)
        live.prepare((1,), master_gain=0.6)
        self.assertEqual(mixxx.values[(FILTER.format(d=1), "super1")], 0.5)
        self.assertEqual(mixxx.values[(EQ.format(d=1), "parameter1")], 1.0)
        self.assertEqual(mixxx.values[("[Master]", "gain")], 0.6)
        live.restore()
        self.assertEqual(mixxx.values[(FILTER.format(d=1), "super1")], 0.13)
        self.assertEqual(mixxx.values[(EQ.format(d=1), "parameter1")], 0.5)
        self.assertEqual(mixxx.values[("[Channel1]", "play")], 0)

    def test_cut_and_automate_reach_their_targets(self) -> None:
        mixxx = ClockMixxx()
        live = Live(mixxx)
        mixxx.values[("[Channel1]", "volume")] = 1.0
        with no_sleep():
            live.cut([("[Channel1]", "volume", 0.0)], seconds=0.0)
            self.assertEqual(mixxx.values[("[Channel1]", "volume")], 0.0)
            mixxx.values[("[Channel1]", "play")] = 1.0
            live.automate(1, TRACK, 0, 16, [("[Channel2]", "volume", 0.0, 1.0)], curve="linear")
        self.assertEqual(mixxx.values[("[Channel2]", "volume")], 1.0)

    def test_linear_curve_is_a_steady_ramp_and_unknown_curves_are_refused(self) -> None:
        mixxx = ClockMixxx(step=0.5)                       # one beat of TRACK per position read
        mixxx.values[("[Channel1]", "play")] = 1.0
        mixxx.cue(1, TRACK.at(0) - 0.5)
        live = Live(mixxx)
        with no_sleep():
            live.automate(1, TRACK, 0, 4, [(EQ.format(d=2), "parameter2", 1.0, 0.0)], curve="linear")
        ramp = [v for g, k, v in mixxx.writes if (g, k) == (EQ.format(d=2), "parameter2")]
        steps = [round(a - b, 6) for a, b in zip(ramp, ramp[1:]) if 0 < b < 1 and 0 < a < 1]
        self.assertTrue(steps and max(steps) - min(steps) < 1e-6)   # equal steps: linear
        with self.assertRaises(ValueError):
            live.automate(1, TRACK, 0, 4, [], curve="wobbly")

    def test_fade_out_takes_gentle_fade_beats_by_default_and_stops_the_deck(self) -> None:
        from hands.live_kit import GENTLE_FADE_BEATS, fade_out
        self.assertGreaterEqual(GENTLE_FADE_BEATS, 16)
        mixxx = ClockMixxx()
        mixxx.values[("[Channel1]", "play")] = 1.0
        mixxx.values[("[Channel2]", "play")] = 1.0
        mixxx.values[("[Channel2]", "volume")] = 0.8
        with no_sleep(), patch.object(Live, "automate", autospec=True) as automate:
            fade_out(Live(mixxx), deck=2, clock_deck=1, clock_track=TRACK, start_beat=100)
        _live, clock, track, b0, b1, lanes = automate.call_args.args
        self.assertEqual((clock, b0, b1), (1, 100, 100 + GENTLE_FADE_BEATS))
        self.assertEqual(lanes, [("[Channel2]", "volume", 0.8, 0.0)])
        self.assertEqual(automate.call_args.kwargs, {"curve": "linear", "fast": False})
        self.assertEqual(mixxx.values[("[Channel2]", "play")], 0)

    def test_a_fast_channel_fader_move_is_refused_before_anything_is_written(self) -> None:
        # Ernest, 2026-10-03: agents move the channel faders TOO FAST; 8 counts is too fast
        mixxx = ClockMixxx()
        mixxx.values[("[Channel1]", "play")] = 1.0
        live = Live(mixxx)
        for b1, curve, lanes in (
            (8, "linear", [("[Channel2]", "volume", 1.0, 0.0)]),           # out too fast
            (4, "linear", [("[Channel2]", "volume", 0.0, 1.0)]),           # in too fast
            (16, "smooth", [("[Channel2]", "volume", 1.0, 0.0)]),          # S-curve peaks 1.5x
            (4, "linear", [("[Channel2]", "volume", 0.0, 0.5)]),           # half a sweep in 4 is still too fast
        ):
            before = len(mixxx.writes)
            with self.subTest(b1=b1, curve=curve), no_sleep(), self.assertRaises(ValueError):
                live.automate(1, TRACK, 0, b1, lanes, curve=curve)
            self.assertEqual(len(mixxx.writes), before)

    def test_gentle_fader_moves_eq_lanes_and_explicit_fast_moves_are_allowed(self) -> None:
        mixxx = ClockMixxx()
        mixxx.values[("[Channel1]", "play")] = 1.0
        live = Live(mixxx)
        with no_sleep():
            live.automate(1, TRACK, 0, 16, [("[Channel2]", "volume", 1.0, 0.0)], curve="linear")
            live.automate(1, TRACK, 16, 24, [("[Channel2]", "volume", 0.0, 0.5)], curve="linear")
            live.automate(1, TRACK, 24, 48, [("[Channel2]", "volume", 0.5, 0.0)], curve="smooth")
            live.automate(1, TRACK, 48, 50, [(EQ.format(d=2), "parameter1", 1.0, 0.0)])   # EQ is not a fader
            live.automate(1, TRACK, 50, 52, [("[Channel2]", "volume", 0.0, 1.0)], fast=True)  # juggle/cut
        self.assertEqual(mixxx.values[("[Channel2]", "volume")], 1.0)

    def test_a_short_fade_out_is_refused_unless_marked_fast(self) -> None:
        from hands.live_kit import fade_out
        mixxx = ClockMixxx()
        mixxx.values[("[Channel1]", "play")] = 1.0
        mixxx.values[("[Channel2]", "volume")] = 1.0
        with no_sleep(), self.assertRaises(ValueError):
            fade_out(Live(mixxx), deck=2, clock_deck=1, clock_track=TRACK, start_beat=0, beats=8)
        with no_sleep():
            fade_out(Live(mixxx), deck=2, clock_deck=1, clock_track=TRACK, start_beat=0, beats=8, fast=True)
        self.assertEqual(mixxx.values[("[Channel2]", "volume")], 0.0)

    def test_wait_raises_when_the_deck_stops(self) -> None:
        with no_sleep(), self.assertRaises(RuntimeError):
            Live(ClockMixxx()).wait(1, 10.0)

    def test_load_cues_tempo_and_pitch_and_leaves_the_deck_silent(self) -> None:
        mixxx = ClockMixxx()
        TRACK._path = "/v/song.mp3"
        with (
            patch("hands.live_kit.load_deck") as load,
            patch("hands.live_kit.set_bpm_target") as tempo,
        ):
            Live(mixxx).load(3, TRACK, 16, bpm=109.25, pitch=0.6)
        load.assert_called_once_with(mixxx, 3, "/v/song.mp3", cue_seconds=TRACK.at(16), expected_bpm=120.0)
        tempo.assert_called_once_with(mixxx, 3, 109.25)
        self.assertEqual(mixxx.values[("[Channel3]", "volume")], 0.0)
        self.assertEqual(mixxx.values[("[Channel3]", "pitch_adjust")], 0.6)
        self.assertEqual(mixxx.values[(EQ.format(d=3), "parameter2")], 1.0)


class TechniqueTests(unittest.TestCase):
    def test_same_song_handoff_ends_on_the_incoming_deck(self) -> None:
        mixxx = ClockMixxx()
        mixxx.values[("[Channel1]", "play")] = 1.0
        mixxx.values[("[Channel1]", "volume")] = 1.0
        mixxx.cue(1, TRACK.at(110))
        with no_sleep():
            same_song_handoff(Live(mixxx), out_deck=1, in_deck=3, track=TRACK, at_beat=116, blend_beats=4)
        self.assertEqual(mixxx.values[("[Channel3]", "play")], 1)
        self.assertEqual(mixxx.values[("[Channel3]", "volume")], 1.0)
        self.assertEqual(mixxx.values[(EQ.format(d=3), "parameter1")], 1.0)
        self.assertEqual(mixxx.values[("[Channel1]", "play")], 0)
        self.assertIn(("[Channel3]", "beatsync_phase", 1), mixxx.writes)
        # the incoming bass stayed cut until the halfway swap
        self.assertIn((EQ.format(d=3), "parameter1", 0.0), mixxx.writes)

    def test_same_song_handoff_with_no_blend_is_an_on_beat_cut(self) -> None:
        mixxx = ClockMixxx()
        mixxx.values[("[Channel1]", "play")] = 1.0
        with no_sleep():
            same_song_handoff(Live(mixxx), out_deck=1, in_deck=2, track=TRACK, at_beat=4, blend_beats=0)
        self.assertEqual(mixxx.values[("[Channel2]", "volume")], 1.0)
        self.assertEqual(mixxx.values[("[Channel1]", "play")], 0)

    def test_eq_split_crossover_never_has_both_riffs_at_full_range(self) -> None:
        mixxx = ClockMixxx()
        mixxx.values[("[Channel2]", "play")] = 1.0
        mixxx.values[("[Channel2]", "volume")] = 1.0
        with no_sleep():
            eq_split_crossover(Live(mixxx), clock_deck=2, clock_track=TRACK, out_deck=2, in_deck=3,
                               enter_beat=8, hold_beats=8, cross_beats=8)
        mids = {}
        for group, key, value in mixxx.writes:
            if (group, key, value) == ("[Channel2]", "play", 0):
                break                     # outgoing deck silent from here on
            mids[(group, key)] = value
            out_mid = mids.get((EQ.format(d=2), "parameter2"), 1.0)
            in_mid = mids.get((EQ.format(d=3), "parameter2"), 0.0)
            self.assertLessEqual(out_mid + in_mid, 1.0 + 1e-9)
        self.assertEqual(mixxx.values[("[Channel2]", "play")], 0)
        self.assertEqual(mixxx.values[(EQ.format(d=3), "parameter2")], 1.0)
        self.assertEqual(mixxx.values[(EQ.format(d=3), "parameter1")], 1.0)

    def test_eq_split_crossover_fades_the_outgoing_fader_gently_even_on_a_short_cross(self) -> None:
        from hands.live_kit import GENTLE_FADE_BEATS
        mixxx = ClockMixxx(step=0.05)
        mixxx.values[("[Channel2]", "play")] = 1.0
        mixxx.values[("[Channel2]", "volume")] = 1.0
        with no_sleep():
            eq_split_crossover(Live(mixxx), clock_deck=2, clock_track=TRACK, out_deck=2, in_deck=3,
                               enter_beat=8, hold_beats=0, cross_beats=8)
        # the fader reaches 0 no earlier than GENTLE_FADE_BEATS after the cross starts
        self.assertGreaterEqual(TRACK.beat_at(mixxx.seconds["[Channel2]"]), 8 + GENTLE_FADE_BEATS - 0.2)
        self.assertEqual(mixxx.values[("[Channel2]", "volume")], 0.0)

    def test_exact_loop_uses_the_native_beat_loop_when_it_can(self) -> None:
        mixxx = ClockMixxx()
        self.assertTrue(exact_loop(Live(mixxx), deck=1, track=TRACK, start_beat=318, beats=4))
        self.assertIn(("[Channel1]", "beatloop_4_activate", 1), mixxx.writes)

    def test_exact_loop_sets_sample_points_for_tuned_loops(self) -> None:
        mixxx = ClockMixxx()
        mixxx.values[("[Channel1]", "track_samplerate")] = 44100.0
        self.assertFalse(exact_loop(Live(mixxx), deck=1, track=TRACK, start_beat=319, beats=31.5))
        self.assertEqual(mixxx.values[("[Channel1]", "loop_start_position")], round(TRACK.at(319) * 44100) * 2)
        self.assertEqual(mixxx.values[("[Channel1]", "loop_end_position")], round(TRACK.at(350.5) * 44100) * 2)
        self.assertIn(("[Channel1]", "reloop_toggle", 1), mixxx.writes)
        with self.assertRaises(ValueError):
            exact_loop(Live(mixxx), deck=1, track=TRACK, start_beat=0, beats=0)

    def test_bar_pattern_validates_then_applies_each_state(self) -> None:
        mixxx = ClockMixxx()
        live = Live(mixxx)
        states = {"F": [("[Channel2]", "volume", 1.0)], ".": [("[Channel2]", "volume", 0.0)]}
        with self.assertRaises(ValueError):
            play_bar_pattern(live, clock_deck=1, clock_track=TRACK, start_beat=0, pattern="F.X", states=states)
        self.assertEqual(mixxx.writes, [])
        mixxx.values[("[Channel1]", "play")] = 1.0
        with no_sleep(), patch.object(live_kit, "CUT_SECONDS", 0.0):
            play_bar_pattern(live, clock_deck=1, clock_track=TRACK, start_beat=0, pattern="F.F.", states=states)
        volumes = [v for g, k, v in mixxx.writes if (g, k) == ("[Channel2]", "volume")]
        self.assertEqual(volumes[-1], 0.0)
        self.assertIn(1.0, volumes)


if __name__ == "__main__":
    unittest.main()
