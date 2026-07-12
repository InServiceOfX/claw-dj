"""Turn a free-text mix brief into a track order for the plan builder.

Profile knobs (smooth / no tricks / longer blends) still live in
`mix_profiles.apply_brief`. This module handles *order* intent:

  "mix Parce Que Tu Crois next to What's The Difference in the first half"
  "only these three: …"
  "start with Regulate, put the Aznavour/Dre pair mid-set"

Engines (same plumbing as Ask the DJ brain):
  nemoclaw — hermes / Nemotron via OpenAI-compatible API
  h-agent  — H Company planning-only task
  none     — skip the agent; keep the finalized playlist order

The agent returns structured constraints (adjacent pairs, regions, optional
subset). We then reorder deterministically with the mix-graph greedy tour
plus forced adjacencies — the agent never invents tracks or MIDI.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from brain.library import Energy, Track
from brain.playlist import normalize

REGION_SLICES = {
    "early": (0.0, 0.33),
    "first_half": (0.0, 0.5),
    "middle": (0.33, 0.67),
    "second_half": (0.5, 1.0),
    "late": (0.67, 1.0),
    "anywhere": (0.0, 1.0),
}


def short_ids(rows: list[dict]) -> dict[str, dict]:
    return {f"t{i:03d}": row for i, row in enumerate(rows)}


def row_to_track(row: dict) -> Track:
    return Track(
        track_id=row["track_id"],
        title=row.get("title") or "",
        artist=row.get("artist") or "",
        bpm=row.get("bpm"),
        key=row.get("key"),
        energy=Energy.MEDIUM,
        genre=row.get("genre"),
    )


def catalog_for_agent(rows: list[dict]) -> list[dict]:
    """Path-stripped view with mix-useful metadata only."""
    return [
        {
            "id": f"t{i:03d}",
            "artist": row.get("artist"),
            "title": row.get("title"),
            "bpm": round(float(row["bpm"]), 1) if row.get("bpm") else None,
            "key": row.get("key"),
        }
        for i, row in enumerate(rows)
    ]


def build_order_prompt(rows: list[dict], brief: str) -> str:
    catalog = catalog_for_agent(rows)
    return f"""You are the Brain of claw-dj, planning a continuous DJ mix for Mixxx.

This is planning-only: do not click, type, open apps, or invent songs.
You are given ONLY tracks already in the finalized playlist. Use their short ids.

User mix brief:
{brief}

Your job: turn the brief into ORDER CONSTRAINTS so the local mix-graph can
build a full set. Honor requests like:
- force two songs adjacent ("next to", "into", "blend X with Y")
- place a pair/song early / first half / middle / second half / late
- use only a few named songs (a short showcase mix)
- prefer a specific opener

Respond with EXACTLY one JSON object (no markdown fences) of this shape:
{{
  "use_only": null,
  "opener_id": null,
  "adjacent": [["t012", "t034"]],
  "adjacent_ordered": false,
  "regions": [{{"ids": ["t012", "t034"], "where": "first_half"}}],
  "notes": ["short human-readable note of what you enforced"]
}}

Rules:
- Ids must be from the catalog below. Never invent ids or titles.
- "use_only": null means keep the full set; or a JSON array of short ids
  when the user wants only a few songs mixed (at least 2).
- "adjacent": pairs that must be neighbors. Order in the pair is free unless
  adjacent_ordered is true (then first id plays before second).
- "regions.where" is one of: early, first_half, middle, second_half, late, anywhere.
- Prefer matching by title (and artist if given). Partial title matches are OK
  when unambiguous (e.g. "Parce Que tu Crois", "What's the Difference").
- If the brief is only about feel (smooth, no tricks) with no order asks,
  return empty adjacent/regions and notes saying so.
- Cover every constraint the user stated in notes[].

