"""Agent-curated playlist candidates from the new-music batch.

The "crate digging" judgment call, made by a real model instead of static
seed files: hand the agent the path-stripped new-music view plus a brief,
get back candidate ids, resolve them locally. The agent never sees file
paths and cannot invent tracks — ids it returns that aren't in the view are
dropped.

Providers:
  Uses brain.llm_providers: signed-in Claude/Codex/Grok CLIs, API keys
  from the gitignored .env (including H Company's direct Models API),
  and a local llama-server. No sandbox or computer-use agent is launched.

Candidate pool (--pool):
  new     — (default) the latest scan's new-music batch only.
  library — the whole crate, keyword-pre-filtered against the brief. Use
            this for briefs about music that's been in the library for a
            while (e.g. "90s West Coast G-funk") — "new" pool can never
            see those, it only ever holds the most recent scan's delta.

Usage:
    uv run python -m brain.pick_candidates --engine claude-cli \\
        --brief "recognizable hits that mix well with a hip-hop/R&B showcase"
    uv run python -m brain.pick_candidates --engine hcompany-api --count 15
    uv run python -m brain.pick_candidates --engine llama-server --pool library \\
        --brief "90s West Coast G-funk, Chronic/Doggystyle era"
    # then: review brain/data/new_music_picks.json, optionally
    uv run python -m brain.pick_candidates --engine claude-cli --add-to-selection
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict

from brain.llm_providers import PROVIDERS, ask
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_VIEW = DATA_DIR / "new_music_agent.json"
DEFAULT_ID_MAP = DATA_DIR / "new_music_ids.json"
DEFAULT_OUT = DATA_DIR / "new_music_picks.json"
NEUTRAL_BRIEF = (
    "recognizable songs that would mix well into a hip-hop/R&B DJ showcase"
)


def condensed_view(view: dict, per_artist: int = 12) -> str:
    """Per-artist listing capped so huge discographies don't flood the prompt."""
    by_artist: dict[str, list[dict]] = defaultdict(list)
    for track in view["tracks"]:
        by_artist[track["artist"]].append(track)
    lines: list[str] = []
    for artist in sorted(by_artist):
        tracks = by_artist[artist]
        seen_titles: set[str] = set()
        shown = 0
        for track in tracks:
            title_key = track["title"].casefold()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            if shown < per_artist:
                lines.append(f"{track['id']}  {artist} — {track['title']}")
                shown += 1
        hidden = len(tracks) - shown
        if hidden > 0:
            lines.append(f"        ({artist}: +{hidden} more not shown)")
    return "\n".join(lines)


def build_prompt(view: dict, brief: str, count: int) -> str:
    return f"""You are the crate-digging Brain of claw-dj, an autonomous hip-hop/R&B DJ.

Below is the candidate pool selected by the user. It may be the latest scan
or a keyword-prefiltered view of the whole library. These candidate tracks, one per line as `id  artist — title`. These are the ONLY songs
that exist; do not invent titles, do not assume albums have other tracks.

Brief: {brief}

Pick up to {count} candidate tracks for the next playlist. Prefer widely
recognizable songs (charting singles, classic album cuts) over deep cuts,
interludes, skits, live versions, or remix duplicates. It is fine to pick
fewer than {count} if the material is thin.

Respond with EXACTLY one JSON array of the chosen ids and nothing else,
e.g. ["n0012", "n0431"].

Candidate tracks:
{condensed_view(view)}
"""


def parse_pick_ids(text: str, allowed: set[str]) -> list[str]:
    """Every JSON array in the reply, filtered to known ids, first hit wins."""
    for candidate in re.findall(r"\[[^\[\]]*\]", text, flags=re.DOTALL):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, list):
            continue
        ids = [item for item in value if isinstance(item, str) and item in allowed]
        if ids or not value:
            return list(dict.fromkeys(ids))
    # fallback: bare ids scattered in prose
    loose = [m for m in re.findall(r"n\d{4}", text) if m in allowed]
    if loose:
        return list(dict.fromkeys(loose))
    raise ValueError(f"agent returned no usable ids: {text[:500]}")


