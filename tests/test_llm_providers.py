"""Model providers: no secrets on disk by claw-dj, clear errors, CLI argv."""
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from brain import llm_providers


class ProviderTest(TestCase):
    def test_every_provider_has_a_way_to_authorize(self) -> None:
        for provider in llm_providers.PROVIDERS.values():
            self.assertTrue(provider.sign_in or provider.env_vars, provider.name)

    def test_unknown_provider_raises(self) -> None:
        with self.assertRaises(llm_providers.ProviderError):
            llm_providers.ask("nemoclaw", "hi")

    def test_api_provider_without_key_explains_env(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(llm_providers, "load_env"):
            with self.assertRaisesRegex(llm_providers.ProviderError, "OPENAI_API_KEY"):
                llm_providers.ask("openai-api", "hi")
            available, detail = llm_providers._status_one(llm_providers.PROVIDERS["xai-api"])
            self.assertFalse(available)
            self.assertIn("XAI_API_KEY", detail)

    def test_env_file_does_not_override_real_environment(self) -> None:
        with TemporaryDirectory() as directory:
            env = Path(directory) / ".env"
            env.write_text("CLAWDJ_TEST_VAR=from_file\nCLAWDJ_TEST_OTHER=file_only\n")
            with patch.dict(os.environ, {"CLAWDJ_TEST_VAR": "from_shell"}, clear=False):
                llm_providers.load_env(env)
                self.assertEqual(os.environ["CLAWDJ_TEST_VAR"], "from_shell")
                self.assertEqual(os.environ["CLAWDJ_TEST_OTHER"], "file_only")
            os.environ.pop("CLAWDJ_TEST_OTHER", None)

    def test_env_file_is_gitignored(self) -> None:
        result = subprocess.run(
            ["git", "check-ignore", "-q", ".env"], cwd=llm_providers.REPO_ROOT, check=False
        )
        self.assertEqual(result.returncode, 0)

    def test_claude_cli_runs_without_tools_and_prompt_on_stdin(self) -> None:
        seen = {}

        def fake_run(cmd, *, stdin=None, timeout_s=30.0):
            seen["cmd"], seen["stdin"] = cmd, stdin
            return subprocess.CompletedProcess(cmd, 0, stdout='{"order": []}', stderr="")

        with patch.object(llm_providers, "_run", side_effect=fake_run), patch.object(llm_providers, "load_env"):
            self.assertEqual(llm_providers.ask("claude-cli", "PROMPT"), '{"order": []}')
        self.assertEqual(seen["cmd"][:2], ["claude", "-p"])
        self.assertIn("--tools", seen["cmd"])
        self.assertEqual(seen["cmd"][seen["cmd"].index("--tools") + 1], "")
        self.assertEqual(seen["stdin"], "PROMPT")

    def test_cli_failure_becomes_provider_error(self) -> None:
        def fake_run(cmd, *, stdin=None, timeout_s=30.0):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Not logged in")

        with patch.object(llm_providers, "_run", side_effect=fake_run), patch.object(llm_providers, "load_env"):
            with self.assertRaisesRegex(llm_providers.ProviderError, "Not logged in"):
                llm_providers.ask("claude-cli", "hi")

    def test_llama_server_down_is_reported_not_raised(self) -> None:
        with patch.dict(os.environ, {"LLAMA_SERVER_URL": "http://127.0.0.1:9"}):
            available, detail = llm_providers._status_one(llm_providers.PROVIDERS["llama-server"])
        self.assertFalse(available)
        self.assertIn("not running", detail)
