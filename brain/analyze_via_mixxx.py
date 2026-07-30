"""Drives Mixxx's own BPM/key analysis for a playlist through the control
API: loads each playlist track into a (muted) deck, waits for the analyzer
to report a BPM, and moves on.

Important: Mixxx often reports BPM over the control API *minutes* before it
flushes into mixxxdb.sqlite (bpm stays 0 / beats NULL there). So we return
the live API readings and callers must write them into claw-dj's library
index — do not rely on sync_mixxx_analysis alone.

No GUI interaction: needs our patched Mixxx running with
`--control-api-port 9995`. The analyzing deck is kept silent (volume 0,
never playing), so this can run while another deck is live.

Usage: uv run python -m brain.analyze_via_mixxx [--deck 4] [--port 9995] \\
           [--tracks brain/data/preliminary_playlist.json]
--tracks takes any JSON list of records with a "track_id" absolute path
(a crate subset, curated playlist, …); default is the lineage set.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from hands.mixxx_control import DEFAULT_PORT, MixxxControl
from hands.transition import deck_group

SET_JSON = Path(__file__).parent / "data" / "lineage_set.json"
ANALYZE_TIMEOUT_S = 60.0

# Mixxx ChromaticKey enum (library/control value) → musical string used elsewhere.
# Source: mixxx/src/track/keys.h ChromaticKey.
_CHROMATIC_KEY = {
    1: "C",
    2: "Db",
    3: "D",
    4: "Eb",
    5: "E",
    6: "F",
    7: "F#",
    8: "G",
    9: "Ab",
    10: "A",
    11: "Bb",
    12: "B",
    13: "Cm",
    14: "Dbm",
    15: "Dm",
    16: "Ebm",
    17: "Em",
    18: "Fm",
    19: "F#m",
    20: "Gm",
    21: "Abm",
    22: "Am",
    23: "Bbm",
    24: "Bm",
}


def wait_for_bpm(mixxx: MixxxControl, group: str, timeout_s: float) -> float | None:
    """Wait for the deck's analyzer to produce a bpm for the *current* track.

    The deck's bpm control keeps the previous track's value briefly after a
    new load, so eject first (the caller does) and require a fresh non-zero
    reading — otherwise every track after the first "passes" instantly with
    the stale bpm and never actually gets analyzed (bit us 2026-07-12).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        bpm = mixxx.get(group, "bpm")
        if bpm > 0:
            return bpm
        time.sleep(0.5)
    return None


def key_from_control(value: float) -> str | None:
    code = int(round(value))
    return _CHROMATIC_KEY.get(code)


def pending_grid_ids(track_ids: list[str]) -> list[str] | None:
    """Which of these tracks have no persisted BeatGrid-2.0 in mixxxdb yet.

    Returns None when the check could not run at all (no mixxxdb, unreadable
    database) — deliberately distinct from an empty list, which asserts that
    every track's grid IS written. A safety report must never let "could not
    check" look like "all clear".

    A live control-API bpm reading does NOT mean Mixxx wrote a beatgrid to
    its own database, and phrase/beat-phase analysis needs the written grid
    (brain/phrase_analysis.py requires beats_version='BeatGrid-2.0' AND
    beats IS NOT NULL). Per docs/HANDOFF.md the write lands minutes later on
    Mixxx's own schedule.

    Paths are matched EXACTLY. A convenience pattern like '%01. Intro.mp3'
    matches nine different albums in this library, which is precisely how a
    manual check of this behaviour was once read off the wrong track.
    """
    if not track_ids:
        return []
    try:
        from shared.mixxx_db import connect_readonly

        conn = connect_readonly()
    except Exception:
        return None
    try:
        persisted = set()
        for track_id in track_ids:
            row = conn.execute(
                """SELECT 1 FROM library
                   JOIN track_locations ON library.location = track_locations.id
                   WHERE track_locations.location = ?
                     AND library.beats_version = 'BeatGrid-2.0'
                     AND library.beats IS NOT NULL""",
                (track_id,),
            ).fetchone()
            if row:
                persisted.add(track_id)
    except Exception:
        return None
    finally:
        conn.close()
    return [track_id for track_id in track_ids if track_id not in persisted]


