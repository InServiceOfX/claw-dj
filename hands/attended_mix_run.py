"""Attended live mix: 3 transitions (4 tracks) via clawdj MIDI.

Stock Mixxx has no --control-api-port; this path is what works on this Mac:
  - You (or the H agent) load tracks into decks
  - Hands runs cue/play/volume/crossfade + beat-anchored transitions over MIDI

Usage (Mixxx open, clawdj mapping enabled on IAC Driver clawdj):
    uv run python -m hands.attended_mix_run
    uv run python -m hands.attended_mix_run --seconds 25 --beats 16
    uv run python -m hands.attended_mix_run --agent   # H agent loads via GUI
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_PLAYLIST = REPO / "brain" / "data" / "playlist.json"
DEFAULT_PLAN = REPO / "brain" / "data" / "mix_plan.json"


def find_clawdj() -> Path:
    for profile in ("release", "debug"):
        candidate = REPO / "core-rust" / "target" / profile / "clawdj"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("clawdj binary missing — cargo build -p clawdj-cli in core-rust/")


def clawdj(*args: str) -> None:
    binary = find_clawdj()
    print(f"  $ clawdj {' '.join(args)}")
    subprocess.run([str(binary), *args], check=True)


def pick_tracks(count: int) -> list[dict]:
    """Prefer mix_plan order (already technique-aware); fall back to playlist."""
    if DEFAULT_PLAN.exists():
        plan = json.loads(DEFAULT_PLAN.read_text())
        tracks = plan.get("tracks") or []
        if len(tracks) >= count:
            return tracks[:count]
    tracks = json.loads(DEFAULT_PLAYLIST.read_text())
    analyzed = [t for t in tracks if t.get("bpm")]
    pool = analyzed if len(analyzed) >= count else tracks
    return pool[:count]


def hands_start(deck: int) -> None:
    clawdj("cmd", json.dumps({"op": "cue", "deck": deck}))
    clawdj("cmd", json.dumps({"op": "volume", "deck": deck, "value": 127}))
    clawdj("cmd", json.dumps({"op": "volume", "deck": 2 if deck == 1 else 1, "value": 127}))
    clawdj("cmd", json.dumps({"op": "crossfade", "value": 0 if deck == 1 else 127}))
    clawdj("cmd", json.dumps({"op": "play", "deck": deck}))


def hands_transition(from_deck: int, to_deck: int, beats: int) -> None:
    clawdj(
        "transition",
        "--from",
        str(from_deck),
        "--to",
        str(to_deck),
        "--beats",
        str(beats),
    )


LOAD_PROMPT = """\
Click directly on the Mixxx application window (waveform/deck area) so Mixxx is
focused — do not use the dock icon. Search or browse the library for the track
titled '{title}' by '{artist}'. Prefer the studio album version if several
appear. Right-click that exact track → hover 'Load to' → hover 'Deck' → click
'Deck {deck}'. Do NOT start playback and do NOT touch other controls. Answer
with the exact track loaded and which deck.
"""


async def human_load_window(track: dict, deck: int, seconds: float = 45.0) -> None:
    """Attended fallback: give the human a timed window to load (no stdin needed)."""
    title, artist = track["title"], track["artist"]
    print(
        f"\n*** ATTENDED LOAD — you have {seconds:.0f}s ***\n"
        f"    Mixxx → find '{title}' by {artist} → right-click → Load to → Deck → Deck {deck}\n"
        f"    Do not press play; Hands will start/sync/crossfade.\n"
    )
    step = 5.0
    left = seconds
    while left > 0:
        print(f"    … {left:.0f}s remaining to load deck {deck}")
        await asyncio.sleep(min(step, left))
        left -= step
    print(f"    continuing (assuming deck {deck} is loaded)")


async def load_track(track: dict, deck: int, *, use_agent: bool, brain=None) -> None:
    title, artist = track["title"], track["artist"]
    print(f"\n>>> LOAD deck {deck}: {artist} — {title}")
    if track.get("bpm"):
        print(f"    bpm={track['bpm']:.1f}  key={track.get('key') or '?'}")
    if use_agent:
        prompt = LOAD_PROMPT.format(title=title, artist=artist, deck=deck)
        last_error: Exception | None = None
        for attempt in (1, 2):
            try:
                if brain is None:
                    from brain.agent import Brain

                    async with Brain() as owned:
                        answer = await owned._run_task(prompt, max_time_s=150)
                else:
                    answer = await brain._run_task(prompt, max_time_s=150)
                print(f"[brain] {str(answer)[:240]}")
                return
            except Exception as error:  # noqa: BLE001 — attended run must continue
                last_error = error
                print(f"[brain] load attempt {attempt} failed: {error}")
        print(f"[brain] giving up on agent load ({last_error}); falling back to human window")
        await human_load_window(track, deck, seconds=50.0)
    else:
        await human_load_window(track, deck, seconds=50.0)


async def run(
    *,
    transitions: int,
    seconds: float,
    beats: int,
    use_agent: bool,
) -> None:
    track_count = transitions + 1
    tracks = pick_tracks(track_count)
    if len(tracks) < track_count:
        raise SystemExit(f"need {track_count} tracks, only have {len(tracks)}")

    print("=" * 60)
    print(f"ATTENDED LIVE MIX — {transitions} transitions ({track_count} tracks)")
    print("Engine: clawdj MIDI (IAC Driver clawdj)")
    print("Loader:", "H agent GUI" if use_agent else "manual (you load)")
    print("=" * 60)
    for i, track in enumerate(tracks, 1):
        tag = f"{track.get('bpm', 0):.1f}/{track.get('key') or '?'}" if track.get("bpm") else "?"
        print(f"  {i}. {track['artist']} — {track['title']}  [{tag}]")
    print()
    print("Preconditions: Mixxx focused, clawdj controller enabled, audio routing OK.")
    print("Hands off mouse/keyboard during H-agent loads if using --agent.")
    if use_agent:
        print("Auto-starting in 3s (agent loads)…")
        await asyncio.sleep(3)
    else:
        input("Press Enter to begin… ")

    # Verify MIDI
    clawdj("setup")

    async def _body(brain=None) -> None:
        live = 1
        await load_track(tracks[0], live, use_agent=use_agent, brain=brain)
        print(f"\n[hands] starting deck {live}")
        hands_start(live)
        live_since = time.monotonic()
        print(f"[live] deck {live}: {tracks[0]['artist']} — {tracks[0]['title']}")

        for index, nxt in enumerate(tracks[1:], start=1):
            idle = 2 if live == 1 else 1
            await load_track(nxt, idle, use_agent=use_agent, brain=brain)
            remaining = seconds - (time.monotonic() - live_since)
            if remaining > 0:
                print(
                    f"[set] ride deck {live} for {remaining:.0f}s "
                    f"before transition {index}/{transitions}…"
                )
                await asyncio.sleep(remaining)
            print(
                f"\n[hands] TRANSITION {index}/{transitions}: "
                f"deck {live} → {idle} over {beats} beats"
            )
            print(f"        {tracks[index - 1]['title']} → {nxt['title']}")
            hands_transition(live, idle, beats)
            live = idle
            live_since = time.monotonic()
            print(f"[live] deck {live}: {nxt['artist']} — {nxt['title']}")

        print(f"\n[set] final track riding {seconds:.0f}s…")
        await asyncio.sleep(seconds)
        clawdj("cmd", json.dumps({"op": "pause", "deck": live}))
        print("=" * 60)
        print(f"DONE — {transitions} transitions complete.")
        print("=" * 60)

    if use_agent:
        from brain.agent import Brain

        async with Brain() as brain:
            await _body(brain)
    else:
        await _body(None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transitions",
        type=int,
        default=3,
        help="number of live transitions (tracks = transitions + 1)",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=28.0,
        help="seconds to ride each track before transitioning",
    )
    parser.add_argument("--beats", type=int, default=16, help="crossfade length in beats")
    parser.add_argument(
        "--agent",
        action="store_true",
        help="use H Company agent to load tracks via Mixxx GUI (otherwise manual Enter prompts)",
    )
    args = parser.parse_args()
    asyncio.run(
        run(
            transitions=args.transitions,
            seconds=args.seconds,
            beats=args.beats,
            use_agent=args.agent,
        )
    )


if __name__ == "__main__":
    main()
