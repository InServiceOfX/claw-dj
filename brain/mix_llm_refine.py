"""Model review of an optimized playback order ("optimizer leads, LLM refines").

The whole-set optimizer (brain.mix_optimizer) always produces a valid order
first. A model then reviews it like a DJ — story arc, energy, which pairings
earn a moment — and may propose a reordered list. The proposal is accepted
only when it passes the hard rules:

* same songs, each exactly once;
* the brief's constraints still hold (opener, adjacency groups, regions,
  mashup payoffs are re-applied and must not change the proposal);
* no more blind backbeat blends, at most one more unverified blend;
* the graph objective stays within a small tolerance of the optimizer's.

Anything else keeps the optimizer's order and says why. A model failure
never blocks Build mix plan.
"""
from __future__ import annotations

import json
from typing import Callable

from brain.mix_order_brief import build_graph, enforce_constraints, parse_constraints, short_ids

OBJECTIVE_TOLERANCE = 0.03  # fraction of the optimizer objective a story choice may cost
MIN_OBJECTIVE_SLACK = 0.5
MAX_EXTRA_UNVERIFIED = 1


def build_refine_prompt(rows: list[dict], graph, brief: str, *, mix_context: dict | None = None) -> str:
    ids = short_ids(rows)
    weak = {t.track_id for t, w in zip(graph.tracks, graph.weak) if w}
    catalog = [
        {
            "id": sid,
            "artist": row.get("artist"),
            "title": row.get("title"),
            "bpm": round(float(row["bpm"]), 1) if row.get("bpm") else None,
            "key": row.get("key"),
            "genre": row.get("genre"),
            "snare_read": "weak" if row["track_id"] in weak else "ok",
            "dj_notes": (row.get("dj_notes") or "") or None,
        }
        for sid, row in ids.items()
    ]
    path_to_short = {row["track_id"]: sid for sid, row in ids.items()}
    edges = [
        {
            "from": path_to_short[e.from_id],
            "to": path_to_short[e.to_id],
            "score": e.score,
            "backbeat": e.backbeat,
            "why": list(e.reasons)[:3],
        }
        for e in graph.report([row["track_id"] for row in rows])
    ]
    return f"""You are the DJ brain of claw-dj reviewing a continuous mix order for Mixxx.

The order below was built by a compatibility optimizer (BPM, key, sample
lineage, genre, chroma texture, snare-parity verifiability). Improve the
listening journey where it matters: opener and closer, energy arc, sample /
lineage payoffs, same-beat pairs, artist runs that feel repetitive. Keep
blends compatible — a swap that creates a tempo or key clash is worse.

Selected mix feel (effective settings): {json.dumps(mix_context or {}, ensure_ascii=False)}
When the brief is empty, use this feel and the DJ notes as your direction.
Aim for a strong first listening pass, with purposeful pacing and clean blends.
Gentle fades, verse/phrase boundaries, source exclusions and backbeat matching
remain authoritative. This is an order review: the builder chooses executable
moves from its analysis and approved evidence. Do not invent measurements,
approve unsupported sample blends or add supporting tracks.

Hard rules you must keep:
- Use every id exactly once; never invent ids.
- A song whose snare_read is "weak" cannot be snare-matched; do not place two
  weak songs next to each other.
- Respect every song's dj_notes: they are the DJ's own instructions
  (cue points, ride lengths, skips, opener/closer, tempo holds).
- Vocals-only (acapella) tracks are layered over instrumentals by the
  builder; keep each acapella next to its instrumental if it already is.

User brief (may be empty): {brief or "(none)"}

Respond with EXACTLY one JSON object (no markdown fences):
{{"order": ["t000", "..."], "notes": ["one short line per change and why"]}}
Return the order unchanged with notes ["no change"] if it is already best.

Catalog ({len(catalog)} songs):
{json.dumps(catalog, indent=1)}

Current order with blend scores:
{json.dumps(edges, indent=1)}
"""


