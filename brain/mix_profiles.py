"""Mix profiles — how a set should *feel*, separated from what it contains.

A profile configures the plan BUILDER only. The plan document stays a
stable, declarative event list and `hands.run_mix_plan` stays a dumb,
beat-accurate executor: every knob here changes what gets written into the
plan, never how the runner interprets it.

Presets are named starting points; the user's free-text mix description
maps onto per-run overrides via `apply_brief` (deterministic keyword pass —
an agent-backed mapper can replace it later without touching the format).
Only knobs validated by real runs live here; grow one at a time.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class MixProfile:
    name: str
    description: str
    seconds_per_track: float = 40.0
    phrase_beats: int = 32
    # Segment lengths in phrases, rotated by slot. Showcase = short + varied.
    ride_phrases_pattern: tuple[int, ...] = (2, 1, 1, 2, 1, 3, 1, 1)
    # A confident phrase pick earns one extra phrase at/above this.
    confidence_extra_phrase: float = 0.60
    # Every Nth slot may enter at the intro instead of a body phrase (0 = never).
    intro_entry_every: int = 4
    # Multiplies each technique's transition beats (rounded to 4-beat grid).
    transition_scale: float = 1.0
    # Showcase flourish rotation applies every Nth transition (1 = all, 0 = never).
    flourish_every: int = 1


PROFILES: dict[str, MixProfile] = {
    "dj-showcase": MixProfile(
        name="dj-showcase",
        description=(
            "Short, varied segments that highlight interesting parts — "
            "mostly smooth blends (hard cuts rare), light flourishes."
        ),
        # Slightly longer fades by default so most landings feel mixed, not cut.
        transition_scale=1.25,
        flourish_every=2,
    ),
    "club-set": MixProfile(
        name="club-set",
        description="Longer rides and blends; keep the floor moving, show off less.",
        seconds_per_track=75.0,
        ride_phrases_pattern=(3, 2, 3, 4, 2, 3),
        intro_entry_every=6,
        transition_scale=1.75,
        flourish_every=4,
    ),
    "warm-up": MixProfile(
        name="warm-up",
        description="Unhurried, smooth, no tricks — long blends, songs breathe.",
        seconds_per_track=100.0,
        ride_phrases_pattern=(3, 4, 3, 4),
        confidence_extra_phrase=0.5,
        intro_entry_every=3,
        transition_scale=2.0,
        flourish_every=0,
    ),
}


def _clamp_pattern(pattern: tuple[int, ...], delta: int) -> tuple[int, ...]:
    return tuple(min(4, max(1, phrases + delta)) for phrases in pattern)


def apply_brief(profile: MixProfile, brief: str) -> tuple[MixProfile, list[str]]:
    """Map a free-text mix description onto profile overrides.

    Deterministic keyword pass. Returns (profile, notes) where notes name
    each adjustment for provenance — never silent.
    """
    text = (brief or "").casefold()
    notes: list[str] = []
    if not text.strip():
        return profile, notes

    def has(*words: str) -> bool:
        return any(re.search(rf"\b{re.escape(word)}", text) for word in words)

    if has("longer", "long blend", "smooth", "breathe", "let it play", "let the", "relaxed"):
        profile = replace(
            profile,
            transition_scale=profile.transition_scale * 1.5,
            ride_phrases_pattern=_clamp_pattern(profile.ride_phrases_pattern, 1),
        )
        notes.append("longer blends + longer rides (smooth/breathe)")
    if has("short", "quick", "fast cuts", "chop", "rapid", "showcase"):
        profile = replace(
            profile,
            transition_scale=max(0.5, profile.transition_scale * 0.75),
            ride_phrases_pattern=_clamp_pattern(profile.ride_phrases_pattern, -1),
        )
        notes.append("quicker transitions + shorter rides (short/quick)")
    # Negations first, exclusively — "no tricks" must not also match "tricks".
    if has("no scratch", "no tricks", "clean", "minimal"):
        profile = replace(profile, flourish_every=0)
        notes.append("flourishes off (clean/minimal)")
    elif has("more scratch", "show off", "tricks", "juggle"):
        profile = replace(profile, flourish_every=1)
        notes.append("flourish on every transition (show off)")
    if has("intro", "from the top", "full songs"):
        profile = replace(profile, intro_entry_every=2)
        notes.append("more intro entries (from the top)")
    return profile, notes


def profile_provenance(profile: MixProfile, mix_brief: str, notes: list[str]) -> dict:
    return {
        "name": profile.name,
        "mix_brief": mix_brief or None,
        "brief_adjustments": notes,
        "values": asdict(profile),
    }
