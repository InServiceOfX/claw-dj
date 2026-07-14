"""Enrich the finalized playlist with everything the mix stage needs.

Runs AFTER "Finalize for Mixxx" and only over the finalized set — never the
full crate. Every step checks SQLite first and fills only what's missing:

  1. bpm/key   — muted-deck Mixxx analysis over the control API (port 9995)
  2. lyrics    — LRCLIB (cached on disk), full text into the `lyrics` table
  3. chroma    — Rust `clawdj chroma` 12-dim pitch fingerprints per track;
                 also rewrites chroma_similarity.json for the whole set so
                 mix ordering/plan techniques get real texture coverage
  4. phrases   — beat-aligned energy cue analysis (intro/body entries) into
                 the `phrases` table + phrase_analysis.json for the planner

Usage:
    uv run python -m brain.enrich_set                # fill all missing
    uv run python -m brain.enrich_set --status       # report only
    uv run python -m brain.enrich_set --skip-lyrics --skip-chroma
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from brain.library_index import connect
from brain.playlist import DATA_DIR, DEFAULT_PLAYLIST_JSON

CHROMA_SIMILARITY = DATA_DIR / "chroma_similarity.json"
PHRASE_OUT = DATA_DIR / "phrase_analysis.json"


def load_set(playlist_path: Path) -> list[dict]:
    payload = json.loads(playlist_path.read_text())
    return payload["tracks"] if isinstance(payload, dict) else payload


def status(db, track_ids: list[str]) -> dict[str, dict]:
    have = {
        table: {
            row[0] for row in db.execute(
                f"SELECT track_id FROM {table} WHERE track_id IN ({','.join('?' * len(track_ids))})",
                track_ids,
            )
        }
        for table in ("lyrics", "chroma", "phrases", "lyric_timelines")
    }
    # BPM alone is enough for the mix plan; key is best-effort (control API
    # may not map, and Mixxx DB flush often lags). Treat bpm IS NOT NULL as ok.
    analyzed = {
        row[0] for row in db.execute(
            f"SELECT track_id FROM tracks WHERE bpm IS NOT NULL AND bpm > 0 "
            f"AND track_id IN ({','.join('?' * len(track_ids))})",
            track_ids,
        )
    }
    # Lyrics row with source not_found still counts as "attempted"; require
    # non-null lyrics text for the lyrics checkbox.
    have_lyrics_text = {
        row[0] for row in db.execute(
            f"SELECT track_id FROM lyrics WHERE lyrics IS NOT NULL "
            f"AND track_id IN ({','.join('?' * len(track_ids))})",
            track_ids,
        )
    }
    return {
        tid: {
            "bpm_key": tid in analyzed,
            "lyrics": tid in have_lyrics_text,
            "chroma": tid in have["chroma"],
            "phrases": tid in have["phrases"],
            # attempted counts: tracks without synced lyrics on LRCLIB get an
            # empty-timeline row so we don't refetch every run
            "timeline": tid in have["lyric_timelines"],
        }
        for tid in track_ids
    }


def fill_bpm(missing: list[dict], port: int) -> None:
    """Analyze via control API and persist readings into claw-dj immediately.

    Do not wait solely on Mixxx DB flush — the control API often has bpm
    while mixxxdb still shows 0 (Many Man / Many Men case, 2026-07-12).
    """
    from brain.analyze_via_mixxx import analyze_tracks, apply_analysis

    results = analyze_tracks(missing, port=port)
    apply_analysis(results)
    # Best-effort: also pull anything Mixxx *did* flush (keys, older tracks).
    time.sleep(2)
    subprocess.run([sys.executable, "-m", "brain.sync_mixxx_analysis"], check=False)


def fill_lyrics(db, tracks: list[dict], *, force: bool = False) -> tuple[int, int]:
    from brain.lyrics import fetch_lyrics

    found = missed = 0
    for track in tracks:
        record = fetch_lyrics(track["artist"], track["title"], force=force)
        db.execute(
            "INSERT OR REPLACE INTO lyrics(track_id, source, fetched_at, lyrics) VALUES (?,?,?,?)",
            (track["track_id"], record.get("source") or "not_found", time.time(),
             record.get("lyrics")),
        )
        if record.get("found"):
            found += 1
        else:
            missed += 1
            print(f"  [lyrics] not found: {track['artist']} — {track['title']}")
    db.commit()
    return found, missed


def fill_chroma(db, tracks: list[dict]) -> int:
    from brain.enrich_playlist import run_chroma

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        out = Path(handle.name)
    result = run_chroma([t["track_id"] for t in tracks], out)
    if not result:
        return 0
    now = time.time()
    stored = 0
    for path, fingerprint in zip(result["paths"], result["fingerprints"]):
        db.execute(
            "INSERT OR REPLACE INTO chroma(track_id, computed_at, fingerprint) VALUES (?,?,?)",
            (path, now, json.dumps(fingerprint)),
        )
        stored += 1
    db.commit()
    return stored


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def rewrite_similarity(db, track_ids: list[str]) -> int:
    """Full-set pairwise cosine matrix from stored fingerprints, in the
    chroma_similarity.json shape mix_graph/build_mix_plan already read."""
    rows = db.execute(
        f"SELECT track_id, fingerprint FROM chroma "
        f"WHERE track_id IN ({','.join('?' * len(track_ids))})",
        track_ids,
    ).fetchall()
    if len(rows) < 2:
        return 0
    paths = [row[0] for row in rows]
    vectors = [json.loads(row[1]) for row in rows]
    matrix = [[round(cosine(a, b), 6) for b in vectors] for a in vectors]
    CHROMA_SIMILARITY.write_text(json.dumps({
        "version": 2,
        "source": "brain.enrich_set (per-track fingerprints from sqlite)",
        "track_count": len(paths),
        "paths": paths,
        "fingerprints": vectors,
        "similarity": matrix,
    }, indent=1) + "\n")
    return len(paths)


def fill_phrases(db, tracks: list[dict], *, max_seconds: float = 300.0) -> int:
    from brain.phrase_analysis import analyze_track
    from shared.mixxx_db import connect_readonly

    query = """
        SELECT track_locations.location, library.title, library.duration,
               library.samplerate, library.beats, library.artist
        FROM library
        JOIN track_locations ON library.location = track_locations.id
        WHERE track_locations.location = ?
          AND library.beats_version = 'BeatGrid-2.0'
          AND library.beats IS NOT NULL
    """
    analyzed = 0
    mixxx = connect_readonly()
    try:
        for track in tracks:
            row = mixxx.execute(query, (track["track_id"],)).fetchone()
            if row is None:
                print(f"  [phrases] no Mixxx beatgrid yet: {track['artist']} — {track['title']}")
                continue
            payload = analyze_track(row, max_seconds=max_seconds)
            db.execute(
                "INSERT OR REPLACE INTO phrases(track_id, analyzed_at, payload) VALUES (?,?,?)",
                (track["track_id"], time.time(), json.dumps(payload)),
            )
            analyzed += 1
    finally:
        mixxx.close()
    db.commit()
    return analyzed


def export_phrases(db, track_ids: list[str]) -> int:
    rows = db.execute(
        f"SELECT payload FROM phrases WHERE track_id IN ({','.join('?' * len(track_ids))})",
        track_ids,
    ).fetchall()
    tracks = [json.loads(row[0]) for row in rows]
    PHRASE_OUT.write_text(json.dumps({"version": 1, "tracks": tracks}, indent=2) + "\n")
    return len(tracks)


def enrichment_status(playlist_path: Path = DEFAULT_PLAYLIST_JSON) -> dict:
    """Gap report for the UI — does not mutate anything."""
    if not playlist_path.exists():
        return {"ready": False, "error": "no finalized playlist", "count": 0}
    tracks = load_set(playlist_path)
    ids = [t["track_id"] for t in tracks]
    if not ids:
        return {"ready": False, "error": "finalized playlist empty", "count": 0}
    with closing(connect()) as db:
        gaps = status(db, ids)
    need = {
        field: [
            {"artist": t.get("artist"), "title": t.get("title"), "track_id": t["track_id"]}
            for t in tracks
            if not gaps[t["track_id"]][field]
        ]
        for field in ("bpm_key", "lyrics", "chroma", "phrases")
    }
    complete = sum(1 for g in gaps.values() if all(g.values()))
    return {
        "ready": True,
        "count": len(tracks),
        "complete": complete,
        "missing": {k: len(v) for k, v in need.items()},
        "missing_tracks": need,
        "message": (
            f"{complete}/{len(tracks)} fully enriched · "
            f"missing bpm/key {len(need['bpm_key'])}, lyrics {len(need['lyrics'])}, "
            f"chroma {len(need['chroma'])}, phrases {len(need['phrases'])}"
        ),
    }


def run_enrich(
    *,
    playlist_path: Path = DEFAULT_PLAYLIST_JSON,
    port: int = 9995,
    skip_bpm: bool = False,
    skip_lyrics: bool = False,
    skip_chroma: bool = False,
    skip_phrases: bool = False,
    skip_timelines: bool = False,
    force_lyrics: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Run the full enrichment pipeline; returns a structured summary for the UI.

    `progress` is an optional callback(str) for live status lines.
    """
    def log(msg: str) -> None:
        print(msg)
        if progress:
            progress(msg)

    if not playlist_path.exists():
        raise FileNotFoundError(f"missing finalized playlist {playlist_path}")
    tracks = load_set(playlist_path)
    ids = [t["track_id"] for t in tracks]
    if len(ids) < 1:
        raise ValueError("finalized playlist is empty")

    log(f"finalized set: {len(tracks)} tracks ({playlist_path})")
    summary: dict = {
        "track_count": len(tracks),
        "bpm_analyzed": 0,
        "lyrics_found": 0,
        "lyrics_missed": 0,
        "chroma_stored": 0,
        "phrases_analyzed": 0,
        "phrases_exported": 0,
        "complete": 0,
        "incomplete": [],
        "log": [],
    }

    def note(msg: str) -> None:
        summary["log"].append(msg)
        log(msg)

    with closing(connect()) as db:
        gaps = status(db, ids)
        need = {
            field: [t for t in tracks if not gaps[t["track_id"]][field]]
            for field in ("bpm_key", "lyrics", "chroma", "phrases", "timeline")
        }
        for field, rows in need.items():
            note(f"missing {field}: {len(rows)}")

        if need["bpm_key"] and not skip_bpm:
            note(f"[bpm/key] analyzing {len(need['bpm_key'])} tracks via muted Mixxx deck…")
            fill_bpm(need["bpm_key"], port)
            summary["bpm_analyzed"] = len(need["bpm_key"])
            # Re-read playlist rows from disk after crate sync? fill_bpm only
            # updates index/crate; playlist.json is refreshed by the editor.
            note("[bpm/key] Mixxx analysis + sync_mixxx_analysis done")
        elif skip_bpm:
            note("[bpm/key] skipped")

        lyric_targets = tracks if force_lyrics else need["lyrics"]
        if lyric_targets and not skip_lyrics:
            note(f"[lyrics] fetching {len(lyric_targets)} tracks from LRCLIB…")
            found, missed = fill_lyrics(db, lyric_targets, force=force_lyrics)
            summary["lyrics_found"] = found
            summary["lyrics_missed"] = missed
            note(f"lyrics: {found} found, {missed} not found")
        elif skip_lyrics:
            note("[lyrics] skipped")

        if need["chroma"] and not skip_chroma:
            note(f"[chroma] fingerprinting {len(need['chroma'])} tracks…")
            stored = fill_chroma(db, need["chroma"])
            summary["chroma_stored"] = stored
            note(f"chroma: {stored} fingerprints stored")
        elif skip_chroma:
            note("[chroma] skipped")
        size = rewrite_similarity(db, ids)
        if size:
            note(f"chroma_similarity.json rewritten for {size} tracks")

        if not skip_phrases:
            gaps = status(db, ids)
            targets = [t for t in tracks if not gaps[t["track_id"]]["phrases"]]
            if targets:
                note(f"[phrases] analyzing {len(targets)} tracks…")
                done = fill_phrases(db, targets)
                summary["phrases_analyzed"] = done
                note(f"phrases: {done} analyzed")
            exported = export_phrases(db, ids)
            summary["phrases_exported"] = exported
            note(f"phrase_analysis.json exported for {exported} tracks")
        else:
            note("[phrases] skipped")

        if not skip_timelines:
            from brain.lyric_timeline import build_for_tracks

            gaps = status(db, ids)
            targets = [t for t in tracks if not gaps[t["track_id"]]["timeline"]]
            if targets:
                note(f"[timelines] verse/chorus maps for {len(targets)} tracks…")
                result = build_for_tracks(db, targets)
                summary["timelines_built"] = result["built"]
                summary["timelines_no_synced"] = result["no_synced"]
                note(f"timelines: {result['built']} built, {result['no_synced']} without synced lyrics")
        else:
            note("[timelines] skipped")

        gaps = status(db, ids)
        summary["complete"] = sum(1 for g in gaps.values() if all(g.values()))
        for tid, g in gaps.items():
            holes = [k for k, ok in g.items() if not ok]
            if holes:
                track = next(t for t in tracks if t["track_id"] == tid)
                row = {
                    "artist": track.get("artist"),
                    "title": track.get("title"),
                    "track_id": tid,
                    "missing": holes,
                }
                summary["incomplete"].append(row)
                note(f"incomplete ({', '.join(holes)}): {track.get('artist')} — {track.get('title')}")
        note(f"enrichment: {summary['complete']}/{len(tracks)} tracks fully enriched")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST_JSON)
    parser.add_argument("--port", type=int, default=9995)
    parser.add_argument("--status", action="store_true", help="report gaps, change nothing")
    parser.add_argument("--skip-bpm", action="store_true")
    parser.add_argument("--skip-lyrics", action="store_true")
    parser.add_argument("--skip-chroma", action="store_true")
    parser.add_argument("--skip-phrases", action="store_true")
    parser.add_argument("--skip-timelines", action="store_true")
    parser.add_argument("--force-lyrics", action="store_true")
    args = parser.parse_args()

    if args.status:
        report = enrichment_status(args.playlist)
        print(report.get("message") or report)
        for field, rows in (report.get("missing_tracks") or {}).items():
            for row in rows[:20]:
                print(f"  missing {field}: {row['artist']} — {row['title']}")
        return

    run_enrich(
        playlist_path=args.playlist,
        port=args.port,
        skip_bpm=args.skip_bpm,
        skip_lyrics=args.skip_lyrics,
        skip_chroma=args.skip_chroma,
        skip_phrases=args.skip_phrases,
        skip_timelines=args.skip_timelines,
        force_lyrics=args.force_lyrics,
    )


if __name__ == "__main__":
    main()