Catalog ({len(catalog)} tracks):
{json.dumps(catalog, indent=1)}
"""


def parse_constraints(text: str, allowed: set[str]) -> dict:
    """Extract the first usable constraints object from an agent reply."""
    candidates: list[str] = []
    stripped = text.strip()
    # fenced ```json ... ```
    for block in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE):
        candidates.append(block)
    # raw objects (greedy enough for one top-level object)
    if stripped.startswith("{"):
        candidates.append(stripped)
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL):
        candidates.append(match.group(0))

    last_error: Exception | None = None
    for raw in candidates:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            last_error = error
            continue
        if not isinstance(value, dict):
            continue
        return _normalize_constraints(value, allowed)
    raise ValueError(
        f"agent returned no usable constraints JSON: {(text or '')[:500]}"
        + (f" ({last_error})" if last_error else "")
    )


def _normalize_constraints(value: dict, allowed: set[str]) -> dict:
    def clean_id(item: object) -> str | None:
        if isinstance(item, str) and item in allowed:
            return item
        return None

    use_only_raw = value.get("use_only")
    use_only: list[str] | None = None
    if isinstance(use_only_raw, list):
        use_only = [i for i in (clean_id(x) for x in use_only_raw) if i]
        if len(use_only) < 2:
            use_only = None

    opener = clean_id(value.get("opener_id"))

    adjacent: list[tuple[str, str]] = []
    for pair in value.get("adjacent") or []:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        a, b = clean_id(pair[0]), clean_id(pair[1])
        if a and b and a != b:
            adjacent.append((a, b))

    regions: list[dict] = []
    for region in value.get("regions") or []:
        if not isinstance(region, dict):
            continue
        ids = [i for i in (clean_id(x) for x in (region.get("ids") or [])) if i]
        where = str(region.get("where") or "anywhere").casefold().replace(" ", "_")
        if where not in REGION_SLICES:
            # map loose synonyms
            if "first" in where or "early" in where and "half" in where:
                where = "first_half"
            elif "second" in where or "later half" in where:
                where = "second_half"
            elif "mid" in where:
                where = "middle"
            elif "early" in where:
                where = "early"
            elif "late" in where:
                where = "late"
            else:
                where = "anywhere"
        if ids:
            regions.append({"ids": ids, "where": where})

    notes = [str(n) for n in (value.get("notes") or []) if n]
    return {
        "use_only": use_only,
        "opener_id": opener,
        "adjacent": adjacent,
        "adjacent_ordered": bool(value.get("adjacent_ordered")),
        "regions": regions,
        "notes": notes,
    }


def force_adjacent(
    order: list[str],
    left: str,
    right: str,
    *,
    ordered: bool = False,
) -> list[str]:
    """Make left and right neighbors. Prefer keeping the earlier index as anchor."""
    if left not in order or right not in order or left == right:
        return order
    ids = [item for item in order if item not in {left, right}]
    i_left = order.index(left)
    i_right = order.index(right)
    anchor_index = min(i_left, i_right)
    # Clamp into the shortened list.
    anchor_index = min(anchor_index, len(ids))
    if ordered:
        pair = [left, right]
    else:
        # Keep original relative order when unordered — less surprising.
        pair = [left, right] if i_left < i_right else [right, left]
    return ids[:anchor_index] + pair + ids[anchor_index:]


def place_block_in_region(order: list[str], block_ids: list[str], where: str) -> list[str]:
    """Move a set of ids (kept contiguous if already adjacent) into a region window."""
    wanted = [i for i in block_ids if i in order]
    if not wanted:
        return order
    # Pull wanted out, preserving their relative order in `order`.
    block = [i for i in order if i in set(wanted)]
    rest = [i for i in order if i not in set(wanted)]
    n = len(rest) + len(block)
    lo_frac, hi_frac = REGION_SLICES.get(where, (0.0, 1.0))
    lo = int(n * lo_frac)
    hi = max(lo + 1, int(n * hi_frac))
    # Prefer the middle of the window.
    insert_at = min(len(rest), max(0, (lo + hi) // 2 - len(block) // 2))
    # Keep insert_at inside [lo, hi) when possible.
    if insert_at < lo:
        insert_at = min(lo, len(rest))
    if insert_at + len(block) > hi and hi <= len(rest) + len(block):
        insert_at = max(0, min(len(rest), hi - len(block)))
    return rest[:insert_at] + block + rest[insert_at:]


def apply_constraints(rows: list[dict], constraints: dict) -> tuple[list[dict], list[str]]:
    """Deterministic reorder: greedy tour, then force adjacency + region windows."""
    from brain.mix_graph import greedy_mix_order, lineage_pairs, load_chroma_pairs, load_lineage

    id_map = short_ids(rows)
    notes = list(constraints.get("notes") or [])

    pool_ids: list[str]
    if constraints.get("use_only"):
        pool_ids = [i for i in constraints["use_only"] if i in id_map]
        if len(pool_ids) < 2:
            raise ValueError("use_only resolved to fewer than 2 known tracks")
        notes.append(f"subset mix: {len(pool_ids)} tracks from brief")
    else:
        pool_ids = list(id_map.keys())

    pool_rows = [id_map[i] for i in pool_ids]
    tracks = [row_to_track(row) for row in pool_rows]
    short_for_path = {row["track_id"]: sid for sid, row in zip(pool_ids, pool_rows)}
    path_for_short = {sid: row["track_id"] for sid, row in zip(pool_ids, pool_rows)}

    lineage = lineage_pairs(tracks, load_lineage())
    chroma = load_chroma_pairs()
    opener_short = constraints.get("opener_id")
    start = None
    if opener_short and opener_short in path_for_short:
        start_path = path_for_short[opener_short]
        start = next(t for t in tracks if t.track_id == start_path)
        notes.append(f"opener forced: {start.artist} — {start.title}")

    ordered_tracks = greedy_mix_order(tracks, start=start, lineage=lineage, chroma=chroma)
    order = [short_for_path[t.track_id] for t in ordered_tracks]

    ordered_flag = bool(constraints.get("adjacent_ordered"))
    for left, right in constraints.get("adjacent") or []:
        if left in order and right in order:
            order = force_adjacent(order, left, right, ordered=ordered_flag)
            a, b = id_map[left], id_map[right]
            notes.append(f"adjacent: {a.get('artist')} — {a.get('title')} ↔ {b.get('artist')} — {b.get('title')}")

    for region in constraints.get("regions") or []:
        ids = [i for i in region.get("ids") or [] if i in order]
        where = region.get("where") or "anywhere"
        if ids and where != "anywhere":
            order = place_block_in_region(order, ids, where)
            labels = [f"{id_map[i].get('title')}" for i in ids]
            notes.append(f"region {where}: {', '.join(labels)}")

    result = [id_map[i] for i in order]
    # De-dupe notes while preserving order.
    seen: set[str] = set()
    uniq_notes = []
    for note in notes:
        if note not in seen:
            seen.add(note)
            uniq_notes.append(note)
    return result, uniq_notes


def order_from_brief(
    rows: list[dict],
    brief: str,
    *,
    engine: str = "nemoclaw",
    ask: Callable[[str], str] | None = None,
) -> tuple[list[dict], list[str], dict]:
    """Resolve brief → (ordered rows, notes, constraints).

    `ask` is injectable for tests. When engine is none/off or brief empty,
    returns the input rows unchanged.
    """
    text = (brief or "").strip()
    if not text or engine in (None, "", "none", "off", "profile-only"):
        return rows, [], {"use_only": None, "adjacent": [], "regions": [], "notes": ["playlist order kept (no order engine)"]}

    allowed = set(short_ids(rows))
    prompt = build_order_prompt(rows, text)
    if ask is None:
        from brain.pick_candidates import ask_h_agent, ask_nemoclaw

        if engine == "nemoclaw":
            ask = ask_nemoclaw
        elif engine == "h-agent":
            ask = ask_h_agent
        else:
            raise ValueError(f"unknown order engine {engine!r}; use nemoclaw, h-agent, or none")

    answer = ask(prompt)
    constraints = parse_constraints(answer, allowed)
    ordered, notes = apply_constraints(rows, constraints)
    return ordered, notes, constraints
