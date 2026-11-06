"""Vocal-over-instrumental layers: the stem crate, the layer plan, and the live run.

Ernest, 2026-10-31: list every vocals-only and instrumental-only track, preview
them, and have Mixxx play one vocal over one instrumental live at similar
levels, with exact backbeat alignment and no off-by-one count. Nothing here
starts Mixxx; the live run is exercised against a simulated deck pair.
"""
from __future__ import annotations

import math
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

import numpy as np

from brain import library_index, plan_notes, stem_crate, stem_layer_plan as slp
from hands import stem_layer


def _index_with(rows: list[dict]) -> Path:
    path = Path(tempfile.mkdtemp()) / "library.sqlite3"
    now = time.time()
    with closing(library_index.connect(path)) as db, db:
        for row in rows:
            db.execute(
                "INSERT INTO tracks (track_id, root, size_bytes, mtime_ns, title, artist, album, genre, "
                "duration_seconds, bpm, key, dj_notes, first_seen_at, last_seen_at, available) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                (row["track_id"], "/x", 1, 1, row["title"], row.get("artist", "A"), row.get("album"), None,
                 row.get("duration_seconds"), row.get("bpm"), row.get("key"), row.get("dj_notes", ""), now, now),
            )
    return path


NO_MIXXX = Path("/nonexistent/mixxxdb.sqlite")





class StemCrateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index_with([
            {"track_id": "/m/ugk/04 Int'l Players Anthem (Explicit Acappella).mp3",
             "title": "Int'l Players Anthem (I Choose You) (Explicit Acappella)", "artist": "UGK with Outkast",
             "duration_seconds": 236.2, "bpm": 79.0, "key": "Bbm"},
            {"track_id": "/m/wham/03 Careless Whisper (Instrumental).mp3",
             "title": "Careless Whisper (Instrumental)", "artist": "Wham!", "duration_seconds": 303.0,
             "bpm": 77.0, "key": "Dm"},
            {"track_id": "/m/ugk/02 Int'l Players Anthem (Instrumental).mp3",
             "title": "Int'l Players Anthem (I Choose You) (Instrumental)", "artist": "UGK with Outkast",
             "bpm": 79.0, "key": "Bbm"},
            {"track_id": "/m/wham/08 Careless Whisper.mp3", "title": "Careless Whisper", "artist": "Wham!"},
            {"track_id": "/m/kelis/02. Accapella (Edit).mp3", "title": "Accapella (Edit)", "artist": "Kelis"},
        ])

    def test_lists_vocals_and_instrumentals_separately_with_bpm_key_length(self) -> None:
        result = stem_crate.list_stems(index_path=self.index, mixxx_db=NO_MIXXX)
        self.assertEqual(result["counts"], {"vocals_only": 1, "instrumental_only": 2})
        vocal = result["vocals_only"][0]
        self.assertEqual((vocal["bpm"], vocal["key"], vocal["duration_seconds"]), (79.0, "Bbm", 236.2))
        self.assertEqual(vocal["bpm_source"], "tags")
        titles = [row["title"] for row in result["instrumental_only"]]
        self.assertIn("Careless Whisper (Instrumental)", titles)
        self.assertNotIn("Accapella (Edit)", [row["title"] for row in result["vocals_only"]])

    def test_search_ignores_apostrophes_and_kind_filter(self) -> None:
        result = stem_crate.list_stems("instrumentals", search="intl players", index_path=self.index, mixxx_db=NO_MIXXX)
        self.assertEqual(result["counts"]["vocals_only"], 0)
        self.assertEqual(len(result["instrumental_only"]), 1)

    def test_hand_override_round_trip_keeps_other_note_text(self) -> None:
        track = "/m/wham/08 Careless Whisper.mp3"
        with closing(library_index.connect(self.index)) as db, db:
            db.execute("UPDATE tracks SET dj_notes = 'cue_seconds=4' WHERE track_id = ?", (track,))
        marked = stem_crate.set_track_kind(track, "instrumental_only", self.index)
        self.assertEqual(marked["kind"], "instrumental_only")
        self.assertEqual(marked["source"], "override")
        self.assertEqual(marked["dj_notes"], "cue_seconds=4; track_kind=instrumental_only")
        listed = stem_crate.list_stems(index_path=self.index, mixxx_db=NO_MIXXX)
        self.assertIn(track, [row["track_id"] for row in listed["instrumental_only"]])
        cleared = stem_crate.set_track_kind(track, "auto", self.index)
        self.assertEqual((cleared["kind"], cleared["dj_notes"]), ("full_mix", "cue_seconds=4"))

    def test_beds_rank_tempo_then_key_and_prefer_a_different_song(self) -> None:
        rows = stem_crate.scan(self.index, with_mixxx=False)
        vocal = next(row for row in rows if row["kind"] == "vocals_only")
        ranked = stem_crate.suggest_beds(vocal, rows)
        self.assertEqual(len(ranked), 2)
        same = next(row for row in ranked if row["same_song"])
        self.assertIn("same song", same["reason"])

    def test_plan_note_overlay_keeps_the_hand_set_track_type(self) -> None:
        carried = plan_notes.carry_library_skips("track_kind=instrumental_only", "ride_beats=64")
        self.assertIn("track_kind=instrumental_only", carried)
        own = plan_notes.carry_library_skips("track_kind=instrumental_only", "track_kind=full_mix")
        self.assertEqual(own, "track_kind=full_mix")


