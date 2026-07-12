"""Lightweight tests for playlist_editor mix endpoints (no HTTP server)."""
from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

# These tests patch DATA_DIR-backed paths by exercising PlaylistApp methods
# against a temporary finalized playlist.


class MixEditorTest(unittest.TestCase):
    def test_start_mix_requires_confirm(self) -> None:
        from brain.playlist_editor import PlaylistApp

        app = PlaylistApp()
        with self.assertRaises(ValueError) as ctx:
            app.start_mix(confirm=False)
        self.assertIn("confirmation", str(ctx.exception).lower())

    def test_build_mix_background_writes_summary(self) -> None:
        from brain import playlist_editor as pe
        from brain.playlist_editor import PlaylistApp

        tracks = [
            {
                "track_id": f"/music/{i}.mp3",
                "artist": f"Artist{i}",
                "title": f"Title{i}",
                "bpm": 90.0 + i,
                "key": "Am",
            }
            for i in range(4)
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            playlist = root / "playlist.json"
            plan_path = root / "mix_plan.json"
            playlist.write_text(json.dumps(tracks))
            with patch.object(pe, "DEFAULT_PLAYLIST_JSON", playlist), patch.object(pe, "MIX_PLAN_PATH", plan_path):
                app = PlaylistApp()
                # Build full finalized set so plan_ready (not stale).
                status = app.build_mix("dj-showcase", "", tracks=None, order_engine="none")
                self.assertEqual(status["building"], 1)
                deadline = time.time() + 10
                while app.mix_thread and app.mix_thread.is_alive() and time.time() < deadline:
                    time.sleep(0.05)
                final = app.mix_status()
                self.assertEqual(final["building"], 0, final)
                self.assertIsNone(final["error"], final)
                self.assertFalse(final.get("plan_stale"), final)
                self.assertTrue(final["plan_ready"], final)
                self.assertEqual(final["summary"]["track_count"], 4)
                self.assertTrue(plan_path.exists())

    def test_finalized_snapshot_and_plan_stale(self) -> None:
        from brain import playlist_editor as pe
        from brain.build_mix_plan import compose_mix_plan
        from brain.playlist_editor import PlaylistApp

        tracks = [
            {
                "track_id": f"/music/{i}.mp3",
                "artist": f"Artist{i}",
                "title": f"Title{i}",
                "bpm": 90.0 + i,
                "key": "Am",
            }
            for i in range(4)
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            playlist = root / "playlist.json"
            plan_path = root / "mix_plan.json"
            playlist.write_text(json.dumps(tracks[:3]))
            compose_mix_plan(
                playlist=playlist,
                profile_name="dj-showcase",
                mix_brief="",
                order_engine="none",
                tracks=3,
                out=plan_path,
            )
            with patch.object(pe, "DEFAULT_PLAYLIST_JSON", playlist), patch.object(pe, "MIX_PLAN_PATH", plan_path):
                app = PlaylistApp()
                status = app.mix_status()
                self.assertTrue(status["playlist_ready"])
                self.assertEqual(status["finalized"]["count"], 3)
                self.assertFalse(status["plan_stale"], status)
                # Adding an unanalyzed track to finalized set: plan still matches
                # analyzed ids, so not stale — but missing_bpm is reported.
                tracks_plus = tracks[:3] + [
                    {"track_id": "/music/x.mp3", "artist": "50 Cent", "title": "Many Man (Wish Death)", "bpm": None, "key": None}
                ]
                playlist.write_text(json.dumps(tracks_plus))
                status2 = app.mix_status()
                self.assertEqual(status2["finalized"]["missing_bpm_count"], 1)
                self.assertFalse(status2["plan_stale"])
                # Adding a new analyzed track makes plan stale.
                tracks_plus2 = tracks  # all 4 analyzed
                playlist.write_text(json.dumps(tracks_plus2))
                status3 = app.mix_status()
                self.assertTrue(status3["plan_stale"])
                self.assertFalse(status3["plan_ready"])

    def test_suggest_blends_always_has_message(self) -> None:
        from brain.library import Track
        from brain.playlist_editor import PlaylistApp

        app = PlaylistApp()
        app.tracks = [
            Track("/a.mp3", "A", "Art", bpm=100.0, key="Am"),
            Track("/b.mp3", "B", "Art", bpm=101.0, key="Am"),
            Track("/c.mp3", "C", "Art", bpm=None, key=None),
            Track("/d.mp3", "D", "Other", bpm=100.5, key="Am"),
        ]
        app.by_id = {t.track_id: t for t in app.tracks}
        app.selection = ["/a.mp3", "/b.mp3", "/c.mp3"]
        app.selected = set(app.selection)
        app.excluded = set()
        result = app.suggest_blends(limit=5)
        self.assertIn("message", result)
        self.assertTrue(result["message"])
        self.assertEqual(len(result["unanalyzed_in_set"]), 1)
        self.assertEqual(result["unanalyzed_in_set"][0]["title"], "C")


if __name__ == "__main__":
    unittest.main()
