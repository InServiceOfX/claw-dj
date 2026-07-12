"""Client for the Mixxx control API — the line-delimited JSON-over-TCP
surface our patched Mixxx serves on 127.0.0.1 when launched with
`--control-api-port <port>` (see the mixxx fork's
src/network/controlapiserver.cpp).

This complements, not replaces, the MIDI path: hands' beat-accurate work
stays on MIDI + beat feedback (core-rust), while this API gives
deterministic actions MIDI can't express — above all loading a specific
file to a deck without driving the GUI — plus full-resolution reads of any
Mixxx control (bpm, position, key, ...).

Stdlib-only on purpose: usable from any venv, script, or agent tool.

    with MixxxControl() as mixxx:
        mixxx.load(1, "/abs/path/track.mp3")
        bpm = mixxx.get("[Channel1]", "bpm")
        mixxx.set("[Channel1]", "play", 1)
"""
from __future__ import annotations

import json
import socket

DEFAULT_PORT = 9995


class MixxxControlError(RuntimeError):
    pass


class MixxxControl:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout_s: float = 5.0):
        self._sock = socket.create_connection((host, port), timeout=timeout_s)
        self._recv_buffer = b""

    def __enter__(self) -> MixxxControl:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._sock.close()

    def _read_line(self) -> dict:
        while b"\n" not in self._recv_buffer:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise MixxxControlError("mixxx closed the control connection")
            self._recv_buffer += chunk
        line, _, self._recv_buffer = self._recv_buffer.partition(b"\n")
        return json.loads(line)

    def _request(self, payload: dict) -> dict:
        self._sock.sendall(json.dumps(payload).encode() + b"\n")
        reply = self._read_line()
        # Pushed subscription events can interleave with replies; skip them
        # here (use a dedicated connection if you need the event stream).
        while "event" in reply:
            reply = self._read_line()
        if not reply.get("ok"):
            raise MixxxControlError(reply.get("error", "unknown control API error"))
        return reply

    def ping(self) -> bool:
        return bool(self._request({"op": "ping"}).get("pong"))

    def get(self, group: str, key: str) -> float:
        return float(self._request({"op": "get", "group": group, "key": key})["value"])

    def set(self, group: str, key: str, value: float) -> None:
        self._request({"op": "set", "group": group, "key": key, "value": float(value)})

    def load(self, deck: int, path: str, play: bool = False) -> None:
        """Load an audio file straight onto a deck — no GUI interaction."""
        self._request({"op": "load", "deck": deck, "path": path, "play": play})

    def subscribe(self, group: str, key: str) -> None:
        self._request({"op": "subscribe", "group": group, "key": key})

    def events(self):
        """Yield pushed change events forever: {"event","group","key","value"}.
        Use on a connection dedicated to subscriptions — interleaving
        request/reply calls on the same connection would eat the replies."""
        while True:
            message = self._read_line()
            if "event" in message:
                yield message
