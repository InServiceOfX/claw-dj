"""Estimate a full plan's play time from JSON alone, without Mixxx or audio I/O."""
from __future__ import annotations

import math

from shared.performance import duration


def _positive(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def estimate_mix_seconds(plan: dict) -> float:
    """Count sequential rides/blends, or the end of a simultaneous timeline.

    Planned beat counts take precedence over nominal seconds when the deck's
    tempo is known. Loading, beat alignment, effects and live ride shortening
    can change actual play time; this is deliberately an approximate total.
    """
    performance = plan.get("performance")
    if performance and performance.get("clips"):
        return duration(performance)

    native_bpms = {
        track.get("track_id"): _positive(track.get("bpm"))
        for track in plan.get("tracks", []) if isinstance(track, dict)
    }
    deck_native: dict[int, float | None] = {}
    deck_bpms: dict[int, float | None] = {}
    total = 0.0
    for event in plan.get("events", []):
        op = event.get("op")
        deck = event.get("deck")
        if op == "load":
            deck_native[deck] = native_bpms.get(event.get("track_id"))
            deck_bpms[deck] = deck_native[deck]
        elif op == "start":
            deck_bpms[deck] = _positive(event.get("bpm_target")) or deck_bpms.get(deck)
        elif op in {"play_body", "finale"}:
            bpm = deck_bpms.get(deck) or native_bpms.get(event.get("track_id"))
            beats = _positive(event.get("beats"))
            seconds = _positive(event.get("seconds")) or 30.0
            if event.get("play_to_end") or beats is None:
                total += seconds
            elif bpm:
                # Approximate a tempo ramp by its average BPM, counting its
                # beats inside the body rather than adding a second ride.
                target = _positive(event.get("exit_bpm_target"))
                ramp = min(beats, _positive(event.get("tempo_ramp_beats")) or 0) if target else 0
                total += (beats - ramp) * 60 / bpm
                if ramp:
                    total += ramp * 60 / ((bpm + target) / 2)
                    deck_bpms[deck] = target
            else:
                total += _positive(event.get("seconds")) or beats * 60 / 100
        elif op == "transition":
            outgoing, incoming = event.get("from_deck"), event.get("to_deck")
            bpm = deck_bpms.get(outgoing) or 100.0
            total += (_positive(event.get("transition_beats")) or 16) * 60 / bpm
            # The incoming track usually settles back to native tempo after
            # the blend; explicit bridge holds and kept blend tempo override it.
            deck_bpms[incoming] = (
                _positive(event.get("incoming_bpm_target"))
                or (bpm if event.get("keep_blend_tempo") else None)
                or _positive(event.get("incoming_settle_bpm"))
                or _positive(event.get("incoming_native_bpm"))
                or deck_native.get(incoming)
            )
        elif op == "opener_effect":
            bpm = deck_bpms.get(deck) or 100.0
            if event.get("style") in {"juggle_intro", "juggle_brake_intro"}:
                beats = max(2, _positive(event.get("juggle_chops")) or 6) * (
                    _positive(event.get("juggle_hold_beats")) or 1)
            else:
                beats = _positive(event.get("tease_beats")) or 4
            total += beats * 60 / bpm
    return total


def mix_duration_label(plan: dict) -> str:
    """Human-readable estimate rounded to minutes, without false precision."""
    seconds = estimate_mix_seconds(plan)
    if 0 < seconds < 60:
        return "under 1 min"
    minutes = int(seconds / 60 + 0.5)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"about {hours} hr" + (f" {minutes} min" if minutes else "")
    return f"about {minutes} min"
