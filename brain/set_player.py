"""Plays a short autonomous set. Division of labor (the whole pitch):

- Brain — the H Company computer-use agent (holo, via brain/agent.py) picks
  the set order and *visibly* loads each next track through Mixxx's real GUI
  (sidebar click, right-click → Load to Deck N). Slow is fine: it happens
  while the current track plays.
- Hands — clawdj-cli (core-rust/) executes each transition beat-accurately
  off Mixxx's live beat-tick feedback: measure BPM, start incoming deck on a
  beat, beat-sync, smoothstep-crossfade over N beats.

Usage:
    uv run python -m brain.set_player --tracks 3 --seconds 60 --beats 16
    uv run python -m brain.set_player --no-holo   # Rust-only dry run: you
        load tracks by hand when prompted, transitions still run live

Assumes: Mixxx open, clawdj mapping enabled, demo_set playlist imported and
analyzed (brain/sync_mixxx_analysis.py), demo_set.json regenerated after the
sync so bpm fields are real.
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
DEMO_SET_JSON = Path(__file__).parent / "data" / "demo_set.json"


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
is lost, click the Mixxx window itself again. In the left sidebar, click the
playlist named 'demo_set'. In its track list, find the track titled
'{title}' by '{artist}' (scroll if needed). Right-click that exact track and
choose 'Load to Deck {deck}' from the context menu (it may be under a
'Load to' submenu). Do NOT start playback and do NOT touch any other
control. Answer with the exact track you loaded and to which deck."""


async def load_track(brain: Brain | None, track: dict, deck: int) -> None:
    title, artist = track["title"], track["artist"]
    if brain is None:
        input(f">>> manually load '{title}' by {artist} into deck {deck}, then press Enter... ")
        return
    print(f"[brain] holo loading '{title}' into deck {deck}...")
    answer = await brain._run_task(
        LOAD_TASK.format(title=title, artist=artist, deck=deck), max_time_s=180
    )
    print(f"[brain] {str(answer)[:200]}")


async def play_set(count: int, seconds: float, beats: int, use_holo: bool) -> None:
    tracks = json.loads(DEMO_SET_JSON.read_text())
    ordered = plan_set(tracks, count)
    print("set plan (BPM-chained):")
    for i, t in enumerate(ordered):
        print(f"  {i + 1}. {t['artist']} - {t['title']}  ({t['bpm']:.1f} BPM, {t.get('key') or '?'})")

    brain_ctx = Brain() if use_holo else None
    if brain_ctx is not None:
        await brain_ctx.__aenter__()
    try:
        live_deck = 1
        await load_track(brain_ctx, ordered[0], live_deck)
        # Cue first: a deck parked at end-of-track accepts play but never beats.
        clawdj("cmd", json.dumps({"op": "cue", "deck": live_deck}))
        clawdj("cmd", json.dumps({"op": "volume", "deck": live_deck, "value": 127}))
        clawdj("cmd", json.dumps({"op": "crossfade", "value": 0 if live_deck == 1 else 127}))
        clawdj("cmd", json.dumps({"op": "play", "deck": live_deck}))
        live_since = time.monotonic()
        print(f"[hands] deck {live_deck} live: {ordered[0]['title']}")

        for nxt in ordered[1:]:
            idle_deck = 2 if live_deck == 1 else 1
            await load_track(brain_ctx, nxt, idle_deck)
            remaining = seconds - (time.monotonic() - live_since)
            if remaining > 0:
                print(f"[set] letting deck {live_deck} ride {remaining:.0f}s more...")
                await asyncio.sleep(remaining)
            print(f"[hands] transition deck {live_deck} -> {idle_deck} ({beats} beats)")
            clawdj("transition", "--from", str(live_deck), "--to", str(idle_deck), "--beats", str(beats))
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
    parser.add_argument("--no-holo", action="store_true", help="skip the H Company agent; load tracks manually")
    args = parser.parse_args()
    asyncio.run(play_set(args.tracks, args.seconds, args.beats, use_holo=not args.no_holo))


if __name__ == "__main__":
    main()
