"""Verse/chorus timelines from synced lyrics — the cut points for
lyric-aware transitions.

LRCLIB's `syncedLyrics` gives per-line `[mm:ss.xx]` timestamps. From those:

  1. parse the LRC into (seconds, text) lines
  2. detect choruses by repetition — chorus lines recur near-verbatim,
     verse lines don't — and group consecutive lines into segments
  3. snap each segment's vocal start to the nearest bar (4 beats) of the
     track's Mixxx beatgrid, so a "cut in when the rapper starts" lands
     on the grid

Segments persist in SQLite (`lyric_timelines`) keyed by track, and are the
foundation for the verse-tour technique (same song on two decks, verse to
verse, chorus skipped) and chorus-skip cuts between songs.

Usage:
    uv run python -m brain.lyric_timeline                 # finalized set
    uv run python -m brain.lyric_timeline --show <query>  # print one timeline
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from brain.playlist import DEFAULT_PLAYLIST_JSON, normalize

LRC_TIME = re.compile(r"\[(\d+):(\d{1,2}(?:[.:]\d{1,3})?)\]")

# A repeated line must be this long (words) to count as chorus evidence —
# short ad-libs ("yeah", "uh huh") repeat everywhere.
MIN_CHORUS_WORDS = 3
# Lines repeating at least this often are chorus material.
MIN_REPEATS = 2
# A silent gap this long between lines starts a new segment (instrumental
# break / beat riding between verses).
GAP_SECONDS = 12.0


@dataclass(frozen=True)
class LyricLine:
    t: float
    text: str


@dataclass
class Segment:
    kind: str            # "verse" | "chorus"
    start: float         # first line's timestamp (vocal onset)
    end: float           # start of the next segment (or last line time)
    bar_start: float | None  # start snapped to the nearest beatgrid bar
    beat_index: int | None   # bar_start expressed in beats from beat 0
    lines: int
    first_line: str


def parse_lrc(lrc: str) -> list[LyricLine]:
    """LRC text → time-sorted lyric lines. Handles multiple timestamps per
    line ([00:10.00][01:20.00]shared hook line)."""
    lines: list[LyricLine] = []
    for raw in (lrc or "").splitlines():
        stamps = LRC_TIME.findall(raw)
        if not stamps:
            continue
        text = LRC_TIME.sub("", raw).strip()
        if not text:
            continue
        for minutes, seconds in stamps:
            lines.append(LyricLine(int(minutes) * 60 + float(seconds.replace(":", ".")), text))
    return sorted(lines, key=lambda line: line.t)


def detect_segments(lines: list[LyricLine]) -> list[Segment]:
    """Group lines into verse/chorus segments by repetition + silence gaps."""
    if not lines:
        return []
    norms = [normalize(line.text) for line in lines]
    counts = Counter(n for n in norms if len(n.split()) >= MIN_CHORUS_WORDS)
    chorus_lines = {n for n, c in counts.items() if c >= MIN_REPEATS}

    labels = ["chorus" if n in chorus_lines else "verse" for n in norms]
    # Smooth single-line islands: a lone verse line inside a chorus (or the
    # reverse) is usually a variation of its neighbours, not a real segment.
    for i in range(1, len(labels) - 1):
        if labels[i - 1] == labels[i + 1] != labels[i]:
            labels[i] = labels[i - 1]

    segments: list[Segment] = []
    start_index = 0
    for i in range(1, len(lines) + 1):
        boundary = (
            i == len(lines)
            or labels[i] != labels[start_index]
            or lines[i].t - lines[i - 1].t >= GAP_SECONDS
        )
        if not boundary:
            continue
        block = lines[start_index:i]
        segments.append(
            Segment(
                kind=labels[start_index],
                start=round(block[0].t, 3),
                end=round(lines[i].t if i < len(lines) else block[-1].t, 3),
                bar_start=None,
                beat_index=None,
                lines=len(block),
                first_line=block[0].text[:80],
            )
        )
        start_index = i
    return segments


def snap_segments(
    segments: list[Segment], *, bpm: float, first_beat_seconds: float
) -> list[Segment]:
    """Snap each vocal onset to the nearest bar (4-beat) boundary of the
    Mixxx beatgrid, so cuts land on the grid instead of mid-bar."""
    if not bpm or bpm <= 0:
        return segments
    bar = 4 * 60.0 / bpm
    for segment in segments:
        bars_in = round((segment.start - first_beat_seconds) / bar)
        segment.bar_start = round(max(0.0, first_beat_seconds + bars_in * bar), 3)
        segment.beat_index = max(0, bars_in * 4)
    return segments


def verse_starts(segments: list[dict]) -> list[dict]:
    """The cut-in points: every verse segment's snapped start."""
    return [
        {"t": s.get("bar_start") or s["start"], "beat_index": s.get("beat_index"),
         "first_line": s["first_line"]}
        for s in segments
        if s["kind"] == "verse"
    ]