def build_whole_library_view(brief: str, *, max_tracks: int = 700) -> tuple[dict, dict[str, str]]:
    """Candidate view scoped to the WHOLE crate, not just the newest scan
    batch — for briefs like "90s West Coast G-funk" that ask about music
    that's been in the library for weeks, which new_music_agent.json can
    never see (it only ever holds the latest scan's delta).

    27k+ tracks is too much to hand an LLM directly, so this pre-filters:
    keyword-score every track's artist/title/album/path against the brief's
    words, keep the top `max_tracks`. Crude but honest — no era/genre
    metadata exists to filter on more precisely (see PROGRESS.md backlog).
    """
    from brain.library import load_crate
    from brain.playlist import normalize

    words = [w for w in normalize(brief).split() if len(w) > 2]
    crate = load_crate()
    if not words:
        scored = [(0, t) for t in crate]
    else:
        scored = []
        for t in crate:
            haystack = normalize(f"{t.artist} {t.title} {t.album or ''} {t.track_id}")
            score = sum(haystack.count(w) for w in words)
            if score > 0:
                scored.append((score, t))
        scored.sort(key=lambda row: -row[0])
    tracks = [t for _, t in scored[:max_tracks]] if scored and scored[0][0] > 0 else crate[:max_tracks]
    id_map = {t.track_id: f"w{i:04d}" for i, t in enumerate(tracks)}
    view = {
        "note": "Whole-library candidates, pre-filtered by keyword match against the brief "
                "(not exhaustive — ask a narrower brief if what you want isn't here).",
        "track_count": len(tracks),
        "tracks": [
            {"id": id_map[t.track_id], "artist": t.artist, "title": t.title,
             "album": t.album, "genre": t.genre, "duration_seconds": t.duration_seconds}
            for t in tracks
        ],
    }
    return view, {v: k for k, v in id_map.items()}


def run_pick(
    *,
    engine: str,
    brief: str,
    count: int = 20,
    view_path: Path = DEFAULT_VIEW,
    id_map_path: Path = DEFAULT_ID_MAP,
    pool: str = "new",
) -> list[dict]:
    """One agent call: view + brief in, resolved picks out. UI entry point.

    pool="new" (default) scopes candidates to the latest scan's new-music
    batch; pool="library" searches the whole crate instead (keyword
    pre-filtered — see build_whole_library_view).
    """
    if engine not in PROVIDERS:
        raise ValueError(f"unknown or retired engine {engine!r}; choose a model provider")
    if pool not in ("new", "library"):
        raise ValueError("pool must be new or library")
    if not 1 <= count <= 50:
        raise ValueError("count must be between 1 and 50")
    if pool == "library":
        view, id_to_path = build_whole_library_view(brief)
    else:
        view = json.loads(view_path.read_text())
        id_to_path = {v: k for k, v in json.loads(id_map_path.read_text()).items()}
    by_id = {t["id"]: t for t in view["tracks"]}
    prompt = build_prompt(view, brief, count)
    answer = ask(engine, prompt)
    return [
        {
            "id": pick_id,
            "artist": by_id[pick_id]["artist"],
            "title": by_id[pick_id]["title"],
            "track_id": id_to_path[pick_id],
        }
        for pick_id in parse_pick_ids(answer, set(by_id))[:count]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=tuple(PROVIDERS), default="claude-cli")
    parser.add_argument(
        "--pool", choices=("new", "library"), default="new",
        help="new = latest scan's new-music batch; library = whole crate, keyword pre-filtered",
    )
    parser.add_argument("--brief", default=NEUTRAL_BRIEF)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--view", type=Path, default=DEFAULT_VIEW)
    parser.add_argument("--id-map", type=Path, default=DEFAULT_ID_MAP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--add-to-selection",
        action="store_true",
        help="append resolved picks to playlist_selection.json",
    )
    args = parser.parse_args()

    print(f"engine={args.engine} pool={args.pool}: asking for up to {args.count} candidates…")
    picks = run_pick(
        engine=args.engine,
        brief=args.brief,
        count=args.count,
        view_path=args.view,
        id_map_path=args.id_map,
        pool=args.pool,
    )
    for pick in picks:
        print(f"  {pick['id']}: {pick['artist']} — {pick['title']}")

    args.out.write_text(
        json.dumps({"engine": args.engine, "brief": args.brief, "picks": picks}, indent=1)
        + "\n"
    )
    print(f"{len(picks)} picks -> {args.out}")

    if args.add_to_selection:
        from brain.playlist import load_selection, save_selection

        selection = load_selection()
        added = [p["track_id"] for p in picks if p["track_id"] not in selection]
        save_selection(selection + added)
        print(f"selection: {len(selection)} -> {len(selection) + len(added)} tracks")
        print("re-order: uv run python -m brain.curate_playlist --mode selection --planner mix-graph")


if __name__ == "__main__":
    main()
