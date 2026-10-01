"""Turn a free-text mix brief into a track order for the plan builder.

Profile knobs (smooth / no tricks / longer blends) still live in
`mix_profiles.apply_brief`. This module handles *order* intent:

  "mix Parce Que Tu Crois next to What's The Difference in the first half"
  "only these three: …"
  "start with Regulate, put the Aznavour/Dre pair mid-set"

Engines: "none" (graph optimizer only) or any brain.llm_providers provider
(Claude / Codex / Grok via signed-in CLI or API key, or llama-server).

The model returns structured constraints (adjacent pairs, regions, optional
subset). We then order the whole set with brain.mix_optimizer plus forced
adjacencies — the model never invents tracks or MIDI.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from brain.library import Energy, Track
from brain.playlist import normalize

# Remix Report ep.12 (hu_Y3dt2JWU): a party-break/mashup that teases another
# song in the same set must be followed by that original, unless the
# original already played.
_MASHUP_HINT = re.compile(
    r"\b(remix|bootleg|mashup|blend|rework|flip|break)\b", re.I
)
_VERSION_STOP = {
    "the",
    "a",
    "an",
    "and",
    "feat",
    "ft",
    "featuring",
    "with",
    "remix",
    "mix",
    "bootleg",
    "mashup",
    "blend",
    "rework",
    "flip",
    "break",
    "radio",
    "edit",
    "version",
    "album",
    "single",
    "instrumental",
    "acapella",
    "acappella",
    "dirty",
    "clean",
    "explicit",
    "bonus",
    "track",
}

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

    referenced: list[str] = []
    use_only_raw = value.get("use_only")
    if isinstance(use_only_raw, list):
        referenced.extend(item for item in use_only_raw if isinstance(item, str))
        if len(referenced) != len(set(referenced)):
            raise ValueError("agent use_only contains duplicate track ids")
    if isinstance(value.get("opener_id"), str):
        referenced.append(value["opener_id"])
    for pair in value.get("adjacent") or []:
        if isinstance(pair, (list, tuple)):
            referenced.extend(item for item in pair[:2] if isinstance(item, str))
    for region in value.get("regions") or []:
        if isinstance(region, dict):
            referenced.extend(
                item for item in (region.get("ids") or []) if isinstance(item, str)
            )
    unknown = sorted(set(referenced) - allowed)
    if unknown:
        raise ValueError(f"agent constraints contain unknown track ids: {unknown}")

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


def core_title(title: str) -> str:
    """Title minus parentheticals and version/remix words."""
    stripped = re.sub(r"\([^)]*\)", " ", title or "")
    stripped = re.sub(r"\[[^\]]*\]", " ", stripped)
    words = [
        token
        for token in normalize(stripped).split()
        if token and token not in _VERSION_STOP
    ]
    return " ".join(words)


def mashup_payoff_pairs(rows: list[dict]) -> list[tuple[str, str]]:
    """(remix_track_id, original_track_id) when a remix teases another song.

    Same-song versions (P.I.M.P. Remix vs P.I.M.P., In Da Club Instrumental
    vs In Da Club) are not payoffs. A title like "Show Me Love In Da Club
    (Hollaboyz Remix)" vs "In Da Club" is.
    """
    pairs: list[tuple[str, str]] = []
    for remix in rows:
        title = remix.get("title") or ""
        if not _MASHUP_HINT.search(title):
            continue
        remix_core = core_title(title)
        remix_artist_tokens = set(normalize(remix.get("artist") or "").split())
        best_id = None
        best_len = 0
        for original in rows:
            if original.get("track_id") == remix.get("track_id"):
                continue
            original_core = core_title(original.get("title") or "")
            if len(original_core) < 6:
                continue
            if original_core == remix_core:
                continue
            haystack = f"{remix_core} {normalize(title)}"
            if original_core not in haystack:
                continue
            leftover = set(remix_core.split()) - set(original_core.split())
            original_artist_tokens = set(
                normalize(original.get("artist") or "").split()
            )
            if leftover and leftover <= (_VERSION_STOP | remix_artist_tokens | original_artist_tokens):
                continue
            if leftover <= _VERSION_STOP:
                continue
            if len(original_core) > best_len:
                best_id = original["track_id"]
                best_len = len(original_core)
        if best_id:
            pairs.append((remix["track_id"], best_id))
    return pairs


def _snare_confidence() -> dict[str, float]:
    """Cached snare-parity confidence per track; empty when no index exists."""
    try:
        from brain.build_mix_plan import load_beat_phase_lookup

        return {tid: float(row.get("confidence") or 0.0) for tid, row in load_beat_phase_lookup().items()}
    except Exception:
        return {}


def build_graph(rows: list[dict], snare_confidence: dict[str, float] | None = None):
    from brain.mix_graph import lineage_pairs, load_chroma_pairs, load_lineage
    from brain.mix_optimizer import MixGraph
    from brain.onset_analysis import SNARE_CONFIDENCE_GATE

    tracks = [row_to_track(row) for row in rows]
    return MixGraph(
        tracks,
        lineage=lineage_pairs(tracks, load_lineage()),
        chroma=load_chroma_pairs(),
        snare_confidence=_snare_confidence() if snare_confidence is None else snare_confidence,
        gate=SNARE_CONFIDENCE_GATE,
    )


def enforce_constraints(
    order: list[str], id_map: dict[str, dict], constraints: dict
) -> tuple[list[str], list[str], list[list[str]]]:
    """Apply region windows, adjacency groups and mashup payoffs to an order
    of short ids. Returns (order, notes, applied adjacency groups)."""
    from brain.order_constraints import assert_intact, merge_groups

    notes: list[str] = []
    short_for_path = {row["track_id"]: sid for sid, row in id_map.items()}
    for region in constraints.get("regions") or []:
        ids = [i for i in region.get("ids") or [] if i in order]
        where = region.get("where") or "anywhere"
        if ids and where != "anywhere":
            order = place_block_in_region(order, ids, where)
            labels = [f"{id_map[i].get('title')}" for i in ids]
            notes.append(f"region {where}: {', '.join(labels)}")

    # Coalesce chained pairs before insertion. Repeated pair insertion can
    # make A-B, then B-C by pulling B out and silently stranding A.
    ordered_flag = bool(constraints.get("adjacent_ordered"))
    groups = merge_groups(list(constraints.get("adjacent") or []))
    applied_groups = []
    for group in groups:
        present = [item for item in group if item in order]
        if len(present) < 2:
            continue
        anchor = min(order.index(item) for item in present)
        block = present if ordered_flag else [item for item in order if item in set(present)]
        order = [item for item in order if item not in set(present)]
        order[anchor:anchor] = block
        applied_groups.append(block)
        labels = [f"{id_map[item].get('artist')} — {id_map[item].get('title')}" for item in block]
        notes.append(f"adjacent group: {' ↔ '.join(labels)}")
    claimed = {item for group in applied_groups for item in group}
    pool_rows = [id_map[i] for i in order]
    for remix_path, original_path in mashup_payoff_pairs(pool_rows):
        remix_s = short_for_path.get(remix_path)
        original_s = short_for_path.get(original_path)
        if remix_s not in order or original_s not in order:
            continue
        if remix_s in claimed or original_s in claimed:
            continue
        remix_title = id_map[remix_s].get("title")
        original_title = id_map[original_s].get("title")
        if order.index(original_s) < order.index(remix_s):
            notes.append(
                f"payoff already before: {original_title} before {remix_title}"
            )
            continue
        order = force_adjacent(order, remix_s, original_s, ordered=True)
        notes.append(
            f"mashup payoff: {remix_title} → {original_title}"
        )
    assert_intact(order, applied_groups)
    return order, notes, applied_groups


def apply_constraints(
    rows: list[dict],
    constraints: dict,
    *,
    snare_confidence: dict[str, float] | None = None,
) -> tuple[list[dict], list[str]]:
    """Deterministic reorder: whole-set optimizer, then force adjacency + region windows."""
    from brain.mix_optimizer import optimize_order, order_summary

    track_ids = [row.get("track_id") for row in rows]
    if len(track_ids) != len(set(track_ids)):
        raise ValueError("candidate pool contains duplicate track ids")
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
    short_for_path = {row["track_id"]: sid for sid, row in zip(pool_ids, pool_rows)}
    path_for_short = {sid: row["track_id"] for sid, row in zip(pool_ids, pool_rows)}

    opener_short = constraints.get("opener_id")
    opener_path = path_for_short.get(opener_short) if opener_short else None
    if opener_path:
        notes.append(f"opener forced: {id_map[opener_short].get('artist')} — {id_map[opener_short].get('title')}")
    closer_short = constraints.get("closer_id")
    closer_path = path_for_short.get(closer_short) if closer_short and closer_short != opener_short else None
    if closer_path:
        notes.append(f"closer forced: {id_map[closer_short].get('artist')} — {id_map[closer_short].get('title')}")
    body_rows = [row for row in pool_rows if row["track_id"] != closer_path]
    graph = build_graph(pool_rows, snare_confidence)

    ordered_paths = optimize_order(build_graph(body_rows, snare_confidence), opener_id=opener_path)
    if closer_path:
        ordered_paths.append(closer_path)
    order = [short_for_path[path] for path in ordered_paths]
    order, enforce_notes, _ = enforce_constraints(order, {sid: id_map[sid] for sid in pool_ids}, constraints)
    notes.extend(enforce_notes)
    summary = order_summary(graph, [path_for_short[i] for i in order])
    notes.append(
        f"whole-set optimizer: mean blend {summary['mean_score']:.2f}, "
        f"{summary['backbeat_verifiable']} snare-verifiable / "
        f"{summary['backbeat_unverified']} unverified blends"
    )

    result = [id_map[i] for i in order]
    # De-dupe notes while preserving order.
    seen: set[str] = set()
    uniq_notes = []
    for note in notes:
        if note not in seen:
            seen.add(note)
            uniq_notes.append(note)
    return result, uniq_notes


RETIRED_ENGINES = {"nemoclaw", "h-agent"}


def apply_note_endpoints(rows: list[dict], constraints: dict) -> list[str]:
    """Honor DJ notes that only work at the ends of a mix.

    `opener_style` (e.g. juggle_intro) only fires on the first song and
    `full_track` (play to the end) only on the last, so a song carrying one
    is pinned there. A brief's explicit opener wins over a note.
    """
    from brain.build_mix_plan import track_directives

    ids = short_ids(rows)
    out: list[str] = []
    openers = [sid for sid, row in ids.items() if track_directives(row)["opener_style"]]
    closers = [sid for sid, row in ids.items() if track_directives(row)["full_track"]]
    if openers and not constraints.get("opener_id"):
        constraints["opener_id"] = openers[0]
        out.append("DJ note opener_style: pinned as opener")
        if len(openers) > 1:
            out.append(f"{len(openers) - 1} other opener_style note(s) cannot also open; first by order kept")
    if closers:
        closer = next((c for c in reversed(closers) if c != constraints.get("opener_id")), None)
        if closer:
            constraints["closer_id"] = closer
            out.append("DJ note full_track: pinned as the closing song")
    return out


def order_from_brief(
    rows: list[dict],
    brief: str,
    *,
    engine: str = "none",
    ask: Callable[[str], str] | None = None,
) -> tuple[list[dict], list[str], dict]:
    """Resolve brief → (ordered rows, notes, constraints).

    `engine` is "none" or a `brain.llm_providers` provider name. The
    whole-set optimizer always builds the order. With a provider, the model
    (1) turns a non-empty brief into constraints and (2) reviews the
    optimized order like a DJ; its reorder is kept only when it passes the
    hard rules (see brain.mix_llm_refine). `ask` is injectable for tests.
    """
    from brain import llm_providers

    text = (brief or "").strip()
    notes_prefix: list[str] = []
    if engine in RETIRED_ENGINES:
        notes_prefix.append(f"order engine {engine!r} is retired; used the graph optimizer")
        engine = "none"
    if engine in (None, "", "none", "off", "profile-only"):
        engine = "none"
    elif engine not in llm_providers.PROVIDERS:
        raise ValueError(
            f"unknown order engine {engine!r}; use none or one of {sorted(llm_providers.PROVIDERS)}"
        )
    if engine != "none" and ask is None:
        ask = lambda prompt: llm_providers.ask(engine, prompt)  # noqa: E731

    if not text or engine == "none":
        constraints = {
            "use_only": None,
            "opener_id": None,
            "adjacent": [],
            "adjacent_ordered": False,
            "regions": [],
            "notes": ["deterministic whole-set mix-quality ordering"],
        }
    else:
        constraints = parse_constraints(ask(build_order_prompt(rows, text)), set(short_ids(rows)))
    notes_prefix.extend(apply_note_endpoints(rows, constraints))
    ordered, notes = apply_constraints(rows, constraints)
    if engine != "none":
        from brain.mix_llm_refine import refine_order

        ordered, refine_notes = refine_order(ordered, constraints, rows, brief=text, ask=ask, provider=engine)
        notes.extend(refine_notes)
    return ordered, notes_prefix + notes, constraints