def _parse_order(text: str, allowed: list[str]) -> tuple[list[str], list[str]]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in model reply")
    payload = json.loads(text[start:end + 1])
    order = [str(item) for item in payload.get("order") or []]
    if sorted(order) != sorted(allowed) or len(set(order)) != len(order):
        raise ValueError("proposed order is not the same songs exactly once")
    notes = [str(n) for n in payload.get("notes") or []][:12]
    return order, notes


def refine_order(
    ordered_rows: list[dict],
    constraints: dict,
    all_rows: list[dict],
    *,
    brief: str,
    ask: Callable[[str], str],
    provider: str,
    snare_confidence: dict[str, float] | None = None,
    mix_context: dict | None = None,
) -> tuple[list[dict], list[str]]:
    """Return (rows in final order, notes). Never raises on model trouble."""
    if len(ordered_rows) < 2:
        return ordered_rows, [f"{provider} review skipped: need at least two songs"]
    graph = build_graph(ordered_rows, snare_confidence)
    current_paths = [row["track_id"] for row in ordered_rows]
    local = short_ids(ordered_rows)
    path_to_local = {row["track_id"]: sid for sid, row in local.items()}
    try:
        reply = ask(build_refine_prompt(ordered_rows, graph, brief, mix_context=mix_context))
        proposal_short, model_notes = _parse_order(reply, list(local))
    except Exception as error:  # provider down, bad JSON, wrong set
        return ordered_rows, [f"{provider} review skipped: {error}"]
    if proposal_short == list(local):
        return ordered_rows, [f"{provider} review: kept the optimized order"]

    # Constraints were expressed in all_rows' short ids; translate to local.
    global_ids = short_ids(all_rows)
    to_local = {
        gid: path_to_local[row["track_id"]]
        for gid, row in global_ids.items()
        if row["track_id"] in path_to_local
    }
    local_constraints = {
        "adjacent": [[to_local[i] for i in pair if i in to_local] for pair in constraints.get("adjacent") or []],
        "adjacent_ordered": constraints.get("adjacent_ordered"),
        "regions": [
            {"ids": [to_local[i] for i in r.get("ids") or [] if i in to_local], "where": r.get("where")}
            for r in constraints.get("regions") or []
        ],
    }
    opener = to_local.get(constraints.get("opener_id") or "")
    if opener and proposal_short[0] != opener:
        return ordered_rows, [f"{provider} review rejected: it moved the requested opener"]
    closer = to_local.get(constraints.get("closer_id") or "")
    if closer and proposal_short[-1] != closer:
        return ordered_rows, [f"{provider} review rejected: it moved the closing song a DJ note pinned"]
    try:
        enforced, _, _ = enforce_constraints(list(proposal_short), local, local_constraints)
    except Exception as error:
        return ordered_rows, [f"{provider} review rejected: {error}"]
    if enforced != proposal_short:
        return ordered_rows, [f"{provider} review rejected: it broke a requested pairing or placement"]

    from brain.mix_optimizer import order_summary

    proposal_paths = [local[sid]["track_id"] for sid in proposal_short]
    before = order_summary(graph, current_paths)
    after = order_summary(graph, proposal_paths)
    slack = max(MIN_OBJECTIVE_SLACK, OBJECTIVE_TOLERANCE * abs(before["objective"]))
    if after["backbeat_blind"] > before["backbeat_blind"]:
        return ordered_rows, [f"{provider} review rejected: it added a blend where neither snare is verified"]
    if after["backbeat_unverified"] > before["backbeat_unverified"] + MAX_EXTRA_UNVERIFIED:
        return ordered_rows, [f"{provider} review rejected: too many more unverified backbeat blends"]
    if after["objective"] < before["objective"] - slack:
        return ordered_rows, [
            f"{provider} review rejected: blend quality fell too far "
            f"({before['objective']:.2f} → {after['objective']:.2f})"
        ]
    by_path = {row["track_id"]: row for row in ordered_rows}
    notes = [f"{provider} review accepted (blend {before['mean_score']:.2f} → {after['mean_score']:.2f})"]
    notes.extend(f"{provider}: {n}" for n in model_notes)
    return [by_path[p] for p in proposal_paths], notes


__all__ = ["build_refine_prompt", "refine_order", "parse_constraints"]
