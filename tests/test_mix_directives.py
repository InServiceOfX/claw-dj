import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.mix_directives import (
    apply_directives,
    build_prompt,
    parse_directives,
    print_diff,
)

TRACKS = [
    {"track_id": "/music/a.mp3", "artist": "Dr. Dre", "title": "Nuthin' But A G Thang",
     "bpm": 94.0, "key": "F#m", "dj_notes": ""},
    {"track_id": "/music/b.mp3", "artist": "Snoop Dogg", "title": "Gin and Juice",
     "bpm": 95.0, "key": "Gm", "dj_notes": "cue_seconds=4"},
    {"track_id": "/music/c.mp3", "artist": "Warren G", "title": "Regulate",
     "bpm": 92.0, "key": "Dm", "dj_notes": ""},
]


class ParseDirectivesTest(TestCase):
    def test_valid_notes_only(self) -> None:
        reply = json.dumps({"notes": {"t001": "ride_beats=64"}, "reorder": None})
        notes, reorder = parse_directives(reply, TRACKS)
        self.assertEqual(notes, {"/music/b.mp3": "ride_beats=64"})
        self.assertIsNone(reorder)

    def test_valid_reorder_permutation(self) -> None:
        reply = json.dumps({"notes": {}, "reorder": ["t002", "t000", "t001"]})
        notes, reorder = parse_directives(reply, TRACKS)
        self.assertEqual(notes, {})
        self.assertEqual(reorder, ["/music/c.mp3", "/music/a.mp3", "/music/b.mp3"])

    def test_unknown_id_rejected(self) -> None:
        reply = json.dumps({"notes": {"t999": "full_track"}, "reorder": None})
        with self.assertRaises(ValueError):
            parse_directives(reply, TRACKS)

    def test_non_permutation_reorder_rejected(self) -> None:
        # drops t002, duplicates t000 — not a permutation
        reply = json.dumps({"notes": {}, "reorder": ["t000", "t000", "t001"]})
        with self.assertRaises(ValueError):
            parse_directives(reply, TRACKS)

    def test_short_reorder_rejected(self) -> None:
        reply = json.dumps({"notes": {}, "reorder": ["t000", "t001"]})
        with self.assertRaises(ValueError):
            parse_directives(reply, TRACKS)

    def test_empty_note_value_rejected(self) -> None:
        reply = json.dumps({"notes": {"t000": ""}, "reorder": None})
        with self.assertRaises(ValueError):
            parse_directives(reply, TRACKS)

    def test_extracts_json_wrapped_in_prose_and_fences(self) -> None:
        reply = (
            "Sure, here's the plan:\n```json\n"
            + json.dumps({"notes": {"t000": "full_track"}, "reorder": None})
            + "\n```\nLet me know if you want changes."
        )
        notes, reorder = parse_directives(reply, TRACKS)
        self.assertEqual(notes, {"/music/a.mp3": "full_track"})

    def test_no_json_object_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_directives("I refuse to answer in JSON.", TRACKS)


class BuildPromptTest(TestCase):
    def test_prompt_includes_all_tracks_and_brief(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "library.sqlite3"
            sqlite3.connect(db_path).execute(
                "CREATE TABLE lyric_timelines (track_id TEXT PRIMARY KEY, lrc TEXT)"
            )
            prompt = build_prompt(TRACKS, "land on Regulate's first verse", db_path)
            for t in TRACKS:
                self.assertIn(t["artist"], prompt)
                self.assertIn(t["title"], prompt)
            self.assertIn("land on Regulate's first verse", prompt)
            self.assertIn("entry_style=verse_landing", prompt)

    def test_prompt_attaches_lyrics_for_mentioned_track(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "library.sqlite3"
            db = sqlite3.connect(db_path)
            db.execute("CREATE TABLE lyric_timelines (track_id TEXT PRIMARY KEY, lrc TEXT)")
            db.execute(
                "INSERT INTO lyric_timelines VALUES (?, ?)",
                ("/music/c.mp3", "[00:12.00]Regulators, mount up"),
            )
            db.commit()
            prompt = build_prompt(TRACKS, "Warren G Regulate should land on the verse", db_path)
            self.assertIn("Regulators, mount up", prompt)


class ApplyDirectivesTest(TestCase):
    def test_apply_writes_sqlite_and_playlist_json(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "library.sqlite3"
            playlist_path = tmp_path / "playlist.json"
            selection_path = tmp_path / "playlist_selection.json"
            playlist_path.write_text(json.dumps(TRACKS))

            from brain.library_index import connect

            with connect(db_path) as db:
                for t in TRACKS:
                    db.execute(
                        "INSERT INTO tracks (track_id, root, size_bytes, mtime_ns, title, "
                        "artist, dj_notes, first_seen_at, last_seen_at) "
                        "VALUES (?, '/music', 0, 0, ?, ?, ?, 0, 0)",
                        (t["track_id"], t["title"], t["artist"], t["dj_notes"]),
                    )
                db.commit()

            notes = {"/music/c.mp3": "entry_style=verse_landing; landing_seconds=12.0"}
            reorder = ["/music/c.mp3", "/music/a.mp3", "/music/b.mp3"]
            apply_directives(
                TRACKS, notes, reorder,
                playlist_path=playlist_path, selection_path=selection_path, db_path=db_path,
            )

            written = json.loads(playlist_path.read_text())
            self.assertEqual([t["track_id"] for t in written], reorder)
            self.assertEqual(written[0]["dj_notes"], notes["/music/c.mp3"])
            # untouched tracks keep their original dj_notes
            self.assertEqual(written[1]["dj_notes"], "")

            selection = json.loads(selection_path.read_text())
            self.assertEqual(selection["track_ids"], reorder)

            with sqlite3.connect(db_path) as db:
                row = db.execute(
                    "SELECT dj_notes FROM tracks WHERE track_id = ?", ("/music/c.mp3",)
                ).fetchone()
            self.assertEqual(row[0], notes["/music/c.mp3"])

    def test_apply_without_reorder_preserves_order(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "library.sqlite3"
            playlist_path = tmp_path / "playlist.json"
            playlist_path.write_text(json.dumps(TRACKS))

            from brain.library_index import connect

            with connect(db_path) as db:
                for t in TRACKS:
                    db.execute(
                        "INSERT INTO tracks (track_id, root, size_bytes, mtime_ns, title, "
                        "artist, dj_notes, first_seen_at, last_seen_at) "
                        "VALUES (?, '/music', 0, 0, ?, ?, ?, 0, 0)",
                        (t["track_id"], t["title"], t["artist"], t["dj_notes"]),
                    )
                db.commit()

            apply_directives(
                TRACKS, {"/music/a.mp3": "full_track"}, None,
                playlist_path=playlist_path, db_path=db_path,
            )
            written = json.loads(playlist_path.read_text())
            self.assertEqual([t["track_id"] for t in written], [t["track_id"] for t in TRACKS])
            self.assertEqual(written[0]["dj_notes"], "full_track")


class PrintDiffTest(TestCase):
    def test_print_diff_does_not_raise(self) -> None:
        notes = {"/music/a.mp3": "full_track"}
        reorder = ["/music/b.mp3", "/music/a.mp3", "/music/c.mp3"]
        print_diff(TRACKS, notes, reorder)
        print_diff(TRACKS, {}, None)
