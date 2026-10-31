"""The stem crate: every vocals-only and instrumental-only track in the library.

Read-only lists for the GUI Stems page and the CLI, with BPM, key and length.
Mixxx's own analysis wins over file tags for BPM/key; unknown stays None
(Mixxx analyzes a track when it loads). A hand override is the
`track_kind=<kind>` token in the track's global DJ note (brain.stems).

    python -m brain.stem_crate list [--kind vocals|instrumentals] [--search Q] [--json]
    python -m brain.stem_crate set-kind TRACK_ID vocals_only|instrumental_only|full_mix|auto
    python -m brain.stem_crate beds VOCAL_TRACK_ID [--limit 10]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from brain import library_index
from brain.mix_graph import bpm_compatibility, key_compatibility
from brain.stems import (
    KINDS,
    TRACK_KIND,
    classify_track,
    core_title,
    is_clean_version,
)

# Cheap SQL prefilter: every name rule in brain.stems needs one of these
# substrings in the title or path (acapella spellings all contain "cap" or
# "apel"; instrumental tags contain "inst" or "karaoke"; stems say "vocal").
_PREFILTER = ("%inst%", "%cap%", "%apel%", "%vocal%", "%karaoke%", "%track_kind=%")
KIND_ALIASES = {
    "vocals": "vocals_only", "vocal": "vocals_only", "acapella": "vocals_only",
    "vocals_only": "vocals_only",
    "instrumentals": "instrumental_only", "instrumental": "instrumental_only",
    "instrumental_only": "instrumental_only",
    "full_mix": "full_mix",
}


def _index(path: Path | None) -> Path:
    return Path(path) if path else library_index.current_index_path()


def _mixxx_analysis(track_ids: list[str], mixxx_db: Path | None = None) -> dict[str, dict]:
    """{track_id: {bpm, key, duration_seconds, replaygain}} from Mixxx, read-only."""
    try:
        from shared.mixxx_db import connect_readonly

        db = connect_readonly(mixxx_db)
    except (FileNotFoundError, sqlite3.Error):
        return {}
    out: dict[str, dict] = {}
    with closing(db):
        for start in range(0, len(track_ids), 400):
            chunk = track_ids[start:start + 400]
            marks = ",".join("?" for _ in chunk)
            try:
                rows = db.execute(
                    "SELECT t.location, l.bpm, l.key, l.duration, l.replaygain FROM library l "
                    f"JOIN track_locations t ON l.location = t.id WHERE t.location IN ({marks}) "
                    "AND l.mixxx_deleted = 0",
                    chunk,
                ).fetchall()
            except sqlite3.Error:
                return out
            for location, bpm, key, duration, replaygain in rows:
                out[location] = {
                    "bpm": float(bpm) if bpm and bpm > 0 else None,
                    "key": key or None,
                    "duration_seconds": float(duration) if duration and duration > 0 else None,
                    "replaygain": float(replaygain) if replaygain and replaygain > 0 else None,
                }
    return out


def _row(record: dict, kind: dict, mixxx: dict | None) -> dict[str, Any]:
    mixxx = mixxx or {}
    bpm = mixxx.get("bpm") or record.get("bpm")
    key = mixxx.get("key") or record.get("key")
    return {
        "track_id": record["track_id"],
        "artist": record.get("artist") or "",
        "title": record.get("title") or "",
        "album": record.get("album") or "",
        "genre": record.get("genre") or "",
        "kind": kind["kind"],
        "kind_source": kind["source"],
        "kind_evidence": kind["evidence"],
        "clean": is_clean_version(record.get("title") or ""),
        "bpm": round(float(bpm), 2) if bpm else None,
        "bpm_source": "mixxx" if mixxx.get("bpm") else ("tags" if record.get("bpm") else None),
        "key": key,
        "duration_seconds": mixxx.get("duration_seconds") or record.get("duration_seconds"),
        "in_mixxx": bool(mixxx),
    }


def scan(index_path: Path | None = None, *, mixxx_db: Path | None = None,
         with_mixxx: bool = True) -> list[dict[str, Any]]:
    """Every available vocals-only / instrumental-only track (and overrides)."""
    clause = " OR ".join(
        "lower(title) LIKE ? OR lower(track_id) LIKE ? OR lower(dj_notes) LIKE ?" for _ in _PREFILTER
    )
    params = [pattern for pattern in _PREFILTER for _ in range(3)]
    with closing(library_index.connect(_index(index_path))) as db:
        rows = db.execute(
            "SELECT track_id, title, artist, album, genre, duration_seconds, bpm, key, dj_notes "
            f"FROM tracks WHERE available = 1 AND ({clause}) ORDER BY artist, title",
            params,
        ).fetchall()
    records = [dict(row) for row in rows]
    stems = []
    for record in records:
        kind = classify_track(record["title"] or "", record["track_id"], record.get("dj_notes") or "")
        if kind["kind"] != "full_mix" or kind["source"] == "override":
            stems.append((record, kind))
    analysis = _mixxx_analysis([r["track_id"] for r, _ in stems], mixxx_db) if with_mixxx else {}
    rows = [_row(record, kind, analysis.get(record["track_id"])) for record, kind in stems]
    rows.sort(key=lambda row: (row["artist"].strip().casefold(), row["title"].strip().casefold(), row["track_id"]))
    return rows


def _matches(row: dict, query: str) -> bool:
    if not query:
        return True
    hay = f"{row['artist']} {row['title']} {row['album']} {row['genre']}".lower().replace("'", "").replace("\u2019", "")
    query = query.replace("'", "").replace("\u2019", "")
    return all(word in hay for word in query.lower().split())


def list_stems(kind: str | None = None, *, search: str = "", index_path: Path | None = None,
               mixxx_db: Path | None = None, rows: list[dict] | None = None) -> dict[str, Any]:
    """{"vocals_only": [...], "instrumental_only": [...], "counts": {...}}."""
    wanted = KIND_ALIASES.get((kind or "").lower()) if kind else None
    if kind and not wanted:
        raise ValueError(f"unknown kind {kind!r}; use vocals or instrumentals")
    rows = scan(index_path, mixxx_db=mixxx_db) if rows is None else rows
    result: dict[str, Any] = {"vocals_only": [], "instrumental_only": []}
    for row in rows:
        if row["kind"] in result and (wanted is None or row["kind"] == wanted) and _matches(row, search):
            result[row["kind"]].append(row)
    result["counts"] = {name: len(result[name]) for name in ("vocals_only", "instrumental_only")}
    return result


def _strip_kind(note: str) -> str:
    stripped = TRACK_KIND.sub("", note or "")
    stripped = re.sub(r"\s*;\s*(;\s*)+", "; ", stripped)
    return stripped.strip().strip(";").strip()


def set_track_kind(track_id: str, kind: str, index_path: Path | None = None) -> dict[str, Any]:
    """Hand override, stored as `track_kind=<kind>` in the global DJ note.

    `auto` removes the override so the name rules decide again. Other note
    text is preserved. Returns the new classification.
    """
    kind = KIND_ALIASES.get(kind.lower(), kind.lower())
    if kind not in KINDS and kind != "auto":
        raise ValueError(f"kind must be one of {', '.join(KINDS)} or auto")
    with closing(library_index.connect(_index(index_path))) as db:
        row = db.execute(
            "SELECT title, dj_notes FROM tracks WHERE track_id = ?", (track_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"not in the library index: {track_id}")
        note = _strip_kind(row["dj_notes"] or "")
        if kind != "auto":
            note = f"{note}; track_kind={kind}" if note else f"track_kind={kind}"
        with db:
            db.execute("UPDATE tracks SET dj_notes = ? WHERE track_id = ?", (note, track_id))
    return {"track_id": track_id, "dj_notes": note, **classify_track(row["title"] or "", track_id, note)}


def suggest_beds(vocal: dict, rows: list[dict], *, limit: int = 10) -> list[dict[str, Any]]:
    """Instrumentals ranked for one vocal: tempo first, then key, then a
    different song (stacking a vocal on its own instrumental is the original
    record). Unknown BPM/key rank low but stay listed: Mixxx analyzes on load.
    """
    ranked = []
    vocal_core = core_title(vocal.get("title") or "")
    for bed in rows:
        if bed["kind"] != "instrumental_only" or bed["track_id"] == vocal["track_id"]:
            continue
        bpm_score, bpm_reason = bpm_compatibility(vocal.get("bpm"), bed.get("bpm"))
        key_score, key_reason = key_compatibility(vocal.get("key"), bed.get("key"))
        same_song = bool(vocal_core) and vocal_core == core_title(bed.get("title") or "")
        score = bpm_score * 3.0 + key_score * 2.0 + (0.0 if same_song else 0.5)
        ranked.append({
            **bed,
            "score": round(score, 3),
            "same_song": same_song,
            "reason": "; ".join(r for r in (bpm_reason, key_reason, "same song (legal, not preferred)" if same_song else "different song") if r),
        })
    ranked.sort(key=lambda row: (-row["score"], row["artist"].lower(), row["title"].lower()))
    return ranked[:limit]


def _length(seconds: float | None) -> str:
    if not seconds:
        return "  —  "
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes:2d}:{rest:02d}"


def format_table(rows: list[dict]) -> list[str]:
    lines = []
    for row in rows:
        bpm = f"{row['bpm']:6.1f}" if row.get("bpm") else "     —"
        key = (row.get("key") or "—")[:4]
        flag = " (clean)" if row.get("clean") else ""
        hand = " [hand]" if row.get("kind_source") == "override" else ""
        lines.append(f"{bpm}  {key:4s}  {_length(row.get('duration_seconds'))}  "
                     f"{row['artist']} — {row['title']}{flag}{hand}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--index", type=Path, help="library.sqlite3 (default: the current collection)")
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="list vocals-only and instrumental-only tracks")
    listing.add_argument("--kind", choices=["vocals", "instrumentals"])
    listing.add_argument("--search", default="")
    listing.add_argument("--json", action="store_true")
    override = sub.add_parser("set-kind", help="hand override for one track")
    override.add_argument("track_id")
    override.add_argument("kind", choices=[*KINDS, "auto"])
    beds = sub.add_parser("beds", help="rank instrumentals for one vocals-only track")
    beds.add_argument("vocal_track_id")
    beds.add_argument("--limit", type=int, default=10)
    beds.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "set-kind":
        print(json.dumps(set_track_kind(args.track_id, args.kind, args.index), ensure_ascii=False))
        return 0
    if args.command == "beds":
        rows = scan(args.index)
        vocal = next((row for row in rows if row["track_id"] == args.vocal_track_id), None)
        if vocal is None or vocal["kind"] != "vocals_only":
            parser.error("that track is not a vocals-only track in the library")
        ranked = suggest_beds(vocal, rows, limit=args.limit)
        if args.json:
            print(json.dumps(ranked, indent=2, ensure_ascii=False))
        else:
            print(f"Beds for {vocal['artist']} — {vocal['title']}:")
            for line, row in zip(format_table(ranked), ranked):
                print(f"  {line}   [{row['reason']}]")
        return 0
    result = list_stems(args.kind, search=args.search, index_path=args.index)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    for name, label in (("vocals_only", "Vocals only"), ("instrumental_only", "Instrumentals")):
        if args.kind and KIND_ALIASES[args.kind] != name:
            continue
        print(f"{label} ({result['counts'][name]})   BPM    key   length")
        for line in format_table(result[name]):
            print(f"  {line}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
