"""Enrich the finalized playlist with everything the mix stage needs.

Runs AFTER "Finalize for Mixxx" and only over the finalized set — never the
full crate. Steps check SQLite or the shared rhythm cache and fill gaps:

  1. bpm/key   — muted-deck Mixxx analysis over the control API (port 9995)
  2. lyrics    — LRCLIB (cached on disk), full text into the `lyrics` table
  3. chroma    — Rust `clawdj chroma` 12-dim pitch fingerprints per track;
                 also rewrites chroma_similarity.json for the whole set so
                 mix ordering/plan techniques get real texture coverage
  4. phrases   — beat-aligned energy cue analysis (intro/body entries) into
                 the `phrases` table + phrase_analysis.json for the planner
  5. backbeat — Rust multiband percussion/section analysis in the shared
                 rhythm cache. Runs after phrases, without deck control.
                 Build reuses it for pair/cue-specific entrances; playback
                 still verifies actual positions/rates.
  6. beat_phase — real onset/waveform snare-parity analysis (which beat-in-
                 bar carries the backbeat) into the `beat_phase` table;
                 depends on phrases (bpm/first_beat_seconds come from
                 there). Retained for legacy compatibility, not proof that
                 the new backbeat analysis is complete.

Usage:
    uv run python -m brain.enrich_set                # fill all missing
    uv run python -m brain.enrich_set --status       # report only
    uv run python -m brain.enrich_set --skip-lyrics --skip-chroma
"""
from __future__ import annotations

import argparse
import json
import os
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


def rhythm_inputs(db, track_ids: list[str]) -> dict[str, dict]:
    """Source grids, independent of plan order/cues and playback tempo holds."""
    if not track_ids:
        return {}
    rows = db.execute(
        f"SELECT track_id, payload FROM phrases WHERE track_id IN ({','.join('?' * len(track_ids))})",
        track_ids,
    ).fetchall()
    result = {}
    for tid, encoded in rows:
        try:
            payload = json.loads(encoded)
            bpm, first = float(payload["bpm"]), float(payload["first_beat_seconds"])
            if not 35 <= bpm <= 300 or not math.isfinite(first) or not -1 <= first <= 86400:
                continue
            result[tid] = {"track_id": tid, "bpm": bpm, "first_beat_seconds": first}
        except (ValueError, TypeError, KeyError):
            continue  # Invalid/missing grids are a gap, never an assumed beat 1.
    return result


def backbeat_status(db, track_ids: list[str]) -> dict[str, dict | None]:
    from brain.rhythm import analysis_status

    grids = rhythm_inputs(db, track_ids)
    return {
        tid: analysis_status(grids[tid], first_beat=grids[tid]["first_beat_seconds"]) if tid in grids else None
        for tid in track_ids
    }


def fill_backbeat(db, tracks: list[dict], *, progress=None) -> dict:
    """Prepare per-track evidence only; never build a plan or drive Mixxx."""
    from brain.rhythm import analyze_track

    grids = rhythm_inputs(db, [t["track_id"] for t in tracks])
    result = {"prepared": 0, "errors": {}}
    for i, track in enumerate(tracks, 1):
        tid = track["track_id"]
        if progress:
            progress(f"  [backbeat] [{i}/{len(tracks)}] {track.get('artist')} — {track.get('title')}")
        try:
            if tid not in grids:
                raise ValueError("missing valid phrase/source beatgrid; analyze phrases first")
            grid = grids[tid]
            evidence = analyze_track({**track, "bpm": grid["bpm"]}, first_beat=grid["first_beat_seconds"])
            result["prepared"] += 1
            weak = sum(s["confidence"] < 0.45 for s in evidence["sections"])
            if progress:
                progress(f"    cached {len(evidence['sections'])} sections; {weak} uncertain (Build checks the selected overlap)")
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            result["errors"][tid] = str(error)
            if progress:
                progress(f"    [backbeat] unavailable: {error}")
    return result


def load_set(playlist_path: Path) -> list[dict]:
    payload = json.loads(playlist_path.read_text())
    return payload["tracks"] if isinstance(payload, dict) else payload


def status(db, track_ids: list[str]) -> dict[str, dict]:
    rhythms = backbeat_status(db, track_ids)
    have = {
        table: {
            row[0] for row in db.execute(
                f"SELECT track_id FROM {table} WHERE track_id IN ({','.join('?' * len(track_ids))})",
                track_ids,
            )
        }
        for table in ("lyrics", "chroma", "phrases", "lyric_timelines", "beat_phase")
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
            # real onset/waveform snare-parity analysis (brain.onset_analysis)
            # -- depends on phrases (that's where bpm/first_beat_seconds come
            # from), so it belongs after phrases in the pipeline.
            "beat_phase": tid in have["beat_phase"],
            "backbeat": rhythms[tid] is not None,
        }
        for tid in track_ids
    }


