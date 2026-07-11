"""The H Company computer-use agent, driven locally through holo-desktop-cli
(https://github.com/hcompai/holo-desktop-cli). Drives Mixxx's actual GUI for
anything that isn't beat-critical (browse library, load a track to a deck,
react to a request) and emits shared.commands.Command objects for Hands to
execute for anything that is.

Needs `holo login` run once on this machine first (see holo-desktop-cli's
README) — this talks to the same hai-agent-runtime daemon `holo run` uses,
over loopback, via holo_desktop.agent_client. No shelling out to the CLI.
"""
from __future__ import annotations

from holo_desktop.agent_client import AgentApiClient, AgentDaemon, SpawnConfig, ensure_running
from holo_desktop.agent_client.requests import build_session_request
from holo_desktop.settings import load_holo_settings

from brain.library import Energy, Track, find_next
from shared.commands import Command, LoadTrack

DEFAULT_AGENT_API_PORT = 18795


class Brain:
    def __init__(self, *, port: int = DEFAULT_AGENT_API_PORT):
        self._current: Track | None = None
        self._port = port
        self._daemon: AgentDaemon | None = None

    async def __aenter__(self) -> Brain:
        settings = load_holo_settings()
        self._daemon = await ensure_running(SpawnConfig(port=self._port), settings=settings)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._daemon is not None:
            await self._daemon.aclose()
            self._daemon = None

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
        if self._daemon is None:
            raise RuntimeError("Brain must be entered via `async with Brain() as brain:` first")
        request = build_session_request(task=task, max_steps=max_steps, max_time_s=max_time_s)
        async with AgentApiClient(self._daemon.base_url, self._daemon.token) as client:
            stream = client.stream(await client.create_session(request))
            async for _event in stream.events():
                pass
            if stream.error:
                raise RuntimeError(f"holo task failed: {stream.error}")
            return stream.answer
