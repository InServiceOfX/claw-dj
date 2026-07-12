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
        for table in ("lyrics", "chroma", "phrases")
    }
    analyzed = {
        row[0] for row in db.execute(
            f"SELECT track_id FROM tracks WHERE bpm IS NOT NULL AND key IS NOT NULL "
            f"AND track_id IN ({','.join('?' * len(track_ids))})",
            track_ids,
        )
    }
    return {
        tid: {
            "bpm_key": tid in analyzed,
            "lyrics": tid in have["lyrics"],
            "chroma": tid in have["chroma"],
            "phrases": tid in have["phrases"],
        }
        for tid in track_ids
    }


def fill_bpm(missing: list[dict], port: int) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(missing, handle)
        tracks_file = handle.name
    subprocess.run(
        [sys.executable, "-m", "brain.analyze_via_mixxx", "--tracks", tracks_file,
         "--port", str(port)],
        check=True,
    )
    # Mixxx flushes analysis to its DB lazily; give it a moment, then sync
    # (sync updates both the index and crate.json).
    time.sleep(5)
    subprocess.run([sys.executable, "-m", "brain.sync_mixxx_analysis"], check=True)


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST_JSON)
    parser.add_argument("--port", type=int, default=9995)
    parser.add_argument("--status", action="store_true", help="report gaps, change nothing")
    parser.add_argument("--skip-bpm", action="store_true")
    parser.add_argument("--skip-lyrics", action="store_true")
    parser.add_argument("--skip-chroma", action="store_true")
    parser.add_argument("--skip-phrases", action="store_true")
    parser.add_argument("--force-lyrics", action="store_true")
    args = parser.parse_args()

    tracks = load_set(args.playlist)
    ids = [t["track_id"] for t in tracks]
    print(f"finalized set: {len(tracks)} tracks ({args.playlist})")

    with closing(connect()) as db:
        gaps = status(db, ids)
        need = {
            field: [t for t in tracks if not gaps[t["track_id"]][field]]
            for field in ("bpm_key", "lyrics", "chroma", "phrases")
        }
        for field, rows in need.items():
            print(f"  missing {field}: {len(rows)}")
        if args.status:
            return

        if need["bpm_key"] and not args.skip_bpm:
            print(f"\n[bpm/key] analyzing {len(need['bpm_key'])} tracks via muted Mixxx deck…")
            fill_bpm(need["bpm_key"], args.port)

        lyric_targets = tracks if args.force_lyrics else need["lyrics"]
        if lyric_targets and not args.skip_lyrics:
            print(f"\n[lyrics] fetching {len(lyric_targets)} tracks from LRCLIB (cached)…")
            found, missed = fill_lyrics(db, lyric_targets, force=args.force_lyrics)
            print(f"  lyrics: {found} found, {missed} not found")

        if need["chroma"] and not args.skip_chroma:
            print(f"\n[chroma] fingerprinting {len(need['chroma'])} tracks…")
            stored = fill_chroma(db, need["chroma"])
            print(f"  chroma: {stored} fingerprints stored")
        size = rewrite_similarity(db, ids)
        if size:
            print(f"  chroma_similarity.json rewritten for {size} tracks")

        if not args.skip_phrases:
            # bpm step may have created beatgrids for previously-unanalyzed
            # tracks, so recheck rather than trusting the initial gap list.
            gaps = status(db, ids)
            targets = [t for t in tracks if not gaps[t["track_id"]]["phrases"]]
            if targets:
                print(f"\n[phrases] analyzing {len(targets)} tracks (ffmpeg energy + beatgrid)…")
                done = fill_phrases(db, targets)
                print(f"  phrases: {done} analyzed")
            exported = export_phrases(db, ids)
            print(f"  phrase_analysis.json exported for {exported} tracks")

        gaps = status(db, ids)
        complete = sum(1 for g in gaps.values() if all(g.values()))
        print(f"\nenrichment: {complete}/{len(tracks)} tracks fully enriched")
        for tid, g in gaps.items():
            holes = [k for k, ok in g.items() if not ok]
            if holes:
                track = next(t for t in tracks if t["track_id"] == tid)
                print(f"  incomplete ({', '.join(holes)}): {track['artist']} — {track['title']}")


if __name__ == "__main__":
    main()
