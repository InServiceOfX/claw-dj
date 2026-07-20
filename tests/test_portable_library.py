"""Merge semantics for carrying library.sqlite3 between machines on the USB.

The import must be safe against ANY local state (fresh clone, stale copy,
diverged edits) — fill-missing only, never clobbering local dj_notes, and
idempotent on a second run.
"""
import tempfile
import time
import unittest
from pathlib import Path

from brain.library_index import connect
from brain.portable_library import export_db, import_db


def _add_track(db, track_id: str, *, bpm=None, key=None, dj_notes="") -> None:
    db.execute(
        """INSERT OR REPLACE INTO tracks
        (track_id, root, size_bytes, mtime_ns, title, artist, album, genre,
         duration_seconds, bpm, key, energy, first_seen_at, last_seen_at,
         available, tag_status, dj_notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,'ok',?)""",
        (track_id, "/music", 1, 1, Path(track_id).stem, "Artist", None, None,
         180.0, bpm, key, None, time.time(), time.time(), dj_notes),
    )


class PortableLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.source = base / "macbook" / "library.sqlite3"
        self.usb = base / "usb" / "library.sqlite3"
        self.dest = base / "macmini" / "library.sqlite3"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_export_then_import_into_empty_machine(self) -> None:
        with connect(self.source) as db:
            _add_track(db, "/music/a.mp3", bpm=94.0, key="Gm", dj_notes="cue_seconds=0")
            db.execute(
                "INSERT INTO phrases(track_id, analyzed_at, payload) VALUES (?,?,?)",
                ("/music/a.mp3", time.time(), "{}"),
            )
            db.execute(
                "INSERT INTO roots(path, added_at) VALUES (?,?)", ("/music", time.time())
            )
            db.commit()
        export_db(self.source, self.usb)
        summary = import_db(self.usb, self.dest)
        self.assertEqual(summary["tracks_added"], 1)
        self.assertEqual(summary["phrases_added"], 1)
        self.assertEqual(summary["roots_added"], 1)
        with connect(self.dest) as db:
            row = db.execute("SELECT bpm, key, dj_notes FROM tracks").fetchone()
        self.assertEqual((row["bpm"], row["key"]), (94.0, "Gm"))
        self.assertEqual(row["dj_notes"], "cue_seconds=0")

    def test_import_fills_missing_analysis_but_never_clobbers_local_notes(self) -> None:
        with connect(self.source) as db:
            _add_track(db, "/music/a.mp3", bpm=94.0, key="Gm", dj_notes="imported note")
            db.commit()
        export_db(self.source, self.usb)
        with connect(self.dest) as db:
            # Local machine has the track already: no analysis yet, but a
            # human already wrote a DIFFERENT note here.
            _add_track(db, "/music/a.mp3", bpm=None, key=None, dj_notes="local note")
            db.commit()
        summary = import_db(self.usb, self.dest)
        self.assertEqual(summary["tracks_added"], 0)
        self.assertEqual(summary["fields_filled"], 2)  # bpm + key
        self.assertEqual(summary["notes_imported"], 0)
        self.assertEqual(summary["note_conflicts"], ["/music/a.mp3"])
        with connect(self.dest) as db:
            row = db.execute("SELECT bpm, key, dj_notes FROM tracks").fetchone()
        self.assertEqual((row["bpm"], row["key"]), (94.0, "Gm"))
        self.assertEqual(row["dj_notes"], "local note")

    def test_import_fills_empty_local_note(self) -> None:
        with connect(self.source) as db:
            _add_track(db, "/music/a.mp3", dj_notes="ride_beats=49")
            db.commit()
        export_db(self.source, self.usb)
        with connect(self.dest) as db:
            _add_track(db, "/music/a.mp3", dj_notes="")
            db.commit()
        summary = import_db(self.usb, self.dest)
        self.assertEqual(summary["notes_imported"], 1)
        with connect(self.dest) as db:
            row = db.execute("SELECT dj_notes FROM tracks").fetchone()
        self.assertEqual(row["dj_notes"], "ride_beats=49")

    def test_second_import_is_a_noop(self) -> None:
        with connect(self.source) as db:
            _add_track(db, "/music/a.mp3", bpm=94.0, dj_notes="note")
            db.execute(
                "INSERT INTO beat_phase(track_id, analyzed_at, snare_parity, "
                "confidence, bpm, first_beat_seconds) VALUES (?,?,?,?,?,?)",
                ("/music/a.mp3", time.time(), 1, 0.5, 94.0, 0.25),
            )
            db.commit()
        export_db(self.source, self.usb)
        import_db(self.usb, self.dest)
        second = import_db(self.usb, self.dest)
        self.assertEqual(second["tracks_added"], 0)
        self.assertEqual(second["fields_filled"], 0)
        self.assertEqual(second["notes_imported"], 0)
        self.assertEqual(second["beat_phase_added"], 0)

    def test_import_without_usb_db_gives_actionable_error(self) -> None:
        with self.assertRaises(FileNotFoundError) as caught:
            import_db(self.usb, self.dest)
        self.assertIn("export", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
