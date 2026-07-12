"""Curate a playlist strictly from songs available in the local crate.

Does not analyze audio. Picks only tracks already known from
`brain.scan_library` (multi-directory metadata scan).

Planners:
  h-agent   — H Company hai-agents Brain, planning-only (no desktop clicks)
  offline   — resolve a JSON pick list (NemoClaw / Hermes / human) against the crate

Usage:
    # 1) ensure crate exists (metadata only, multi-root OK)
    uv run python -m brain.scan_library \\
        /Volumes/USB322FD/Music/RnB /Volumes/USB322FD/Music/HipHop --catalog

    # 2a) H Company agent picks from available tracks
    uv run python -m brain.curate_playlist \\
        --brief "late-night West Coast R&B into Snoop-era hip-hop, 12 tracks" \\
        --count 12 --planner h-agent

    # 2b) NemoClaw / any agent returns picks; resolve offline
    uv run python -m brain.curate_playlist \\
        --from-picks brain/data/agent_picks.json --planner offline

    # dry-run prints the ordered selection without writing playlist files
    uv run python -m brain.curate_playlist --brief "..." --count 8 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from brain.catalog import DEFAULT_CATALOG, agent_view, build_catalog, write_catalog
from brain.library import Track, load_crate
from brain.playlist import (
    DEFAULT_PLAYLIST_JSON,
    DEFAULT_PLAYLIST_M3U,
    DEFAULT_SELECTION,
    export_playlist,
    normalize,
    save_selection,
)

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_PICKS = DATA_DIR / "agent_picks.json"
DEFAULT_CANDIDATES = 180


def filter_tracks(
    tracks: list[Track],
    *,
    roots: list[Path] | None = None,
    query: str | None = None,
) -> list[Track]:
    selected = tracks
    if roots:
        root_strs = [str(root.resolve()) for root in roots]
        selected = [
            track
            for track in selected
            if any(track.track_id.startswith(root) for root in root_strs)
        ]
    if query:
        tokens = [token for token in re.split(r"\s+", query.casefold()) if token]
        if tokens:
            selected = [
                track
                for track in selected
                if all(
                    token
                    in f"{track.artist} {track.title} {track.album or ''} {track.genre or ''} {track.track_id}".casefold()
                    for token in tokens
                )
            ]
    return selected


def candidate_pool(
    tracks: list[Track],
    brief: str,
    *,
    limit: int = DEFAULT_CANDIDATES,
) -> list[Track]:
    """Rank available tracks for an agent prompt without audio analysis.

    Full crates are too large for a single prompt (~14k). Score by brief token
    hits against artist/title/album/genre/path, then keep the top `limit`.
    """
    tokens = [token for token in re.split(r"[^a-z0-9]+", brief.casefold()) if len(token) > 2]
    stop = {
        "the",
        "and",
        "for",
        "with",
        "into",
        "from",
        "that",
        "this",
        "track",
        "tracks",
        "song",
        "songs",
        "playlist",
        "mix",
        "set",
        "hour",
        "night",
        "late",
    }
    tokens = [token for token in tokens if token not in stop]
    if not tokens:
        return sorted(tracks, key=lambda t: (t.artist.casefold(), t.title.casefold()))[:limit]

    scored: list[tuple[int, Track]] = []
    for track in tracks:
        hay = f"{track.artist} {track.title} {track.album or ''} {track.genre or ''} {track.track_id}".casefold()
        score = sum(hay.count(token) for token in tokens)
        if score:
            scored.append((score, track))
    scored.sort(
        key=lambda pair: (-pair[0], pair[1].artist.casefold(), pair[1].title.casefold())
    )
    pool = [track for _, track in scored[:limit]]
    if len(pool) < min(limit, len(tracks)):
        # Pad with popular-adjacent leftovers so the agent still has room.
        seen = {track.track_id for track in pool}
        for track in sorted(tracks, key=lambda t: (t.artist.casefold(), t.title.casefold())):
            if track.track_id in seen:
                continue
            pool.append(track)
            if len(pool) >= limit:
                break
    return pool


def parse_agent_ids(answer: object, allowed: set[str], *, count: int) -> list[str]:
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
        # Prefer exact length when present; otherwise take unique allowed ids.
        uniq: list[str] = []
        for item in ids:
            if item not in uniq:
                uniq.append(item)
        if uniq:
            return uniq[:count]
    raise ValueError(f"agent did not return a usable id array: {text[:600]}")


def resolve_picks(
    tracks: list[Track],
    picks: list[dict | str],
    *,
    short_id_map: dict[str, Track] | None = None,
) -> list[Track]:
    """Resolve agent picks (short id, track_id path, or artist/title) to crate rows.

    Short ids only resolve through `short_id_map` (usually the same candidate
    pool the agent saw). Absolute paths and artist/title match against `tracks`.
    """
    by_path = {track.track_id: track for track in tracks}
    by_short = short_id_map or {}
    resolved: list[Track] = []
    seen: set[str] = set()

    def add(track: Track | None) -> None:
        if track is None or track.track_id in seen:
            return
        seen.add(track.track_id)
        resolved.append(track)

    for pick in picks:
        if isinstance(pick, str):
            if pick in by_path:
                add(by_path[pick])
            elif pick in by_short:
                add(by_short[pick])
            continue
        if not isinstance(pick, dict):
            continue
        if pick.get("track_id") in by_path:
            add(by_path[pick["track_id"]])
            continue
        short = pick.get("id")
        if isinstance(short, str) and short in by_short:
            add(by_short[short])
            continue
        artist = pick.get("artist")
        title = pick.get("title")
        if not artist or not title:
            continue
        wanted_artist = normalize(str(artist))
        wanted_title = normalize(str(title))
        matches = [
            track
            for track in tracks
            if (
                wanted_artist in normalize(track.artist)
                or normalize(track.artist) in wanted_artist
            )
            and (
                wanted_title == normalize(track.title)
                or wanted_title in normalize(track.title)
                or wanted_title in normalize(Path(track.track_id).stem)
            )
        ]
        if matches:
            add(min(matches, key=lambda t: (len(t.title), t.track_id)))
    return resolved


def short_id_map_for(pool: list[Track]) -> dict[str, Track]:
    return {f"t{index:05d}": track for index, track in enumerate(pool)}


async def curate_with_h_agent(
    pool: list[Track],
    brief: str,
    *,
    count: int,
) -> list[Track]:
    from brain.agent import Brain

    catalog = build_catalog(pool)
    view = agent_view(catalog, include_paths=False)
    # Keep the prompt small: summary + candidate rows only.
    options = view["tracks"]
    prompt = f"""You are the Brain of an autonomous DJ (claw-dj).
