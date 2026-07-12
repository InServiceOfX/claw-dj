"""Plan and play a short sample-lineage demo through patched Mixxx.

The H Company agent may order the set, but deterministic Hands load, seek,
start, sync, and crossfade the decks. This keeps model latency out of the
beat-critical path.

Usage:
    uv run python -m brain.quick_mix --dry-run
    uv run python -m brain.quick_mix --planner h-agent --seconds 20 --beats 4
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from brain.agent import Brain
from brain.playlist import normalize
from hands.mixxx_control import DEFAULT_PORT, MixxxControl
from hands.transition import crossfader_target, deck_group, transition

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_SET = DATA_DIR / "lineage_set.json"
DEFAULT_SEED = Path(__file__).parent / "playlist_seeds" / "quick_lineage_demo.json"
LOAD_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class DemoTrack:
    id: str
    artist: str
    title: str
    track_id: str
    bpm_hint: float | None
    cue_seconds: float
    sample_artist: str
    sample_title: str
    sample_element: str
    hook_phrase: str
    research_url: str


@dataclass(frozen=True)
class DeckState:
    deck: int
    bpm: float
    duration: float


def resolve_demo_tracks(
    seed_path: Path = DEFAULT_SEED, set_path: Path = DEFAULT_SET
) -> list[DemoTrack]:
    seed = json.loads(seed_path.read_text())
    tracks = json.loads(set_path.read_text())
    resolved = []
    for item in seed:
        wanted_artist = normalize(item["artist"])
        wanted_title = normalize(item["title"])
        matches = [
            track
            for track in tracks
            if wanted_artist in normalize(track["artist"])
            and wanted_title in normalize(track["title"])
        ]
        if not matches:
            raise ValueError(
                f"demo track not found: {item['artist']} - {item['title']}"
            )
        track = min(matches, key=lambda row: (len(row["title"]), row["track_id"]))
        resolved.append(
            DemoTrack(
                **item,
                track_id=track["track_id"],
                bpm_hint=track.get("bpm"),
            )
        )
    return resolved


def parse_agent_order(answer: object, expected_ids: list[str]) -> list[str]:
    text = json.dumps(answer) if isinstance(answer, (dict, list)) else str(answer)
    candidates = re.findall(r"\[[^\[\]]*\]", text, flags=re.DOTALL)
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(value, list)
            and all(isinstance(item, str) for item in value)
            and len(value) == len(expected_ids)
            and set(value) == set(expected_ids)
        ):
            return value
    raise ValueError(f"H agent did not return each track id exactly once: {text[:500]}")


async def order_with_h_agent(tracks: list[DemoTrack]) -> list[DemoTrack]:
    options = [
        {
            "id": track.id,
            "artist": track.artist,
            "title": track.title,
            "bpm_hint": track.bpm_hint,
            "sample_source": f"{track.sample_artist} - {track.sample_title}",
            "sample_element": track.sample_element,
            "hook_phrase": track.hook_phrase,
        }
        for track in tracks
    ]
    prompt = f"""You are the Brain of a two-speed autonomous DJ.
This is a planning-only task: do not click or type in any desktop application.
Order these {len(tracks)} songs for a short sample-lineage showcase. Prioritize a
clear sample story, then smooth tempo flow. The two Walk On By descendants
should remain adjacent. Return exactly one JSON array containing every id once,
with no other JSON arrays. You may explain the order after that array.

