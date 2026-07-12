"""The H Company computer-use agent, driven through the hai-agents SDK
(https://pypi.org/project/hai-agents/) in local-desktop mode. Drives Mixxx's
actual GUI for anything that isn't beat-critical (browse library, load a
track to a deck, react to a request) and emits shared.commands.Command
objects for Hands to execute for anything that is.

Needs `hai login` run once on this machine first — separate from
holo-desktop-cli's `holo login`; the two commands write different API keys
to different files (~/.config/hai/.env vs ~/.holo/.env), one per H Company
product (Agent Platform vs Models API).

Originally built on holo-desktop-cli, but its closed-source
hai-agent-runtime binary has no published Linux build yet. This uses the
hai-agents[desktop] SDK instead: a pure-Python local bridge
(hai_agents_local, via pyautogui/python-xlib) that drives the screen
in-process, no daemon binary required. Confirmed working on Linux X11
(GNOME) after installing gnome-screenshot, which pyautogui's Linux
screenshot backend needs.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values
from hai_agents import AsyncClient
from hai_agents.core.api_error import ApiError
from hai_agents_local import stop_bridges

from brain.library import Energy, Track, find_next
from shared.commands import Command, LoadTrack

AGENT_NAME = "claw-dj-brain"
DEFAULT_MAX_STEPS = 20
DEFAULT_MAX_TIME_S = 180.0

# Same key/file `hai login` writes to (~/.config/hai/.env). Read directly
# instead of the hai-agents CLI's own credential helper, which lives in an
# internal module (hai_agents_common) not exposed by the `desktop` extra.
# On macOS, `holo login` may be the only completed login; it writes
# ~/.holo/.env (Models API). Prefer Agent Platform key when both exist.
_HAI_ENV_PATH = (
    Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    / "hai"
    / ".env"
)
_HOLO_ENV_PATH = Path.home() / ".holo" / ".env"


def _resolve_api_key() -> str | None:
    if key := os.environ.get("HAI_API_KEY"):
        return key
    for path in (_HAI_ENV_PATH, _HOLO_ENV_PATH):
        if path.exists():
            if key := dotenv_values(path).get("HAI_API_KEY"):
                return key
    return None


class Brain:
    def __init__(self) -> None:
        self._current: Track | None = None
        self._client: AsyncClient | None = None
        self._agent = None

    async def __aenter__(self) -> Brain:
        self._client = AsyncClient(api_key=_resolve_api_key())
        try:
            self._agent = await self._client.agents.create_agent(
                name=AGENT_NAME,
                description="Drives Mixxx's GUI on this machine for claw-dj.",
                environments=[
                    {"id": "this-machine", "kind": "desktop", "host": "user_device"}
                ],
            )
        except ApiError as error:
            if error.status_code != 409:
                raise
            self._agent = await self._client.agents.get_agent(AGENT_NAME)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        # Local bridges run on daemon threads (hai_agents_local.manager); stop
        # them explicitly because Brain may live inside a longer-running process.
        stop_bridges()
        self._client = None
        self._agent = None

    def decide_next(self, requested_energy: Energy) -> Command | None:
        track = find_next(self._current, requested_energy)
        if track is None:
            return None
        self._current = track
        return LoadTrack(deck=self._next_free_deck(), track_id=track.track_id)

    def _next_free_deck(self) -> int:
        # TODO: track real deck state instead of hardcoding.
        return 2

    async def load_track_via_gui(self, track: Track, deck: int) -> str | dict:
        """Visible on screen during the demo: agent searches Mixxx's
        library browser and drags the track onto a deck."""
        return await self._run_task(
            f"In Mixxx, search the track library for '{track.title}' by "
            f"{track.artist} and load it into deck {deck}."
        )

    async def _run_task(
        self, task: str, *, max_steps: int | None = None, max_time_s: float | None = None
    ) -> str | dict:
        if self._client is None or self._agent is None:
            raise RuntimeError("Brain must be entered via `async with Brain() as brain:` first")
        result = await self._client.run_session(
            agent=self._agent,
            messages=task,
            max_steps=max_steps or DEFAULT_MAX_STEPS,
            timeout_seconds=max_time_s or DEFAULT_MAX_TIME_S,
        )
        if result.error:
            raise RuntimeError(f"hai-agents task failed: {result.error}")
        return result.answer
