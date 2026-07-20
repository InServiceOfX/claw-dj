"""Turn a free-text DJ brief into structured dj_notes edits + reordering.

This is the "mix-brief" text box's engine: Ernest (or any user) types
natural-language instructions about specific tracks/transitions — verse
landing points, cue timing, reordering — and an LLM translates that into
the same `dj_notes` directive syntax `brain.build_mix_plan.track_directives`
already parses, grounded in each mentioned track's real synced lyrics so it
isn't guessing timestamps from memory.

Two hard safety rules, because both bugs already happened by hand once:
  - Every track_id the model returns is checked against the actual
    finalized playlist (brain/data/playlist.json) before anything is
    written — never trust a model-generated path, and never let a
    same-titled-but-wrong file copy silently eat an edit.
  - A reorder must be an exact permutation of the existing track set — the
    model can resequence, never invent or drop a track.

Dry-run by default: prints a diff of what would change. Pass --apply to
actually write. Reorders touch brain/data/playlist.json and
playlist_selection.json directly (not a crate.json round trip — crate.json
is only refreshed on scan/analyze/sync, so it can be stale relative to a
dj_notes write made seconds ago).

Usage:
    uv run python -m brain.mix_directives --brief "..."
    uv run python -m brain.mix_directives --brief "..." --engine generic --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from brain.pick_candidates import ENGINES, ask_h_agent
from brain.playlist import DEFAULT_PLAYLIST_JSON, DEFAULT_SELECTION, normalize

DATA_DIR = Path(__file__).parent / "data"

DIRECTIVE_VOCAB = """\
Known dj_notes directive tokens (embed as key=value inside the prose, \
semicolon-separated, exactly like the examples below — build_mix_plan.py's \
track_directives() parses these with a regex, so spelling/casing of the \
keys must match exactly):
  cue_seconds=<number>       seconds into the track to start riding from
  ride_phrases=<int>         how many 32-beat phrases to ride before the next transition
  ride_beats=<int>           exact beat count to ride (overrides ride_phrases when set)
  play_bpm=<number>          play this track at a specific BPM instead of its native one
  entry_style=beat_drop | gentle_blend | verse_landing
  landing_seconds=<number>   (with entry_style=verse_landing) exact second the vocal/verse lands
  landing_beats=<int>        (with entry_style=verse_landing) beat count to land on
  opener_style=echo_tease_drop | juggle_intro | juggle_brake_intro   (only meaningful on the first track)
  full_track                 bare flag — play the whole track, no cut

Real examples written by hand this project (style + precision to match):
  "Pre-roll during the blend and land exactly on Kurupt first verse; protect \
the full verse before the next transition; ride through Snoop's verse, \
which ends at 4:02.81 (\\"Doggy Dogg's done\\"). entry_style=verse_landing; \
landing_seconds=28.740; landing_beats=24; ride_beats=335"
  "Skip most of the spoken community-message intro; ok to catch some of it \
during the blend, but land fully on Snoop's first verse, no cutting into \
the middle of it; ride through the verse, which runs to the chorus at \
82.9s. entry_style=verse_landing; landing_seconds=37.230; landing_beats=24; \
ride_beats=78"
  "Higher-tempo song -- fine to run it slightly faster than its native \
tempo to sit better against faster neighbors. play_bpm=98.5"
"""


def load_playlist(path: Path = DEFAULT_PLAYLIST_JSON) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"no finalized playlist at {path} — finalize a set in the "
            "playlist editor first (this operates on the finalized set, "
            "not the whole crate)."
        )
    return json.loads(path.read_text())


def _mentioned_tracks(brief: str, tracks: list[dict], *, limit: int = 6) -> list[dict]:
    """Lightweight token-overlap match — which tracks does the brief seem to
    be talking about? Those get real lyric grounding attached to the prompt;
    everything else just gets its bare metadata line."""
    words = [w for w in normalize(brief).split() if len(w) > 2]
    if not words:
        return []
    scored = []
    for track in tracks:
        haystack = normalize(f"{track['artist']} {track['title']}")
        score = sum(haystack.count(w) for w in words)
        if score > 0:
            scored.append((score, track))
    scored.sort(key=lambda pair: -pair[0])
    return [t for _, t in scored[:limit]]


def _lyric_excerpt(track_id: str, db_path: Path, *, max_chars: int = 6000) -> str | None:
    with closing(sqlite3.connect(db_path)) as db:
        row = db.execute(
            "SELECT lrc FROM lyric_timelines WHERE track_id = ?", (track_id,)
        ).fetchone()
    if not row or not row[0]:
        return None
    lrc = row[0]
    if len(lrc) > max_chars:
        return lrc[:max_chars] + "\n[...truncated...]"
    return lrc


def build_prompt(tracks: list[dict], brief: str, db_path: Path) -> str:
    id_map = {t["track_id"]: f"t{i:03d}" for i, t in enumerate(tracks)}
    lines = [
        "You are editing an ordered DJ set for a West Coast hip-hop mix "
        "(claw-dj). Below is the current track order with each track's "
        "short id, artist, title, bpm, key, and any existing dj_notes "
        "(a human DJ's annotations). A DJ is giving you a free-text "
        "instruction. Translate it into structured edits.\n",
        DIRECTIVE_VOCAB,
        "\nCurrent order:",
    ]
    for i, t in enumerate(tracks):
        sid = id_map[t["track_id"]]
        notes = t.get("dj_notes") or "(none)"
        lines.append(
            f"  [{i}] {sid}  {t['artist']} — {t['title']}  "
            f"bpm={t.get('bpm')} key={t.get('key')}  dj_notes: {notes}"
        )

    grounded = _mentioned_tracks(brief, tracks)
    if grounded:
        lines.append(
            "\nRaw synced lyrics (LRC, timestamped) for tracks the brief "
            "appears to reference — use these to find EXACT verse/chorus "
            "boundaries. Do not guess a timestamp if it isn't visible here; "
            "leave entry_style/landing fields off rather than invent one."
        )
        for t in grounded:
            sid = id_map[t["track_id"]]
            excerpt = _lyric_excerpt(t["track_id"], db_path)
            if excerpt:
                lines.append(f"\n--- {sid} ({t['artist']} — {t['title']}) ---\n{excerpt}")
            else:
                lines.append(
                    f"\n--- {sid} ({t['artist']} — {t['title']}) --- "
                    "(no synced lyrics available — rely on the brief's own "
                    "description, don't invent timestamps)"
                )

    lines.append(f"\nDJ's instruction:\n{brief}\n")
    lines.append(
        "Reply with exactly one JSON object, nothing else outside it:\n"
        '{\n'
        '  "notes": {"<short id>": "<new full dj_notes text>", ...},\n'
        '  "reorder": ["<short id>", ...] or null\n'
        "}\n"
        "Rules:\n"
        '- "notes" keys must be short ids from the list above (t000 style), '
        "never a real file path.\n"
        '- Each notes value replaces that track\'s ENTIRE dj_notes field — '
        "if it already has notes worth keeping, include them.\n"
        '- Only include a track in "notes" if the brief actually gives it '
        "new instructions; leave everything else out.\n"
        '- "reorder", if given, must list every short id above exactly '
        "once — reordering, never adding or dropping a track.\n"
        '- If the brief doesn\'t ask for reordering, set "reorder" to null.\n'
    )
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict:
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON object found in reply: {text[:500]}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"reply looked like JSON but failed to parse: {exc}\n{candidate[:500]}"
                    ) from exc
    raise ValueError(f"unbalanced braces in reply: {text[:500]}")


def parse_directives(text: str, tracks: list[dict]) -> tuple[dict[str, str], list[str] | None]:
    """Validate an LLM reply against the real track set.

    Returns (notes: {track_id: new_dj_notes}, reorder: [track_id, ...] | None).
    Raises ValueError on any id that doesn't match, or a reorder that isn't
    an exact permutation — never partially apply a bad response.
    """
    id_map = {f"t{i:03d}": t["track_id"] for i, t in enumerate(tracks)}
    parsed = _extract_json_object(text)
    if not isinstance(parsed, dict):
        raise ValueError(f"top-level reply must be a JSON object, got {type(parsed)}")

    raw_notes = parsed.get("notes") or {}
    if not isinstance(raw_notes, dict):
        raise ValueError(f'"notes" must be an object, got {type(raw_notes)}')
    notes: dict[str, str] = {}
    for sid, note in raw_notes.items():
        if sid not in id_map:
            raise ValueError(f'"notes" references unknown id {sid!r} — refusing to guess a track')
        if not isinstance(note, str) or not note.strip():
            raise ValueError(f"notes[{sid!r}] must be a non-empty string, got {note!r}")
        notes[id_map[sid]] = note.strip()

    raw_reorder = parsed.get("reorder")
    reorder: list[str] | None = None
    if raw_reorder is not None:
        if not isinstance(raw_reorder, list) or not all(isinstance(x, str) for x in raw_reorder):
            raise ValueError(f'"reorder" must be a list of strings or null, got {raw_reorder!r}')
        if set(raw_reorder) != set(id_map) or len(raw_reorder) != len(id_map):
            missing = set(id_map) - set(raw_reorder)
            extra = set(raw_reorder) - set(id_map)
            raise ValueError(
                "\"reorder\" is not an exact permutation of the current track "
                f"set — missing={sorted(missing)} extra={sorted(extra)} "
                f"(refusing to invent or drop tracks)"
            )
        reorder = [id_map[sid] for sid in raw_reorder]

    return notes, reorder


def print_diff(tracks: list[dict], notes: dict[str, str], reorder: list[str] | None) -> None:
    by_id = {t["track_id"]: t for t in tracks}
    if notes:
        print(f"\ndj_notes changes ({len(notes)}):")
        for track_id, new_note in notes.items():
            t = by_id[track_id]
            old = t.get("dj_notes") or "(none)"
            print(f"  {t['artist']} — {t['title']}")
            print(f"    old: {old}")
            print(f"    new: {new_note}")
    else:
        print("\nno dj_notes changes.")

    if reorder:
        old_order = [t["track_id"] for t in tracks]
        if reorder == old_order:
            print("\nreorder: requested but identical to current order (no-op).")
        else:
            print("\nreorder:")
            old_pos = {track_id: i for i, track_id in enumerate(old_order)}
            for new_pos, track_id in enumerate(reorder):
                t = by_id[track_id]
                moved = new_pos - old_pos[track_id]
                marker = f"  ({moved:+d})" if moved else ""
                print(f"  [{new_pos:2d}] {t['artist']} — {t['title']}{marker}")
    else:
        print("no reorder.")


def apply_directives(
    tracks: list[dict],
    notes: dict[str, str],
    reorder: list[str] | None,
    *,
    playlist_path: Path = DEFAULT_PLAYLIST_JSON,
    selection_path: Path = DEFAULT_SELECTION,
    db_path: Path | None = None,
) -> None:
    from brain.library_index import DEFAULT_INDEX, connect
    from brain.playlist import save_selection

    db_path = db_path or DEFAULT_INDEX

    if notes:
        with closing(connect(db_path)) as db:
            for track_id, new_note in notes.items():
                db.execute(
                    "UPDATE tracks SET dj_notes = ? WHERE track_id = ?",
                    (new_note, track_id),
                )
            db.commit()

    by_id = {t["track_id"]: dict(t) for t in tracks}
    for track_id, new_note in notes.items():
        by_id[track_id]["dj_notes"] = new_note

    order = reorder if reorder else [t["track_id"] for t in tracks]
    new_rows = [by_id[track_id] for track_id in order]
    playlist_path.write_text(json.dumps(new_rows, indent=2) + "\n")

    if reorder:
        save_selection(order, path=selection_path)


def run(
    *,
    brief: str,
    engine: str,
    apply: bool,
    playlist_path: Path = DEFAULT_PLAYLIST_JSON,
    db_path: Path | None = None,
) -> None:
    from brain.library_index import DEFAULT_INDEX

    db_path = db_path or DEFAULT_INDEX
    tracks = load_playlist(playlist_path)
    prompt = build_prompt(tracks, brief, db_path)

    print(f"engine={engine}: interpreting brief against {len(tracks)} tracks…")
    if engine == "h-agent":
        reply = ask_h_agent(prompt)
    else:
        reply = ENGINES[engine](prompt)

    notes, reorder = parse_directives(reply, tracks)
    print_diff(tracks, notes, reorder)

    if not notes and not reorder:
        print("\nnothing to do — brief didn't resolve to any concrete edit.")
        return

    if not apply:
        print("\ndry-run only — pass --apply to write these changes.")
        return

    apply_directives(tracks, notes, reorder, playlist_path=playlist_path, db_path=db_path)
    print(
        f"\napplied. wrote dj_notes for {len(notes)} track(s) to library.sqlite3 + playlist.json"
        + (", and reordered playlist.json + playlist_selection.json" if reorder else "")
        + ".\nRebuild the mix plan to pick these up: "
        "uv run python -m brain.build_mix_plan --tracks <n> --profile <profile>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--brief", required=True, help="free-text DJ instruction")
    parser.add_argument("--engine", choices=("nemoclaw", "h-agent", "generic"), default="nemoclaw")
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry-run diff only)")
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST_JSON)
    args = parser.parse_args()

    run(brief=args.brief, engine=args.engine, apply=args.apply, playlist_path=args.playlist)


if __name__ == "__main__":
    main()
