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
import os
import socket
import subprocess
from collections import deque
from collections.abc import Callable

DEFAULT_PORT = 9995


class MixxxControlError(RuntimeError):
    pass


class MixxxNotRunning(MixxxControlError):
    pass


class MixxxControlUnavailable(MixxxControlError):
    pass


class MixxxControl:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout_s: float = 5.0):
        self._sock = socket.create_connection((host, port), timeout=timeout_s)
        self._recv_buffer = b""
        self._pending_events: deque[dict] = deque()

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
        # Pushed subscription events can interleave with replies. Preserve
        # them for events() instead of dropping them: losing a beat_active
        # edge during the subscribe acknowledgement makes a long ride finish
        # exactly one count late.
        while "event" in reply:
            self._pending_events.append(reply)
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
        Events that raced with a request acknowledgement are yielded first.
        Use on a connection dedicated to subscriptions."""
        while self._pending_events:
            yield self._pending_events.popleft()
        while True:
            message = self._read_line()
            if "event" in message:
                yield message


def validates_mixxx_control(port: int, *, timeout_s: float = 0.5) -> bool:
    """True only when localhost answers the patched Mixxx ping protocol."""
    try:
        with MixxxControl(port=int(port), timeout_s=timeout_s) as mixxx:
            return mixxx.ping()
    except (OSError, ValueError, json.JSONDecodeError, MixxxControlError):
        return False


def mixxx_process_ids(*, ps_output: str | None = None) -> list[int]:
    """Find running Mixxx processes without depending on a fixed app path."""
    if ps_output is None:
        ps_output = subprocess.run(
            ["ps", "-axo", "pid=,comm=,args="],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    result: list[int] = []
    for line in ps_output.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) < 2:
            continue
        pid_text, command = fields[:2]
        args = fields[2] if len(fields) > 2 else ""
        executable = os.path.basename(command).casefold()
        if executable == "mixxx" or "/mixxx.app/contents/macos/mixxx" in args.casefold():
            try:
                result.append(int(pid_text))
            except ValueError:
                pass
    return sorted(set(result))


def mixxx_listener_ports(pid: int, *, lsof_output: str | None = None) -> list[int]:
    """Return TCP listener ports owned by one known Mixxx process."""
    if lsof_output is None:
        result = subprocess.run(
            ["lsof", "-nP", "-a", "-p", str(pid), "-iTCP", "-sTCP:LISTEN", "-Fn"],
            check=False,
            capture_output=True,
            text=True,
        )
        lsof_output = result.stdout
    ports: set[int] = set()
    for line in lsof_output.splitlines():
        if not line.startswith("n") or ":" not in line:
            continue
        tail = line.rsplit(":", 1)[-1]
        port_text = tail.split()[0]
        if port_text.isdigit():
            ports.add(int(port_text))
    return sorted(ports)


def discover_mixxx_control_port(
    *,
    preferred: int = DEFAULT_PORT,
    explicit: int | None = None,
    process_ids: list[int] | None = None,
    listener_lookup: Callable[[int], list[int]] | None = None,
    probe: Callable[[int], bool] = validates_mixxx_control,
) -> int:
    """Resolve a validated control port without broad arbitrary scanning.

    An explicit override is the sole candidate when supplied. Otherwise the
    preferred port and listeners owned by running Mixxx processes are probed
    using the real JSON ping request.
    """
    pids = mixxx_process_ids() if process_ids is None else process_ids
    if explicit is not None:
        if probe(int(explicit)):
            return int(explicit)
        if pids:
            raise MixxxControlUnavailable(
                f"Mixxx is running, but its control API is not reachable on explicit port {explicit}"
            )
        raise MixxxNotRunning(f"no running Mixxx control API on explicit port {explicit}")

    candidates = [int(preferred)]
    lookup = listener_lookup or mixxx_listener_ports
    for pid in pids:
        for port in lookup(pid):
            if port not in candidates:
                candidates.append(port)
    for port in candidates:
        if probe(port):
            return port
    if pids:
        raise MixxxControlUnavailable(
            "Mixxx is running, but no listener owned by that process answered the control API ping"
        )
    raise MixxxNotRunning("Mixxx is not running")


def plan_control_port(plan: dict) -> int | None:
    value = (plan.get("runtime") or {}).get("mixxx_control_port")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Validate/discover the patched Mixxx control API")
    sub = parser.add_subparsers(dest="command", required=True)
    probe_parser = sub.add_parser("probe")
    probe_parser.add_argument("port", type=int)
    discover_parser = sub.add_parser("discover")
    discover_parser.add_argument("--preferred", type=int, default=DEFAULT_PORT)
    discover_parser.add_argument("--explicit", type=int)
    args = parser.parse_args()
    if args.command == "probe":
        raise SystemExit(0 if validates_mixxx_control(args.port) else 1)
    try:
        print(discover_mixxx_control_port(preferred=args.preferred, explicit=args.explicit))
    except MixxxControlUnavailable as error:
        print(error, file=__import__("sys").stderr)
        raise SystemExit(3) from None
    except MixxxNotRunning as error:
        print(error, file=__import__("sys").stderr)
        raise SystemExit(4) from None


if __name__ == "__main__":
    main()
