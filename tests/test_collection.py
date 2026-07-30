"""The collection's location is data, not a constant in source code.

Covers R1' (no volume label or mount prefix in code/config defaults) and R2'
(the collection's stable id and this machine's mount base are recorded in the
index, so the portable-database location is re-derivable without reading
code). Track identity itself is still the absolute path on purpose -- see
tests/test_music_collection_identity.py.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain.collection import (
    CollectionNotConfiguredError,
    configured_collection,
    derive_mount_base,
    marker_path,
    portable_db_path,
    register_collection,
    resolve_portable_db,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _record(path: Path, **_kwargs):
    return "ok", {
        "track_id": str(path), "title": path.stem, "artist": "Artist",
        "album": None, "genre": None, "duration_seconds": None,
        "size_bytes": path.stat().st_size,
    }


def _collection_with_roots(directory: str) -> tuple[Path, Path]:
    """A drive laid out like the real one: genre roots under one collection."""
    base = Path(directory) / "MyDrive" / "Music"
    for genre in ("HipHop", "RnB"):
        (base / genre).mkdir(parents=True)
        (base / genre / "song.mp3").write_bytes(b"not-real-audio")
    return base, Path(directory) / "library.sqlite3"


class NoHardcodedVolumeLabelTests(unittest.TestCase):
    def test_no_volume_label_in_module_level_code_defaults(self) -> None:
        """R1' negative test.

        The label may appear in prose (docstrings, docs, test fixtures) where
        it documents the contract, but must not be a module-level constant or
        an argparse/function default that code would actually use. This is the
        wall that stops `/Volumes/<label>/...` creeping back in as a default.
        """
        offenders: list[str] = []
        for source in sorted((REPO_ROOT / "brain").rglob("*.py")):
            for number, line in enumerate(
                source.read_text().splitlines(), start=1
            ):
                stripped = line.strip()
                if "/Volumes/" not in stripped:
                    continue
                # Prose is fine; an assignment or a default= is not.
                is_assignment = (
                    "=" in stripped.split("/Volumes/")[0]
                    and not stripped.startswith("#")
                    and not stripped.startswith("*")
                )
                if is_assignment:
                    offenders.append(
                        f"{source.relative_to(REPO_ROOT)}:{number}: {stripped}"
                    )
        self.assertEqual(offenders, [], "hardcoded mount path used as a default")

    def test_portable_db_resolution_needs_a_registered_collection(self) -> None:
        """Never guess a drive: refuse with an actionable message instead."""
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "library.sqlite3"
            with self.assertRaises(CollectionNotConfiguredError) as caught:
                resolve_portable_db(index)
            message = str(caught.exception)
            self.assertIn("brain.collection register", message)
            self.assertIn("--usb-db", message)


class CollectionRegistrationTests(unittest.TestCase):
    def test_mount_base_is_derived_from_the_configured_roots(self) -> None:
        """An existing setup needs no manual configuration: the genre roots
        share the collection as their common parent."""
        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)
            from brain.scan_library import incremental_scan

            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan(
                    [base / "HipHop", base / "RnB"],
                    index_path=index,
                    min_age_seconds=0,
                )

            self.assertEqual(derive_mount_base(index_path=index), base.resolve())

    def test_register_records_mount_base_and_a_stable_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)

            result = register_collection(base, index_path=index)

            self.assertEqual(result["mount_base"], str(base.resolve()))
            self.assertEqual(result["volume_label"], "Music")
            self.assertTrue(result["marker_created"])
            stored = configured_collection(index)
            self.assertEqual(stored["collection_id"], result["collection_id"])
            self.assertEqual(stored["mount_base"], str(base.resolve()))
            # Re-derivable from data alone, with no reference to source code.
            self.assertEqual(
                resolve_portable_db(index), portable_db_path(base.resolve() / 'clawdj')
            )

    def test_an_existing_clawdj_dir_above_the_collection_is_reused(self) -> None:
        """Regression: do not strand an established portable database.

        The real drive keeps `<drive>/clawdj/` beside `<drive>/Music/`, not
        inside it. Assuming `<mount_base>/clawdj` pointed export/import at a
        path one level below the actual 22MB database and its archives, which
        would have silently created a second, empty copy. The existing
        directory is discovered by searching upward instead.
        """
        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)
            established = base.parent / "clawdj"
            established.mkdir()
            (established / "library.sqlite3").write_bytes(b"pretend-db")

            result = register_collection(base, index_path=index)

            self.assertEqual(result["data_dir"], str(established.resolve()))
            self.assertEqual(
                resolve_portable_db(index),
                established.resolve() / "library.sqlite3",
            )
            # The marker landed beside the real database, not in a new dir.
            self.assertTrue(marker_path(established).exists())
            self.assertFalse((base / "clawdj").exists())

    def test_the_id_travels_with_the_drive_not_the_machine(self) -> None:
        """R2's portability point.

        The id lives in a marker on the collection, so a second machine
        registering the same drive records the SAME collection id. If the id
        were minted per machine, two machines could never agree on which
        collection they were both looking at.
        """
        with tempfile.TemporaryDirectory() as directory:
            base, first_index = _collection_with_roots(directory)
            second_index = Path(directory) / "other-machine.sqlite3"

            first = register_collection(base, index_path=first_index)
            second = register_collection(base, index_path=second_index)

            self.assertEqual(first["collection_id"], second["collection_id"])
            self.assertTrue(first["marker_created"])
            self.assertFalse(second["marker_created"])

    def test_re_registering_updates_the_mount_base_and_keeps_the_id(self) -> None:
        """The same drive mounted somewhere else is still the same collection.

        This is what makes a remount (or a different platform's mount point)
        survivable without minting a second identity.
        """
        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)
            original = register_collection(base, index_path=index)

            moved = Path(directory) / "remounted"
            moved.mkdir()
            (moved / "clawdj").mkdir()
            # Carry the marker across, as moving the physical drive would.
            marker_path(moved / 'clawdj').write_text(marker_path(base / 'clawdj').read_text())

            after = register_collection(moved, index_path=index)

            self.assertEqual(after["collection_id"], original["collection_id"])
            self.assertEqual(
                configured_collection(index)["mount_base"], str(moved.resolve())
            )

    def test_unreadable_marker_is_reported_not_silently_replaced(self) -> None:
        """A corrupt marker must not cause a new identity to be minted, which
        would orphan everything keyed to the old one."""
        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)
            marker_path(base / 'clawdj').parent.mkdir(parents=True, exist_ok=True)
            marker_path(base / 'clawdj').write_text("{not json")

            with self.assertRaises(RuntimeError) as caught:
                register_collection(base, index_path=index)
            self.assertIn("collection marker", str(caught.exception))

    def test_marker_contents_are_json_with_the_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)
            result = register_collection(base, index_path=index)
            payload = json.loads(marker_path(base / 'clawdj').read_text())
            self.assertEqual(payload["collection_id"], result["collection_id"])


class SchemaMigrationTests(unittest.TestCase):
    def test_index_predating_data_dir_migrates_and_re_registers(self) -> None:
        """Regression: an existing index must not break on the new column.

        `CREATE TABLE IF NOT EXISTS` does not alter a table that already
        exists, so an index whose `collections` table was created before
        `data_dir` needs an additive migration. Hit for real on the live
        library; fresh temp databases in the other tests could never catch it.
        """
        from contextlib import closing

        from brain.library_index import connect

        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)
            # Build the older shape by hand, then drop the new column.
            with closing(connect(index)) as db:
                db.execute("DROP TABLE collections")
                db.execute(
                    """CREATE TABLE collections (
                           collection_id TEXT PRIMARY KEY,
                           mount_base TEXT NOT NULL,
                           volume_label TEXT,
                           created_at REAL NOT NULL,
                           last_seen_at REAL)"""
                )
                db.execute(
                    "INSERT INTO collections(collection_id, mount_base, "
                    "volume_label, created_at, last_seen_at) VALUES (?,?,?,?,?)",
                    # Resolved, as register_collection always writes it.
                    ("legacy-id", str(base.resolve()), "Music", 1.0, 1.0),
                )
                db.commit()

            # Connecting migrates; the legacy row survives with an empty value.
            with closing(connect(index)) as db:
                columns = {row[1] for row in db.execute("PRAGMA table_info(collections)")}
            self.assertIn("data_dir", columns)
            self.assertEqual(configured_collection(index)["data_dir"], "")

            # An empty data_dir must refuse rather than guess a location.
            with self.assertRaises(CollectionNotConfiguredError) as caught:
                resolve_portable_db(index)
            self.assertIn("re-run", str(caught.exception))

            # Re-registering repopulates it without minting a new identity.
            result = register_collection(base, index_path=index)
            self.assertEqual(result["collection_id"], "legacy-id")
            self.assertEqual(result["data_dir"], str((base / "clawdj").resolve()))
            self.assertEqual(
                resolve_portable_db(index),
                (base / "clawdj" / "library.sqlite3").resolve(),
            )


class PortableLibraryResolutionTests(unittest.TestCase):
    def test_export_then_import_use_the_registered_location(self) -> None:
        """End to end with no explicit --usb-db and no hardcoded label.

        Mirrors the real two-machine flow: index a collection, export to the
        drive, then merge that export into a second machine's empty index --
        both sides resolving the drive path from their own registration.
        """
        from brain.portable_library import export_db, import_db
        from brain.scan_library import incremental_scan

        with tempfile.TemporaryDirectory() as directory:
            base, index = _collection_with_roots(directory)
            with patch("brain.scan_library._read_record", side_effect=_record):
                incremental_scan(
                    [base / "HipHop", base / "RnB"],
                    index_path=index,
                    min_age_seconds=0,
                )
            register_collection(base, index_path=index)

            destination = export_db(index)
            self.assertEqual(destination, portable_db_path(base.resolve() / 'clawdj'))
            self.assertTrue(destination.exists())

            other_machine = Path(directory) / "other-machine.sqlite3"
            register_collection(base, index_path=other_machine)
            summary = import_db(local=other_machine)

            # The two indexed tracks carried over without either side naming
            # a volume label.
            self.assertEqual(summary["tracks_added"], 2)


if __name__ == "__main__":
    unittest.main()