def _beatgrid_for(track_id: str) -> tuple[float, float] | None:
    from brain.phrase_analysis import decode_beat_grid
    from shared.mixxx_db import connect_readonly

    conn = connect_readonly()
    try:
        row = conn.execute(
            """
            SELECT library.samplerate, library.beats
            FROM library JOIN track_locations ON library.location = track_locations.id
            WHERE track_locations.location = ?
              AND library.beats_version = 'BeatGrid-2.0' AND library.beats IS NOT NULL
            """,
            (track_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    bpm, first_frame = decode_beat_grid(bytes(row[1]))
    return bpm, first_frame / float(row[0])


def build_for_tracks(db, tracks: list[dict], *, force: bool = False) -> dict:
    """Fill `lyric_timelines` for tracks missing one. Check-before-fetch:
    cached lyric hits without a synced_lyrics field are refetched once."""
    from brain.lyrics import fetch_lyrics

    have = {
        row[0] for row in db.execute("SELECT track_id FROM lyric_timelines")
    }
    built = no_synced = 0
    for track in tracks:
        if track["track_id"] in have and not force:
            continue
        record = fetch_lyrics(track["artist"], track["title"])
        if record.get("found") and "synced_lyrics" not in record:
            # cache predates the synced-lyrics field — refetch once
            record = fetch_lyrics(track["artist"], track["title"], force=True)
        lrc = record.get("synced_lyrics")
        lines = parse_lrc(lrc) if lrc else []
        if not lines:
            no_synced += 1
            print(f"  [timeline] no synced lyrics: {track['artist']} — {track['title']}")
            db.execute(
                "INSERT OR REPLACE INTO lyric_timelines(track_id, computed_at, source, lrc, segments)"
                " VALUES (?,?,?,?,?)",
                (track["track_id"], time.time(), record.get("source") or "not_found",
                 None, json.dumps([])),
            )
            continue
        segments = detect_segments(lines)
        grid = _beatgrid_for(track["track_id"])
        if grid:
            segments = snap_segments(segments, bpm=grid[0], first_beat_seconds=grid[1])
        db.execute(
            "INSERT OR REPLACE INTO lyric_timelines(track_id, computed_at, source, lrc, segments)"
            " VALUES (?,?,?,?,?)",
            (track["track_id"], time.time(), record.get("source") or "lrclib",
             lrc, json.dumps([asdict(s) for s in segments])),
        )
        built += 1
    db.commit()
    return {"built": built, "no_synced": no_synced, "already": len(have)}


def show_timeline(db, query: str) -> None:
    rows = db.execute(
        "SELECT lt.track_id, lt.segments FROM lyric_timelines lt WHERE lt.track_id LIKE ?",
        (f"%{query}%",),
    ).fetchall()
    for track_id, payload in rows:
        segments = json.loads(payload)
        print(Path(track_id).stem)
        for s in segments:
            snapped = f" (bar {s['bar_start']:.1f}s, beat {s['beat_index']})" if s.get("bar_start") is not None else ""
            print(f"  {s['start']:7.1f}s  {s['kind']:6s} ×{s['lines']:2d}{snapped}  “{s['first_line']}”")


def main() -> None:
    from contextlib import closing

    from brain.library_index import connect

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST_JSON)
    parser.add_argument("--force", action="store_true", help="rebuild even if a timeline exists")
    parser.add_argument("--show", default=None, help="print the stored timeline for tracks matching this path substring")
    args = parser.parse_args()

    with closing(connect()) as db:
        if args.show is not None:
            show_timeline(db, args.show)
            return
        payload = json.loads(args.playlist.read_text())
        tracks = payload["tracks"] if isinstance(payload, dict) else payload
        print(f"building lyric timelines for {len(tracks)} tracks…")
        summary = build_for_tracks(db, tracks, force=args.force)
        print(
            f"timelines: {summary['built']} built, {summary['no_synced']} without synced lyrics, "
            f"{summary['already']} already stored"
        )


if __name__ == "__main__":
    main()
