"""Focused contracts for active, per-volume music collections."""
from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


def _record(collection_id: str, mount: Path, index: Path, name: str | None = None) -> dict:
    return {
        "collection_id": collection_id,
        "display_name": name or collection_id,
        "mount_base": str(mount),
        "data_dir": str(index.parent),
        "index_path": str(index),
        "volume_label": mount.name,
        "last_used_at": None,
    }


def _fake_audio_record(path: Path, **_kwargs):
    return "ok", {
        "track_id": str(path),
        "title": path.stem,
        "artist": "Artist",
        "album": None,
        "genre": None,
        "duration_seconds": None,
        "size_bytes": path.stat().st_size,
    }


def _insert_track(index: Path, track_id: str, title: str, note: str = "") -> None:
    from brain.library_index import connect

    with closing(connect(index)) as db:
        now = time.time()
        db.execute(
            """INSERT INTO tracks
               (track_id,root,size_bytes,mtime_ns,title,artist,album,genre,
                duration_seconds,bpm,key,energy,dj_notes,first_seen_at,
                last_seen_at,available,tag_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,'ok')""",
            (
                track_id,
                str(Path(track_id).parent),
                1,
                1,
                title,
                "Artist",
                None,
                None,
                None,
                None,
                None,
                None,
                note,
                now,
                now,
            ),
        )
        db.commit()


class CollectionRegistryTest(unittest.TestCase):
    def test_missing_registry_preserves_legacy_fallback_without_creating_state(self):
        from brain import collection_registry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            fallback = root / "legacy.sqlite3"
            self.assertEqual(
                collection_registry.active_index_path(
                    registry_path=registry, fallback=fallback
                ),
                fallback,
            )
            self.assertFalse(registry.exists())

    def test_register_activate_and_restart_preserve_every_collection(self):
        from brain import collection_registry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            first_mount = root / "First"
            second_mount = root / "Second"
            first_mount.mkdir()
            second_mount.mkdir()
            first_index = first_mount / "clawdj" / "library.sqlite3"
            second_index = second_mount / "clawdj" / "library.sqlite3"
            first_index.parent.mkdir()
            second_index.parent.mkdir()
            first_index.touch()
            second_index.touch()

            collection_registry.register(
                _record("first", first_mount, first_index), registry_path=registry
            )
            collection_registry.register(
                _record("second", second_mount, second_index), registry_path=registry
            )
            collection_registry.activate("first", registry_path=registry)

            self.assertEqual(
                [item["collection_id"] for item in collection_registry.list_collections(registry_path=registry)],
                ["first", "second"],
            )
            self.assertEqual(
                collection_registry.active_collection(registry_path=registry)["collection_id"],
                "first",
            )
            # Reading the file again models a process restart: the last-used
            # pointer remains first and no volume probing selects another.
            self.assertEqual(json.loads(registry.read_text())["active_collection_id"], "first")

    def test_unavailable_active_collection_never_falls_back_or_changes_pointer(self):
        from brain import collection_registry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            mount = root / "Mounted"
            mount.mkdir()
            index = mount / "library.sqlite3"
            index.touch()
            collection_registry.register(
                _record("chosen", mount, index), registry_path=registry
            )
            index.unlink()

            with self.assertRaises(collection_registry.CollectionUnavailable):
                collection_registry.active_index_path(
                    registry_path=registry, fallback=root / "legacy.sqlite3"
                )
            self.assertEqual(json.loads(registry.read_text())["active_collection_id"], "chosen")

    def test_malformed_and_conflicting_identities_are_rejected(self):
        from brain import collection_registry

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            registry.write_text('{"version": 1, "collections": "wrong"}')
            with self.assertRaises(collection_registry.RegistryFormatError):
                collection_registry.list_collections(registry_path=registry)

            registry.unlink()
            mount = root / "Drive"
            mount.mkdir()
            first = mount / "one.sqlite3"
            second = mount / "two.sqlite3"
            first.touch()
            second.touch()
            collection_registry.register(
                _record("same", mount, first), registry_path=registry
            )
            with self.assertRaises(ValueError):
                collection_registry.register(
                    _record("same", mount, second), registry_path=registry
                )


