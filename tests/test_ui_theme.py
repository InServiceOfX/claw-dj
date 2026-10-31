"""Classic stays the default GUI look; 16-bit is an opt-in skin (Ernest, 2026-10-31).

Story: user_stories/story__when_i_open_the_gui_i_can_pick_classic_or_a_16_bit_adventure_style.md
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest import TestCase, skipUnless

from brain.api import api_static_assets

WEB = Path(__file__).parents[1] / "brain" / "web"
HTML = (WEB / "playlist.html").read_text()
CSS = (WEB / "theme_adventure.css").read_text()


def _rule_selectors(css: str) -> list[str]:
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    selectors = []
    for match in re.finditer(r"([^{}]+)\{", body):
        head = match.group(1).strip()
        if head.startswith("@"):
            continue
        selectors.extend(part.strip() for part in head.split(","))
    return selectors


class ClassicIsDefaultTest(TestCase):
    def test_html_starts_classic(self):
        self.assertIn('<html lang="en" data-ui-theme="classic">', HTML)

    def test_switch_has_both_styles(self):
        self.assertIn('data-ui-theme-choice="classic" aria-pressed="true"', HTML)
        self.assertIn('data-ui-theme-choice="adventure" aria-pressed="false"', HTML)

    def test_theme_stylesheet_is_linked_and_served_as_css(self):
        self.assertIn('<link rel="stylesheet" href="/web/theme_adventure.css">', HTML)
        body, status, headers = api_static_assets.handle(None, {"file": "theme_adventure.css"}, "GET", None, {})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/css")
        self.assertEqual(body, CSS.encode())

    def test_every_rule_is_scoped_to_the_adventure_style(self):
        selectors = _rule_selectors(CSS)
        self.assertGreater(len(selectors), 50)
        loose = [s for s in selectors if not s.startswith('html[data-ui-theme="adventure"]')]
        self.assertEqual(loose, [])

    def test_storage_access_is_guarded(self):
        for access in re.findall(r"[^\n]*localStorage\.(?:get|set)Item\('clawdj\.uiTheme'[^\n]*", HTML):
            self.assertIn("try {", access)
            self.assertIn("catch (_)", access)

    def test_offline_and_original_art(self):
        self.assertNotRegex(CSS, r"url\(|@import|https?://")
        for name in ("nintendo", "mario", "zelda", "stardew", "concernedape"):
            self.assertNotIn(name, CSS.lower())
            self.assertNotIn(name, HTML.lower())


def _theme_scripts() -> tuple[str, str]:
    head = re.search(r"<script>\s*// Interface style:.*?</script>", HTML, re.S).group(0)
    tail = re.search(r"<script>\s*// Interface style switch:.*?</script>", HTML, re.S).group(0)
    strip = lambda block: block.removeprefix("<script>").removesuffix("</script>")
    return strip(head), strip(tail)


@skipUnless(shutil.which("node"), "node is not installed")
class ThemeSwitchScriptTest(TestCase):
    def _run(self, storage: str) -> dict:
        head, tail = _theme_scripts()
        script = """
const vm = require('node:vm');
const attrs = {};
const store = {};
const storage = %(storage)s;
const buttons = ['classic', 'adventure'].map(choice => ({
  dataset: {uiThemeChoice: choice}, pressed: null, listeners: {},
  setAttribute(name, value) { if (name === 'aria-pressed') this.pressed = value; },
  addEventListener(event, callback) { this.listeners[event] = callback; },
}));
const localStorage = storage === 'throws'
  ? {getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }}
  : {getItem(key) { return key in store ? store[key] : (storage || null); }, setItem(key, value) { store[key] = value; }};
const document = {
  documentElement: {setAttribute(name, value) { attrs[name] = value; }, getAttribute(name) { return attrs[name]; }},
  querySelectorAll() { return buttons; },
};
const context = {document, localStorage};
vm.runInNewContext(%(head)s, context);
const first = attrs['data-ui-theme'];
vm.runInNewContext(%(tail)s, context);
const pressedAtLoad = buttons.map(b => b.pressed);
buttons[1].listeners.click();
const afterClick = attrs['data-ui-theme'];
console.log(JSON.stringify({first, pressedAtLoad, afterClick, saved: store['clawdj.uiTheme'] || null,
  pressedAfter: buttons.map(b => b.pressed)}));
""" % {"storage": json.dumps(storage), "head": json.dumps(head), "tail": json.dumps(tail)}
        out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def test_first_visit_is_classic_and_click_switches(self):
        result = self._run("")
        self.assertEqual(result["first"], "classic")
        self.assertEqual(result["pressedAtLoad"], ["true", "false"])
        self.assertEqual(result["afterClick"], "adventure")
        self.assertEqual(result["saved"], "adventure")
        self.assertEqual(result["pressedAfter"], ["false", "true"])

    def test_saved_adventure_applies_before_paint(self):
        self.assertEqual(self._run("adventure")["first"], "adventure")

    def test_unknown_saved_value_stays_classic(self):
        self.assertEqual(self._run("<script>")["first"], "classic")

    def test_blocked_storage_stays_classic_and_still_switches(self):
        result = self._run("throws")
        self.assertEqual(result["first"], "classic")
        self.assertEqual(result["afterClick"], "adventure")
        self.assertIsNone(result["saved"])
