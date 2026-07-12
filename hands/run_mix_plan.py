"""Execute a continuous mix plan against Mixxx's control API.

Plays Mixxx like an instrument: loads tracks, rides EQ/filter/rate, beat-syncs,
crossfades, optional scratch-ins — all from brain/data/mix_plan.json.

Requires Mixxx launched with the patched control API:
    mixxx --developer --control-api-port 9995

Usage:
    uv run python -m hands.run_mix_plan --dry-run
    uv run python -m hands.run_mix_plan
    uv run python -m hands.run_mix_plan --plan brain/data/mix_plan.json --port 9995
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from hands.mixxx_control import DEFAULT_PORT, MixxxControl
from hands.transition import crossfader_target, deck_group, smoothstep, wait_for_beats, wait_for_next_beat

PLAN_DEFAULT = Path(__file__).resolve().parent.parent / "brain" / "data" / "mix_plan.json"
LOAD_TIMEOUT_S = 30.0

EQ_GROUP = "[EqualizerRack1_{channel}_Effect1]"
FILTER_GROUP = "[QuickEffectRack1_{channel}]"


def _wait_for(mixxx: MixxxControl, group: str, key: str, predicate, timeout_s: float) -> float:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        value = mixxx.get(group, key)
        if predicate(value):
            return value
        time.sleep(0.1)
    raise TimeoutError(f"{group},{key} not ready within {timeout_s:.1f}s")


def eq_group(deck: int) -> str:
    return EQ_GROUP.format(channel=f"[Channel{deck}]")


def filter_group(deck: int) -> str:
    return FILTER_GROUP.format(channel=f"[Channel{deck}]")


def reset_instrument(mixxx: MixxxControl) -> None:
    mixxx.set("[Master]", "crossfader", -1.0)
    mixxx.set("[Master]", "gain", 1.0)
    mixxx.set("[Master]", "volume", 1.0)
    for deck in (1, 2):
        group = deck_group(deck)
        mixxx.set(group, "volume", 1.0)
        mixxx.set(group, "pregain", 1.0)
        mixxx.set(group, "rate", 0.0)
        mixxx.set(group, "keylock", 1)
        mixxx.set(group, "quantize", 1)
        mixxx.set(group, "mute", 0)
        try:
            eg = eq_group(deck)
            mixxx.set(eg, "parameter1", 0.5)
            mixxx.set(eg, "parameter2", 0.5)
            mixxx.set(eg, "parameter3", 0.5)
        except Exception:
            pass
        try:
            mixxx.set(filter_group(deck), "super1", 0.5)
        except Exception:
            pass


def settle_rate(mixxx: MixxxControl, deck: int, steps: int = 8) -> None:
    """Glide the deck back to its native tempo after a beatsync landing.

    Without this, sync chains the first track's tempo through the whole set
    (observed live: every transition anchored at 101 BPM). Riding the pitch
    back to 0 lets each track keep its own energy, and makes the planner's
    tempo-direction choices audible. Keylock is on, so pitch is unaffected.
    """
    group = deck_group(deck)
    try:
        current = mixxx.get(group, "rate")
    except Exception:
        return
    if abs(current) < 0.01:
        mixxx.set(group, "rate", 0.0)
        return
    bpm = mixxx.get(group, "bpm") or 100.0
    period = 60.0 / max(60.0, min(200.0, bpm))
    for i in range(1, steps + 1):
        mixxx.set(group, "rate", current * (1.0 - i / steps))
        time.sleep(period)
    print(f"  rate settled to native tempo on deck {deck}")


def load_deck(
    mixxx: MixxxControl,
    deck: int,
    path: str,
    cue_fraction: float = 0.1,
    cue_seconds: float | None = None,
) -> None:
    group = deck_group(deck)
    mixxx.set(group, "play", 0)
    try:
        mixxx.set(group, "eject", 1)
        _wait_for(mixxx, group, "track_loaded", lambda v: v < 0.5, 5.0)
    except TimeoutError:
        pass
    mixxx.load(deck, path)
    _wait_for(mixxx, group, "track_loaded", lambda v: v >= 0.5, LOAD_TIMEOUT_S)
    duration = _wait_for(mixxx, group, "duration", lambda v: v > 0, LOAD_TIMEOUT_S)
    _wait_for(mixxx, group, "bpm", lambda v: v > 0, LOAD_TIMEOUT_S)
    position = cue_seconds / duration if cue_seconds is not None else cue_fraction
    mixxx.set(group, "playposition", min(0.95, max(0.0, position)))
    mixxx.set(group, "volume", 1.0)
    mixxx.set(group, "keylock", 1)
    mixxx.set(group, "quantize", 1)
    mixxx.set(group, "rate", 0.0)
    cue_label = f"{cue_seconds:.2f}s" if cue_seconds is not None else f"{position:.1%}"
    print(f"[load] deck {deck}: {Path(path).name}  ({duration:.0f}s, cue {cue_label})")


def apply_moves(mixxx: MixxxControl, from_deck: int, to_deck: int, moves: list[str]) -> None:
    """Pre-transition instrument gestures (EQ/filter/scratch)."""
    out_g, in_g = deck_group(from_deck), deck_group(to_deck)
    for move in moves:
        if move == "eq_kill_out_low":
            try:
                mixxx.set(eq_group(from_deck), "parameter1", 0.0)
            except Exception:
                pass
        elif move == "eq_boost_in_mid":
            try:
                mixxx.set(eq_group(to_deck), "parameter2", 0.7)
            except Exception:
                pass
        elif move == "eq_dip_out_mid":
            try:
                mixxx.set(eq_group(from_deck), "parameter2", 0.25)
            except Exception:
                pass
        elif move == "eq_kill_out_high":
            try:
                mixxx.set(eq_group(from_deck), "parameter3", 0.0)
            except Exception:
                pass
        elif move == "eq_restore":
            for deck in (from_deck, to_deck):
                try:
                    eg = eq_group(deck)
                    mixxx.set(eg, "parameter1", 0.5)
                    mixxx.set(eg, "parameter2", 0.5)
                    mixxx.set(eg, "parameter3", 0.5)
                except Exception:
                    pass
        elif move == "filter_open_in":
            try:
                mixxx.set(filter_group(to_deck), "super1", 0.65)
            except Exception:
                pass
        elif move == "filter_sweep_out":
            try:
                # sweep filter closed on outgoing
                for value in (0.5, 0.35, 0.2, 0.1):
                    mixxx.set(filter_group(from_deck), "super1", value)
                    time.sleep(0.05)
            except Exception:
                pass
        elif move == "filter_reset":
            for deck in (from_deck, to_deck):
                try:
                    mixxx.set(filter_group(deck), "super1", 0.5)
                except Exception:
                    pass
        elif move == "rate_nudge_in":
            mixxx.set(in_g, "rate", 0.05)
        elif move == "optional_scratch_in":
            # Briefly reveal a rate-wiggle, then restore the analyzed cue.
            cue = mixxx.get(in_g, "playposition")
            start_cf = mixxx.get("[Master]", "crossfader")
            preview_cf = start_cf + 0.28 * (crossfader_target(to_deck) - start_cf)
            mixxx.set(in_g, "keylock", 0)
            mixxx.set(in_g, "play", 1)
            for i in range(6):
                mixxx.set(in_g, "rate", -0.6 if i % 2 == 0 else 0.7)
                mixxx.set("[Master]", "crossfader", preview_cf if i % 2 else start_cf)
                time.sleep(0.07)
            mixxx.set("[Master]", "crossfader", start_cf)
            mixxx.set(in_g, "rate", 0.0)
            mixxx.set(in_g, "keylock", 1)
            mixxx.set(in_g, "play", 0)
            mixxx.set(in_g, "playposition", cue)
        elif move == "optional_loop_roll_out":
            try:
                mixxx.set(out_g, "beatloop_4_activate", 1)
                time.sleep(0.4)
                mixxx.set(out_g, "reloop_toggle", 1)
            except Exception:
                pass
        # sync / crossfade handled by transition()


def perform_transition(mixxx: MixxxControl, event: dict, *, port: int) -> None:
    """Execute one beat-anchored transition with continuous instrument curves."""
    from_deck = int(event["from_deck"])
    to_deck = int(event["to_deck"])
    beats = int(event.get("transition_beats", 16))
    moves = list(event.get("moves") or [])
    technique = event.get("technique", "standard_blend")
    out_g, in_g = deck_group(from_deck), deck_group(to_deck)
    bpm = mixxx.get(out_g, "bpm")
    if bpm <= 0:
        raise RuntimeError(f"{out_g} reports no BPM")
    sync = "sync" in moves and technique != "half_time_or_cut"
    hard = technique in {"key_clash_cut", "half_time_or_cut"} or "hard_cut" in moves

    print(f"  anchoring on {out_g} beat ({bpm:.2f} BPM)")
    wait_for_next_beat(port, out_g)
    mixxx.set(in_g, "play", 1)
    if sync:
        mixxx.set(in_g, "beatsync", 1)

    start_cf = mixxx.get("[Master]", "crossfader")
    end_cf = crossfader_target(to_deck)
    if hard:
        mixxx.set("[Master]", "crossfader", end_cf)
        mixxx.set(out_g, "play", 0)
        print(f"  on-beat cut -> deck {to_deck} ({'sync' if sync else 'native tempo'})")
        return

    fade_s = beats * 60.0 / bpm
    bass_swap = any(move in moves for move in ("eq_kill_out_low", "eq_dip_out_mid", "eq_kill_out_high"))
    if bass_swap:
        try:
            mixxx.set(eq_group(to_deck), "parameter1", 0.0)
        except Exception:
            bass_swap = False

    swapped = False
    t0 = time.monotonic()
    while True:
        progress = min(1.0, (time.monotonic() - t0) / fade_s)
        curve = smoothstep(progress)
        mixxx.set("[Master]", "crossfader", start_cf + (end_cf - start_cf) * curve)
        if bass_swap and progress >= 0.5 and not swapped:
            mixxx.set(eq_group(from_deck), "parameter1", 0.0)
            mixxx.set(eq_group(to_deck), "parameter1", 0.5)
            swapped = True
            print("  bass swap")
        if "filter_sweep_out" in moves:
            try:
                mixxx.set(filter_group(from_deck), "super1", 0.5 - 0.4 * curve)
            except Exception:
                pass
        if "optional_transformer_cuts" in moves and progress > 0.72:
            # Four restrained chops near the landing, still ending on target.
            phase = int((progress - 0.72) / 0.07)
            if phase < 4 and phase % 2 == 0:
                mixxx.set("[Master]", "crossfader", start_cf)
        if progress >= 1.0:
            break
        time.sleep(0.02)

    mixxx.set("[Master]", "crossfader", end_cf)
    mixxx.set(out_g, "play", 0)
    print(f"  {beats}-beat landing -> deck {to_deck}")


def run_plan(plan: dict, *, port: int, dry_run: bool, max_events: int | None) -> None:
    events = plan["events"]
    if max_events:
        events = events[:max_events]

    if dry_run:
        for i, event in enumerate(events, 1):
            op = event.get("op")
            print(f"{i:03d}  {op:24}  {json.dumps({k: v for k, v in event.items() if k != 'op'})[:140]}")
        print(f"dry-run: {len(events)} events (no Mixxx connection)")
        return

    with MixxxControl(port=port, timeout_s=LOAD_TIMEOUT_S + 5) as mixxx:
        pending_preload: dict | None = None
        for i, event in enumerate(events, 1):
            op = event["op"]
            print(f"\n[{i}/{len(events)}] {op}")
            if op == "reset_instrument":
                reset_instrument(mixxx)
            elif op == "load":
                load_deck(
                    mixxx,
                    event["deck"],
                    event["track_id"],
                    event.get("cue_fraction", 0.1),
                    event.get("cue_seconds"),
                )
            elif op == "start":
                deck = event["deck"]
                mixxx.set("[Master]", "crossfader", crossfader_target(deck))
                mixxx.set(deck_group(deck), "play", 1)
                print(f"  deck {deck} playing")
            elif op == "play_body":
                beats = event.get("beats")
                seconds = float(event.get("seconds", 30))
                if beats is not None:
                    print(f"  riding {event.get('track')} for {beats} live beats")
                else:
                    print(f"  riding {event.get('track')} for {seconds:.0f}s")
                print(f"  hints: {event.get('instrument_hints')}")
                if beats is not None:
                    wait_for_beats(port, deck_group(int(event["deck"])), int(beats))
                else:
                    time.sleep(seconds)
            elif op == "preload_after_transition":
                pending_preload = event
            elif op == "transition":
                from_deck = int(event["from_deck"])
                to_deck = int(event["to_deck"])
                beats = int(event.get("transition_beats", 16))
                moves = list(event.get("moves") or [])
                print(f"  {event.get('technique')}: {event.get('from_track')} → {event.get('to_track')}")
                print(f"  moves: {moves}")
                print(f"  notes: {event.get('notes')}")
                # Ensure incoming is loaded (may already be)
                preview_moves = {
                    "optional_scratch_in",
                    "optional_loop_roll_out",
                    "rate_nudge_in",
                    "eq_boost_in_mid",
                    "filter_open_in",
                }
                apply_moves(mixxx, from_deck, to_deck, [move for move in moves if move in preview_moves])
                perform_transition(mixxx, event, port=port)
                # restore EQ/filter after land
                apply_moves(mixxx, from_deck, to_deck, ["eq_restore", "filter_reset"])
                settle_rate(mixxx, to_deck)
                if pending_preload and pending_preload.get("deck") == from_deck:
                    print(f"  preload next into freed deck {from_deck}")
                    load_deck(
                        mixxx,
                        from_deck,
                        pending_preload["track_id"],
                        pending_preload.get("cue_fraction", 0.1),
                        pending_preload.get("cue_seconds"),
                    )
                    pending_preload = None
            elif op == "finale":
                beats = event.get("beats")
                seconds = float(event.get("seconds", 30))
                if beats:
                    print(f"  finale {event.get('track')} ({beats} beats)")
                    wait_for_beats(port, deck_group(int(event["deck"])), int(beats))
                else:
                    print(f"  finale {event.get('track')} ({seconds:.0f}s)")
                    time.sleep(seconds)
            elif op == "stop_all":
                for deck in (1, 2):
                    mixxx.set(deck_group(deck), "play", 0)
                print("  stopped")
            else:
                print(f"  (skip unknown op {op})")
    print("\nmix plan complete")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN_DEFAULT)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-events", type=int, default=None, help="execute only the first N events")
    args = parser.parse_args()
    if not args.plan.exists():
        raise SystemExit(f"missing {args.plan} — run: uv run python -m brain.build_mix_plan")
    plan = json.loads(args.plan.read_text())
    run_plan(plan, port=args.port, dry_run=args.dry_run, max_events=args.max_events)


if __name__ == "__main__":
    main()
