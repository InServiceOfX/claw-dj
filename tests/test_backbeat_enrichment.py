"""Analyze caches track evidence; Build alone plans entrances. No live decks."""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from brain import enrich_set, rhythm
from brain.library_index import connect as real_connect


class BackbeatEnrichmentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.index = self.root / "library.sqlite3"
        self.playlist = self.root / "playlist.json"
        self.cache = self.root / "rhythm"
        self.audio = self.root / "song.wav"
        self.audio.write_bytes(b"test audio; decoding mocked")
        self.track = {"track_id": str(self.audio), "artist": "Artist", "title": "Song",
                      "bpm": 120.0, "cue_seconds": 0.123,
                      "source_grid": {"grid_bpm": 120.0, "first_beat_seconds": 0.0}}
        self.playlist.write_text(json.dumps([self.track]))
        self.evidence = {
            "version": 1, "bpm": 120.0, "first_beat_seconds": 0.0,
            "duration_seconds": 100.0, "onsets": [],
            "sections": [{"start_seconds": 0.0, "end_seconds": 100.0,
                          "cadence_beats": 2.0, "phase_beats": 1.0,
                          "confidence": 0.2, "coverage": 0.4,
                          "spread_beats": 0.1, "source": "fixture"}],
        }
        with closing(real_connect(self.index)) as db:
            db.execute(
                "INSERT INTO tracks(track_id,root,size_bytes,mtime_ns,title,artist,"
                "bpm,first_seen_at,last_seen_at) VALUES (?,'/test',1,1,'Song','Artist',120,0,0)",
                (str(self.audio),),
            )
            self.seed_grid(db)
            # Legacy parity is present but must not count as new analysis.
            db.execute("INSERT INTO beat_phase VALUES (?,0,1,0.9,120,0)", (str(self.audio),))
            db.commit()
        patches = [
            patch("brain.enrich_set.connect", lambda: real_connect(self.index)),
            patch("brain.enrich_set.CHROMA_SIMILARITY", self.root / "chroma.json"),
            patch("brain.enrich_set.PHRASE_OUT", self.root / "phrases.json"),
            patch("brain.rhythm.CACHE", self.cache),
            patch("brain.rhythm._analyzer_identity", return_value={
                "version": rhythm.VERSION, "analyzer_sha256": "a" * 64,
                "binary_sha256": "b" * 64}),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        decoder = patch("brain.rhythm.core", side_effect=lambda *a, **k: copy.deepcopy(self.evidence))
        self.decoder = decoder.start()
        self.addCleanup(decoder.stop)

    def seed_grid(self, db, first=0.0):
        db.execute("INSERT OR REPLACE INTO phrases VALUES (?,0,?)",
                   (str(self.audio), json.dumps({"bpm": 120.0, "first_beat_seconds": first})))
        db.commit()

    def run_analysis(self, **overrides):
        opts = dict(playlist_path=self.playlist, skip_bpm=True, skip_lyrics=True,
                    skip_chroma=True, skip_phrases=True, skip_timelines=True,
                    skip_beat_phase=True)
        with redirect_stdout(io.StringIO()):
            return enrich_set.run_enrich(**(opts | overrides))

    def report(self):
        return enrich_set.enrichment_status(self.playlist)

    def test_legacy_parity_is_not_new_analysis(self):
        report = self.report()
        self.assertEqual(report["missing"]["beat_phase"], 0)
        self.assertEqual(report["missing"]["backbeat"], 1)
        self.assertEqual(report["backbeat"]["analyzed"], 0)
        self.decoder.assert_not_called()

    def test_analyze_reuses_uncertain_cache_without_touching_cues_or_decks(self):
        original = self.playlist.read_bytes()
        with patch("brain.enrich_set.fill_bpm") as bpm, patch("brain.rhythm.alignment") as align:
            first, second = self.run_analysis(), self.run_analysis()
        self.assertEqual(first["backbeat_analyzed"], 1)
        self.assertEqual(second["backbeat_analyzed"], 0)
        self.assertEqual(first["backbeat_errors"], {})
        self.assertEqual(self.decoder.call_count, 1)
        bpm.assert_not_called()
        align.assert_not_called()
        self.assertEqual(self.playlist.read_bytes(), original)
        self.assertEqual(self.report()["backbeat"]["tracks_with_uncertain_sections"], 1)
        self.assertEqual(self.report()["missing"]["backbeat"], 0)

    def test_build_reuses_analysis_and_fills_it_if_analyze_was_skipped(self):
        self.run_analysis()
        plan = {"tracks": [copy.deepcopy(self.track)], "events": []}
        rhythm.prepare_plan(plan)
        self.assertEqual(self.decoder.call_count, 1)
        self.assertEqual(plan["tracks"][0]["cue_seconds"], 0.123)
        other = self.root / "other.wav"
        other.write_bytes(b"different audio")
        plan["tracks"].append({**self.track, "track_id": str(other)})
        rhythm.prepare_plan(plan)
        self.assertEqual(self.decoder.call_count, 2)

    def test_status_is_read_only_and_never_hashes_audio_or_runs_dsp(self):
        self.run_analysis()
        before = {str(p): (p.stat().st_mtime_ns, p.read_bytes())
                  for p in self.cache.rglob("*") if p.is_file()}
        with patch("brain.rhythm._digest", side_effect=AssertionError("no audio hash on status")):
            for _ in range(3):
                self.assertEqual(self.report()["backbeat"]["analyzed"], 1)
        after = {str(p): (p.stat().st_mtime_ns, p.read_bytes())
                 for p in self.cache.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(self.decoder.call_count, 1)

    def test_changed_audio_is_stale_and_reanalyzed(self):
        self.run_analysis()
        self.audio.write_bytes(b"changed longer source audio fixture")
        self.assertEqual(self.report()["missing"]["backbeat"], 1)
        self.assertEqual(self.run_analysis()["backbeat_analyzed"], 1)
        self.assertEqual(self.decoder.call_count, 2)

    def test_changed_grid_uses_an_independent_cache_reference(self):
        self.run_analysis()
        with closing(real_connect(self.index)) as db:
            self.seed_grid(db, first=0.1)
        self.assertEqual(self.report()["missing"]["backbeat"], 1)
        self.run_analysis()
        self.assertEqual(self.decoder.call_count, 2)
        with closing(real_connect(self.index)) as db:
            self.seed_grid(db)
        self.assertEqual(self.report()["missing"]["backbeat"], 0)

    def test_changed_annotations_and_analyzer_invalidate_status(self):
        self.run_analysis()
        annotation = self.cache / "annotations" / f"{rhythm._digest(self.audio)}.json"
        rhythm.atomic_json(annotation, {"downbeat_seconds": 0.2})
        self.assertEqual(self.report()["missing"]["backbeat"], 1)
        self.run_analysis()
        self.assertEqual(self.decoder.call_count, 2)
        self.assertEqual(self.report()["missing"]["backbeat"], 0)
        with patch("brain.rhythm._analyzer_identity", return_value={"version": 99}):
            self.assertEqual(self.report()["missing"]["backbeat"], 1)

    def test_corrupt_cache_is_regenerated(self):
        self.run_analysis()
        cached = next(self.cache.glob("*.json"))
        cached.write_text("broken JSON")
        self.assertEqual(self.report()["missing"]["backbeat"], 1)
        self.run_analysis()
        self.assertEqual(self.decoder.call_count, 2)
        self.assertEqual(self.report()["missing"]["backbeat"], 0)

    def test_old_cache_without_reference_is_reused_without_decoding(self):
        self.run_analysis()
        next((self.cache / "references").glob("*.json")).unlink()
        self.assertEqual(self.report()["missing"]["backbeat"], 1)
        self.run_analysis()
        self.assertEqual(self.decoder.call_count, 1)
        self.assertEqual(self.report()["missing"]["backbeat"], 0)

    def test_malformed_reference_is_a_gap_not_a_status_crash(self):
        self.run_analysis()
        reference = next((self.cache / "references").glob("*.json"))
        reference.write_text('{"identity": []}')
        self.assertEqual(self.report()["missing"]["backbeat"], 1)

    def test_editor_analyze_action_includes_backbeat_when_mixxx_is_offline(self):
        from brain.playlist_editor import PlaylistApp

        # Exercise the actual background action without loading real editor state.
        app = object.__new__(PlaylistApp)
        app.mix_state = {"mixxx_control_port": 10443}
        app.enrich_thread = app.mix_thread = app.mix_run_thread = None
        app.selection = []
        app._persist_control_port = Mock()
        app._playlist_path = Mock(return_value=self.playlist)
        app._scoped_paths = Mock(return_value=None)
        app.reexport_finalized = Mock()
        app.mix_status = lambda: dict(app.mix_state)
        actual_run = enrich_set.run_enrich

        def local_steps_only(**kwargs):
            return actual_run(**(kwargs | dict(skip_lyrics=True, skip_chroma=True,
                              skip_phrases=True, skip_timelines=True, skip_beat_phase=True)))

        with patch("brain.enrich_set.run_enrich", side_effect=local_steps_only) as run, \
             patch("hands.mixxx_control.MixxxControl", side_effect=OSError("offline")), \
             redirect_stdout(io.StringIO()):
            app.start_enrich()
            app.enrich_thread.join(timeout=3)
        self.assertFalse(app.enrich_thread.is_alive())
        self.assertIsNone(app.mix_state["enrich_error"])
        self.assertEqual(app.mix_state["enrich_report"]["backbeat_analyzed"], 1)
        self.assertTrue(run.call_args.kwargs["skip_bpm"])
        self.assertNotIn("skip_backbeat", run.call_args.kwargs)
        self.assertIn("backbeat", app.mix_state["enrich_message"])

    def test_phrases_created_in_this_run_are_immediately_analyzed(self):
        with closing(real_connect(self.index)) as db:
            db.execute("DELETE FROM phrases")
            db.commit()
        def fill(db, tracks, **kwargs):
            self.seed_grid(db)
            return len(tracks)
        with patch("brain.enrich_set.fill_phrases", side_effect=fill):
            summary = self.run_analysis(skip_phrases=False)
        self.assertEqual(summary["phrases_analyzed"], 1)
        self.assertEqual(summary["backbeat_analyzed"], 1)

    def test_invalid_grid_is_explicit_and_skip_flag_prevents_analysis(self):
        with closing(real_connect(self.index)) as db:
            db.execute("UPDATE phrases SET payload='{}'")
            db.commit()
        summary = self.run_analysis()
        self.assertIn("missing valid phrase/source beatgrid", summary["backbeat_errors"][str(self.audio)])
        self.decoder.assert_not_called()
        with patch("brain.enrich_set.fill_backbeat") as fill:
            self.run_analysis(skip_backbeat=True)
        fill.assert_not_called()

    def test_analyzer_failure_is_reported_without_false_readiness(self):
        self.decoder.side_effect = RuntimeError("decoder unavailable")
        summary = self.run_analysis()
        self.assertEqual(summary["backbeat_analyzed"], 0)
        self.assertEqual(summary["backbeat_errors"][str(self.audio)], "decoder unavailable")
        self.assertEqual(self.report()["backbeat"]["missing_or_stale"], 1)

    def test_offline_cli_skips_mixxx_discovery(self):
        with patch("sys.argv", ["enrich_set", "--skip-bpm"]), \
             patch("brain.enrich_set.run_enrich") as run, \
             patch("hands.mixxx_control.discover_mixxx_control_port") as discover:
            enrich_set.main()
        discover.assert_not_called()
        self.assertTrue(run.call_args.kwargs["skip_bpm"])
        self.assertFalse(run.call_args.kwargs["skip_backbeat"])


if __name__ == "__main__":
    unittest.main()
