"""Static browser contracts for the Curate collection picker."""
from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).parents[1]
WEB = ROOT / "brain" / "web"


class CollectionPickerFrontendTest(TestCase):
    def test_picker_is_above_existing_active_collection_ingest_controls(self):
        html = (WEB / "playlist.html").read_text()
        self.assertLess(html.index('id="collection-picker"'), html.index('id="add-root"'))
        self.assertIn('aria-live="polite"', html[html.index('id="collection-picker"'):])
        self.assertIn("import './collection_picker.js'", (WEB / "arrange.js").read_text())

    def test_new_collection_requires_estimate_and_confirmation_before_scan(self):
        source = (WEB / "collection_picker.js").read_text()
        self.assertIn("/api/collections", source)
        self.assertIn("action: 'estimate'", source)
        self.assertIn("action: 'browse'", source)
        self.assertIn("window.confirm", source)
        self.assertIn("scan: scanRequested", source)
        self.assertIn("collectionchange", source)
        self.assertIn("collection-browse-mount", source)
        self.assertIn("collection-browse-root", source)
        self.assertIn("state.form", source)
        self.assertNotIn("index_path", source)
        # Must not wire Mixxx/enrichment into this flow (help text may mention them as excluded).
        self.assertNotRegex(source.lower(), r"mixxx[_-]control")
        self.assertNotRegex(source, r"['\"]/api/mix")
        self.assertNotRegex(source, r"action:\s*['\"]enrich['\"]")