def fill_bpm(missing: list[dict], port: int, *, progress=None) -> None:
    """Analyze via control API and persist readings into claw-dj immediately.

    Do not wait solely on Mixxx DB flush — the control API often has bpm
    while mixxxdb still shows 0 (Many Man / Many Men case, 2026-07-12).
    """
    from brain.analyze_via_mixxx import analyze_tracks, apply_analysis

    results = analyze_tracks(missing, port=port, progress=progress)
    apply_analysis(results)
    # Best-effort: also pull anything Mixxx *did* flush (keys, older tracks).
    time.sleep(2)
    subprocess.run([sys.executable, "-m", "brain.sync_mixxx_analysis"], check=False)


def fill_lyrics(db, tracks: list[dict], *, force: bool = False, progress=None) -> tuple[int, int]:
    from brain.lyrics import fetch_lyrics

    found = missed = 0
    for i, track in enumerate(tracks, 1):
        label = f"[{i}/{len(tracks)}] {track['artist']} — {track['title']}"
        if progress:
            progress(f"  [lyrics] {label}")
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
            msg = f"  [lyrics] not found: {track['artist']} — {track['title']}"
            print(msg)
            if progress:
                progress(msg)
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


def fill_phrases(db, tracks: list[dict], *, max_seconds: float = 300.0, progress=None) -> int:
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
        for i, track in enumerate(tracks, 1):
            label = f"[{i}/{len(tracks)}] {track['artist']} — {track['title']}"
            if progress:
                progress(f"  [phrases] {label}")
            row = mixxx.execute(query, (track["track_id"],)).fetchone()
            if row is None:
                msg = f"  [phrases] no Mixxx beatgrid yet: {track['artist']} — {track['title']}"
                print(msg)
                if progress:
                    progress(msg)
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


