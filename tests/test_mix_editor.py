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
                status = app.build_mix("dj-showcase", "quick showcase", tracks=3)
                self.assertEqual(status["building"], 1)
                deadline = time.time() + 10
                while app.mix_thread and app.mix_thread.is_alive() and time.time() < deadline:
                    time.sleep(0.05)
                final = app.mix_status()
                self.assertEqual(final["building"], 0, final)
                self.assertIsNone(final["error"], final)
                self.assertTrue(final["plan_ready"])
                self.assertEqual(final["summary"]["track_count"], 3)
                self.assertTrue(plan_path.exists())


if __name__ == "__main__":
    unittest.main()