class AlignmentTests(unittest.TestCase):
    def test_full_mix_offset_is_found_and_both_halves_agree(self) -> None:
        sr = slp.ANALYSIS_SR
        rng = np.random.default_rng(7)
        seconds = 60
        vocal = np.zeros(sr * seconds, dtype=np.float32)
        t = 0.3
        while t < seconds - 1:  # irregular syllables, band-limited noise bursts
            n = int(sr * rng.uniform(0.08, 0.3))
            start = int(t * sr)
            burst = rng.normal(0, 0.3, n).astype(np.float32) * np.hanning(n).astype(np.float32)
            vocal[start:start + n] += np.convolve(burst, np.ones(4) / 4, mode="same").astype(np.float32)
            t += rng.uniform(0.15, 0.6)
        offset = 1.237
        full = np.zeros(int(sr * (seconds + 3)), dtype=np.float32)
        full[int(offset * sr):int(offset * sr) + len(vocal)] += vocal
        beat = int(sr * 60 / 90)
        for k in range(0, len(full) - 400, beat):  # drums under the voice
            full[k:k + 400] += rng.normal(0, 0.5, 400).astype(np.float32)
        aligned = slp.align_to_sibling(vocal, full, sr=sr)
        self.assertTrue(aligned["usable"], aligned)
        self.assertAlmostEqual(aligned["offset_seconds"], offset, delta=0.012)

    def test_vocal_span_finds_the_chosen_section(self) -> None:
        db = [-80.0] * 100 + [-10.0] * 40 + [-80.0] * 60 + [-12.0] * 80 + [-80.0] * 20
        self.assertEqual(slp.vocal_span(db), {"first_seconds": 5.0, "last_seconds": 14.0})
        verse = slp.vocal_span(db, start_seconds=8.0)
        self.assertEqual(verse["first_seconds"], 10.0)

    def test_count_shift_must_be_a_whole_snare_cycle(self) -> None:
        period = 60 / 90
        vocal_map = slp.BeatMap(np.arange(0.2, 60, period), snare_parity=1)
        with self.assertRaises(slp.LayerPlanError):
            slp.choose_vocal_anchor(vocal_map, 10.0, count_shift_beats=1)
        anchor = slp.choose_vocal_anchor(vocal_map, 10.0)
        self.assertNotEqual(anchor % 2, vocal_map.snare_parity)        # a kick beat, not a snare
        self.assertLessEqual(abs(vocal_map.time_at(anchor) - 10.0), 1.5 * period)
        self.assertEqual(slp.choose_vocal_anchor(vocal_map, 10.0, count_shift_beats=2), anchor + 2)

    def test_bed_entry_is_whole_bars_after_the_first_kick(self) -> None:
        bed_map = slp.BeatMap(np.arange(0.5, 120, 60 / 90), snare_parity=0)
        entry = slp.choose_bed_entry(bed_map, 0.0, lead_bars=8)
        self.assertEqual(entry % 2, 1)
        self.assertEqual(entry - bed_map.kick_index_at_or_after(0.0), 32)

    def test_tempo_folds_double_time_grids(self) -> None:
        self.assertAlmostEqual(slp.fold_tempo(158.0, 80.0), 79.0)

    def test_beat_map_follows_a_drifting_drummer(self) -> None:
        frame = slp.HOP / slp.ANALYSIS_SR
        seconds, bpm = 200.0, 76.3
        k = np.arange(int(seconds * bpm / 60))
        drift = 0.2 * np.sin(2 * np.pi * k * (60 / bpm) / 150.0)       # +/-200 ms like Careless Whisper
        true_beats = k * 60 / bpm + 0.4 + drift
        envelope = np.zeros(int(seconds / frame) + 10)
        for i, t in enumerate(true_beats):
            envelope[int(round(t / frame))] += 1.0 if i % 2 else 0.7
        beat_map, info = slp.build_beat_map(envelope, frame_seconds=frame, bpm=76.0, duration=seconds)
        self.assertGreater(info["drift_ms"], 150)
        inner = [t for t in true_beats if 20 < t < seconds - 20]
        worst = max(abs(beat_map.time_at(round(beat_map.index_at(t))) - t) for t in inner)
        self.assertLess(worst, 0.03)

    def test_snare_parity_reads_snare_against_kick(self) -> None:
        sr = slp.ANALYSIS_SR
        rng = np.random.default_rng(3)
        beats = np.arange(0.5, 30, 0.75)
        y = np.zeros(int(sr * 31), dtype=np.float32)
        tt = np.arange(int(0.08 * sr)) / sr
        for i, t in enumerate(beats):
            n = int(t * sr)
            if i % 2:   # snare: noise burst
                y[n:n + len(tt)] += (rng.normal(0, 0.6, len(tt)) * np.exp(-tt * 40)).astype(np.float32)
            else:       # kick: low thump
                y[n:n + len(tt)] += (np.sin(2 * np.pi * 60 * tt) * np.exp(-tt * 30)).astype(np.float32)
        parity, confidence = slp.snare_parity(y, beats, sr=sr)
        self.assertEqual(parity, 1)
        self.assertGreater(confidence, 0.2)


