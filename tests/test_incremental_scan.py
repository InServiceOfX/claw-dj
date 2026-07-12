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


if __name__ == "__main__":
    unittest.main()
