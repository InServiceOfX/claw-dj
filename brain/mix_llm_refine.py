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
from pathlib import Path
from typing import Callable

from brain.mix_order_brief import build_graph, enforce_constraints, parse_constraints, short_ids

OBJECTIVE_TOLERANCE = 0.03  # fraction of the optimizer objective a story choice may cost
MIN_OBJECTIVE_SLACK = 0.5
MAX_EXTRA_UNVERIFIED = 1


PROMPT_PATH = Path(__file__).resolve().parent / "llm_prompts" / "build_review.md"
TOP_NEXT = 5


def _mmss(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


def vocal_outline(segments: list[dict] | None) -> str | None:
    """Compact verse/chorus outline from a lyric timeline, or None."""
    items = []
    for seg in segments or []:
        try:
            kind, start, end = str(seg.get("kind") or ""), float(seg["start"]), float(seg["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if kind:
            items.append((kind, start, end))
    if not items:
        return None
    parts = [f"{kind} {_mmss(start)}-{_mmss(end)}" for kind, start, end in items[:12]]
    if len(items) > 12:
        parts.append(f"+{len(items) - 12} more")
    verses = [end for kind, _, end in items if kind.casefold() == "verse"]
    tail = f"; last verse ends {_mmss(max(verses))}" if verses else ""
    return ", ".join(parts) + tail


def _segments_lookup() -> dict[str, list[dict]]:
    try:
        from brain.build_mix_plan import load_lyric_segment_lookup

        return load_lyric_segment_lookup()
    except Exception:  # no index on this machine / in tests
        return {}


def mix_sheet(rows: list[dict], graph, *, segments: dict[str, list[dict]] | None = None, top_next: int = TOP_NEXT) -> dict:
    """The distilled, pre-scored input the model reviews (Grokicad-style)."""
    ids = short_ids(rows)
    path_to_short = {row["track_id"]: sid for sid, row in ids.items()}
    segments = _segments_lookup() if segments is None else segments
    songs = []
    for sid, row in ids.items():
        i = graph.index[row["track_id"]]
        ranked = sorted(
            (j for j in range(len(graph.tracks)) if j != i),
            key=lambda j: (-graph.edges[i][j].score, graph.tracks[j].track_id),
        )[:top_next]
        best_next = []
        for j in ranked:
            edge = graph.edges[i][j]
            label = "blind" if graph.weak[i] and graph.weak[j] else (
                "one_side_unverified" if graph.weak[i] or graph.weak[j] else "verifiable"
            )
            best_next.append([path_to_short[graph.tracks[j].track_id], round(edge.score, 2), label, list(edge.reasons)[:2]])
        songs.append({
            "id": sid,
            "artist": row.get("artist"),
            "title": row.get("title"),
            "genre": row.get("genre"),
            "bpm": round(float(row["bpm"]), 1) if row.get("bpm") else None,
            "key": row.get("key"),
            "minutes": round(float(row["duration_seconds"]) / 60, 1) if row.get("duration_seconds") else None,
            "snare_read": "weak" if graph.weak[i] else "ok",
            "vocals": vocal_outline(segments.get(row["track_id"])),
            "dj_notes": (row.get("dj_notes") or "") or None,
            "best_next": best_next,
        })
    current = [
        [path_to_short[e.from_id], path_to_short[e.to_id], e.score, e.backbeat]
        for e in graph.report([row["track_id"] for row in rows])
    ]
    return {"songs": songs, "current_order": current}


def build_refine_prompt(rows: list[dict], graph, brief: str, *, mix_context: dict | None = None,
                        segments: dict[str, list[dict]] | None = None) -> str:
    sheet = mix_sheet(rows, graph, segments=segments)
    # One song / one blend per line: compact but still readable in the audit file.
    songs = "\n".join(json.dumps(s, ensure_ascii=False) for s in sheet["songs"])
    current = "\n".join(json.dumps(e, ensure_ascii=False) for e in sheet["current_order"])
    return (
        PROMPT_PATH.read_text()
        + "\n\n## This mix\n\n"
        + f"mix_feel: {json.dumps(mix_context or {}, ensure_ascii=False)}\n"
        + f"User brief (may be empty): {brief or '(none)'}\n\n"
        + f"songs ({len(sheet['songs'])}):\n{songs}\n\n"
        + "current_order ([from, to, score, backbeat]):\n"
        + current + "\n"
    )


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