This is a planning-only task: do not click, type, or open any desktop app.

Curate a playlist of exactly {count} tracks FROM THE CANDIDATE LIST ONLY.
You may only use ids that appear in the candidates. Do not invent songs.
Brief: {brief}

Return exactly one JSON array of short ids (e.g. ["t00012","t00003",...]) with
length {count}, then optionally explain the flow in prose after that array.

Library summary:
- available candidates: {len(options)}
- top artists in full crate context: {json.dumps(view.get("top_artists", [])[:15])}

Candidates:
{json.dumps(options, indent=2)}
"""
    async with Brain() as brain:
        answer = await brain._run_task(prompt, max_steps=4, max_time_s=120)
    allowed = {entry["id"] for entry in options}
    ids = parse_agent_ids(answer, allowed, count=count)
    by_id = {entry["id"]: pool[i] for i, entry in enumerate(options)}
    return [by_id[item] for item in ids if item in by_id]


def load_picks_file(path: Path) -> list[dict | str]:
    payload = json.loads(path.read_text())
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("picks", "track_ids", "ids", "tracks"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
    raise ValueError(f"unrecognized picks format in {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--brief",
        default="smooth R&B into West Coast hip-hop, dancefloor-friendly",
        help="curation brief for the H agent (ignored for pure offline id lists)",
    )
    parser.add_argument("--count", type=int, default=12, help="target playlist length")
    parser.add_argument(
        "--planner",
        choices=("h-agent", "offline"),
        default="offline",
        help="h-agent uses H Company Brain; offline resolves --from-picks",
    )
    parser.add_argument("--from-picks", type=Path, default=None)
    parser.add_argument(
        "--roots",
        type=Path,
        nargs="*",
        default=None,
        help="optional absolute roots; only tracks under these paths are eligible",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="optional AND keyword filter on artist/title/album/genre/path",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=DEFAULT_CANDIDATES,
        help="max candidates shown to the H agent (brief-ranked)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-catalog", action="store_true")
    args = parser.parse_args()

    tracks = load_crate()
    if not tracks:
        raise SystemExit(
            "crate is empty — run: uv run python -m brain.scan_library <dir> [<dir>...]"
        )

    eligible = filter_tracks(tracks, roots=args.roots, query=args.filter)
    if not eligible:
        raise SystemExit("no tracks matched roots/filter constraints")

    if args.write_catalog:
        write_catalog(eligible, path=DEFAULT_CATALOG, roots=[str(r) for r in (args.roots or [])])
        print(f"catalog -> {DEFAULT_CATALOG} ({len(eligible)} eligible tracks)")

    pool = candidate_pool(eligible, args.brief, limit=args.candidates)
    id_map = short_id_map_for(pool)

    if args.planner == "h-agent":
        print(f"eligible {len(eligible)}; candidate pool {len(pool)}; asking H agent…")
        selected = asyncio.run(
            curate_with_h_agent(pool, args.brief, count=args.count)
        )
    else:
        picks_path = args.from_picks or DEFAULT_PICKS
        if not picks_path.exists():
            template = {
                "brief": args.brief,
                "count": args.count,
                "note": (
                    "Replace picks with short ids from candidates, absolute track_id "
                    "paths, or {artist,title} objects. Only songs in the local crate resolve."
                ),
                "candidates": [
                    {
                        "id": f"t{i:05d}",
                        "artist": track.artist,
                        "title": track.title,
                        "genre": track.genre,
                    }
                    for i, track in enumerate(pool[: min(40, len(pool))])
                ],
                "picks": [f"t{i:05d}" for i in range(min(args.count, len(pool)))],
            }
            picks_path.parent.mkdir(parents=True, exist_ok=True)
            picks_path.write_text(json.dumps(template, indent=2) + "\n")
            raise SystemExit(
                f"wrote offline picks template -> {picks_path}\n"
                "edit picks (or have NemoClaw fill them), then re-run with --planner offline"
            )
        picks = load_picks_file(picks_path)
        # Short ids map to the brief-ranked pool; paths/artist-title use eligible.
        selected = resolve_picks(eligible, picks, short_id_map=id_map)
        if not selected:
            raise SystemExit(f"no picks from {picks_path} resolved against the crate")

    selected = selected[: args.count]
    print(f"curated {len(selected)} tracks:")
    for index, track in enumerate(selected, start=1):
        tag = f"{track.bpm:.0f}BPM/{track.key}" if track.bpm else "unanalyzed"
        print(f"  {index:02d}. {track.artist} — {track.title}  [{tag}]")

    if args.dry_run:
        return

    ids = [track.track_id for track in selected]
    save_selection(ids, DEFAULT_SELECTION)
    export_playlist(
        tracks,
        ids,
        json_path=DEFAULT_PLAYLIST_JSON,
        m3u_path=DEFAULT_PLAYLIST_M3U,
    )
    print(f"wrote {DEFAULT_SELECTION}")
    print(f"wrote {DEFAULT_PLAYLIST_JSON}")
    print(f"wrote {DEFAULT_PLAYLIST_M3U}")


if __name__ == "__main__":
    main()