VOCAL_ID = "/m/ugk/04 Int'l Players Anthem (Explicit Acappella).mp3"
BED_ID = "/m/wham/03 Careless Whisper (Instrumental).mp3"


def _bed_beats(drift: float = 0.0) -> list[float]:
    k = np.arange(380)
    period = 60 / 77.0
    return list(k * period + 0.3 + drift * np.sin(2 * np.pi * k * period / 150.0))


def _plan(index: Path, *, drift: float = 0.0, **kwargs) -> dict:
    vp = 60 / 79.0
    rms = [-80.0] * 400 + [-12.0] * 3000 + [-80.0] * 200   # vocal from 20 s to 170 s

    def measure(kind, path, **kw):
        if kind == "vocal":
            return {"first_seconds": 20.0, "last_seconds": 170.0, "rms_db_50ms": rms, "loudness_db": -20.0,
                    "duration_seconds": 180.0, "real_bpm": 79.0, "drift_ms": 10.0,
                    "beats": list(np.arange(0.1, 180.0, vp)), "snare_parity": 1,
                    "backbeat": "measured_via_full_mix",
                    "sibling": {"track_id": "/m/ugk/full.mp3", "title": "full", "offset_seconds": 0.004,
                                "confidence": 2.5, "half_disagreement_ms": 9.6, "usable": True}}
        return {"beats": _bed_beats(drift), "snare_parity": 0, "bpm": 77.0, "drift_ms": drift * 2000,
                "snare_confidence": 0.6, "loudness_db": -18.0, "duration_seconds": 300.0}

    return slp.plan_layer(VOCAL_ID, BED_ID, index_path=index, mixxx_db=NO_MIXXX, measure=measure, **kwargs)


class LayerPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        StemCrateTests.setUp(self)  # the same library rows

    def test_plan_keeps_the_vocal_speed_and_lands_kick_on_kick(self) -> None:
        plan = _plan(self.index)
        self.assertEqual(plan["alignment"]["backbeat"], "measured")
        self.assertEqual(plan["alignment"]["count1"], "guessed")
        self.assertEqual(plan["alignment"]["alternatives"], [-2, 2])
        self.assertAlmostEqual(plan["tempo"]["bed_rate"], 79.0 / 77.0, places=4)
        self.assertEqual(plan["levels"]["method"], "measured_gated_loudness")
        self.assertLess(plan["levels"]["bed_pregain"], 1.0)
        v, b = plan["vocal"], plan["bed"]
        self.assertNotEqual(v["anchor_index"] % 2, v["beat_map"]["snare_parity"])
        self.assertNotEqual(b["entry_index"] % 2, b["beat_map"]["snare_parity"])
        self.assertLessEqual(v["cue_seconds"], v["first_word_seconds"])
        self.assertGreater(plan["layer_seconds"], 140)

    def test_chosen_verse_start_is_respected(self) -> None:
        plan = _plan(self.index, vocal_from_seconds=60.0)
        self.assertGreaterEqual(plan["vocal"]["cue_seconds"], 60.0)
        self.assertGreaterEqual(plan["vocal"]["first_word_seconds"], 60.0)

    def test_a_one_beat_shift_is_refused_and_a_drifting_bed_is_announced(self) -> None:
        with self.assertRaises(slp.LayerPlanError):
            _plan(self.index, count_shift_beats=1)
        plan = _plan(self.index, drift=0.2)
        self.assertTrue(any("rides the pitch" in w for w in plan["warnings"]))

    def test_a_bed_must_have_a_beat_and_full_mix_beds_dip_their_mids(self) -> None:
        with self.assertRaises(slp.LayerPlanError):
            slp.plan_layer(VOCAL_ID, VOCAL_ID, index_path=self.index, mixxx_db=NO_MIXXX, measure=lambda *a, **k: {})
        levels = slp._levels({"loudness_db": -20}, {"loudness_db": -18}, "full_mix", None, None)
        self.assertLess(levels["bed_eq"]["mid"], 0.5)


class FakeDeck:
    def __init__(self, duration: float, file_bpm: float) -> None:
        self.duration, self.file_bpm = duration, file_bpm
        self.position = 0.0
        self.last = 0.0
        self.playing = False
        self.values: dict[str, float] = {"rateRange": 0.08, "rate": 0.0}

    @property
    def speed(self) -> float:
        # this fake's slider is inverted, as on some Mixxx skins
        return 1.0 - self.values["rate"] * self.values["rateRange"]


