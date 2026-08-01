"""Focused tempfile coverage for multi-plan integration modules 16-31."""
from __future__ import annotations

import io
import json
from email.message import Message
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from brain import api_router, bunch_store, library_index, plan_cli, plan_mix_envelope, plan_notes, plan_paths, plan_revision, plan_store, transition_overrides
from brain.api import (
    api_bunch_item, api_bunches_collection, api_plan_arrange, api_plan_bunches,
    api_plan_detail, api_plan_duplicate, api_plan_journal, api_plan_notes,
    api_plan_order, api_plan_tracks, api_plan_transitions, api_plans_active,
    api_plans_collection, api_static_assets,
)
from brain.api.common import ApiError, rev, snapshot
from brain.playlist_editor import ensure_plan_workspace, make_handler


class PlanIntegrationTest(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plans = self.root / "data" / "plans"
        self.db = self.root / "data" / "library.sqlite3"
        self.patches = [
            patch.object(plan_paths, "DEFAULT_PLANS_DIR", self.plans),
            patch.object(bunch_store, "DEFAULT_INDEX", self.db),
            patch.object(plan_notes, "DEFAULT_INDEX", self.db),
            patch.object(library_index, "DEFAULT_INDEX", self.db),
        ]
        for item in self.patches:
            item.start()
        self.app = SimpleNamespace(mix_state={"running": 0}, load_plan_control_port=lambda slug: None)

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def plan(self, name="Plan A"):
        meta = plan_store.create(name)
        plan_store.set_active(meta.slug)
        return meta

    def call(self, module, slug=None, method="GET", body=None, query=None, params=None):
        params = params or ({"slug": slug} if slug else {})
        return module.handle(self.app, params, method, body or {}, query or {})[0]

    def test_router_literal_precedence_not_found_and_405_allow(self):
        api_router.clear()
        detail, active = object(), object()
        api_router.register("/api/plans/<slug>", ("GET",), detail)
        api_router.register("/api/plans/active", ("GET", "POST"), active)
        self.assertIs(api_router.route("GET", "/api/plans/active?x=1")[0], active)
        self.assertEqual(api_router.route("GET", "/api/plans/example")[1], {"slug": "example"})
        with self.assertRaises(api_router.NotFound):
            api_router.route("GET", "/missing")
        with self.assertRaises(api_router.MethodNotAllowed) as caught:
            api_router.route("DELETE", "/api/plans/active")
        self.assertEqual(caught.exception.headers["Allow"], "GET, POST")

    def test_static_collection_active_detail_duplicate_and_journal_families(self):
        web = self.root / "web"; web.mkdir(); (web / "x.js").write_text("export {}")
        with patch.object(api_static_assets, "WEB_ROOT", web):
            payload, status, headers = api_static_assets.handle(self.app, {"file": "x.js"}, "GET", {}, {})
        self.assertEqual((status, headers["Content-Type"]), (200, "text/javascript"))
        created = self.call(api_plans_collection, method="POST", body={"display_name": "2001 Mix"})
        slug = created["slug"]
        plan_store.set_active(slug)
        self.assertEqual(self.call(api_plans_active)["slug"], slug)
        listing = self.call(api_plans_collection)
        self.assertEqual(listing["plans"][0]["status"], "wip")
        base = self.call(api_plan_detail, slug)["rev"]
        renamed = self.call(api_plan_detail, slug, "POST", {"display_name": "Renamed", "base_rev": base})
        self.assertEqual(renamed["slug"], slug)
        marked = self.call(api_plan_detail, slug, "POST", {"status": "ready", "base_rev": renamed["rev"]})
        self.assertEqual(marked["status"], "ready")
        copied = self.call(api_plan_duplicate, slug, "POST", {"display_name": "Variant"})
        self.assertEqual((copied["status"], copied["origin_ref"]), ("wip", slug))
        self.assertEqual(self.call(api_plan_journal, slug)["entries"][0]["action"], "set_status")

    def test_active_switch_refuses_during_live_run_and_unknown_is_non_destructive(self):
        first, second = self.plan("First"), plan_store.create("Second")
        self.app.mix_state["running"] = 1
        with self.assertRaises(ApiError) as caught:
            self.call(api_plans_active, method="POST", body={"slug": second.slug})
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(plan_store.get_active().slug, first.slug)
        self.app.mix_state["running"] = 0
        with self.assertRaises(ApiError) as missing:
            self.call(api_plans_active, method="POST", body={"slug": "missing"})
        self.assertEqual(missing.exception.status, 404)
        self.assertEqual(plan_store.get_active().slug, first.slug)

    def test_arrange_snapshot_notes_transitions_order_and_stale_refusal(self):
        meta = self.plan()
        paths = plan_paths.resolve(meta.slug)
        paths.selection.write_text(json.dumps({"track_ids": ["a", "b", "c"]}))
        paths.playlist.write_text(json.dumps([{"track_id": x, "title": x} for x in ("a", "b", "c")]))
        arranged = self.call(api_plan_arrange, meta.slug)
        self.assertEqual([x["track_id"] for x in arranged["tracks"]], ["a", "b", "c"])
        self.assertEqual(arranged["segments"], [])
        note = self.call(api_plan_notes, meta.slug, "POST", {"track_id": "a", "note": "ride intro", "author": "llm", "base_rev": arranged["rev"]})
        transition = self.call(api_plan_transitions, meta.slug, "POST", {"from_track_id": "a", "to_track_id": "b", "note": "echo out", "author": "llm", "base_rev": note["rev"]})
        artifact = plan_mix_envelope.decorate({"version": 2, "tracks": [{"track_id": x, "title": x} for x in ("a", "b", "c")], "segments": [{"from_track_id": "a", "to_track_id": "b", "technique": "blend"}], "events": []}, meta.slug, paths)
        paths.mix_plan.write_text(json.dumps(artifact))
        merged = snapshot(meta.slug)
        self.assertEqual((merged["segments"][0]["note"], merged["segments"][0]["author"]), ("echo out", "llm"))
        moved = self.call(api_plan_order, meta.slug, "POST", {"track_ids": ["b", "c", "a"], "base_rev": transition["rev"]})
        refreshed = snapshot(meta.slug)
        self.assertEqual(refreshed["notes"][2]["layer"], "plan")
        self.assertEqual(refreshed["artifact"]["version"], 3)
        self.assertTrue(refreshed["stale"])
        self.assertIn("a->b", moved["orphaned_transitions"])
        with self.assertRaises(plan_revision.StalePlanError):
            self.call(api_plan_tracks, meta.slug, "POST", {"add": ["d"], "base_rev": arranged["rev"]})

    def test_track_removal_reconciles_activation_without_mutating_library_bunch(self):
        meta = self.plan()
        paths = plan_paths.resolve(meta.slug)
        paths.selection.write_text(json.dumps({"track_ids": ["a", "b", "c"]}))
        paths.playlist.write_text(json.dumps([{"track_id": x} for x in ("a", "b", "c")]))
        bunch = bunch_store.create("pair", ["a", "b"], True)
        activation = self.call(api_plan_bunches, meta.slug, "POST", {"bunch_id": bunch.bunch_id, "enabled": True, "base_rev": rev(meta.slug)})
        result = self.call(api_plan_tracks, meta.slug, "POST", {"remove": ["a"], "base_rev": activation["rev"]})
        self.assertEqual(result["deactivated_bunches"][0]["bunch_id"], bunch.bunch_id)
        self.assertEqual(bunch_store.get(bunch.bunch_id).track_ids, ("a", "b"))

    def test_bunch_route_families_allow_library_overlap_and_structure_conflict(self):
        meta = self.plan()
        first = self.call(api_bunches_collection, method="POST", body={"label": "AB", "track_ids": ["a", "b"], "ordered": True})
        second = self.call(api_bunches_collection, method="POST", body={"label": "BC", "track_ids": ["b", "c"], "ordered": True})
        one = self.call(api_plan_bunches, meta.slug, "POST", {"bunch_id": first["bunch_id"], "enabled": True, "base_rev": rev(meta.slug)})
        with self.assertRaises(ApiError) as caught:
            self.call(api_plan_bunches, meta.slug, "POST", {"bunch_id": second["bunch_id"], "enabled": True, "base_rev": one["rev"]})
        self.assertEqual(caught.exception.payload["conflicting_bunch_id"], first["bunch_id"])
        self.assertEqual(caught.exception.payload["shared_track_ids"], ["b"])
        updated = api_bunch_item.handle(self.app, {"bunch_id": first["bunch_id"]}, "POST", {"label": "Great pair"}, {})[0]
        self.assertEqual(updated["label"], "Great pair")

    def test_bootstrap_preserves_legacy_and_cli_show_matches_snapshot(self):
        legacy = plan_paths.legacy_paths()
        legacy.selection.parent.mkdir(parents=True, exist_ok=True)
        legacy.selection.write_text(json.dumps({"track_ids": ["a"]}))
        legacy.playlist.write_text(json.dumps([{"track_id": "a"}]))
        result = ensure_plan_workspace()
        self.assertIn(result["status"], {"migrated", "bootstrapped"})
        self.assertTrue(legacy.selection.exists())
        expected = snapshot(plan_store.get_active().slug)
        output = io.StringIO()
        with redirect_stdout(output):
            code = plan_cli.main(["show", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), expected)

    def test_editor_refresh_uses_active_paths_and_persists_selected_port(self):
        from brain.library import Track
        from brain.playlist_editor import PlaylistApp

        meta = self.plan()
        paths = plan_paths.resolve(meta.slug)
        paths.selection.write_text(json.dumps({"track_ids": ["a"]}))
        legacy_playlist = plan_paths.legacy_paths().playlist
        legacy_playlist.parent.mkdir(parents=True, exist_ok=True)
        legacy_playlist.write_text("legacy")
        tracks = [Track("a", "Song", "Artist", bpm=100.0, key="Am")]
        selection_loader = lambda *args: json.loads(args[0].read_text())["track_ids"] if args else []
        with patch("brain.playlist_editor.load_crate", return_value=tracks), patch("brain.playlist_editor.load_selection", side_effect=selection_loader), patch("brain.playlist_editor.load_exclusions", return_value=[]):
            app = PlaylistApp()
            refreshed = app.reexport_finalized()
            app.set_control_port(10017)
        self.assertEqual(refreshed["count"], 1)
        self.assertEqual(json.loads(paths.playlist.read_text())[0]["track_id"], "a")
        self.assertEqual(legacy_playlist.read_text(), "legacy")
        self.assertEqual(app.load_plan_control_port(meta.slug), 10017)

    def test_cli_parser_exposes_every_required_command_family(self):
        command_names = set(plan_cli.parser()._subparsers._group_actions[0].choices)
        self.assertEqual(command_names, {"list", "new", "switch", "show", "add", "remove", "move", "note", "transition", "mark", "bunch", "build", "log", "status"})
        parsed = plan_cli.parser().parse_args(["transition", "set", "--from", "a", "--to", "b", "--note", "cut here", "--author", "llm", "--force"])
        self.assertEqual((parsed.transition_command, parsed.note, parsed.author), ("set", "cut here", "llm"))

    def test_http_structured_404_409_and_legacy_endpoint_compatibility(self):
        meta = self.plan()
        app = SimpleNamespace(
            mix_state={"running": 0},
            metadata=lambda: {"legacy": True},
            load_plan_control_port=lambda slug: None,
        )
        handler = make_handler(app)
        status, payload, _ = self.request(handler, "GET", "/api/meta")
        self.assertEqual((status, payload), (200, {"legacy": True}))
        status, payload, headers = self.request(handler, "GET", "/api/selection")
        self.assertEqual((status, payload["error"], headers["Allow"]), (405, "method_not_allowed", "POST"))
        status, payload, _ = self.request(handler, "GET", "/api/plans/missing")
        self.assertEqual((status, payload["error"]), (404, "plan_not_found"))
        current = rev(meta.slug)
        status, payload, _ = self.request(handler, "POST", f"/api/plans/{meta.slug}/tracks", {"add": ["a"], "base_rev": "stale"})
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"], "stale_plan")
        self.assertEqual(payload["current_rev"], current)

    def request(self, handler_class, method, path, body=None):
        encoded = json.dumps(body or {}).encode()
        handler = handler_class.__new__(handler_class)
        handler.command = method
        handler.path = path
        handler.request_version = "HTTP/1.1"
        handler.requestline = f"{method} {path} HTTP/1.1"
        handler.client_address = ("127.0.0.1", 1)
        handler.server = SimpleNamespace()
        handler.close_connection = True
        handler.headers = Message()
        handler.headers["Content-Length"] = str(len(encoded))
        handler.rfile = io.BytesIO(encoded)
        handler.wfile = io.BytesIO()
        getattr(handler, f"do_{method}")()
        raw = handler.wfile.getvalue()
        head, _, payload = raw.partition(b"\r\n\r\n")
        lines = head.decode().split("\r\n")
        status = int(lines[0].split()[1])
        headers = dict(line.split(": ", 1) for line in lines[1:] if ": " in line)
        return status, json.loads(payload or b"{}"), headers


if __name__ == "__main__":
    import unittest
    unittest.main()
