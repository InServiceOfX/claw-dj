"""Gentle faders: the one rule every claw-dj harness shares for blend speed.

Ernest, 2026-10-03: agents move the channel faders "TOO FAST ... STOP doing
that ... blend it in gently." A blend into a different song moves its faders
on a steady (linear) ramp over at least GENTLE_BLEND_BEATS counts. Only
deliberate cuts, platter/echo/filter exits, beat juggles and same-song
handoffs of identical material may move faster.
See user_stories/story__blend_with_gentle_faders_never_fast.md.
"""
from __future__ import annotations

GENTLE_BLEND_BEATS = 16
FAST_TECHNIQUES = frozenset({
    "key_clash_cut", "half_time_or_cut", "beat_drop_entry", "echo_out_exit", "filter_drop_exit",
})
FAST_MOVES = frozenset({
    "hard_cut", "brake_out", "spinback_out", "echo_out_exit", "filter_drop_exit", "key_blend",
})


def is_gentle_blend(event: dict) -> bool:
    """True when a transition is a fader blend into a different song (not a
    deliberate cut or exit), so it must take GENTLE_BLEND_BEATS or more."""
    return (event.get("technique") not in FAST_TECHNIQUES
            and not FAST_MOVES.intersection(event.get("moves") or []))


def gentle_beats(event: dict, beats: float) -> int:
    """`beats` for a cut or exit; at least GENTLE_BLEND_BEATS for a blend."""
    beats = int(beats)
    return max(GENTLE_BLEND_BEATS, beats) if is_gentle_blend(event) else beats
