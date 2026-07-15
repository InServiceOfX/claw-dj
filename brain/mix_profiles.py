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
    # First N transitions prioritize longer beat-matched blends and suppress tricks.
    smooth_opening_transitions: int = 0
    # Never let the outgoing deck go fully silent (no brake/hard-cut fallback
    # for extreme tempo gaps — downgrades to a smoother, always-blending
    # tempo_gap_blend instead). For "keep the floor dancing" profiles.
    avoid_silence: bool = False


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
        description=(
            "Keep the floor dancing: same energy, near-constant BPM, the beat "
            "never stops — no hard cuts, only the occasional planned drop."
        ),
        seconds_per_track=75.0,
        ride_phrases_pattern=(3, 2, 3, 4, 2, 3),
        intro_entry_every=6,
        transition_scale=1.75,
        flourish_every=5,
        avoid_silence=True,
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
    "mix-to-listen": MixProfile(
        name="mix-to-listen",
        description=(
            "A listening mix, not a performance — play the best parts of each "
            "song at whatever length earns it, no showcase cuts, no rush."
        ),
        seconds_per_track=85.0,
        # Variable on purpose — some songs' best part is short, some deserve
        # to run; unlike warm-up's uniform long pattern, this leans on
        # confidence_extra_phrase to decide length per track.
        ride_phrases_pattern=(2, 3, 2, 4, 3, 2, 4, 3),
        confidence_extra_phrase=0.45,
        intro_entry_every=5,
        transition_scale=1.6,
        flourish_every=0,
        avoid_silence=True,
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

    smooth_opening = has(
        "smooth opening", "smooth first", "opening blends", "opening transitions"
    )
    if (
        has("longer", "long blend", "breathe", "let it play", "let the", "relaxed")
        or (has("smooth") and not smooth_opening)
    ):
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
    if smooth_opening:
        profile = replace(profile, smooth_opening_transitions=7)
        notes.append("first 7 transitions use longer trick-free beat-matched blends")
    return profile, notes


def profile_provenance(profile: MixProfile, mix_brief: str, notes: list[str]) -> dict:
    return {
        "name": profile.name,
        "mix_brief": mix_brief or None,
        "brief_adjustments": notes,
        "values": asdict(profile),
    }