class CollectionLifecycleTest(unittest.TestCase):
    def test_create_records_legacy_and_preserves_reused_database_and_marker(self):
        from brain import collection, collection_registry
        from brain.library_index import configured_roots, export_records

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            legacy = root / "local" / "library.sqlite3"
            _insert_track(legacy, "/legacy/song.mp3", "Legacy", "human note")
            mount = root / "NewDrive"
            music = mount / "Music"
            music.mkdir(parents=True)

            with patch.object(collection, "DEFAULT_INDEX", legacy), patch(
                "brain.scan_library.incremental_scan"
            ) as scanner:
                created = collection.create_collection(
                    mount,
                    roots=[music],
                    display_name="New crate",
                    registry_path=registry,
                )
            scanner.assert_not_called()

            self.assertEqual(created["display_name"], "New crate")
            self.assertEqual(configured_roots(Path(created["index_path"])), [str(music.resolve())])
            known = collection_registry.list_collections(registry_path=registry)
            self.assertEqual(len(known), 2)
            self.assertTrue(any(item["index_path"] == str(legacy.resolve()) for item in known))
            self.assertEqual(export_records(legacy)[0]["dj_notes"], "human note")

            marker = Path(created["data_dir"]) / collection.MARKER_NAME
            marker_before = marker.read_bytes()
            _insert_track(Path(created["index_path"]), str(music / "kept.mp3"), "Kept", "keep me")
            with patch.object(collection, "DEFAULT_INDEX", legacy):
                reused = collection.create_collection(
                    mount, roots=[music], registry_path=registry
                )
            self.assertEqual(reused["collection_id"], created["collection_id"])
            self.assertEqual(marker.read_bytes(), marker_before)
            self.assertEqual(export_records(Path(reused["index_path"]))[0]["dj_notes"], "keep me")

    def test_estimate_counts_paths_without_reading_tags_or_scanning(self):
        from brain.collection import estimate_scan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.mp3").write_bytes(b"x")
            (root / "two.flac").write_bytes(b"x")
            (root / "notes.txt").write_text("not audio")
            with patch("brain.scan_library._read_record") as tag_reader:
                estimate = estimate_scan([root])
            self.assertEqual(estimate["audio_file_count"], 2)
            self.assertGreaterEqual(estimate["estimated_seconds"], 0)
            tag_reader.assert_not_called()


class ActiveIndexAndScanIsolationTest(unittest.TestCase):
    def test_omitted_path_switches_live_while_explicit_path_always_wins(self):
        from brain import collection, collection_registry, library_index

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            legacy = root / "legacy.sqlite3"
            first_mount = root / "First"
            second_mount = root / "Second"
            first_mount.mkdir()
            second_mount.mkdir()
            first_index = first_mount / "library.sqlite3"
            second_index = second_mount / "library.sqlite3"
            _insert_track(first_index, "/first.mp3", "First")
            _insert_track(second_index, "/second.mp3", "Second")
            _insert_track(legacy, "/legacy.mp3", "Legacy")
            collection_registry.register(
                _record("first", first_mount, first_index), registry_path=registry
            )
            collection_registry.register(
                _record("second", second_mount, second_index), registry_path=registry
            )

            with patch.object(collection_registry, "DEFAULT_REGISTRY", registry), patch.object(
                library_index, "DEFAULT_INDEX", legacy
            ):
                self.assertEqual(library_index.export_records()[0]["title"], "Second")
                collection_registry.activate("first", registry_path=registry)
                self.assertEqual(library_index.export_records()[0]["title"], "First")
                self.assertEqual(library_index.export_records(legacy)[0]["title"], "Legacy")

    def test_scan_resolves_one_active_database_for_the_entire_run(self):
        from brain import collection_registry, library_index
        from brain.scan_library import incremental_scan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            first_mount = root / "First"
            second_mount = root / "Second"
            music = root / "Music"
            first_mount.mkdir()
            second_mount.mkdir()
            music.mkdir()
            song = music / "song.mp3"
            song.write_bytes(b"x")
            first_index = first_mount / "library.sqlite3"
            second_index = second_mount / "library.sqlite3"
            with closing(library_index.connect(first_index)):
                pass
            with closing(library_index.connect(second_index)):
                pass
            collection_registry.register(
                _record("first", first_mount, first_index), registry_path=registry
            )
            collection_registry.register(
                _record("second", second_mount, second_index), registry_path=registry, activate=False
            )

            def switch_during_tag_read(path: Path, **kwargs):
                collection_registry.activate("second", registry_path=registry)
                return _fake_audio_record(path, **kwargs)

            with patch.object(collection_registry, "DEFAULT_REGISTRY", registry), patch.object(
                library_index, "DEFAULT_INDEX", root / "legacy.sqlite3"
            ), patch("brain.scan_library._read_record", side_effect=switch_during_tag_read):
                incremental_scan([music], min_age_seconds=0)

            self.assertEqual(len(library_index.export_records(first_index)), 1)
            self.assertEqual(library_index.export_records(second_index), [])
            self.assertEqual(
                collection_registry.active_collection(registry_path=registry)["collection_id"],
                "second",
            )


