"""Curate a mixable playlist from songs available on this machine.

Pipeline (this is the hackathon answer to "can H agents curate a playlist?"):

1. **Respect the user set** — anything already enabled in
   `playlist_selection.json` is kept unless `--replace-user` is set.
2. **Large list = researched hits per folder artist**, matched only against
   the local crate (Wikipedia / chart seed files under `playlist_seeds/`).
   No inventing deep cuts the library doesn't have.
3. **Refine for mix opportunities** — BPM (rate-adjust tolerant), key/Camelot,
   sample lineage, light title-token hooks. Order with a greedy mix tour, then
   optionally let the H Company agent re-order for story/energy.
4. **Waveform** is *not* used on the large list (too heavy; Mixxx beatgrids
   already cover beatmatch once analyzed). See `brain/mix_graph.py`.

Subjective asks (genre, region, era, mood) are **per-playlist input**, not
rules: pass them with `--brief` (feeds the h-agent/offline planners) and/or
`--seed` (narrows which researched-hit pool is drawn from). The default brief
is neutral — it asks only for good mixing, no genre/region slant.

Usage:
    # rebuild from researched hits + keep current user selection, mix-order
    uv run python -m brain.curate_playlist --mode hits --planner mix-graph

    # H agent only reorders the hit pool (planning-only, no GUI)
    uv run python -m brain.curate_playlist --mode hits --planner h-agent

    # re-order the CURRENT enabled set only (what you like in the UI)
    uv run python -m brain.curate_playlist --mode selection --planner h-agent

    # per-playlist subjective ask, this run only
    uv run python -m brain.curate_playlist --mode hits --planner h-agent \
        --brief "West Coast hip-hop into classic R&B; end on slow jams"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from brain.library import Track, load_crate
from brain.mix_graph import (
    greedy_mix_order,
    lineage_pairs,
    load_lineage,
    pair_score,
    transition_report,
)
from brain.playlist import (
    DEFAULT_PLAYLIST_JSON,
    DEFAULT_PLAYLIST_M3U,
    DEFAULT_SEED,
    DEFAULT_SELECTION,
    export_playlist,
    load_seed,
    load_selection,
    match_seed,
    save_selection,
)

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_PICKS = DATA_DIR / "agent_picks.json"
EXTRA_HITS = Path(__file__).parent / "playlist_seeds" / "extra_folder_hits.json"
DEFAULT_REPORT = DATA_DIR / "mix_transitions.json"

# Objective mixing goals only — subjective asks (genre, region, era, mood)
# belong in a per-playlist --brief, never hardcoded here.
NEUTRAL_BRIEF = (
    "maximize seamless blends and sample call-backs; "
    "dancefloor energy that builds then cools"
)


def all_hit_seeds(paths: list[Path] | None = None) -> list[dict]:
    if paths:
        seeds: list[dict] = []
        for path in paths:
            seeds.extend(load_seed(path))
    else:
        seeds = list(load_seed(DEFAULT_SEED))
        if EXTRA_HITS.exists():
            seeds.extend(json.loads(EXTRA_HITS.read_text()))
    # de-dupe by normalized artist|title
    seen: set[str] = set()
    unique: list[dict] = []
    for item in seeds:
        key = f"{item['artist'].casefold()}|{item['title'].casefold()}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def match_hits(tracks: list[Track], seed_paths: list[Path] | None = None) -> list[Track]:
    matches = match_seed(tracks, all_hit_seeds(seed_paths))
    found = [m.track for m in matches if m.track is not None]
    # stable unique by path
    out: list[Track] = []
    seen: set[str] = set()
    for track in found:
        if track.track_id in seen:
            continue
        seen.add(track.track_id)
        out.append(track)
    return out


def merge_keep_user(hits: list[Track], user_ids: list[str], crate: list[Track]) -> list[Track]:
    by_id = {track.track_id: track for track in crate}
    ordered: list[Track] = []
    seen: set[str] = set()
    for track_id in user_ids:
        track = by_id.get(track_id)
        if track and track.track_id not in seen:
            ordered.append(track)
            seen.add(track.track_id)
    for track in hits:
        if track.track_id not in seen:
            ordered.append(track)
            seen.add(track.track_id)
    return ordered


def parse_agent_ids(answer: object, allowed: set[str]) -> list[str]:
    text = json.dumps(answer) if isinstance(answer, (dict, list)) else str(answer)
    candidates = re.findall(r"\[[^\[\]]*\]", text, flags=re.DOTALL)
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, list) or not value:
            continue
        ids = [item for item in value if isinstance(item, str) and item in allowed]
        uniq: list[str] = []
        for item in ids:
            if item not in uniq:
                uniq.append(item)
        # require covering most of the set (agent may drop a couple)
        if len(uniq) >= max(3, int(0.7 * len(allowed))):
            # append any missing allowed ids at the end so nothing is dropped
            for item in allowed:
                if item not in uniq:
                    uniq.append(item)
            return uniq
    raise ValueError(f"agent did not return a usable id array: {text[:700]}")


async def order_with_h_agent(
    tracks: list[Track],
    brief: str,
    *,
    lineage: set[tuple[str, str]] | None,
) -> list[Track]:
    """H agent reorders an already-chosen available set for mix storytelling."""
    from brain.agent import Brain

    options = []
    for index, track in enumerate(tracks):
        neighbors = []
        for other in tracks:
            if other.track_id == track.track_id:
                continue
            edge = pair_score(track, other, lineage=lineage)
            if edge.score >= 0.7:
                neighbors.append(
                    {
                        "id": f"t{tracks.index(other):03d}",
                        "score": round(edge.score, 2),
                        "why": edge.reasons[:2],
                    }
                )
        neighbors.sort(key=lambda row: -row["score"])
        options.append(
            {
                "id": f"t{index:03d}",
                "artist": track.artist,
                "title": track.title,
                "bpm": track.bpm,
                "key": track.key,
                "strong_mix_into": neighbors[:5],
            }
        )

    prompt = f"""You are the Brain of claw-dj, an autonomous hip-hop/R&B DJ for Mixxx.

