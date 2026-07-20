import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain.library_index import export_records, scan_status
from brain.scan_library import incremental_scan


class IncrementalScanTests(unittest.TestCase):
    def test_second_scan_does_not_read_unchanged_tags(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            song = root / "song.mp3"
            song.write_bytes(b"not-real-audio")
            index = Path(directory) / "library.sqlite3"

            def record(path, **_kwargs):
                return "ok", {
                    "track_id": str(path), "title": "Song", "artist": "Artist",
                    "album": "Album", "genre": "RnB", "duration_seconds": 180.0,
                    "size_bytes": path.stat().st_size,
                }

            with patch("brain.scan_library._read_record", side_effect=record) as reader:
                first = incremental_scan([root], index_path=index, min_age_seconds=0)
                second = incremental_scan([root], index_path=index, min_age_seconds=0)

            self.assertEqual(first["new"], 1)
            self.assertEqual(second["new"], 0)
            self.assertEqual(second["unchanged"], 1)
            self.assertEqual(reader.call_count, 1)
            self.assertEqual(export_records(index)[0]["artist"], "Artist")
            self.assertEqual(scan_status(index)["track_count"], 1)

    def test_changed_and_removed_files_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            song = root / "song.flac"
            song.write_bytes(b"one")
            index = Path(directory) / "library.sqlite3"

            def record(path, **_kwargs):
                return "ok", {
                    "track_id": str(path), "title": path.stem, "artist": "Unknown Artist",
                    "album": None, "genre": None, "duration_seconds": None,
                    "size_bytes": path.stat().st_size,
                }

            with patch("brain.scan_library._read_record", side_effect=record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
                song.write_bytes(b"a changed file")
                changed = incremental_scan([root], index_path=index, min_age_seconds=0)
                song.unlink()
                removed = incremental_scan([root], index_path=index, min_age_seconds=0)

            self.assertEqual(changed["changed"], 1)
            self.assertEqual(removed["missing"], 1)
            self.assertEqual(export_records(index), [])

    def test_scan_reports_live_progress_to_stdout_and_scan_state(self) -> None:
        # scan_state.processed was previously written only once, at the very
        # end -- a long ingest sat on "0/N files" in the GUI (which polls
        # scan_state every 750ms) and printed nothing on the CLI. The
        # progress lines and the discovered count are the observable
        # contract for both surfaces.
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            for i in range(3):
                (root / f"song{i}.mp3").write_bytes(b"not-real-audio")
            index = Path(directory) / "library.sqlite3"

            def record(path, **_kwargs):
                return "ok", {
                    "track_id": str(path), "title": path.stem, "artist": "Artist",
                    "album": None, "genre": None, "duration_seconds": None,
                    "size_bytes": path.stat().st_size,
                }

            output = io.StringIO()
            with patch("brain.scan_library._read_record", side_effect=record):
                with redirect_stdout(output):
                    incremental_scan(
                        [root], index_path=index, min_age_seconds=0, progress_every=1
                    )

            printed = output.getvalue()
            self.assertIn("discovered 3 audio files", printed)
            self.assertIn("reading tags for 3 new/changed file(s)", printed)
            # progress_every=1 -> per-file rate/ETA lines during the tag read
            self.assertIn("3/3 new/changed files", printed)
            status = scan_status(index)
            self.assertEqual(status["discovered"], 3)
            self.assertEqual(status["processed"], 3)


if __name__ == "__main__":
    unittest.main()
