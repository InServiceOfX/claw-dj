"""Shared provider routing and review boundaries, using synthetic music only."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from brain import llm_providers, pick_candidates, playlist_editor


class CandidateProviderTest(TestCase):
    def test_every_provider_uses_the_same_scoped_pick_call(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            view, ids = root / "view.json", root / "ids.json"
            view.write_text(json.dumps({"tracks": [
                {"id": f"n{i:04}", "artist": "Artist", "title": f"Song {i}"}
                for i in range(3)
            ]}))
            ids.write_text(json.dumps({f"/private/music/{i}.mp3": f"n{i:04}" for i in range(3)}))
            for provider in llm_providers.PROVIDERS:
                with self.subTest(provider=provider), patch.object(pick_candidates, "ask", return_value='["n0000","invented","n0000","n0001","n0002"]') as ask:
                    picks = pick_candidates.run_pick(engine=provider, brief="smooth", count=2, view_path=view, id_map_path=ids)
                    self.assertEqual([p["id"] for p in picks], ["n0000", "n0001"])
                    self.assertEqual(ask.call_args.args[0], provider)
                    self.assertNotIn("/private/music", ask.call_args.args[1])

    def test_whole_library_uses_library_pool_instead_of_latest_scan(self):
        view = {"tracks": [{"id": "w0000", "artist": "Artist", "title": "Old song"}]}
        with patch.object(pick_candidates, "build_whole_library_view", return_value=(view, {"w0000": "/old.mp3"})) as library, patch.object(pick_candidates, "ask", return_value='["w0000"]'):
            picks = pick_candidates.run_pick(engine="llama-server", brief="old soul", pool="library", view_path=Path("/does-not-exist"))
        library.assert_called_once_with("old soul")
        self.assertEqual(picks[0]["track_id"], "/old.mp3")

    def test_invalid_inputs_never_call_a_provider_or_read_pool_files(self):
        for engine, pool, count in [("nemoclaw", "new", 20), ("h-agent", "new", 20), ("generic", "new", 20), ("both", "new", 20), ("llama-server", "other", 20), ("llama-server", "new", 51)]:
            with self.subTest(engine=engine, pool=pool, count=count), patch.object(pick_candidates, "ask") as ask:
                with self.assertRaises(ValueError):
                    pick_candidates.run_pick(engine=engine, brief="smooth", pool=pool, count=count)
                ask.assert_not_called()

    def test_empty_array_is_an_honest_empty_result(self):
        self.assertEqual(pick_candidates.parse_pick_ids("[]", {"n0000"}), [])


class BrainPreviewTest(TestCase):
    def app(self):
        with patch.object(playlist_editor.PlaylistApp, "reload"):
            app = playlist_editor.PlaylistApp()
        app._annotate = lambda picks: picks
        return app

    def test_candidate_job_saves_provider_cache_but_does_not_apply_selection(self):
        with TemporaryDirectory() as tmp:
            cache = Path(tmp) / "picks.json"
            app = self.app()
            picks = [{"track_id": "/synthetic.mp3", "artist": "Artist", "title": "Song"}]
            with patch.object(playlist_editor, "BRAIN_CACHE", {"hcompany-api": cache}), patch("brain.pick_candidates.run_pick", return_value=picks) as pick, patch.object(app, "apply_picks") as apply:
                app.ask_brain("smooth", "hcompany-api", 5, "library")
                app.brain_thread.join(3)
                self.assertFalse(app.brain_thread.is_alive())
                self.assertIsNone(app.brain_state["error"])
                self.assertEqual(json.loads(cache.read_text())["picks"], picks)
                pick.assert_called_once_with(engine="hcompany-api", brief="smooth", count=5, pool="library")
                apply.assert_not_called()

    def test_every_provider_can_preview_notes_without_writing(self):
        rows = [{"track_id": "/synthetic.mp3", "artist": "Artist", "title": "Song", "dj_notes": ""}]
        for provider in llm_providers.PROVIDERS:
            app = self.app()
            with self.subTest(provider=provider), patch("brain.mix_directives.load_playlist", return_value=rows), patch("brain.mix_directives.build_prompt", return_value="PROMPT"), patch("brain.mix_directives.parse_directives", return_value=({"/synthetic.mp3": "ride_beats=192"}, None)), patch.object(llm_providers, "ask", return_value="{}") as ask, patch("brain.mix_directives.apply_directives") as apply:
                app.ask_directives("let the verse breathe", provider)
                app.directives_thread.join(3)
                self.assertIsNone(app.directives_state["error"])
                self.assertEqual(app.directives_state["preview"]["notes"][0]["new"], "ride_beats=192")
                ask.assert_called_once_with(provider, "PROMPT")
                apply.assert_not_called()

    def test_retired_engines_cannot_start_a_worker(self):
        app = self.app()
        for engine in ("nemoclaw", "h-agent", "generic", "both", "none"):
            with self.subTest(engine=engine), self.assertRaisesRegex(ValueError, "retired"):
                app.ask_brain("smooth", engine, 20)
            with self.assertRaisesRegex(ValueError, "retired"):
                app.ask_directives("smooth", engine)
        self.assertIsNone(app.brain_thread)
        self.assertIsNone(app.directives_thread)

    def test_build_rejects_missing_analysis_before_writing_or_model_calls(self):
        with TemporaryDirectory() as tmp:
            playlist = Path(tmp) / "playlist.json"
            playlist.write_text(json.dumps([{"track_id": "/synthetic.mp3", "bpm": 0}]))
            app = self.app()
            with patch.object(app, "_playlist_path", return_value=playlist), patch.object(app, "_mix_plan_path", return_value=Path(tmp) / "mix.json"), patch.object(app, "_active_slug", return_value=None), patch.object(llm_providers, "ask") as ask:
                with self.assertRaisesRegex(ValueError, "Analyze & enrich"):
                    app.build_mix("club-set", "smooth", order_engine="hcompany-api")
                self.assertIsNone(app.mix_thread)
                ask.assert_not_called()
