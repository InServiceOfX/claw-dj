"""Agent-curated playlist candidates from the new-music batch.

The "crate digging" judgment call, made by a real model instead of static
seed files: hand the agent the path-stripped new-music view plus a brief,
get back candidate ids, resolve them locally. The agent never sees file
paths and cannot invent tracks — ids it returns that aren't in the view are
dropped.

Engines:
  nemoclaw — hermes sandbox (NVIDIA Nemotron) via its OpenAI-compatible API.
             Needs: `openshell forward start --background 8642 hermes`.
  h-agent  — H Company Agent Platform via hai_agents (planning-only task,
             no GUI). Needs holo/hai login credentials on this machine.
  generic  — any OpenAI-chat-compatible endpoint: xAI/Grok, a local
             Ollama/LM Studio server, OpenAI itself. Configured via env
             vars CLAWDJ_LLM_BASE_URL / CLAWDJ_LLM_API_KEY /
             CLAWDJ_LLM_MODEL — see ask_generic()'s docstring.

Candidate pool (--pool):
  new     — (default) the latest scan's new-music batch only.
  library — the whole crate, keyword-pre-filtered against the brief. Use
            this for briefs about music that's been in the library for a
            while (e.g. "90s West Coast G-funk") — "new" pool can never
            see those, it only ever holds the most recent scan's delta.

Usage:
    uv run python -m brain.pick_candidates --engine nemoclaw \\
        --brief "recognizable hits that mix well with a hip-hop/R&B showcase"
    uv run python -m brain.pick_candidates --engine h-agent --count 15
    uv run python -m brain.pick_candidates --engine generic --pool library \\
        --brief "90s West Coast G-funk, Chronic/Doggystyle era"
    # then: review brain/data/new_music_picks.json, optionally
    uv run python -m brain.pick_candidates --engine nemoclaw --add-to-selection
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.request
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_VIEW = DATA_DIR / "new_music_agent.json"
DEFAULT_ID_MAP = DATA_DIR / "new_music_ids.json"
DEFAULT_OUT = DATA_DIR / "new_music_picks.json"
NEMOCLAW_URL = "http://127.0.0.1:8642/v1/chat/completions"

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

New music just landed in the user's library. Below is the complete list of
new tracks, one per line as `id  artist — title`. These are the ONLY songs
that exist; do not invent titles, do not assume albums have other tracks.

Brief: {brief}

Pick up to {count} candidate tracks for the next playlist. Prefer widely
recognizable songs (charting singles, classic album cuts) over deep cuts,
interludes, skits, live versions, or remix duplicates. It is fine to pick
fewer than {count} if the material is thin.

Respond with EXACTLY one JSON array of the chosen ids and nothing else,
e.g. ["n0012", "n0431"].

New tracks:
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
        if ids:
            return list(dict.fromkeys(ids))
    # fallback: bare ids scattered in prose
    loose = [m for m in re.findall(r"n\d{4}", text) if m in allowed]
    if loose:
        return list(dict.fromkeys(loose))
    raise ValueError(f"agent returned no usable ids: {text[:500]}")


def ask_nemoclaw(prompt: str, *, timeout_s: float = 600.0) -> str:
    token = subprocess.run(
        ["nemoclaw", "hermes", "gateway-token", "--quiet"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    payload = json.dumps(
        {
            "model": "hermes-agent",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
    ).encode()
    request = urllib.request.Request(
        NEMOCLAW_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        body = json.loads(response.read())
    return body["choices"][0]["message"]["content"]


def ask_generic(prompt: str, *, timeout_s: float = 300.0) -> str:
    """Any OpenAI-chat-compatible endpoint — xAI/Grok, a local Ollama/LM
    Studio server, OpenAI itself, or anything else speaking the same wire
    format. Configured entirely by env vars so no provider-specific code is
    needed here:

      CLAWDJ_LLM_BASE_URL   e.g. https://api.x.ai/v1  or  http://localhost:11434/v1
      CLAWDJ_LLM_API_KEY    provider key (local servers often ignore this — pass "ollama" or similar placeholder)
      CLAWDJ_LLM_MODEL      e.g. grok-4  or  llama3.1  (whatever the endpoint serves)

    xAI's API is documented as OpenAI-compatible at api.x.ai/v1 — set
    CLAWDJ_LLM_BASE_URL=https://api.x.ai/v1, CLAWDJ_LLM_API_KEY=<your xai key>,
    CLAWDJ_LLM_MODEL=grok-4 (check x.ai for the current model name).
    """
    import os

    base_url = os.environ.get("CLAWDJ_LLM_BASE_URL")
    api_key = os.environ.get("CLAWDJ_LLM_API_KEY")
    model = os.environ.get("CLAWDJ_LLM_MODEL")
    missing = [
        name for name, value in (
            ("CLAWDJ_LLM_BASE_URL", base_url),
            ("CLAWDJ_LLM_API_KEY", api_key),
            ("CLAWDJ_LLM_MODEL", model),
        ) if not value
    ]
    if missing:
        raise RuntimeError(
            f"generic engine needs env vars: {', '.join(missing)} "
            "(see ask_generic docstring in brain/pick_candidates.py)"
        )
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
    ).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        body = json.loads(response.read())
    return body["choices"][0]["message"]["content"]


def ask_h_agent(prompt: str) -> str:
    import asyncio

    from brain.agent import Brain

    async def run() -> str:
        async with Brain() as brain:
            answer = await brain._run_task(
                "This is planning-only: do not click, type, or open apps. "
                "Answer in text.\n\n" + prompt,
                max_steps=4,
                max_time_s=240,
            )
        return json.dumps(answer) if isinstance(answer, (dict, list)) else str(answer)

    return asyncio.run(run())


ENGINES = {"nemoclaw": ask_nemoclaw, "generic": ask_generic}


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
    if pool == "library":
        view, id_to_path = build_whole_library_view(brief)
    else:
        view = json.loads(view_path.read_text())
        id_to_path = {v: k for k, v in json.loads(id_map_path.read_text()).items()}
    by_id = {t["id"]: t for t in view["tracks"]}
    prompt = build_prompt(view, brief, count)
    if engine == "h-agent":
        answer = ask_h_agent(prompt)
    else:
        answer = ENGINES[engine](prompt)
    return [
        {
            "id": pick_id,
            "artist": by_id[pick_id]["artist"],
            "title": by_id[pick_id]["title"],
            "track_id": id_to_path[pick_id],
        }
        for pick_id in parse_pick_ids(answer, set(by_id))
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("nemoclaw", "h-agent", "generic"), default="nemoclaw")
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