class FakeMixxx:
    """Two decks on a virtual clock; play can start `latency` seconds late."""

    def __init__(self, clock, *, vocal_latency: float = 0.0) -> None:
        self.clock = clock
        self.decks = {"[Channel1]": FakeDeck(300.0, 154.0), "[Channel2]": FakeDeck(180.0, 79.3)}
        self.latency = {"[Channel1]": 0.0, "[Channel2]": vocal_latency}
        self.started: dict[str, float] = {}
        self.master: dict[tuple, float] = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def _advance(self) -> None:
        now = self.clock.now
        for group, deck in self.decks.items():
            if deck.playing:
                begin = max(self.started[group], deck.last)
                if now > begin:
                    deck.position += (now - begin) * deck.speed
                deck.last = max(now, begin)

    def get(self, group, key):
        self._advance()
        deck = self.decks.get(group)
        if deck is None:
            return self.master.get((group, key), 0.0)
        if key == "playposition":
            return deck.position / deck.duration
        if key == "duration":
            return deck.duration
        if key == "beat_distance":
            return (deck.position / (60 / deck.file_bpm)) % 1
        if key == "file_bpm":
            return deck.file_bpm
        if key == "bpm":
            return deck.file_bpm * deck.speed
        if key == "play":
            return 1.0 if deck.playing else 0.0
        if key == "volume":
            return deck.values.get("volume", 1.0)
        return deck.values.get(key, 0.0)

    def set(self, group, key, value):
        self._advance()
        deck = self.decks.get(group)
        if deck is None:
            self.master[(group, key)] = value
            return
        if key == "play":
            if value and not deck.playing:
                deck.playing = True
                self.started[group] = self.clock.now + self.latency[group]
                deck.last = self.started[group]
            elif not value:
                deck.playing = False
        elif key == "playposition":
            deck.position = value * deck.duration
        else:
            deck.values[key] = value


class VirtualClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.001, seconds)


class LiveLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        StemCrateTests.setUp(self)

    def _run(self, plan: dict, fake: FakeMixxx, clock: VirtualClock) -> dict:
        def load(mixxx, deck, path, cue_fraction=0.1, cue_seconds=None, expected_bpm=None, **_):
            mixxx.decks[f"[Channel{deck}]"].position = float(cue_seconds or 0.0)

        with mock.patch("hands.run_mix_plan.load_deck", load), \
                mock.patch("hands.run_mix_plan.reset_instrument", lambda m: None), \
                mock.patch("hands.run_mix_plan.time.monotonic", clock), \
                mock.patch("hands.audition_transition.running_mix_processes", lambda **k: []), \
                mock.patch("hands.audition_transition.playing_decks", lambda m: []):
            return stem_layer.run_layer(plan, port=1, control_factory=lambda **k: fake,
                                        clock=clock, sleep=clock.sleep)

    def test_snares_hold_on_a_steady_instrumental(self) -> None:
        clock = VirtualClock()
        fake = FakeMixxx(clock)
        report = self._run(_plan(self.index), fake, clock)
        self.assertLess(report["held_within_ms"], 30.0)
        self.assertEqual(fake.master[("[Master]", "crossfader")], 0.0)
        self.assertEqual(fake.decks["[Channel2]"].values["rate"], 0.0)   # the voice is not stretched
        self.assertFalse(fake.decks["[Channel1]"].playing)                 # stopped after the fade

    def test_snares_hold_while_the_instrumental_drifts_200_ms(self) -> None:
        clock = VirtualClock()
        fake = FakeMixxx(clock, vocal_latency=0.02)
        report = self._run(_plan(self.index, drift=0.2), fake, clock)
        self.assertLess(report["held_within_ms"], 30.0, report["held_within_ms"])

    def test_schedule_and_dry_run_never_touch_mixxx(self) -> None:
        plan = _plan(self.index)
        timing = stem_layer.schedule(plan)
        self.assertGreater(timing["vocal_start_after_s"], 0)
        self.assertGreater(timing["total_seconds"], timing["layer_end_after_s"])
        factory = mock.Mock(side_effect=AssertionError("dry run must not connect"))
        stem_layer.run_layer(plan, dry_run=True, control_factory=factory)

    def test_lock_error_sign(self) -> None:
        plan = _plan(self.index)
        b, v = plan["bed"]["entry_index"], plan["vocal"]["anchor_index"]
        self.assertAlmostEqual(stem_layer.lock_error_beats(plan, b + 0.1, v), 0.1)


