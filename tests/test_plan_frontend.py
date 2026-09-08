"""Focused static and real-HTTP checks for frontend architecture modules 32-35."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, skipUnless
from unittest.mock import patch

from brain import bunch_store, library_index, plan_notes, plan_paths, plan_store
from brain.playlist_editor import make_handler


ROOT = Path(__file__).parents[1]
WEB = ROOT / "brain" / "web"
MODULES = (
    "plan_client.js",
    "plan_picker.js",
    "arrange.js",
    "transition_editor.js",
    "collection_picker.js",
)


class PlanFrontendStaticTest(TestCase):
    @skipUnless(shutil.which("node"), "node is not installed")
    def test_song_note_editor_behavior(self):
        result = subprocess.run([shutil.which("node"), str(ROOT / "tests/song_notes_frontend.cjs")],
                                cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playlist_integrates_picker_above_workflow_and_arrange_hash_tab(self):
        html = (WEB / "playlist.html").read_text()
        self.assertLess(html.index('id="plan-picker"'), html.index('class="nav"'))
        self.assertIn('id="nav-arrange" data-page="arrange">3 · Arrange', html)
        self.assertIn('id="page-arrange"', html)
        self.assertIn('<script type="module" src="/web/arrange.js"></script>', html)
        self.assertNotIn("9995", html)
        self.assertNotRegex(html, r"\bport\s*:")

    def test_module_import_graph_and_concurrency_contracts_are_present(self):
        client = (WEB / "plan_client.js").read_text()
        picker = (WEB / "plan_picker.js").read_text()
        arrange = (WEB / "arrange.js").read_text()
        editor = (WEB / "transition_editor.js").read_text()
        self.assertIn("if (!response.ok)", client)
        self.assertIn("base_rev", client)
        self.assertIn("PlanConflictError", client)
        self.assertIn("new AbortController()", client)
        self.assertIn("conflicting_bunch_id", arrange)
        self.assertIn("shared_track_ids", arrange)
        self.assertIn("library bunch", arrange.lower())
        self.assertIn("event.preventDefault()", arrange)
        self.assertIn("aria-live", arrange)
        self.assertNotIn("Element.moveBefore", arrange)
        self.assertIn("setStatus", picker)
        self.assertIn("author: 'human'", editor)
        self.assertIn("override_fields", editor)

    def test_every_referenced_web_script_exists(self):
        html = (WEB / "playlist.html").read_text()
        sources = re.findall(r'<script[^>]+src="/web/([^"/]+)"', html)
        self.assertEqual(sources, ["arrange.js"])
        for source in sources:
            self.assertTrue((WEB / source).is_file(), source)

    @skipUnless(shutil.which("node"), "node is not installed")
    def test_browser_modules_parse_with_node_check(self):
        for module in MODULES:
            result = subprocess.run(
                [shutil.which("node"), "--check", str(WEB / module)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"{module}: {result.stderr}")


class PlanFrontendHttpTest(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        root = Path(self.temp.name)
        self.plans = root / "plans"
        self.db = root / "library.sqlite3"
        self.patches = [
            patch.object(plan_paths, "DEFAULT_PLANS_DIR", self.plans),
            patch.object(bunch_store, "DEFAULT_INDEX", self.db),
            patch.object(plan_notes, "DEFAULT_INDEX", self.db),
            patch.object(library_index, "DEFAULT_INDEX", self.db),
        ]
        for item in self.patches:
            item.start()
        self.plan = plan_store.create("Notorious BIG tribute mix")
        plan_store.set_active(self.plan.slug)
        app = SimpleNamespace(mix_state={"running": 0}, load_plan_control_port=lambda slug: None)
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        except PermissionError:
            for item in reversed(self.patches):
                item.stop()
            self.temp.cleanup()
            self.skipTest("execution sandbox does not permit a loopback listener")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=2) as response:
            return response.status, response.headers, response.read()

    def test_real_editor_server_serves_html_modules_and_arrange_api(self):
        status, headers, html = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"3 \xc2\xb7 Arrange", html)
        for module in MODULES:
            status, headers, body = self.get(f"/web/{module}")
            self.assertEqual(status, 200)
            self.assertEqual(headers.get_content_type(), "text/javascript")
            self.assertTrue(body)
        status, _, body = self.get("/api/plans")
        self.assertEqual(status, 200)
        plans = json.loads(body)["plans"]
        self.assertEqual(plans[0]["display_name"], "Notorious BIG tribute mix")
        status, headers, body = self.get(f"/api/plans/{self.plan.slug}/arrange")
        self.assertEqual(status, 200)
        arranged = json.loads(body)
        self.assertEqual((arranged["slug"], arranged["tracks"], arranged["segments"]), (self.plan.slug, [], []))
        self.assertEqual(headers["ETag"], f'"{arranged["rev"]}"')


if __name__ == "__main__":
    import unittest
    unittest.main()
