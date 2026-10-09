"""Model providers: no secrets on disk by claw-dj, clear errors, CLI argv."""
import os
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from brain import llm_providers


class ProviderTest(TestCase):
    def test_h_key_alone_enables_the_documented_free_tier_model(self):
        with patch.dict(os.environ, {"HAI_API_KEY": "synthetic-test-key"}, clear=True):
            available, detail = llm_providers._status_one(llm_providers.PROVIDERS["hcompany-api"])
        self.assertTrue(available)
        self.assertIn("holo3-1-35b-a3b", detail)
        self.assertNotIn("synthetic-test-key", detail)

    def test_h_api_uses_bearer_auth_and_text_only_chat_with_model_override(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"choices": [{"message": {"content": '["n0000"]', "reasoning": "ignored"}}]}).encode()
        for model in (None, "holo4-35b-a3b"):
            env = {"HAI_API_KEY": "synthetic-test-key"}
            if model:
                env["CLAWDJ_HCOMPANY_MODEL"] = model
            with patch.dict(os.environ, env, clear=True), patch.object(llm_providers, "load_env"), patch("urllib.request.urlopen", return_value=response) as urlopen:
                self.assertEqual(llm_providers.ask("hcompany-api", "PROMPT", timeout_s=12), '["n0000"]')
                request = urlopen.call_args.args[0]
                self.assertEqual(request.full_url, "https://api.hcompany.ai/v1/chat/completions")
                self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-test-key")
                body = json.loads(request.data)
                self.assertEqual(body["model"], model or "holo3-1-35b-a3b")
                self.assertEqual(body["messages"], [{"role": "user", "content": "PROMPT"}])
                self.assertFalse(body["chat_template_kwargs"]["enable_thinking"])
                self.assertNotIn("tools", body)

    def test_refresh_updates_and_removes_file_keys_but_preserves_shell_values(self):
        with TemporaryDirectory() as tmp, patch.dict(os.environ, {"CLAWDJ_HCOMPANY_MODEL": "shell-model"}, clear=True), patch.dict(llm_providers._ENV_LOADED, {}, clear=True):
            env = Path(tmp) / ".env"
            env.write_text("HAI_API_KEY=first\nCLAWDJ_HCOMPANY_MODEL=file-model\n")
            llm_providers.load_env(env)
            self.assertEqual(os.environ["HAI_API_KEY"], "first")
            self.assertEqual(os.environ["CLAWDJ_HCOMPANY_MODEL"], "shell-model")
            env.write_text("HAI_API_KEY=second\n")
            llm_providers.load_env(env)
            self.assertEqual(os.environ["HAI_API_KEY"], "second")
            env.write_text("")
            llm_providers.load_env(env)
            self.assertNotIn("HAI_API_KEY", os.environ)
            self.assertEqual(os.environ["CLAWDJ_HCOMPANY_MODEL"], "shell-model")

    def test_malformed_empty_and_truncated_api_answers_fail_clearly(self):
        for payload in ({}, {"choices": []}, {"choices": [{"message": {"content": None}}]}, {"choices": [{"message": {"content": "<think>still thinking"}}]}, {"choices": [{"message": {"content": "[]"}, "finish_reason": "length"}]}):
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
            with self.subTest(payload=payload), patch("urllib.request.urlopen", return_value=response), self.assertRaises(llm_providers.ProviderError):
                llm_providers._ask_openai_compatible("http://local/v1", None, None, "PROMPT", 1)

    def test_local_inline_reasoning_is_not_treated_as_candidate_ids(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"choices": [{"message": {"content": '<think>Consider ["n0001"]</think>["n0000"]'}}]}).encode()
        with patch("urllib.request.urlopen", return_value=response):
            self.assertEqual(llm_providers._ask_openai_compatible("http://local/v1", None, None, "PROMPT", 1), '["n0000"]')

    def test_status_failure_is_isolated(self):
        def status(provider):
            if provider.name == "hcompany-api":
                raise RuntimeError("do not expose error contents")
            return True, "ready"
        with patch.object(llm_providers, "load_env"), patch.object(llm_providers, "_status_one", side_effect=status):
            rows = llm_providers.status_all()
        self.assertEqual(sum(row["available"] for row in rows), len(rows)-1)
        self.assertNotIn("do not expose", str(rows))

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
        # Build review is one bounded answer: no tools, so no turns spent exploring.
        self.assertIn("--tools", seen["cmd"])
        self.assertEqual(seen["cmd"][seen["cmd"].index("--tools") + 1], "")
        self.assertNotIn("--permission-mode", seen["cmd"])
        self.assertEqual(seen["stdin"], "PROMPT")

    def test_codex_exec_is_not_passed_a_turn_flag_it_rejects(self) -> None:
        seen = {}

        def fake_run(cmd, *, stdin=None, timeout_s=30.0):
            seen["cmd"] = cmd
            out = next(part for part in cmd if str(part).endswith("answer.txt"))
            Path(out).write_text('{"order": []}')
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch.object(llm_providers, "_run", side_effect=fake_run), patch.object(llm_providers, "load_env"):
            self.assertEqual(llm_providers.ask("codex-cli", "PROMPT"), '{"order": []}')
        self.assertIn("exec", seen["cmd"])
        self.assertNotIn("--max-turns", seen["cmd"])

    def test_grok_cli_answers_once_without_tools(self) -> None:
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout='{"order": []}', stderr="")

        with patch.object(llm_providers.subprocess, "run", side_effect=fake_run), patch.object(llm_providers, "load_env"):
            self.assertEqual(llm_providers.ask("grok-cli", "PROMPT"), '{"order": []}')
        self.assertEqual(seen["cmd"][seen["cmd"].index("--max-turns") + 1], "1")
        self.assertIn("--disable-web-search", seen["cmd"])
        self.assertNotIn("--always-approve", seen["cmd"])
        self.assertIn("--no-subagents", seen["cmd"])
        self.assertNotEqual(seen["cmd"][seen["cmd"].index("--cwd") + 1], str(llm_providers.REPO_ROOT))
        self.assertIn("--prompt-file", seen["cmd"])

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
