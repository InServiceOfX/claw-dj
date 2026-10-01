"""Model-choreographed DJ showcase moves (Mix feel: DJ showcase).

Without a model, DJ showcase rotates a fixed flourish list every other
blend. With a model provider selected, the model sees every transition of
the final order (tempo, key, compatibility reasons, backbeat status, DJ
notes) and picks one move per blend from the moves the runner can actually
play, aiming for a varied, ambitious showcase.

Every pick is validated; anything illegal falls back to the rotation:
* only catalog moves; DJ notes win (no_flourish, a noted exit/entry style);
* the smooth opening stays smooth;
* dramatic exits (no overlap) are rare: never two in a row, at most one in
  four blends, and never on a sample-lineage pair whose blend is the story.

Backbeat matching is unaffected: flourishes decorate a beat-matched blend,
and dramatic exits do not overlap the two songs.
"""
from __future__ import annotations

import json
from typing import Callable

FLOURISHES: dict[str, str] = {
    "bass_swap": "EQ swap of the low end between decks during a beat-matched blend (subtle, always safe).",
    "stutter_fill": "Beat-synced stutter of the outgoing deck right before the blend (energy builder).",
    "loop_roll": "Shrinking loop roll on the outgoing deck into the blend (classic build-up).",
    "censor_fill": "Slip-mode reverse 'censor' of a word/beat on the outgoing deck (turntablist touch).",
    "transformer_cut": "Rhythmic transformer cuts on the outgoing deck before the blend (scratch-DJ flair).",
}
EXITS: dict[str, str] = {
    "echo_out": "Outgoing fades under a rising echo tail; incoming starts clean (no overlap). Good for tempo gaps.",
    "filter_drop": "Low-pass sweep removes the outgoing drums, then the incoming drops clean on the one (no overlap).",
}
MAX_EXIT_SHARE = 0.25


def build_prompt(transitions: list[dict], brief: str) -> str:
    catalog = {"flourish": FLOURISHES, "exit": {"none": "Normal beat-matched blend.", **EXITS}}
    return f"""You are the DJ brain of claw-dj choreographing a DJ SHOWCASE mix in Mixxx.

The point of this mix is to show off claw-dj's mixing skill: use the full
range of moves, vary them, build energy, and save the most dramatic moments
for where they land best (energy peaks, tempo gaps, big hooks). Keep the
first blends smooth so the set establishes itself.

For EACH transition pick:
- "flourish": one of {list(FLOURISHES)}
- "exit": one of ["none", {", ".join(repr(k) for k in EXITS)}]  (dramatic exits are rare:
  never two in a row, at most one in four transitions)

Hard rules:
- Use only the moves listed in the catalog below.
- Respect each song's dj_notes; never override them.
- Prefer "exit": "none" on sample/lineage pairs: the blend itself is the story.
- Backbeat (snare) matching is done by the planner; do not try to change it.

User brief (may be empty): {brief or "(none)"}

Move catalog:
{json.dumps(catalog, indent=1)}

Transitions in playback order:
{json.dumps(transitions, indent=1)}

Respond with EXACTLY one JSON object (no markdown fences):
{{"moves": [{{"i": 0, "flourish": "loop_roll", "exit": "none", "why": "short reason"}}, ...]}}
"""


def _parse(text: str) -> list[dict]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in model reply")
    moves = json.loads(text[start:end + 1]).get("moves")
    if not isinstance(moves, list):
        raise ValueError("reply has no moves list")
    return moves


def validate(
    moves: list[dict],
    transitions: list[dict],
    *,
    smooth_opening: int,
) -> tuple[dict[int, dict], list[str]]:
    """Return ({index: {"flourish", "exit", "why"}}, notes) of legal picks."""
    plan: dict[int, dict] = {}
    notes: list[str] = []
    by_index = {t["i"]: t for t in transitions}
    exits_used = 0
    exit_budget = max(0, int(len(transitions) * MAX_EXIT_SHARE))
    last_exit_index = -10
    for item in sorted(moves, key=lambda m: int(m.get("i", -1)) if str(m.get("i", "")).lstrip("-").isdigit() else -1):
        try:
            i = int(item.get("i"))
        except (TypeError, ValueError):
            continue
        t = by_index.get(i)
        if t is None or i in plan:
            continue
        flourish = item.get("flourish")
        exit_style = item.get("exit") or "none"
        if flourish not in FLOURISHES:
            flourish = None
        if exit_style != "none" and exit_style not in EXITS:
            exit_style = "none"
        if i < smooth_opening:
            continue  # opening stays smooth; builder enforces it too
        if t.get("no_flourish"):
            flourish = None
        if exit_style != "none":
            reason = None
            if t.get("noted_style"):
                reason = "a DJ note sets this transition's style"
            elif t.get("lineage"):
                reason = "sample-lineage blend is the story"
            elif i - last_exit_index <= 1:
                reason = "two dramatic exits in a row"
            elif exits_used >= exit_budget:
                reason = "dramatic-exit budget used"
            if reason:
                notes.append(f"showcase move {i + 1}: {exit_style} declined ({reason})")
                exit_style = "none"
            else:
                exits_used += 1
                last_exit_index = i
        if flourish is None and exit_style == "none":
            continue
        plan[i] = {"flourish": flourish, "exit": exit_style, "why": str(item.get("why") or "")[:120]}
    return plan, notes


def choreograph(
    transitions: list[dict],
    *,
    brief: str,
    ask: Callable[[str], str],
    provider: str,
    smooth_opening: int,
) -> tuple[dict[int, dict], list[str]]:
    """Ask the model; never raises (an empty plan keeps the rotation)."""
    if not transitions:
        return {}, []
    try:
        moves = _parse(ask(build_prompt(transitions, brief)))
    except Exception as error:
        return {}, [f"{provider} showcase choreography skipped: {error}"]
    plan, notes = validate(moves, transitions, smooth_opening=smooth_opening)
    exits = sum(1 for p in plan.values() if p["exit"] != "none")
    kinds = sorted({p["flourish"] for p in plan.values() if p["flourish"]})
    notes.insert(
        0,
        f"{provider} choreographed {len(plan)}/{len(transitions)} showcase moves "
        f"({exits} dramatic exits; flourishes: {', '.join(kinds) or 'none'})",
    )
    return plan, notes
