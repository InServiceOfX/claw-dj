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

The availability tests also pin the scan's forgiving contract: it skips only
the suspicious work, keeps indexing everything else, and reports why, so a
single bad volume never blocks ingesting new music.
"""
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from brain.library_index import (
    configured_roots,
    connect,
    export_records,
    scan_status,
)
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

    def _seed(self, directory: str, count: int) -> tuple[Path, Path]:
        root = Path(directory) / "music"
        root.mkdir()
        for index_number in range(count):
            (root / f"song{index_number:03d}.mp3").write_bytes(b"not-real-audio")
        return root, Path(directory) / "library.sqlite3"

    def test_root_losing_most_of_its_tracks_keeps_them_available_and_warns(self) -> None:
        """A root that stops returning most of its files is a suspect mount.

        Formerly a known gap: a present-but-empty root was read as "every file
        was deleted", flipping availability and orphaning the enrichment and
        human dj_notes keyed to those track_ids.

        The scan does NOT abort -- aborting would block ingesting new music
        until the volume was fixed. It skips only the availability update,
        reports the reason, and finishes.
        """
        with tempfile.TemporaryDirectory() as directory:
            root, index = self._seed(directory, 24)

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
                self.assertEqual(len(export_records(index)), 24)

                for song in root.glob("*.mp3"):
                    song.unlink()
                summary = incremental_scan(
                    [root], index_path=index, min_age_seconds=0
                )

            # Completed, and flipped nothing: the expensive keys are intact.
            self.assertEqual(summary["missing"], 0)
            self.assertEqual(len(export_records(index)), 24)
            # Reported, per root, with an actionable way to proceed.
            self.assertEqual(len(summary["suspect_roots"]), 1)
            self.assertEqual(summary["suspect_roots"][0]["root"], str(root.resolve()))
            self.assertEqual(summary["suspect_roots"][0]["gone"], 24)
            self.assertIn("allow_bulk_removal", summary["warnings"])
            # Surfaced persistently for the GUI, and not as a failure.
            status = scan_status(index)
            self.assertIn("allow_bulk_removal", status["warnings"])
            self.assertIsNone(status["error"])

    def test_new_music_is_still_indexed_while_a_root_looks_suspect(self) -> None:
        """The scan stays forgiving: one bad volume must not stop ingest.

        This is the whole reason the guard warns instead of aborting -- new
        music in a healthy root still gets its metadata on the same run.
        """
        with tempfile.TemporaryDirectory() as directory:
            healthy = Path(directory) / "RnB"
            flaky = Path(directory) / "HipHop"
            for root in (healthy, flaky):
                root.mkdir()
                for index_number in range(24):
                    (root / f"song{index_number:03d}.mp3").write_bytes(b"x")
            index = Path(directory) / "library.sqlite3"

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([healthy, flaky], index_path=index, min_age_seconds=0)
                for song in flaky.glob("*.mp3"):
                    song.unlink()
                (healthy / "brand-new.mp3").write_bytes(b"x")
                summary = incremental_scan(
                    [healthy, flaky], index_path=index, min_age_seconds=0
                )

            self.assertEqual(summary["new"], 1)
            self.assertEqual(summary["suspect_roots"][0]["root"], str(flaky.resolve()))
            indexed = {Path(row["track_id"]).name for row in export_records(index)}
            self.assertIn("brand-new.mp3", indexed)
            # 48 originals still available + the new file.
            self.assertEqual(len(export_records(index)), 49)

    def test_bulk_removal_override_permits_the_flip(self) -> None:
        """The guard is a safety catch, not a wall -- real cleanups must work."""
        with tempfile.TemporaryDirectory() as directory:
            root, index = self._seed(directory, 24)

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
                for song in root.glob("*.mp3"):
                    song.unlink()
                summary = incremental_scan(
                    [root],
                    index_path=index,
                    min_age_seconds=0,
                    allow_bulk_removal=True,
                )

            self.assertEqual(summary["missing"], 24)
            self.assertEqual(export_records(index), [])

    def test_losing_a_minority_of_tracks_proceeds_normally(self) -> None:
        """Ordinary deletion handling is untouched below the refusal threshold."""
        with tempfile.TemporaryDirectory() as directory:
            root, index = self._seed(directory, 24)

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
                for song in sorted(root.glob("*.mp3"))[:4]:
                    song.unlink()
                summary = incremental_scan(
                    [root], index_path=index, min_age_seconds=0
                )

            self.assertEqual(summary["missing"], 4)
            self.assertEqual(len(export_records(index)), 20)

    def test_guard_is_evaluated_per_root_and_healthy_roots_still_reconcile(self) -> None:
        """One flaky root among several must not be masked by the healthy ones,
        and must not freeze deletion handling for the roots that are fine.

        Six genre roots are scanned together in practice; averaging the loss
        across all of them would hide a single volume going bad, and refusing
        globally would stop ordinary cleanups elsewhere.
        """
        with tempfile.TemporaryDirectory() as directory:
            healthy = Path(directory) / "RnB"
            flaky = Path(directory) / "HipHop"
            for root in (healthy, flaky):
                root.mkdir()
                for index_number in range(24):
                    (root / f"song{index_number:03d}.mp3").write_bytes(b"x")
            index = Path(directory) / "library.sqlite3"

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([healthy, flaky], index_path=index, min_age_seconds=0)
                for song in flaky.glob("*.mp3"):
                    song.unlink()
                # A genuine, proportionate deletion in the healthy root.
                for song in sorted(healthy.glob("*.mp3"))[:2]:
                    song.unlink()
                summary = incremental_scan(
                    [healthy, flaky], index_path=index, min_age_seconds=0
                )

            self.assertEqual(
                [row["root"] for row in summary["suspect_roots"]],
                [str(flaky.resolve())],
            )
            # Healthy root's 2 deletions applied; flaky root's 24 held back.
            self.assertEqual(summary["missing"], 2)
            self.assertEqual(len(export_records(index)), 46)

    def test_small_root_below_the_guard_floor_still_marks_deletions(self) -> None:
        """Deliberate floor: a handful of tracks is not a mass-orphan hazard.

        Re-indexing a few files is trivial, so the guard would only produce
        false refusals at that size. Documented rather than incidental.
        """
        with tempfile.TemporaryDirectory() as directory:
            root, index = self._seed(directory, 3)

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan([root], index_path=index, min_age_seconds=0)
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
