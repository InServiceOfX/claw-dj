"""Characterization tests for the music-collection identity contract.

Written BEFORE any change, against the untouched implementation, so the
current behavior is pinned as a mold before the collection/mount work
starts. See docs/dj-formats/ for the unrelated DJ-format mold; this file
covers how tracks are identified and when they are considered available.

Decision recorded 2026-07-30 (Ernest): track identity stays the ABSOLUTE
file path for now (Tier 1). A relative-path migration (Tier 2) is deferred
until a real trigger appears -- running on Linux, or moving the collection
off the USB stick onto internal/NAS storage. Because identity is the
absolute path, the volume label is part of the collection contract: a
replacement volume must be named identically or every track_id and every
human dj_notes annotation orphans.

The test named ...currently_marks_all_tracks_unavailable pins a KNOWN GAP,
not desired behavior. It is here so the fix has a documented starting
point.
"""
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from brain.library_index import configured_roots, connect, export_records
from brain.scan_library import incremental_scan


def _record(path: Path, **_kwargs):
    """Stand in for the mutagen tag read so these tests need no real audio."""
    return "ok", {
        "track_id": str(path),
        "title": path.stem,
        "artist": "Artist",
        "album": None,
        "genre": None,
        "duration_seconds": None,
        "size_bytes": path.stat().st_size,
    }


class TrackIdentityTests(unittest.TestCase):
    def test_track_id_is_the_absolute_file_path(self) -> None:
        """Tier 2 tripwire.

        Identity is deliberately the absolute path today. If a future change
        makes track_id collection-relative, the scan's identity function
        (brain/scan_library.py) and every stored key must move together --
        otherwise a rescan sees every file as new and writes duplicate rows
        under both key styles. This test failing is the intended signal that
        such a migration is underway and must be completed atomically.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            song = root / "song.mp3"
            song.write_bytes(b"not-real-audio")
            index = Path(directory) / "library.sqlite3"

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)

            with closing(connect(index)) as db:
                row = db.execute("SELECT track_id, root FROM tracks").fetchone()

            self.assertEqual(row["track_id"], str(song.resolve()))
            self.assertTrue(Path(row["track_id"]).is_absolute())
            self.assertEqual(row["root"], str(root.resolve()))


class RootAvailabilityTests(unittest.TestCase):
    def test_absent_root_refuses_to_scan_and_leaves_the_index_untouched(self) -> None:
        """An unplugged USB stick must not be read as 'the music was deleted'.

        incremental_scan validates every root before opening the database, so
        an absent mount raises and no availability is rewritten. This is the
        safety property that makes an unplugged stick harmless; it must not
        regress when mount handling changes.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            (root / "song.mp3").write_bytes(b"not-real-audio")
            index = Path(directory) / "library.sqlite3"

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
            self.assertEqual(len(export_records(index)), 1)

            missing_root = Path(directory) / "not-mounted"
            with self.assertRaises(FileNotFoundError):
                incremental_scan([missing_root], index_path=index, min_age_seconds=0)

            # Still available: the failed scan changed nothing.
            self.assertEqual(len(export_records(index)), 1)

    def test_single_deleted_file_marks_only_that_track_unavailable(self) -> None:
        """Per-file missing detection is correct and must survive the R5 fix.

        The guard against a mass availability flip must not be built by
        removing ordinary deletion handling.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            keep = root / "keep.mp3"
            drop = root / "drop.mp3"
            keep.write_bytes(b"not-real-audio")
            drop.write_bytes(b"not-real-audio")
            index = Path(directory) / "library.sqlite3"

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
                drop.unlink()
                summary = incremental_scan(
                    [root], index_path=index, min_age_seconds=0
                )

            self.assertEqual(summary["missing"], 1)
            remaining = [row["track_id"] for row in export_records(index)]
            self.assertEqual(remaining, [str(keep.resolve())])

    def test_present_but_empty_root_currently_marks_all_tracks_unavailable(self) -> None:
        """KNOWN GAP (not desired behavior) -- pinned so the fix has a baseline.

        A root that still exists but yields zero files -- a flaky or partially
        mounted ExFAT volume, or an unreadable directory -- is treated as
        'every file under it was deleted'. On the real library that silently
        flips ~54k rows to available=0 and orphans the enrichment and
        human dj_notes keyed to them.

        The intended behavior is to refuse a mass availability flip when a
        root that previously held tracks suddenly returns nothing. When that
        guard lands, this test should be replaced by its positive form.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            for index_number in range(3):
                (root / f"song{index_number}.mp3").write_bytes(b"not-real-audio")
            index = Path(directory) / "library.sqlite3"

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
                self.assertEqual(len(export_records(index)), 3)

                for song in root.glob("*.mp3"):
                    song.unlink()
                summary = incremental_scan(
                    [root], index_path=index, min_age_seconds=0
                )

            self.assertEqual(summary["missing"], 3)
            self.assertEqual(export_records(index), [])


class ConfiguredRootsTests(unittest.TestCase):
    def test_roots_are_user_specified_and_persisted_per_machine(self) -> None:
        """Roots are already user-specified data, not hardcoded paths.

        They are registered by scanning them and read back from the index, so
        each machine carries its own set. The collection work must preserve
        this rather than reintroduce a fixed location.
        """
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "HipHop"
            second = Path(directory) / "RnB"
            for root in (first, second):
                root.mkdir()
                (root / "song.mp3").write_bytes(b"not-real-audio")
            index = Path(directory) / "library.sqlite3"

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([first, second], index_path=index, min_age_seconds=0)

            self.assertEqual(
                configured_roots(index),
                sorted([str(first.resolve()), str(second.resolve())]),
            )


if __name__ == "__main__":
    unittest.main()