class CollectionsApiAndPlaylistAppTest(unittest.TestCase):
    def _app(self, registry: Path, legacy: Path):
        return SimpleNamespace(
            registry_path=registry,
            legacy_index=legacy,
            scan_thread=None,
            enrich_thread=None,
            mix_thread=None,
            mix_run_thread=None,
            mix_state={"building": 0, "enriching": 0, "running": 0},
            brain_state={"running": 0},
            directives_state={"running": 0},
            reload=Mock(),
            start_scan=Mock(return_value={"running": 1}),
        )

    def test_api_estimate_register_get_and_activate_busy_contracts(self):
        from brain.api import api_collections
        from brain.api.common import ApiError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            legacy = root / "legacy.sqlite3"
            mount = root / "Drive"
            music = mount / "Music"
            music.mkdir(parents=True)
            (music / "song.mp3").write_bytes(b"x")
            app = self._app(registry, legacy)

            estimate, status, _ = api_collections.handle(
                app, {}, "POST", {"action": "estimate", "mount_base": str(mount), "roots": [str(music)]}, {}, {}
            )
            self.assertEqual((status, estimate["audio_file_count"]), (200, 1))

            registered, status, _ = api_collections.handle(
                app,
                {},
                "POST",
                {
                    "action": "register",
                    "mount_base": str(mount),
                    "roots": [str(music)],
                    "display_name": "Drive crate",
                    "scan": False,
                },
                {},
                {},
            )
            self.assertEqual(status, 201)
            app.reload.assert_called_once()
            app.start_scan.assert_not_called()

            listed, status, _ = api_collections.handle(app, {}, "GET", {}, {}, {})
            self.assertEqual(status, 200)
            self.assertEqual(listed["active_collection_id"], registered["collection_id"])
            self.assertTrue(listed["collections"][0]["mounted"])

            app.mix_state["building"] = 1
            with self.assertRaises(ApiError) as caught:
                api_collections.handle(
                    app,
                    {},
                    "POST",
                    {"action": "activate", "collection_id": registered["collection_id"]},
                    {},
                    {},
                )
            self.assertEqual(caught.exception.status, 409)

            with self.assertRaises(ApiError) as caught:
                api_collections.handle(
                    app,
                    {},
                    "POST",
                    {"action": "register", "mount_base": str(mount), "index_path": "/tmp/client.sqlite3"},
                    {},
                    {},
                )
            self.assertEqual(caught.exception.status, 400)

            app.mix_state["building"] = 0
            second_mount = root / "SecondDrive"
            second_music = second_mount / "Music"
            second_music.mkdir(parents=True)
            scanned, status, _ = api_collections.handle(
                app,
                {},
                "POST",
                {
                    "action": "register",
                    "mount_base": str(second_mount),
                    "roots": [str(second_music)],
                    "scan": True,
                },
                {},
                {},
            )
            self.assertEqual((status, scanned["scan_started"]), (201, True))
            app.start_scan.assert_called_once_with()

    def test_real_loopback_get_uses_registered_collection_route(self):
        from brain import collection_registry
        from brain.playlist_editor import make_handler

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            mount = root / "Drive"
            mount.mkdir()
            index = mount / "library.sqlite3"
            _insert_track(index, "/song.mp3", "Song")
            collection_registry.register(
                _record("drive", mount, index), registry_path=registry
            )
            app = self._app(registry, root / "legacy.sqlite3")
            try:
                server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
            except PermissionError:
                self.skipTest("execution sandbox does not permit a loopback listener")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address
                with urllib.request.urlopen(f"http://{host}:{port}/api/collections", timeout=2) as response:
                    payload = json.loads(response.read())
                self.assertEqual(payload["active_collection_id"], "drive")
                self.assertEqual(payload["collections"][0]["display_name"], "drive")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_playlist_app_reload_follows_active_database_without_startup_prompt(self):
        from brain import collection_registry, library_index
        from brain.playlist_editor import PlaylistApp

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            first_mount = root / "First"
            second_mount = root / "Second"
            first_mount.mkdir()
            second_mount.mkdir()
            first_index = first_mount / "library.sqlite3"
            second_index = second_mount / "library.sqlite3"
            _insert_track(first_index, "/first.mp3", "First")
            _insert_track(second_index, "/second.mp3", "Second")
            collection_registry.register(
                _record("first", first_mount, first_index), registry_path=registry
            )
            collection_registry.register(
                _record("second", second_mount, second_index), registry_path=registry
            )

            with patch.object(collection_registry, "DEFAULT_REGISTRY", registry), patch.object(
                library_index, "DEFAULT_INDEX", root / "legacy.sqlite3"
            ), patch.object(PlaylistApp, "_scoped_paths", return_value=None), patch(
                "brain.playlist_editor.load_selection", return_value=[]
            ), patch("brain.playlist_editor.load_exclusions", return_value=[]), patch(
                "brain.playlist_editor.DEFAULT_CRATE_CACHE", root / "crate.json"
            ), patch(
                "builtins.input", side_effect=AssertionError("startup must not prompt")
            ):
                app = PlaylistApp()
                self.assertEqual([track.title for track in app.tracks], ["Second"])
                collection_registry.activate("first", registry_path=registry)
                app.reload()
                self.assertEqual([track.title for track in app.tracks], ["First"])

    def test_unavailable_last_used_collection_keeps_selector_server_reachable(self):
        from brain import collection, collection_registry, library_index
        from brain.api import api_collections
        from brain.playlist_editor import PlaylistApp

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "collections.json"
            missing_mount = root / "Missing"
            available_mount = root / "Available"
            missing_mount.mkdir()
            available_mount.mkdir()
            missing_index = missing_mount / "library.sqlite3"
            available_index = available_mount / "library.sqlite3"
            _insert_track(missing_index, "/missing.mp3", "Missing")
            _insert_track(available_index, "/available.mp3", "Available")
            collection_registry.register(
                _record("missing", missing_mount, missing_index), registry_path=registry
            )
            collection_registry.register(
                _record("available", available_mount, available_index),
                registry_path=registry,
                activate=False,
            )
            missing_index.unlink()

            with patch.object(collection_registry, "DEFAULT_REGISTRY", registry), patch.object(
                library_index, "DEFAULT_INDEX", root / "legacy.sqlite3"
            ), patch.object(
                collection, "DEFAULT_INDEX", root / "legacy.sqlite3"
            ), patch.object(PlaylistApp, "_scoped_paths", return_value=None), patch(
                "brain.playlist_editor.load_selection", return_value=[]
            ), patch("brain.playlist_editor.load_exclusions", return_value=[]), patch(
                "brain.playlist_editor.DEFAULT_CRATE_CACHE", root / "crate.json"
            ), patch("builtins.input", side_effect=AssertionError("startup must not prompt")):
                app = PlaylistApp()
                self.assertEqual(app.tracks, [])
                self.assertIn("unavailable", app.ingest_status()["error"])
                listed, status, _ = api_collections.handle(app, {}, "GET", {}, {}, {})
                self.assertEqual(status, 200)
                self.assertEqual(listed["active_collection_id"], "missing")
                activated, status, _ = api_collections.handle(
                    app,
                    {},
                    "POST",
                    {"action": "activate", "collection_id": "available"},
                    {},
                    {},
                )
                self.assertEqual((status, activated["collection_id"]), (200, "available"))
                self.assertEqual([track.title for track in app.tracks], ["Available"])


if __name__ == "__main__":
    unittest.main()
