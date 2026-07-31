"""Versioned DJ transition grammars, independent of mix-feel profiles.

``MixProfile`` answers how long/flashy/continuous a set should feel.
``DjFormat`` answers which phrase structures and transition recipes are
allowed.  Keeping those axes separate lets (for example) a club set and a
listening mix both follow the same practicing DJ's hip-hop/R&B rules.

Each format declares its enforcement level. Strict formats must prove their
structural requirements from beatgrid/timeline data or explicit human DJ
annotations. Guided formats may use explicitly labeled fallbacks, but must
never present those fallbacks as expert-certified transitions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DjFormat:
    name: str
    label: str
    description: str
    version: int = 1
    spec_path: str | None = None
    strict: bool = False
    planner: str | None = None
    beats_per_bar: int = 4
    phrase_bars: int = 8
    default_recipe: str | None = None
    recipes: tuple[str, ...] = ()
    # "active": default, shown in the GUI dropdown.
    # "experimental": shown but visibly labeled not-yet-reliable — ear tests
    #   through 2026-07-31 found BOTH expert formats produced worse
    #   transitions than plain "none" + a free-text mix brief.
    # "archived": hidden from the GUI dropdown; the format definition and
    #   planner still work if invoked directly (CLI --dj-format, or tests)
    #   so the engineering behind it isn't lost, just not steered toward.
    status: str = "active"

    @property
    def phrase_beats(self) -> int:
        return self.beats_per_bar * self.phrase_bars


FORMATS: dict[str, DjFormat] = {
    "none": DjFormat(
        name="none",
        label="No expert format",
        description="Use the selected mix profile and per-track DJ notes.",
    ),
    "hiphop-rnb-8bar": DjFormat(
        name="hiphop-rnb-8bar",
        label="Hip-hop / R&B · strict 8-bar",
        description=(
            "Practicing-DJ transition grammar: every entry lands on beat 1; "
            "outgoing chorus/hook and incoming 8-bar intro are phrase-aligned. "
            "Archived 2026-07-31: live A/B comparisons sounded worse than "
            "'none', hidden from the GUI pending a fix."
        ),
        spec_path="docs/dj-formats/HIP_HOP_RNB_8_BAR.md",
        strict=True,
        planner="hiphop_rnb_8bar",
        default_recipe="chorus_to_intro",
        recipes=(
            "chorus_to_intro",
            "acapella_hook_swap",
            "intro_loop_under_entry",
        ),
        status="archived",
    ),
    "hiphop-rnb-guided": DjFormat(
        name="hiphop-rnb-guided",
        label="Hip-hop / R&B · guided",
        description=(
            "Every entry still lands on beat 1. Use the practicing-DJ "
            "8-bar recipes when verified; label other phrase-aligned "
            "transitions as guided fallbacks. Experimental — not yet "
            "reliable; ear tests through 2026-07-31 preferred 'none'."
        ),
        spec_path="docs/dj-formats/HIP_HOP_RNB_GUIDED.md",
        planner="hiphop_rnb_guided",
        default_recipe="chorus_to_intro",
        recipes=(
            "chorus_to_intro",
            "acapella_hook_swap",
            "intro_loop_under_entry",
            "phrase_aligned_fallback",
        ),
        status="experimental",
    ),
}


def get_format(name: str) -> DjFormat:
    try:
        return FORMATS[name]
    except KeyError as error:
        raise ValueError(
            f"unknown DJ format {name!r}; choose from {sorted(FORMATS)}"
        ) from error


def visible_formats() -> dict[str, DjFormat]:
    """Formats worth surfacing as a default GUI choice (i.e. not archived)."""
    return {name: fmt for name, fmt in FORMATS.items() if fmt.status != "archived"}


def format_provenance(dj_format: DjFormat) -> dict:
    return {
        **asdict(dj_format),
        "phrase_beats": dj_format.phrase_beats,
        "enforcement": (
            "strict"
            if dj_format.strict
            else ("guided" if dj_format.planner else "off")
        ),
    }