Tracks:
{json.dumps(options, indent=2)}
"""
    async with Brain() as brain:
        answer = await brain._run_task(prompt, max_steps=4, max_time_s=90)
    ids = parse_agent_order(answer, [track.id for track in tracks])
    by_id = {track.id: track for track in tracks}
    return [by_id[track_id] for track_id in ids]


def cue_position(cue_seconds: float, duration: float) -> float:
    if duration <= 0:
        raise ValueError("duration must be positive")
    return min(0.99, max(0.0, cue_seconds / duration))


def _wait_for(
    mixxx: MixxxControl, group: str, key: str, predicate, timeout_s: float
) -> float:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        value = mixxx.get(group, key)
        if predicate(value):
            return value
        time.sleep(0.1)
    raise TimeoutError(f"{group},{key} was not ready within {timeout_s:.1f}s")


def prepare_deck(track: DemoTrack, deck: int, port: int) -> DeckState:
    group = deck_group(deck)
    with MixxxControl(port=port, timeout_s=LOAD_TIMEOUT_S + 5) as mixxx:
        mixxx.set(group, "play", 0)
        mixxx.set(group, "eject", 1)
        _wait_for(mixxx, group, "track_loaded", lambda value: value < 0.5, 5.0)
        mixxx.load(deck, track.track_id)
        _wait_for(
            mixxx, group, "track_loaded", lambda value: value >= 0.5, LOAD_TIMEOUT_S
        )
        duration = _wait_for(
            mixxx, group, "duration", lambda value: value > 0, LOAD_TIMEOUT_S
        )
        bpm = _wait_for(mixxx, group, "bpm", lambda value: value > 0, LOAD_TIMEOUT_S)
        mixxx.set(group, "playposition", cue_position(track.cue_seconds, duration))
        mixxx.set(group, "volume", 1.0)
        mixxx.set(group, "keylock", 1)
        mixxx.set(group, "quantize", 1)
    print(
        f"[load] deck {deck}: {track.artist} - {track.title} "
        f"@ {bpm:.2f} BPM, cue {track.cue_seconds:.1f}s"
    )
    return DeckState(deck=deck, bpm=bpm, duration=duration)


def start_first_deck(state: DeckState, port: int) -> None:
    group = deck_group(state.deck)
    with MixxxControl(port=port) as mixxx:
        mixxx.set("[Master]", "crossfader", crossfader_target(state.deck))
        mixxx.set(group, "play", 1)


def transition_settings(
    from_bpm: float, to_bpm: float, blend_beats: int
) -> tuple[int, bool]:
    tempo_gap = abs(to_bpm - from_bpm) / from_bpm
    if tempo_gap > 0.06:
        return 1, False
    return blend_beats, True


def print_plan(tracks: list[DemoTrack]) -> None:
    print("sample-lineage quick mix:")
    for index, track in enumerate(tracks, 1):
        print(
            f"  {index}. {track.artist} - {track.title} "
            f"(~{track.bpm_hint or 0:.1f} BPM)"
        )
        print(
            f"     samples {track.sample_artist} - {track.sample_title}: "
            f"{track.sample_element}; cue phrase: {track.hook_phrase!r}"
        )


def play_mix(tracks: list[DemoTrack], *, seconds: float, beats: int, port: int) -> None:
    if len(tracks) < 2:
        raise ValueError("a mix needs at least two tracks")
    current_track = tracks[0]
    current = prepare_deck(current_track, 1, port)
    start_first_deck(current, port)
    live_since = time.monotonic()
    print(f"[live] deck 1: {current_track.title}")

    for next_track in tracks[1:]:
        next_deck = 2 if current.deck == 1 else 1
        incoming = prepare_deck(next_track, next_deck, port)
        remaining = seconds - (time.monotonic() - live_since)
        if remaining > 0:
            time.sleep(remaining)
        transition_beats, sync = transition_settings(current.bpm, incoming.bpm, beats)
        style = "blend" if sync else "on-beat cut"
        print(
            f"[mix] {current_track.title} -> {next_track.title}: "
            f"{style}, {transition_beats} beat(s)"
        )
        transition(
            current.deck,
            incoming.deck,
            beats=transition_beats,
            port=port,
            sync=sync,
        )
        current_track = next_track
        current = incoming
        live_since = time.monotonic()
        print(f"[live] deck {current.deck}: {current_track.title}")

    remaining = seconds - (time.monotonic() - live_since)
    if remaining > 0:
        time.sleep(remaining)
    with MixxxControl(port=port) as mixxx:
        mixxx.set(deck_group(current.deck), "play", 0)
    print("[done] quick mix complete")


async def async_main(args: argparse.Namespace) -> None:
    tracks = resolve_demo_tracks()[: args.tracks]
    if args.planner == "h-agent":
        tracks = await order_with_h_agent(tracks)
    print_plan(tracks)
    if not args.dry_run:
        play_mix(tracks, seconds=args.seconds, beats=args.beats, port=args.port)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--planner", choices=("seed", "h-agent"), default="seed")
    parser.add_argument("--tracks", type=int, default=6, choices=range(2, 7))
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--beats", type=int, default=4)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.seconds <= 0 or args.beats <= 0:
        parser.error("--seconds and --beats must be positive")
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