This is planning-only: do not click, type, open apps, or invent songs.

You are given ONLY tracks that already exist on the user's machine and are
already selected as researched hits / user picks. Your job is to ORDER them
into a set that creates opportunities to use Mixxx like an instrument:
beatmatched blends, camelot-friendly moves, sample-lineage call-backs, and
energy flow.

Brief: {brief}

Rules:
- Return exactly one JSON array of the short ids covering EVERY track once.
- Prefer sequences where consecutive tracks have high strong_mix_into scores.
- Cluster sample/lineage pairs when present.
- Prefer gradual BPM moves (rate adjust is OK within ~8%; half-time OK).
- Prefer same or relative/neighbor keys when BPM is close.
- Do not drop tracks; do not add unknown titles.

Tracks:
{json.dumps(options, indent=2)}
"""
    async with Brain() as brain:
        answer = await brain._run_task(prompt, max_steps=4, max_time_s=150)
    allowed = {f"t{i:03d}" for i in range(len(tracks))}
    ids = parse_agent_ids(answer, allowed)
    by_id = {f"t{i:03d}": track for i, track in enumerate(tracks)}
    return [by_id[item] for item in ids if item in by_id]


def load_picks_file(path: Path) -> list[dict | str]:
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("picks", "track_ids", "ids", "tracks", "order"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
    raise ValueError(f"unrecognized picks format in {path}")


def resolve_order(tracks: list[Track], picks: list[dict | str]) -> list[Track]:
    by_path = {track.track_id: track for track in tracks}
    by_short = {f"t{i:03d}": track for i, track in enumerate(tracks)}
    ordered: list[Track] = []
    seen: set[str] = set()
    for pick in picks:
        track = None
        if isinstance(pick, str):
            track = by_path.get(pick) or by_short.get(pick)
        elif isinstance(pick, dict):
            if pick.get("track_id") in by_path:
                track = by_path[pick["track_id"]]
            elif pick.get("id") in by_short:
                track = by_short[str(pick["id"])]
        if track and track.track_id not in seen:
            ordered.append(track)
            seen.add(track.track_id)
    for track in tracks:
        if track.track_id not in seen:
            ordered.append(track)
            seen.add(track.track_id)
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("hits", "selection"),
        default="hits",
        help="hits = researched top songs matched to crate; selection = current UI set only",
    )
    parser.add_argument(
        "--planner",
        choices=("mix-graph", "h-agent", "offline", "none"),
        default="mix-graph",
        help="mix-graph = deterministic BPM/key/lineage order; h-agent = H Company reorder",
    )
    parser.add_argument(
        "--brief",
        default=NEUTRAL_BRIEF,
        help=(
            "per-playlist subjective ask, in your own words (e.g. 'West Coast "
            "hip-hop into classic R&B', 'slow-jam 90s R&B only', 'keep it "
            "grimy East Coast'). Default applies no genre/region/era slant."
        ),
    )
    parser.add_argument(
        "--seed",
        type=Path,
        action="append",
        default=None,
        help=(
            "seed file(s) under brain/playlist_seeds/ to draw researched hits "
            "from (repeatable). Default: all standard hit seeds."
        ),
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="optional cap after ordering (0 = keep full large list)",
    )
    parser.add_argument(
        "--replace-user",
        action="store_true",
        help="do not merge/preserve the current playlist_selection.json picks",
    )
    parser.add_argument("--from-picks", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    crate = load_crate()
    if not crate:
        raise SystemExit("crate empty — run brain.scan_library on HipHop + RnB roots first")

    user_ids = [] if args.replace_user else load_selection()
    if args.mode == "selection":
        by_id = {track.track_id: track for track in crate}
        pool = [by_id[i] for i in user_ids if i in by_id]
        if not pool:
            raise SystemExit("no current selection — enable tracks in playlist_editor or use --mode hits")
        print(f"mode=selection: {len(pool)} user-enabled tracks")
    else:
        hits = match_hits(crate, args.seed)
        unmatched = len(all_hit_seeds(args.seed)) - len(hits)
        print(f"mode=hits: matched {len(hits)} researched hits ({unmatched} seed rows unmatched)")
        pool = hits if args.replace_user else merge_keep_user(hits, user_ids, crate)
        print(f"pool after merging user selection: {len(pool)} tracks "
              f"(user kept {sum(1 for t in pool if t.track_id in set(user_ids))})")

    lineage = lineage_pairs(pool, load_lineage())
    print(f"sample/lineage edges in pool: {len(lineage)}")

    if args.planner == "none":
        ordered = pool
    elif args.planner == "mix-graph":
        start = pool[0] if pool else None
        ordered = greedy_mix_order(pool, start=start, lineage=lineage)
        print("planner=mix-graph: greedy BPM/key/lineage tour")
    elif args.planner == "h-agent":
        # pre-seed with mix-graph so the agent starts from a strong order
        seed_order = greedy_mix_order(pool, start=pool[0] if pool else None, lineage=lineage)
        print(f"planner=h-agent: asking H Company agent to reorder {len(seed_order)} tracks…")
        ordered = asyncio.run(
            order_with_h_agent(seed_order, args.brief, lineage=lineage)
        )
    else:
        picks_path = args.from_picks or DEFAULT_PICKS
        if not picks_path.exists():
            template = {
                "brief": args.brief,
                "note": "Return an ordered list of short ids from candidates only.",
                "candidates": [
                    {
                        "id": f"t{i:03d}",
                        "artist": t.artist,
                        "title": t.title,
                        "bpm": t.bpm,
                        "key": t.key,
                    }
                    for i, t in enumerate(pool)
                ],
                "picks": [f"t{i:03d}" for i in range(len(pool))],
            }
            picks_path.parent.mkdir(parents=True, exist_ok=True)
            picks_path.write_text(json.dumps(template, indent=2) + "\n")
            raise SystemExit(f"wrote picks template -> {picks_path}; edit and re-run")
        ordered = resolve_order(pool, load_picks_file(picks_path))
        print(f"planner=offline: resolved order from {picks_path}")

    if args.count and args.count > 0:
        ordered = ordered[: args.count]

    report = transition_report(ordered, lineage=lineage)
    avg = sum(row["score"] for row in report) / len(report) if report else 0.0
    print(f"ordered {len(ordered)} tracks; mean transition score {avg:.2f}")
    for index, track in enumerate(ordered[:12], start=1):
        tag = f"{track.bpm:.1f}/{track.key}" if track.bpm else "unanalyzed"
        print(f"  {index:02d}. {track.artist} — {track.title}  [{tag}]")
    if len(ordered) > 12:
        print(f"  … +{len(ordered) - 12} more")
    for row in report[:5]:
        print(f"  mix {row['score']:.2f}: {row['from']} → {row['to']} ({'; '.join(row['reasons'][:2])})")

    if args.dry_run:
        return

    ids = [track.track_id for track in ordered]
    save_selection(ids, DEFAULT_SELECTION)
    export_playlist(crate, ids, json_path=DEFAULT_PLAYLIST_JSON, m3u_path=DEFAULT_PLAYLIST_M3U)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {"brief": args.brief, "mean_score": avg, "transitions": report}, indent=2
        )
        + "\n"
    )
    print(f"wrote {DEFAULT_SELECTION}")
    print(f"wrote {DEFAULT_PLAYLIST_JSON}")
    print(f"wrote {DEFAULT_PLAYLIST_M3U}")
    print(f"wrote {args.report}")
    print("reload http://127.0.0.1:8787 (restart playlist_editor if it was started earlier)")


if __name__ == "__main__":
    main()