def analyze_tracks(
    records: list[dict],
    *,
    deck: int = 4,
    port: int = DEFAULT_PORT,
    timeout_s: float = ANALYZE_TIMEOUT_S,
    progress=None,
) -> list[dict]:
    """Load each record into a muted deck; return live API analysis rows.

    Each result: {track_id, artist, title, bpm, key, ok}.
    `progress`, if given, is called with each per-track status line — lets
    a web UI stream real-time console output instead of one static message
    for the whole batch.
    """
    def emit(msg: str) -> None:
        print(msg)
        if progress:
            progress(msg)

    group = deck_group(deck)
    results: list[dict] = []
    with MixxxControl(port=port, timeout_s=timeout_s + 10) as mixxx:
        mixxx.set(group, "volume", 0.0)
        for i, record in enumerate(records, 1):
            track_id = record["track_id"]
            label = (
                f"[{i}/{len(records)}] {record['artist']} - {record['title']}"
                if "artist" in record
                else f"[{i}/{len(records)}] {track_id}"
            )
            emit(label)
            # Eject so the bpm control drops to 0 before the next load — a
            # stale non-zero reading otherwise satisfies wait_for_bpm
            # immediately and the track never gets analyzed.
            #
            # Ejecting does NOT flush the previous track's analysis to
            # mixxxdb, despite what this comment used to claim. Measured
            # 2026-07-30: eject alone leaves beats NULL indefinitely, and so
            # does reloading the same track; only LOADING A DIFFERENT track
            # persists the pending grid. That is why the loop below is
            # followed by an explicit flush pass — otherwise the final track
            # of every batch is left unpersisted.
            mixxx.set(group, "eject", 1)
            time.sleep(1.0)
            mixxx.set(group, "eject", 0)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and mixxx.get(group, "bpm") > 0:
                time.sleep(0.5)
            mixxx.load(deck, track_id)
            bpm = wait_for_bpm(mixxx, group, timeout_s)
            key_str = None
            if bpm is not None:
                # Key often appears a beat after bpm; poll briefly.
                for _ in range(10):
                    try:
                        key_str = key_from_control(mixxx.get(group, "key"))
                    except Exception:
                        key_str = None
                    if key_str:
                        break
                    time.sleep(0.3)
                emit(f"    mixxx bpm: {bpm:.2f}" + (f"  key: {key_str}" if key_str else ""))
            else:
                emit("    analyzer produced no bpm (timeout)")
            # Keep the track loaded a moment so Mixxx has a chance to start
            # writing analysis — still not reliable, which is why we persist
            # the API reading ourselves.
            time.sleep(1.0)
            results.append(
                {
                    "track_id": track_id,
                    "artist": record.get("artist"),
                    "title": record.get("title"),
                    "bpm": bpm,
                    "key": key_str,
                    "ok": bpm is not None and bpm > 0,
                }
            )
    ok = sum(1 for row in results if row["ok"])
    print(f"\n{ok}/{len(records)} analyzed via control API (live reading).")
    print("Persist with brain.enrich_set / apply_analysis — Mixxx DB flush is lazy.")

    # bpm/key are safe (we persist the live reading ourselves), but phrases and
    # beat_phase need Mixxx's WRITTEN grid, which lands on its own schedule.
    # Say which tracks are still waiting instead of letting the gap surface
    # later as a silently skipped track in enrich_set.
    pending = pending_grid_ids([row["track_id"] for row in results if row["ok"]])
    if pending is None:
        print("\ncould not read mixxxdb to check which beatgrids were written.")
    elif pending:
        print(
            f"\n{len(pending)} of {ok} track(s) have no written Mixxx beatgrid yet "
            "— bpm/key are saved, but phrases/beat_phase will skip them:"
        )
        for track_id in pending:
            print(f"    pending: {Path(track_id).name}")
        print(
            "  Mixxx writes the grid minutes later on its own schedule; a clean "
            "quit does not force it. Re-run Analyze & enrich later to pick them "
            "up, or right-click → Analyze in Mixxx, which always persists."
        )
    return results


def apply_analysis(results: list[dict]) -> int:
    """Write control-API bpm/key into library index + crate.json immediately.

    This is the reliable path when mixxxdb still shows bpm=0 after analysis.
    """
    from contextlib import closing

    from brain.library import DEFAULT_CRATE_CACHE
    from brain.library_index import connect, export_records

    written = 0
    with closing(connect()) as db:
        for row in results:
            if not row.get("ok") or not row.get("bpm"):
                continue
            db.execute(
                "UPDATE tracks SET bpm=?, key=COALESCE(?, key) WHERE track_id=?",
                (float(row["bpm"]), row.get("key"), row["track_id"]),
            )
            written += 1
        db.commit()
        records = export_records()
    if records:
        DEFAULT_CRATE_CACHE.write_text(json.dumps(records, indent=2) + "\n")
    print(f"applied {written} control-API bpm/key rows -> library index + crate.json")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck", type=int, default=4, help="deck used for analysis loads")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--tracks",
        type=Path,
        default=SET_JSON,
        help='JSON list of records with a "track_id" path (crate subset, playlist, …)',
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write live API bpm/key into claw-dj library index (recommended)",
    )
    args = parser.parse_args()

    records = json.loads(args.tracks.read_text())
    results = analyze_tracks(records, deck=args.deck, port=args.port)
    if args.apply:
        apply_analysis(results)
    else:
        print("Tip: re-run with --apply to persist bpm/key even when Mixxx DB lags.")


if __name__ == "__main__":
    main()
