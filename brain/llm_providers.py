"""Model providers for Build mix plan (and any other brain step that wants one).

One text-in / text-out call, many ways to reach a model:

  CLI sign-in (your subscription, browser login owned by the vendor's CLI):
    claude-cli   `claude -p`            sign in: `claude auth login`
    codex-cli    `codex exec`           sign in: `codex login`
    grok-cli     `grok --prompt-file`   sign in: `grok login --oauth`
  API key (kept in the repo's gitignored `.env`, never in plan files):
    anthropic-api  ANTHROPIC_API_KEY   (+ optional CLAWDJ_ANTHROPIC_MODEL)
    openai-api     OPENAI_API_KEY      + CLAWDJ_OPENAI_MODEL
    xai-api        XAI_API_KEY         + CLAWDJ_XAI_MODEL
  Local:
    llama-server   LLAMA_SERVER_URL (default http://127.0.0.1:8080)

claw-dj never runs an OAuth flow or stores a token itself: the vendor CLI owns
its login, and API keys stay in `.env`. Every provider is optional — callers
must work without one (the graph optimizer builds the mix alone).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"
DEFAULT_LLAMA_SERVER_URL = "http://127.0.0.1:8080"
NONE = "none"


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    kind: str  # "cli" | "api" | "local"
    sign_in: str | None = None  # terminal command the user runs once
    env_vars: tuple[str, ...] = ()


PROVIDERS: dict[str, Provider] = {
    p.name: p
    for p in (
        Provider("claude-cli", "Claude (signed-in CLI)", "cli", sign_in="claude auth login"),
        Provider("codex-cli", "OpenAI Codex (signed-in CLI)", "cli", sign_in="codex login"),
        Provider("grok-cli", "Grok (signed-in CLI)", "cli", sign_in="grok login --oauth"),
        Provider("anthropic-api", "Claude API key", "api", env_vars=("ANTHROPIC_API_KEY",)),
        Provider("openai-api", "OpenAI API key", "api", env_vars=("OPENAI_API_KEY", "CLAWDJ_OPENAI_MODEL")),
        Provider("xai-api", "xAI Grok API key", "api", env_vars=("XAI_API_KEY", "CLAWDJ_XAI_MODEL")),
        Provider("llama-server", "llama.cpp llama-server (local)", "local", env_vars=("LLAMA_SERVER_URL",)),
    )
}


class ProviderError(RuntimeError):
    """A provider was chosen but could not answer (not signed in, no key, down)."""


def load_env(path: Path = ENV_PATH) -> None:
    """Load `.env` without overriding variables already in the environment."""
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv is a declared dependency; be defensive
        return
    load_dotenv(path, override=False)


def _run(cmd: list[str], *, stdin: str | None = None, timeout_s: float = 30.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, input=stdin, capture_output=True, text=True, timeout=timeout_s, check=False
    )


def _cli_status(name: str) -> tuple[bool, str]:
    binary = {"claude-cli": "claude", "codex-cli": "codex", "grok-cli": "grok"}[name]
    if shutil.which(binary) is None:
        return False, f"`{binary}` is not installed"
    try:
        if name == "claude-cli":
            result = _run(["claude", "auth", "status"], timeout_s=15)
            try:
                logged_in = bool(json.loads(result.stdout).get("loggedIn"))
            except (json.JSONDecodeError, AttributeError):
                logged_in = False
            return logged_in, "signed in" if logged_in else "not signed in"
        if name == "codex-cli":
            result = _run(["codex", "login", "status"], timeout_s=15)
            text = (result.stdout + result.stderr).strip()
            ok = result.returncode == 0 and "not logged in" not in text.casefold()
            return ok, text.splitlines()[0] if text else ("signed in" if ok else "not signed in")
        # grok has no non-interactive status command; its login writes auth.json.
        auth = Path.home() / ".grok" / "auth.json"
        ok = auth.exists() and auth.stat().st_size > 2
        return ok, "signed in" if ok else "not signed in"
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, f"status check failed: {error}"


def _llama_url() -> str:
    return (os.environ.get("LLAMA_SERVER_URL") or DEFAULT_LLAMA_SERVER_URL).rstrip("/")


def _status_one(provider: Provider) -> tuple[bool, str]:
    if provider.kind == "cli":
        return _cli_status(provider.name)
    if provider.kind == "api":
        missing = [var for var in provider.env_vars if not os.environ.get(var)]
        if missing:
            return False, "set " + ", ".join(missing) + " in .env"
        model = {
            "anthropic-api": os.environ.get("CLAWDJ_ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL,
            "openai-api": os.environ.get("CLAWDJ_OPENAI_MODEL"),
            "xai-api": os.environ.get("CLAWDJ_XAI_MODEL"),
        }[provider.name]
        return True, f"key set · model {model}"
    url = _llama_url()
    try:
        with urllib.request.urlopen(url + "/health", timeout=2) as response:
            ok = response.status == 200
        return ok, f"running at {url}" if ok else f"unhealthy at {url}"
    except (urllib.error.URLError, OSError):
        return False, f"not running at {url} (start llama-server or set LLAMA_SERVER_URL)"


def status_all() -> list[dict]:
    """Every provider with availability, for the GUI. Never raises."""
    load_env()
    rows = []
    for provider in PROVIDERS.values():
        available, detail = _status_one(provider)
        rows.append({**asdict(provider), "available": available, "detail": detail})
    return rows


def _ask_claude_cli(prompt: str, timeout_s: float) -> str:
    cmd = ["claude", "-p", "--output-format", "text", "--tools", "", "--no-session-persistence"]
    if os.environ.get("CLAWDJ_CLAUDE_CLI_MODEL"):
        cmd += ["--model", os.environ["CLAWDJ_CLAUDE_CLI_MODEL"]]
    result = _run(cmd, stdin=prompt, timeout_s=timeout_s)
    if result.returncode != 0:
        raise ProviderError(f"claude -p failed: {(result.stderr or result.stdout).strip()[:400]}")
    return result.stdout


def _ask_codex_cli(prompt: str, timeout_s: float) -> str:
    with tempfile.TemporaryDirectory(prefix="clawdj-codex-") as tmp:
        out = Path(tmp) / "answer.txt"
        cmd = [
            "codex", "exec", "--skip-git-repo-check", "--ephemeral",
            "-s", "read-only", "--color", "never", "-C", tmp, "-o", str(out), "-",
        ]
        if os.environ.get("CLAWDJ_CODEX_CLI_MODEL"):
            cmd[2:2] = ["-m", os.environ["CLAWDJ_CODEX_CLI_MODEL"]]
        result = _run(cmd, stdin=prompt, timeout_s=timeout_s)
        if result.returncode != 0 or not out.exists():
            raise ProviderError(f"codex exec failed: {(result.stderr or result.stdout).strip()[-400:]}")
        return out.read_text()


def _ask_grok_cli(prompt: str, timeout_s: float) -> str:
    with tempfile.TemporaryDirectory(prefix="clawdj-grok-") as tmp:
        prompt_file = Path(tmp) / "prompt.txt"
        prompt_file.write_text(prompt)
        cmd = [
            "grok", "--prompt-file", str(prompt_file), "--output-format", "plain",
            "--no-subagents", "--disable-web-search", "--max-turns", "1", "--cwd", tmp,
        ]
        if os.environ.get("CLAWDJ_GROK_CLI_MODEL"):
            cmd += ["--model", os.environ["CLAWDJ_GROK_CLI_MODEL"]]
        result = subprocess.run(
            cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=timeout_s, check=False,
        )
        if result.returncode != 0:
            raise ProviderError(f"grok failed: {(result.stderr or result.stdout).strip()[:400]}")
        return result.stdout


def _ask_anthropic_api(prompt: str, timeout_s: float) -> str:
    import anthropic

    client = anthropic.Anthropic(timeout=timeout_s)  # reads ANTHROPIC_API_KEY
    model = os.environ.get("CLAWDJ_ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    try:
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as error:
        raise ProviderError(f"Claude API {error.status_code}: {error.message}") from error
    except anthropic.APIConnectionError as error:
        raise ProviderError(f"Claude API unreachable: {error}") from error
    if response.stop_reason == "refusal":
        raise ProviderError("Claude API declined the request")
    return "".join(block.text for block in response.content if block.type == "text")


def _ask_openai_compatible(base_url: str, api_key: str | None, model: str | None, prompt: str, timeout_s: float) -> str:
    body: dict = {"messages": [{"role": "user", "content": prompt}]}
    if model:
        body["model"] = model
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), headers=headers
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise ProviderError(f"{base_url} HTTP {error.code}: {error.read()[:400]!r}") from error
    except (urllib.error.URLError, OSError) as error:
        raise ProviderError(f"{base_url} unreachable: {error}") from error
    return payload["choices"][0]["message"]["content"]


def ask(provider: str, prompt: str, *, timeout_s: float = 600.0) -> str:
    """Send one prompt, return the model's text. Raises ProviderError."""
    load_env()
    if provider not in PROVIDERS:
        raise ProviderError(f"unknown provider {provider!r}; choose from {sorted(PROVIDERS)}")
    try:
        if provider == "claude-cli":
            return _ask_claude_cli(prompt, timeout_s)
        if provider == "codex-cli":
            return _ask_codex_cli(prompt, timeout_s)
        if provider == "grok-cli":
            return _ask_grok_cli(prompt, timeout_s)
    except subprocess.TimeoutExpired as error:
        raise ProviderError(f"{provider} timed out after {timeout_s:.0f}s") from error
    except FileNotFoundError as error:
        raise ProviderError(f"{provider}: {error}") from error
    if provider == "anthropic-api":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderError("set ANTHROPIC_API_KEY in .env")
        return _ask_anthropic_api(prompt, timeout_s)
    if provider == "openai-api":
        key, model = os.environ.get("OPENAI_API_KEY"), os.environ.get("CLAWDJ_OPENAI_MODEL")
        if not key or not model:
            raise ProviderError("set OPENAI_API_KEY and CLAWDJ_OPENAI_MODEL in .env")
        return _ask_openai_compatible("https://api.openai.com/v1", key, model, prompt, timeout_s)
    if provider == "xai-api":
        key, model = os.environ.get("XAI_API_KEY"), os.environ.get("CLAWDJ_XAI_MODEL")
        if not key or not model:
            raise ProviderError("set XAI_API_KEY and CLAWDJ_XAI_MODEL in .env")
        return _ask_openai_compatible("https://api.x.ai/v1", key, model, prompt, timeout_s)
    return _ask_openai_compatible(
        _llama_url() + "/v1", None, os.environ.get("LLAMA_SERVER_MODEL"), prompt, timeout_s
    )
