"""Beat-anchored deck transition over the Mixxx control API — the pure-TCP
counterpart of core-rust's MIDI `clawdj transition`. Exists because Linux has
no IAC-style loopback MIDI bus by default; the control API needs zero MIDI
setup and reads Mixxx's own analyzed BPM instead of measuring beat ticks.

What a transition does (mirrors the Rust engine's behavior):
  1. read the outgoing deck's live BPM from Mixxx ([ChannelN],bpm)
  2. wait for the outgoing deck's next beat ([ChannelN],beat_active edge)
  3. start the incoming deck and beat-sync it ([ChannelN],beatsync)
  4. smoothstep-crossfade over N beats (fade seconds = beats * 60 / BPM)
  5. stop the outgoing deck

Mixxx control conventions used here: crossfader is [Master] -1.0 (left/deck1)
to +1.0 (right/deck2); volume is 0..1; play is 0/1.

Usage (Mixxx running with --control-api-port 9995, tracks loaded):
    uv run python -m hands.transition --from 1 --to 2 --beats 16
"""

from __future__ import annotations

import argparse
import time

from hands.mixxx_control import DEFAULT_PORT, MixxxControl


def deck_group(deck: int) -> str:
    return f"[Channel{deck}]"


def crossfader_target(deck: int) -> float:
    # Decks 1/3 sit on the left of the crossfader, 2/4 on the right.
    return -1.0 if deck % 2 == 1 else 1.0


def smoothstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def wait_for_next_beat(port: int, group: str, timeout_s: float = 10.0) -> None:
    """Block until the group's next beat_active rising edge (own connection,
    since pushed events would interleave with request replies otherwise)."""
    # A healthy beat_active stream produces an edge in well under two seconds
    # for the tempos we mix. Fail over quickly instead of adding a ten-second
    # hole to the set when the subscription itself is stale.
    event_timeout_s = min(timeout_s, 3.0)
    with MixxxControl(port=port, timeout_s=event_timeout_s) as events_conn:
        events_conn.subscribe(group, "beat_active")
        deadline = time.monotonic() + timeout_s
        try:
            for event in events_conn.events():
                if event["value"] >= 1.0:
                    return
                if time.monotonic() > deadline:
                    break
        except TimeoutError:
            pass
    # Some dynamically loaded decks keep playing while Mixxx's control-API
    # subscription drops beat_active notifications. Do not kill a live set
    # for a missing push event: use the deck's analyzed BPM as a bounded
    # fallback anchor. The next transition can still land within one beat.
    with MixxxControl(port=port, timeout_s=2.0) as mixxx:
        bpm = mixxx.get(group, "bpm")
        playing = mixxx.get(group, "play") >= 0.5
    if bpm > 0 and playing:
        period = 60.0 / bpm
        print(f"  (no beat_active edge from {group}; timing fallback at {bpm:.2f} BPM)")
        time.sleep(period)
        return
    raise TimeoutError(f"no beat from {group} within {timeout_s}s (deck is not playing)")


def wait_for_beats(port: int, group: str, beats: int, timeout_s: float = 90.0) -> None:
    """Count beat_active rising edges on a dedicated event connection."""
    if beats <= 0:
        return
    with MixxxControl(port=port, timeout_s=2.0) as mixxx:
        bpm = mixxx.get(group, "bpm")
        playing = mixxx.get(group, "play") >= 0.5
    if bpm <= 0 or not playing:
        raise TimeoutError(f"cannot wait for beats from {group}: deck is not playing at a valid BPM")

    period = 60.0 / bpm
    # Four missing beats are enough to decide the subscription is unhealthy;
    # the old 90-second timeout made a dropped notification stream sound like
    # the DJ simply stopped. Preserve total musical time with a BPM fallback.
    event_timeout_s = min(timeout_s, max(2.0, 4.0 * period))
    started = time.monotonic()
    with MixxxControl(port=port, timeout_s=event_timeout_s) as events_conn:
        events_conn.subscribe(group, "beat_active")
        count = 0
        previous = 0.0
        deadline = time.monotonic() + timeout_s
        try:
            for event in events_conn.events():
                value = float(event["value"])
                if value >= 1.0 and previous < 1.0:
                    count += 1
                    if count >= beats:
                        return
                previous = value
                if time.monotonic() > deadline:
                    break
        except TimeoutError:
            pass
    elapsed = time.monotonic() - started
    remaining = max(0.0, beats * period - elapsed)
    print(
        f"  (beat_active stream stopped after {count}/{beats} beats; "
        f"timing remaining {remaining:.1f}s at {bpm:.2f} BPM)"
    )
    time.sleep(remaining)


def transition(
    from_deck: int,
    to_deck: int,
    beats: int = 16,
    port: int = DEFAULT_PORT,
    step_s: float = 0.02,
    sync: bool = True,
) -> None:
    if from_deck == to_deck:
        raise ValueError("from_deck and to_deck must differ")
    if from_deck not in range(1, 5) or to_deck not in range(1, 5):
        raise ValueError("deck numbers must be between 1 and 4")
    if beats <= 0:
        raise ValueError("beats must be positive")
    if step_s <= 0:
        raise ValueError("step_s must be positive")

    out_group, in_group = deck_group(from_deck), deck_group(to_deck)
    with MixxxControl(port=port) as mixxx:
        bpm = mixxx.get(out_group, "bpm")
        if bpm <= 0:
            raise RuntimeError(
                f"{out_group} reports no bpm — is it playing an analyzed track?"
            )
        fade_s = beats * 60.0 / bpm
        print(
            f"[transition] {out_group} @ {bpm:.1f} BPM -> {in_group}, {beats} beats = {fade_s:.1f}s fade"
        )

        mixxx.set(in_group, "volume", 1.0)

        print("[transition] waiting for a beat to anchor on...")
        wait_for_next_beat(port, out_group)
        mixxx.set(in_group, "play", 1)
        if sync:
            mixxx.set(in_group, "beatsync", 1)
            print(f"[transition] {in_group} started + beat-synced, fading...")
        else:
            print(
                f"[transition] {in_group} started on-beat without tempo sync, cutting..."
            )

        start_pos = mixxx.get("[Master]", "crossfader")
        end_pos = crossfader_target(to_deck)
        t0 = time.monotonic()
        while True:
            progress = (time.monotonic() - t0) / fade_s
            mixxx.set(
                "[Master]",
                "crossfader",
                start_pos + (end_pos - start_pos) * smoothstep(progress),
            )
            if progress >= 1.0:
                break
            time.sleep(step_s)

        mixxx.set(out_group, "play", 0)
        print(f"[transition] done — {in_group} live, {out_group} stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_deck", type=int, required=True)
    parser.add_argument("--to", dest="to_deck", type=int, required=True)
    parser.add_argument("--beats", type=int, default=16)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    transition(args.from_deck, args.to_deck, beats=args.beats, port=args.port)


if __name__ == "__main__":
    main()