class MixSheetStemTests(unittest.TestCase):
    def test_vocal_gets_type_and_ranked_beds(self) -> None:
        from brain.mix_llm_refine import _mark_stems

        ids = {
            "t000": {"track_id": "/a", "title": "Get Up (Acapella)", "artist": "50 Cent", "bpm": 93.0, "key": "F#m"},
            "t001": {"track_id": "/b", "title": "Outta Control - Instrumental", "artist": "50 Cent", "bpm": 92.0, "key": "Ebm"},
            "t002": {"track_id": "/c", "title": "In Da Club", "artist": "50 Cent", "bpm": 90.0, "key": "F#m"},
        }
        songs = [{"id": sid} for sid in ids]
        _mark_stems(songs, ids)
        self.assertEqual(songs[0]["type"], "vocals_only")
        self.assertEqual(songs[0]["layer_beds"][0][0], "t001")
        self.assertEqual(songs[1]["type"], "instrumental")
        self.assertNotIn("type", songs[2])


class StemApiTests(unittest.TestCase):
    def test_routes_register_and_refuse_a_one_beat_count_shift(self) -> None:
        from brain import api_router
        from brain.api import api_stems
        from brain.playlist_editor import PlaylistApp

        api_router.clear()
        for pattern, methods, handler in api_stems.ROUTES:
            api_router.register(pattern, methods, handler)
        handler, _ = api_router.route("POST", "/api/stems/layer")
        self.assertIs(handler, api_stems.layer)
        app = object.__new__(PlaylistApp)
        app.mix_run_thread, app.mix_state = None, {"running": 0, "mixxx_control_port": 9995}
        app.control_port_override = None
        app.audition = mock.Mock(is_playing=lambda: False)
        app.stem_layer = mock.Mock()
        app.by_id = {}
        app.registry_path, app.legacy_index = "/nonexistent/registry.json", Path("/tmp/x.sqlite3")
        with self.assertRaises(api_stems.ApiError) as raised:
            api_stems.layer(app, {}, "POST", {"vocal_id": "/a", "bed_id": "/b", "count_shift_beats": 1}, {})
        self.assertEqual(raised.exception.status, 409)
        api_stems.layer(app, {}, "POST", {"vocal_id": "/a", "bed_id": "/b", "count_shift_beats": 2, "dry_run": True}, {})
        kwargs = app.stem_layer.start.call_args.kwargs
        self.assertEqual(kwargs["options"]["count_shift_beats"], 2)
        self.assertTrue(kwargs["options"]["dry_run"])
        api_router.clear()

    def test_session_command_carries_the_choices(self) -> None:
        session = stem_layer.StemLayerSession(python="py")
        cmd = session.command(vocal_id="/v", bed_id="/b", port=9995,
                              options={"vocal_from_seconds": 20.5, "count_shift_beats": -2, "dry_run": True,
                                       "index_path": "/i.sqlite3"})
        self.assertEqual(cmd[:4], ["py", "-u", "-m", "hands.stem_layer"])
        for flag in ("--vocal-from", "20.5", "--count-shift", "-2", "--dry-run", "--index"):
            self.assertIn(flag, cmd)


class TempoTests(unittest.TestCase):
    def test_whole_file_tempo_is_precise_enough_for_a_long_layer(self) -> None:
        frame = slp.HOP / slp.ANALYSIS_SR
        bpm = 93.37
        seconds = 180
        times = np.arange(int(seconds / frame)) * frame
        envelope = np.zeros_like(times)
        beat = 60 / bpm
        for k in range(int(seconds / beat)):
            envelope[int(round(k * beat / frame))] += 1.0 if k % 2 else 0.6   # kick / snare
        found = slp.refine_tempo(envelope, frame_seconds=frame, coarse_bpm=93.0)
        # 0.02% over 150 s is 30 ms of drift: the guard
        self.assertLess(abs(found - bpm) / bpm, 0.0002, found)
