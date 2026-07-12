"""Plays a short autonomous set. Division of labor (the whole pitch):

- Brain — the H Company computer-use agent (hai-agents, via brain/agent.py) picks
  the set order and *visibly* loads each next track through Mixxx's real GUI
  (sidebar click, right-click → Load to Deck N). Slow is fine: it happens
  while the current track plays.
- Hands — clawdj-cli (core-rust/) executes each transition beat-accurately
  off Mixxx's live beat-tick feedback: measure BPM, start incoming deck on a
  beat, beat-sync, smoothstep-crossfade over N beats.

Usage:
    uv run python -m brain.set_player --tracks 3 --seconds 60 --beats 16
    uv run python -m brain.set_player --no-agent  # Rust-only dry run: you
        load tracks by hand when prompted, transitions still run live
    uv run python -m brain.set_player --set lineage --loader control-api
        # lineage_set playlist, tracks loaded straight onto decks over the
        # patched Mixxx's --control-api-port JSON API (hands/mixxx_control.py)
        # — deterministic, no vision loop in the load path

Assumes: Mixxx open, clawdj mapping enabled, the chosen playlist imported and
analyzed (brain/sync_mixxx_analysis.py), its .json regenerated after the sync
so bpm fields are real. `--loader control-api` additionally assumes Mixxx was
launched with `--control-api-port 9995` (our fork's flag).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path

from brain.agent import Brain

REPO_ROOT = Path(__file__).parent.parent
SET_JSONS = {
    "demo": Path(__file__).parent / "data" / "demo_set.json",
    "lineage": Path(__file__).parent / "data" / "lineage_set.json",
}


def find_clawdj_binary() -> Path:
    for profile in ("release", "debug"):
        candidate = REPO_ROOT / "core-rust" / "target" / profile / "clawdj"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "clawdj binary not found — run `cargo build` in core-rust/ first"
    )


def clawdj(*args: str) -> None:
    binary = find_clawdj_binary()
    subprocess.run([str(binary), *args], check=True)


def plan_set(tracks: list[dict], count: int) -> list[dict]:
    """Greedy nearest-BPM chain: start from the median-BPM track (mid-energy
    opener, avoids starting on a double-time outlier) and always hop to the
    closest-tempo unplayed track, so every transition is beat-syncable."""
    pool = [t for t in tracks if t.get("bpm")]
    if len(pool) < count:
        raise ValueError(f"only {len(pool)} tracks with bpm, need {count}")
    pool.sort(key=lambda t: t["bpm"])
    current = pool.pop(len(pool) // 2)
    ordered = [current]
    while len(ordered) < count:
        current = min(pool, key=lambda t: abs(t["bpm"] - current["bpm"]))
        pool.remove(current)
        ordered.append(current)
    return ordered


LOAD_TASK = """\
Click directly on the Mixxx application window (its main waveform/deck area)
to make sure Mixxx is the focused, frontmost application — its own menu bar
must be showing before you do anything else. Do not use the dock; if focus
is lost, click the Mixxx window itself again (never click the dock icon
repeatedly — it opens other apps, not Mixxx). In the left sidebar, click the
playlist named 'demo_set'. In its track list, find the track titled
'{title}' by '{artist}' (scroll if needed). Right-click that exact track to
open its context menu, hover 'Load to' to open its submenu, hover 'Deck' in
that submenu to open a further submenu listing Deck 1/2/3/4, then click
'Deck {deck}'. (Confirmed working path — three nested menu levels: right-click
-> Load to -> Deck -> Deck {deck}.) Do NOT start playback and do NOT touch any
other control. Answer with the exact track you loaded and to which deck."""


async def load_track(
    brain: Brain | None, track: dict, deck: int, control_api_port: int | None = None
) -> None:
    title, artist = track["title"], track["artist"]
    if control_api_port is not None:
        from hands.mixxx_control import MixxxControl

        print(f"[hands] control API loading '{title}' into deck {deck}...")
        with MixxxControl(port=control_api_port) as mixxx:
            mixxx.load(deck, track["track_id"])
        return
    if brain is None:
        input(f">>> manually load '{title}' by {artist} into deck {deck}, then press Enter... ")
        return
    print(f"[brain] hai-agents loading '{title}' into deck {deck}...")
    answer = await brain._run_task(
        LOAD_TASK.format(title=title, artist=artist, deck=deck), max_time_s=180
    )
    print(f"[brain] {str(answer)[:200]}")


def hands_cue_and_go(live_deck: int, engine_port: int | None) -> None:
    """Put the first deck live: cue to start, full volume, crossfader on it."""
    if engine_port is not None:
        from hands.mixxx_control import MixxxControl
        from hands.transition import crossfader_target, deck_group

        with MixxxControl(port=engine_port) as mixxx:
            group = deck_group(live_deck)
            mixxx.set(group, "playposition", 0.0)
            mixxx.set(group, "volume", 1.0)
            mixxx.set("[Master]", "crossfader", crossfader_target(live_deck))
            mixxx.set(group, "play", 1)
        return
    clawdj("cmd", json.dumps({"op": "cue", "deck": live_deck}))
    clawdj("cmd", json.dumps({"op": "volume", "deck": live_deck, "value": 127}))
    clawdj("cmd", json.dumps({"op": "crossfade", "value": 0 if live_deck == 1 else 127}))
    clawdj("cmd", json.dumps({"op": "play", "deck": live_deck}))


def hands_transition(live_deck: int, idle_deck: int, beats: int, engine_port: int | None) -> None:
    if engine_port is not None:
        from hands.transition import transition

        transition(live_deck, idle_deck, beats=beats, port=engine_port)
        return
    clawdj("transition", "--from", str(live_deck), "--to", str(idle_deck), "--beats", str(beats))


async def play_set(
    count: int,
    seconds: float,
    beats: int,
    use_agent: bool,
    set_name: str = "demo",
    control_api_port: int | None = None,
    engine_port: int | None = None,
) -> None:
    tracks = json.loads(SET_JSONS[set_name].read_text())
    ordered = plan_set(tracks, count)
    print("set plan (BPM-chained):")
    for i, t in enumerate(ordered):
        print(f"  {i + 1}. {t['artist']} - {t['title']}  ({t['bpm']:.1f} BPM, {t.get('key') or '?'})")

    brain_ctx = Brain() if use_agent and control_api_port is None else None
    if brain_ctx is not None:
        await brain_ctx.__aenter__()
    try:
        live_deck = 1
        await load_track(brain_ctx, ordered[0], live_deck, control_api_port)
        # Cue first: a deck parked at end-of-track accepts play but never beats.
        hands_cue_and_go(live_deck, engine_port)
        live_since = time.monotonic()
        print(f"[hands] deck {live_deck} live: {ordered[0]['title']}")

        for nxt in ordered[1:]:
            idle_deck = 2 if live_deck == 1 else 1
            await load_track(brain_ctx, nxt, idle_deck, control_api_port)
            remaining = seconds - (time.monotonic() - live_since)
            if remaining > 0:
                print(f"[set] letting deck {live_deck} ride {remaining:.0f}s more...")
                await asyncio.sleep(remaining)
            print(f"[hands] transition deck {live_deck} -> {idle_deck} ({beats} beats)")
            hands_transition(live_deck, idle_deck, beats, engine_port)
            live_deck = idle_deck
            live_since = time.monotonic()
            print(f"[hands] deck {live_deck} live: {nxt['title']}")

        print(f"[set] last track riding; set of {count} complete.")
    finally:
        if brain_ctx is not None:
            await brain_ctx.__aexit__(None, None, None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracks", type=int, default=3)
    parser.add_argument("--seconds", type=float, default=60.0, help="play time per track before transitioning")
    parser.add_argument("--beats", type=int, default=16, help="crossfade length in beats")
    parser.add_argument(
        "--no-agent",
        "--no-holo",
        dest="no_agent",
        action="store_true",
        help="skip the H Company agent and load tracks manually (--no-holo is kept as an alias)",
    )
    parser.add_argument(
        "--set",
        dest="set_name",
        choices=sorted(SET_JSONS),
        default="demo",
        help="which playlist json to play from",
    )
    parser.add_argument(
        "--loader",
        choices=("agent", "manual", "control-api"),
        default=None,
        help="how tracks get onto decks; default follows --no-agent, "
        "'control-api' loads over the patched Mixxx's JSON API",
    )
    parser.add_argument(
        "--control-api-port",
        type=int,
        default=9995,
        help="port Mixxx's --control-api-port was given (loader/engine=control-api)",
    )
    parser.add_argument(
        "--engine",
        choices=("midi", "control-api"),
        default="midi",
        help="transition engine: 'midi' = core-rust clawdj over the MIDI "
        "mapping (needs a virtual MIDI port), 'control-api' = pure-TCP "
        "hands/transition.py against the patched Mixxx",
    )
    args = parser.parse_args()
    control_api_port = args.control_api_port if args.loader == "control-api" else None
    engine_port = args.control_api_port if args.engine == "control-api" else None
    use_agent = args.loader == "agent" if args.loader else not args.no_agent
    asyncio.run(
        play_set(
            args.tracks,
            args.seconds,
            args.beats,
            use_agent=use_agent,
            set_name=args.set_name,
            control_api_port=control_api_port,
            engine_port=engine_port,
        )
    )


if __name__ == "__main__":
    main()