def fill_beat_phase(db, tracks: list[dict], *, max_seconds: float = 240.0, progress=None) -> int:
    """Fill `beat_phase` (real onset/waveform snare-parity analysis).

    Depends on `phrases` already being filled -- that's where bpm/
    first_beat_seconds come from (Mixxx's own analyzed beatgrid), so this
    step belongs after phrases in the enrichment order. See
    brain.onset_analysis for what "snare parity" means and why.
    """
    from brain.onset_analysis import detect_snare_phase

    analyzed = 0
    for i, track in enumerate(tracks, 1):
        label = f"[{i}/{len(tracks)}] {track['artist']} — {track['title']}"
        if progress:
            progress(f"  [beat_phase] {label}")
        row = db.execute(
            "SELECT payload FROM phrases WHERE track_id = ?", (track["track_id"],)
        ).fetchone()
        if row is None:
            msg = f"  [beat_phase] no phrase/beatgrid data yet: {track['artist']} — {track['title']}"
            print(msg)
            if progress:
                progress(msg)
            continue
        payload = json.loads(row[0])
        bpm, first_beat = payload.get("bpm"), payload.get("first_beat_seconds")
        if not bpm or first_beat is None:
            continue
        result = detect_snare_phase(
            track["track_id"], bpm=bpm, first_beat_seconds=first_beat, max_seconds=max_seconds
        )
        db.execute(
            "INSERT OR REPLACE INTO beat_phase"
            "(track_id, analyzed_at, snare_parity, confidence, bpm, first_beat_seconds) "
            "VALUES (?,?,?,?,?,?)",
            (
                track["track_id"], time.time(), result["snare_parity"], result["confidence"],
                bpm, first_beat,
            ),
        )
        analyzed += 1
    db.commit()
    return analyzed


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
        rhythms = backbeat_status(db, ids)
    need = {
        field: [
            {"artist": t.get("artist"), "title": t.get("title"), "track_id": t["track_id"]}
            for t in tracks
            if not gaps[t["track_id"]][field]
        ]
        for field in ("bpm_key", "lyrics", "chroma", "phrases", "beat_phase", "backbeat")
    }
    complete = sum(1 for g in gaps.values() if all(g.values()))
    return {
        "ready": True,
        "count": len(tracks),
        "complete": complete,
        "missing": {k: len(v) for k, v in need.items()},
        "missing_tracks": need,
        "backbeat": {
            "analyzed": sum(r is not None for r in rhythms.values()),
            "missing_or_stale": len(need["backbeat"]),
            "tracks_with_uncertain_sections": sum(bool(r and r["uncertain_sections"]) for r in rhythms.values()),
            "note": "Backbeat = snare/clap. Cached track analysis is not blend readiness; Build checks the selected overlaps, playback verifies live timing.",
        },
        "message": (
            f"{complete}/{len(tracks)} fully enriched · "
            f"missing bpm/key {len(need['bpm_key'])}, lyrics {len(need['lyrics'])}, "
            f"chroma {len(need['chroma'])}, phrases {len(need['phrases'])}, "
            f"beat_phase (legacy) {len(need['beat_phase'])}, "
            f"backbeat (missing/stale) {len(need['backbeat'])}"
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
    skip_beat_phase: bool = False,
    skip_backbeat: bool = False,
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
        "beat_phase_analyzed": 0,
        "backbeat_analyzed": 0,
        "backbeat_errors": {},
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
            for field in ("bpm_key", "lyrics", "chroma", "phrases", "timeline", "beat_phase", "backbeat")
        }
        for field, rows in need.items():
            note(f"missing {field}: {len(rows)}")

        bpm_targets = list(need["bpm_key"])
        if need["phrases"] and not skip_bpm:
            # A BPM imported from tags is enough for ordinary mix planning but
            # does not prove Mixxx has a persisted BeatGrid-2.0. Phrase and
            # guided-format analysis require that written grid. Include any
            # phrase-missing tracks whose Mixxx grid is absent even when their
            # local BPM field is already populated.
            from brain.analyze_via_mixxx import pending_grid_ids

            pending = pending_grid_ids(
                [track["track_id"] for track in need["phrases"]]
            )
            if pending is not None:
                pending_set = set(pending)
                known = {track["track_id"] for track in bpm_targets}
                bpm_targets.extend(
                    track
                    for track in need["phrases"]
                    if track["track_id"] in pending_set
                    and track["track_id"] not in known
                )

        if bpm_targets and not skip_bpm:
            note(
                f"[bpm/grid] analyzing {len(bpm_targets)} tracks via muted "
                "Mixxx deck…"
            )
            fill_bpm(bpm_targets, port, progress=note)
            summary["bpm_analyzed"] = len(bpm_targets)
            # Re-read playlist rows from disk after crate sync? fill_bpm only
            # updates index/crate; playlist.json is refreshed by the editor.
            note("[bpm/grid] Mixxx analysis + sync_mixxx_analysis done")
        elif skip_bpm:
            note("[bpm/key] skipped")

        lyric_targets = tracks if force_lyrics else need["lyrics"]
        if lyric_targets and not skip_lyrics:
            note(f"[lyrics] fetching {len(lyric_targets)} tracks from LRCLIB…")
            found, missed = fill_lyrics(db, lyric_targets, force=force_lyrics, progress=note)
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
                done = fill_phrases(db, targets, progress=note)
                summary["phrases_analyzed"] = done
                note(f"phrases: {done} analyzed")
            exported = export_phrases(db, ids)
            summary["phrases_exported"] = exported
            note(f"phrase_analysis.json exported for {exported} tracks")
        else:
            note("[phrases] skipped")

        if not skip_backbeat:
            gaps = status(db, ids)
            targets = [t for t in tracks if not gaps[t["track_id"]]["backbeat"]]
            if targets:
                note(f"[backbeat] multiband percussion/section analysis for {len(targets)} missing or stale tracks…")
                result = fill_backbeat(db, targets, progress=note)
                summary["backbeat_analyzed"] = result["prepared"]
                summary["backbeat_errors"] = result["errors"]
                note(f"backbeat: {result['prepared']} prepared, {len(result['errors'])} unavailable")
            else:
                note(f"[backbeat] all {len(tracks)} tracks have current cached rhythm analysis")
            note("[backbeat] Build uses the cache for cue-preserving entrances; live playback verifies alignment")
        else:
            note("[backbeat] skipped")

        if not skip_beat_phase:
            # Depends on phrases (bpm/first_beat_seconds come from there) --
            # tracks phrases just filled above are immediately eligible.
            gaps = status(db, ids)
            targets = [t for t in tracks if not gaps[t["track_id"]]["beat_phase"]]
            if targets:
                note(f"[beat_phase] real onset/waveform analysis for {len(targets)} tracks…")
                done = fill_beat_phase(db, targets, progress=note)
                summary["beat_phase_analyzed"] = done
                note(f"beat_phase: {done} analyzed")
        else:
            note("[beat_phase] skipped")

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
        retryable = 0
        for tid, g in gaps.items():
            holes = [k for k, ok in g.items() if not ok]
            if holes:
                track = next(t for t in tracks if t["track_id"] == tid)
                # Tell the user WHICH gaps a re-run can actually fix.
                # Chroma on .m4a: the Rust/Symphonia decoder can't read
                # these files' channel layout — a permanent limitation;
                # the fix is swapping the playlist to an mp3 copy of the
                # same song if one exists. Phrases: Mixxx flushes deck
                # analysis to its DB minutes late, so "no Mixxx beatgrid
                # yet" heals on its own — re-running later fixes it.
                is_m4a = tid.lower().endswith(".m4a")
                hints = []
                if "chroma" in holes and is_m4a:
                    hints.append("chroma: m4a decode limitation — re-running "
                                 "won't help; swap to an mp3 copy if one exists")
                if "phrases" in holes:
                    hints.append("phrases: Mixxx flushes analysis lazily — "
                                 "re-run Analyze in a few minutes")
                    retryable += 1
                if "chroma" in holes and not is_m4a:
                    hints.append("chroma: re-run may help")
                    retryable += 1
                if "beat_phase" in holes and "phrases" in holes:
                    hints.append("beat_phase: depends on phrases (bpm/grid) — "
                                 "will fill once phrases succeeds, same re-run")
                elif "beat_phase" in holes:
                    hints.append("beat_phase: re-run Analyze — should fill "
                                 "now that phrases exist")
                    retryable += 1
                if "backbeat" in holes:
                    reason = summary["backbeat_errors"].get(tid, "missing or stale cache; run Analyze & enrich missing")
                    hints.append(f"backbeat: {reason}")
                row = {
                    "artist": track.get("artist"),
                    "title": track.get("title"),
                    "track_id": tid,
                    "missing": holes,
                    "hints": hints,
                }
                summary["incomplete"].append(row)
                note(f"incomplete ({', '.join(holes)}): {track.get('artist')} — {track.get('title')}")
                for hint in hints:
                    note(f"    ↳ {hint}")
        summary["retryable"] = retryable
        note(f"enrichment: {summary['complete']}/{len(tracks)} tracks fully enriched")
        if retryable:
            note(f"re-running Analyze later can fix {retryable} of the gaps above")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST_JSON)
    parser.add_argument(
        "--port",
        type=int,
        default=(
            int(os.environ["CLAWDJ_MIXXX_CONTROL_PORT"])
            if os.environ.get("CLAWDJ_MIXXX_CONTROL_PORT")
            else None
        ),
        help="explicit Mixxx control port; otherwise validate/discover it from the running process",
    )
    parser.add_argument("--status", action="store_true", help="report gaps, change nothing")
    parser.add_argument("--skip-bpm", action="store_true")
    parser.add_argument("--skip-lyrics", action="store_true")
    parser.add_argument("--skip-chroma", action="store_true")
    parser.add_argument("--skip-phrases", action="store_true")
    parser.add_argument("--skip-timelines", action="store_true")
    parser.add_argument("--skip-beat-phase", action="store_true")
    parser.add_argument("--skip-backbeat", action="store_true", help="skip multiband percussion and section-local rhythm analysis")
    parser.add_argument("--force-lyrics", action="store_true")
    args = parser.parse_args()

    if args.status:
        report = enrichment_status(args.playlist)
        print(report.get("message") or report)
        for field, rows in (report.get("missing_tracks") or {}).items():
            for row in rows[:20]:
                print(f"  missing {field}: {row['artist']} — {row['title']}")
        return

    from hands.mixxx_control import DEFAULT_PORT, discover_mixxx_control_port

    port = (args.port or DEFAULT_PORT) if args.skip_bpm else discover_mixxx_control_port(
        preferred=DEFAULT_PORT,
        explicit=args.port,
    )
    run_enrich(
        playlist_path=args.playlist,
        port=port,
        skip_bpm=args.skip_bpm,
        skip_lyrics=args.skip_lyrics,
        skip_chroma=args.skip_chroma,
        skip_phrases=args.skip_phrases,
        skip_timelines=args.skip_timelines,
        skip_beat_phase=args.skip_beat_phase,
        skip_backbeat=args.skip_backbeat,
        force_lyrics=args.force_lyrics,
    )


if __name__ == "__main__":
    main()
