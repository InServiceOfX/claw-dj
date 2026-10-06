"""Run DJ workflow regressions without opening a user's mounted library.

Usage: python tests/run_dj_workflow_checks.py
Legacy tests which use the default library get an empty temporary index; tests
with explicit fixture paths retain those paths. Local HTTP fixtures still run.
"""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import collection_registry, library_index, playlist_editor

MODULES = (
    "test_advanced_mix",
    "test_dj_brain_providers", "test_llm_providers", "test_mix_order_brief",
    "test_mix_directives", "test_mix_editor", "test_plan_frontend",
    "test_mix_optimizer", "test_dj_notes_respected", "test_listen_ride",
    "test_showcase_moves", "test_mix_plan", "test_mix_runner",
    "test_source_cutoffs", "test_stems",
)


def main():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        index = root / "library.sqlite3"
        with (
            patch.object(collection_registry, "DEFAULT_REGISTRY", root / "registry.json"),
            patch.object(library_index, "DEFAULT_INDEX", index),
            patch.object(library_index, "current_index_path", side_effect=lambda path=None: Path(path) if path is not None else index),
            patch.object(playlist_editor, "DEFAULT_CRATE_CACHE", root / "crate.json"),
            patch.object(playlist_editor, "load_crate", return_value=[]),
        ):
            with library_index.connect(index) as db:
                db.commit()
            suite = unittest.defaultTestLoader.loadTestsFromNames([f"tests.{name}" for name in MODULES])
            return unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
