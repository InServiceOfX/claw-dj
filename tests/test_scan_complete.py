import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.catalog import find_duplicates
from brain.scan_library import choose_title, incomplete_reason, title_from_filename


class TitleFromRenameTest(TestCase):
    def test_filename_preferred_for_man_men_typo(self) -> None:
        path = Path("/music/04. Many Men (Wish Death).mp3")
        self.assertEqual(title_from_filename(path), "Many Men (Wish Death)")
        self.assertEqual(
            choose_title("Many Man (Wish Death)", "Many Men (Wish Death)"),
            "Many Men (Wish Death)",
        )
        # Unrelated tag wins when not a near-typo of the filename.
        self.assertEqual(choose_title("In Da Club", "04. Track"), "In Da Club")


class IncompleteFileTest(TestCase):
    def test_sibling_part_marker_flags_file(self) -> None:
        with TemporaryDirectory() as tmp:
            audio = Path(tmp) / "song.mp3"
            audio.write_bytes(b"x" * 128)
            (Path(tmp) / "song.mp3.part").write_bytes(b"")
            reason = incomplete_reason(audio, min_age_seconds=0, now=time.time())
            self.assertIn(".part", reason)

    def test_zero_byte_placeholder_flags_file(self) -> None:
        with TemporaryDirectory() as tmp:
            audio = Path(tmp) / "song.mp3"
            audio.write_bytes(b"")
            reason = incomplete_reason(audio, min_age_seconds=0, now=time.time())
            self.assertEqual(reason, "zero-byte placeholder")

    def test_recent_mtime_flags_file_but_old_file_passes(self) -> None:
        with TemporaryDirectory() as tmp:
            audio = Path(tmp) / "song.mp3"
            audio.write_bytes(b"x" * 128)
            self.assertIsNotNone(
                incomplete_reason(audio, min_age_seconds=300, now=time.time())
            )
            # Same file "seen" 10 minutes later counts as settled.
            self.assertIsNone(
                incomplete_reason(audio, min_age_seconds=300, now=time.time() + 600)
            )


class DuplicateDetectionTest(TestCase):
    def test_same_song_different_rips_grouped(self) -> None:
        records = [
            {
                "track_id": "/m/HipHop/Snoop/Gin And Juice.mp3",
                "artist": "Snoop Doggy Dogg",
                "title": "Gin And Juice",
            },
            {
                "track_id": "/m/HipHop/Compilations/gin and juice (Explicit).mp3",
                "artist": "Snoop Doggy Dogg",
                "title": "Gin And Juice (Explicit)",
            },
            {
                "track_id": "/m/HipHop/Snoop/Lodi Dodi.mp3",
                "artist": "Snoop Doggy Dogg",
                "title": "Lodi Dodi",
            },
        ]
        groups = find_duplicates(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["track_ids"]), 2)
        self.assertEqual(groups[0]["artist"], "snoop doggy dogg")

    def test_untitled_records_never_grouped(self) -> None:
        records = [
            {"track_id": "/a.mp3", "artist": "X", "title": ""},
            {"track_id": "/b.mp3", "artist": "X", "title": ""},
        ]
        self.assertEqual(find_duplicates(records), [])
