"""Two-track DJ showcase: scratch-in, beat juggle, then a blended landing.

Uses the first two tracks from the quick-lineage demo seed (Warning -> Full Clip).

    uv run python -m hands.showcase_mix
"""

from __future__ import annotations

import argparse
import time

from brain.quick_mix import cue_position, resolve_demo_tracks
from hands.mixxx_control import DEFAULT_PORT, MixxxControl
from hands.transition import crossfader_target, deck_group, transition

LOAD_TIMEOUT_S = 30.0


def _wait_for(mixxx: MixxxControl, group: str, key: str, predicate, timeout_s: float) -> float:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        value = mixxx.get(group, key)
        if predicate(value):
            return value
        time.sleep(0.1)
    raise TimeoutError(f"{group},{key} was not ready within {timeout_s:.1f}s")


def prepare_deck(mixxx: MixxxControl, deck: int, path: str, cue_seconds: float) -> tuple[float, float]:
    group = deck_group(deck)
    mixxx.set(group, "play", 0)
    mixxx.set(group, "eject", 1)
    _wait_for(mixxx, group, "track_loaded", lambda value: value < 0.5, 5.0)
    mixxx.load(deck, path)
    _wait_for(mixxx, group, "track_loaded", lambda value: value >= 0.5, LOAD_TIMEOUT_S)
    duration = _wait_for(mixxx, group, "duration", lambda value: value > 0, LOAD_TIMEOUT_S)
    bpm = _wait_for(mixxx, group, "bpm", lambda value: value > 0, LOAD_TIMEOUT_S)
    cue = cue_position(cue_seconds, duration)
    mixxx.set(group, "playposition", cue)
    mixxx.set(group, "volume", 1.0)
    mixxx.set(group, "pregain", 1.0)
    mixxx.set(group, "mute", 0)
    mixxx.set(group, "keylock", 1)
    mixxx.set(group, "quantize", 1)
    mixxx.set(group, "rate", 0)
    return bpm, cue


def reset_audio_bus(mixxx: MixxxControl) -> None:
    mixxx.set("[Master]", "headMix", 1.0)
    mixxx.set("[Master]", "gain", 1.0)
    mixxx.set("[Master]", "volume", 1.0)


def drop_at_cue(mixxx: MixxxControl, deck: int, cue: float) -> None:
    group = deck_group(deck)
    mixxx.set(group, "play", 0)
    mixxx.set(group, "playposition", cue)
    mixxx.set(group, "play", 1)


def scratch_in(
    mixxx: MixxxControl,
    deck: int,
    cue: float,
    *,
    strokes: int = 14,
    stroke_s: float = 0.09,
) -> None:
    group = deck_group(deck)
    mixxx.set(group, "keylock", 0)
    mixxx.set(group, "play", 0)
    mixxx.set(group, "playposition", max(0.0, cue - 0.01))
    mixxx.set(group, "volume", 1.0)
    mixxx.set(group, "play", 1)
    for i in range(strokes):
        mixxx.set(group, "rate", -0.75 if i % 2 == 0 else 0.85)
        time.sleep(stroke_s)
    mixxx.set(group, "rate", 0)
    mixxx.set(group, "keylock", 1)


def beat_juggle(
    mixxx: MixxxControl,
    *,
    deck_a: int,
    deck_b: int,
    cue_a: float,
    cue_b: float,
    cycles: int,
    hold_s: float,
) -> None:
    for cycle in range(cycles):
        drop_at_cue(mixxx, deck_a, cue_a)
        mixxx.set("[Master]", "crossfader", crossfader_target(deck_a))
        time.sleep(hold_s)
        drop_at_cue(mixxx, deck_b, cue_b)
        mixxx.set("[Master]", "crossfader", crossfader_target(deck_b))
        time.sleep(hold_s)
        print(f"[juggle] cycle {cycle + 1}/{cycles}")


def transformer_cuts(mixxx: MixxxControl, cuts: int, hold_s: float = 0.16) -> None:
    for i in range(cuts):
        mixxx.set("[Master]", "crossfader", -1.0 if i % 2 == 0 else 1.0)
        time.sleep(hold_s)


def run_showcase(port: int = DEFAULT_PORT) -> None:
    tracks = resolve_demo_tracks()[:2]
    track_a, track_b = tracks[0], tracks[1]
    deck_a, deck_b = 1, 2

    print(f"[showcase] {track_a.artist} - {track_a.title}")
    print(f"[showcase] {track_b.artist} - {track_b.title}")

    with MixxxControl(port=port, timeout_s=LOAD_TIMEOUT_S + 5) as mixxx:
        reset_audio_bus(mixxx)
        bpm_a, cue_a = prepare_deck(mixxx, deck_a, track_a.track_id, track_a.cue_seconds)
        bpm_b, cue_b = prepare_deck(mixxx, deck_b, track_b.track_id, track_b.cue_seconds)
        print(f"[load] deck {deck_a}: {bpm_a:.1f} BPM @ cue {track_a.cue_seconds:.1f}s")
        print(f"[load] deck {deck_b}: {bpm_b:.1f} BPM @ cue {track_b.cue_seconds:.1f}s")

        drop_at_cue(mixxx, deck_a, cue_a)
        mixxx.set("[Master]", "crossfader", crossfader_target(deck_a))
        print("[live] deck 1 intro")
        time.sleep(4.0)

        print("[scratch] pulling deck 2 in")
        scratch_in(mixxx, deck_b, cue_b)
        start = time.monotonic()
        while time.monotonic() - start < 1.8:
            progress = (time.monotonic() - start) / 1.8
            mixxx.set(
                "[Master]",
                "crossfader",
                -1.0 + 1.6 * progress,
            )
            time.sleep(0.04)

        print("[juggle] alternating cue drops")
        beat_juggle(
            mixxx,
            deck_a=deck_a,
            deck_b=deck_b,
            cue_a=cue_a,
            cue_b=cue_b,
            cycles=6,
            hold_s=0.48,
        )

        print("[cuts] transformer fader chops")
        mixxx.set(deck_group(deck_a), "play", 1)
        mixxx.set(deck_group(deck_b), "play", 1)
        transformer_cuts(mixxx, cuts=10)

    tempo_gap = abs(bpm_a - bpm_b) / bpm_a
    sync = tempo_gap <= 0.06
    beats = 8 if sync else 2
    print(f"[mix] landing on deck {deck_b} ({'blend' if sync else 'on-beat cut'})")
    transition(deck_a, deck_b, beats=beats, port=port, sync=sync)

    with MixxxControl(port=port) as mixxx:
        time.sleep(10.0)
        mixxx.set(deck_group(deck_b), "play", 0)
        mixxx.set(deck_group(deck_a), "play", 0)
        mixxx.set("[Master]", "crossfader", crossfader_target(deck_b))
    print("[done] showcase complete")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    run_showcase(port=args.port)


if __name__ == "__main__":
    main()
