"""Folder dialog helpers used by the local collection picker."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from brain import folder_dialog


class FolderDialogTest(unittest.TestCase):
    def test_initial_dir_prefers_existing_directory(self):
        with patch.object(Path, "is_dir", return_value=True):
            resolved = folder_dialog._initial_dir("/Volumes/Elements")
        self.assertIsInstance(resolved, Path)

    def test_cancelled_osascript_becomes_cancelled_error(self):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "user canceled"

        with patch("brain.folder_dialog.subprocess.run", return_value=Result()):
            with self.assertRaises(folder_dialog.FolderDialogCancelled):
                folder_dialog._choose_macos(prompt="Pick", initial=None)

    def test_successful_osascript_returns_path(self, tmp_path_factory=None):
        class Result:
            returncode = 0
            stdout = "/Volumes/Elements/\n"
            stderr = ""

        with patch("brain.folder_dialog.subprocess.run", return_value=Result()):
            with patch.object(Path, "resolve", return_value=Path("/Volumes/Elements")):
                chosen = folder_dialog._choose_macos(prompt="Pick", initial=None)
        self.assertEqual(chosen, Path("/Volumes/Elements"))
