"""NemoClaw sandbox name resolution for the DJ brain engine."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from brain import pick_candidates


class NemoclawSandboxResolveTests(unittest.TestCase):
    def test_env_override_wins(self) -> None:
        with patch.dict("os.environ", {"CLAWDJ_NEMOCLAW_SANDBOX": "my-sandbox"}):
            self.assertEqual(pick_candidates._nemoclaw_sandbox_name(), "my-sandbox")

    def test_list_default_starred_sandbox(self) -> None:
        listing = """
  Sandboxes:
    nemoclaw-hermes *
      agent: hermes
"""

        class Result:
            stdout = listing
            stderr = ""

        with patch.dict("os.environ", {}, clear=False):
            with patch.dict("os.environ"):
                import os

                os.environ.pop("CLAWDJ_NEMOCLAW_SANDBOX", None)
                with patch("brain.pick_candidates.subprocess.run", return_value=Result()):
                    self.assertEqual(
                        pick_candidates._nemoclaw_sandbox_name(), "nemoclaw-hermes"
                    )

    def test_gateway_token_failure_is_actionable(self) -> None:
        class Result:
            returncode = 1
            stdout = ""
            stderr = "Sandbox 'hermes' does not exist."

        with patch("brain.pick_candidates.subprocess.run", return_value=Result()):
            with self.assertRaises(RuntimeError) as caught:
                pick_candidates._nemoclaw_gateway_token("hermes")
        message = str(caught.exception)
        self.assertIn("Docker Desktop", message)
        self.assertIn("h-agent", message)
