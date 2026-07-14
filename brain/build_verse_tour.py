"""Verse tour: one song on two decks, cut verse to verse, skip the chorus.

The lyric-timeline layer gives bar-snapped vocal onsets per verse; this
builds a plan (same event schema `hands.run_mix_plan` already executes)
that alternates decks A/B through the verses of ONE track — e.g. hear the
guest verses back to back with every chorus skipped. Cuts are on-beat
crossfader slams (`hard_cut`), anchored on the outgoing deck's beat.

Usage:
    uv run python -m brain.build_verse_tour --track "21 Questions"
    uv run python -m hands.run_mix_plan --plan brain/data/verse_tour_plan.json --dry-run
    uv run python -m hands.run_mix_plan --plan brain/data/verse_tour_plan.json
"""
from __future__ import annotations

import argparse
import json
from contextlib import closing
from pathlib import Path

from brain.playlist import DATA_DIR, normalize

DEFAULT_OUT = DATA_DIR / "verse_tour_plan.json"


def find_track(query: str) -> dict:
    """Resolve a title/artist/path substring against the crate; prefer
    Mixxx-analyzed copies (the tour needs a live beatgrid)."""
    crate = json.loads((DATA_DIR / "crate.json").read_text())
    wanted = normalize(query)
    hits = [
        t for t in crate
        if wanted in normalize(f"{t.get('artist','')} {t.get('title','')}")
        or wanted in normalize(t["track_id"])
    ]
    if not hits:
        raise SystemExit(f"no crate track matches {query!r}")
    hits.sort(key=lambda t: (t.get("bpm") is None, len(t["track_id"])))
    return hits[0]


def load_segments(db, track_id: str) -> list[dict]:
    row = db.execute(
        "SELECT segments FROM lyric_timelines WHERE track_id = ?", (track_id,)
    ).fetchone()
    if row is None:
        raise SystemExit(
            "no lyric timeline for this track — run: uv run python -m brain.lyric_timeline"
        )
    return json.loads(row[0])


def tour_verses(segments: list[dict], *, min_lines: int = 4) -> list[dict]:
    """The verses worth touring: bar-snapped, long enough to be real verses
    (short blocks are ad-libs/bridges)."""
    return [
        s for s in segments
        if s["kind"] == "verse" and s.get("bar_start") is not None and s["lines"] >= min_lines
    ]


def build_verse_tour_plan(
    track: dict,
    segments: list[dict],
    *,
    min_lines: int = 4,
    max_verses: int | None = None,
) -> dict:
    verses = tour_verses(segments, min_lines=min_lines)
    if max_verses:
        verses = verses[:max_verses]
    if len(verses) < 2:
        raise SystemExit(
            f"only {len(verses)} tourable verses — need at least 2 "
            "(try --min-lines lower, or the track's timeline is chorus-heavy)"
        )
    bpm = track.get("bpm")
    if not bpm:
        raise SystemExit("track has no bpm — analyze it in Mixxx first")

    def verse_beats(segment: dict) -> int:
        # Play the verse to its end (the following chorus/gap start);
        # reserve 1 beat for the cut anchor.
        length = max(4, round((segment["end"] - segment["start"]) * bpm / 60.0))
        return max(4, length - 1)

    label = f"{track['artist']} — {track['title']}"
    events: list[dict] = [
        {"op": "reset_instrument", "detail": "verse tour: same track on decks 1+2"},
        {
            "op": "load", "deck": 1, "track_id": track["track_id"],
            "artist": track["artist"], "title": track["title"],
            "cue_seconds": verses[0]["bar_start"], "cue_source": "lyric_verse",
        },
        {
            "op": "load", "deck": 2, "track_id": track["track_id"],
            "artist": track["artist"], "title": track["title"],
            "cue_seconds": verses[1]["bar_start"], "cue_source": "lyric_verse",
        },
        {"op": "start", "deck": 1},
    ]
    for i, verse in enumerate(verses):
        deck = 1 if i % 2 == 0 else 2
        other = 2 if deck == 1 else 1
        last = i == len(verses) - 1
        body = {
            "op": "finale" if last else "play_body",
            "deck": deck,
            "beats": verse_beats(verse),
            "seconds": round(verse["end"] - verse["start"], 1),
            "track": f"{label} · verse {i + 1}: “{verse['first_line']}”",
        }
        if not last:
            body["instrument_hints"] = [
                "Optional: tweak [ChannelN] filterHighEq mid-verse",
            ]
        events.append(body)
        if last:
            break
        if i + 2 < len(verses):
            # The deck we're about to leave gets re-cued to the verse after next.
            events.append(
                {
                    "op": "preload_after_transition", "deck": deck,
                    "track_id": track["track_id"], "artist": track["artist"],
                    "title": track["title"],
                    "cue_seconds": verses[i + 2]["bar_start"],
                    "cue_source": "lyric_verse",
                }
            )
        events.append(
            {
                "op": "transition",
                "from_deck": deck, "to_deck": other,
                "transition_beats": 1,
                "technique": "verse_cut",
                # No sync: same track, same tempo — beatsync phase-pull would
                # fight the lyric cue. Quantize keeps the slam on the grid.
                "moves": ["hard_cut"],
                "from_track": f"{label} · verse {i + 1}",
                "to_track": f"{label} · verse {i + 2}: “{verses[i + 1]['first_line']}”",
                "notes": f"chorus skipped — on-beat cut into “{verses[i + 1]['first_line']}”",
            }
        )
    events.append({"op": "stop_all"})

    return {
        "version": 2,
        "profile": {"name": "verse-tour", "track": label, "verses": len(verses)},
        "phrase_interval_beats": 32,
        "tracks": [
            {
                "artist": track["artist"], "title": track["title"],
                "bpm": bpm, "key": track.get("key"), "track_id": track["track_id"],
                "cue_seconds": verses[0]["bar_start"], "cue_source": "lyric_verse",
            }
        ],
        "events": events,
    }


def main() -> None:
    from brain.library_index import connect

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", required=True, help="title/artist/path substring")
    parser.add_argument("--min-lines", type=int, default=4)
    parser.add_argument("--max-verses", type=int, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    track = find_track(args.track)
    with closing(connect()) as db:
        segments = load_segments(db, track["track_id"])
    plan = build_verse_tour_plan(
        track, segments, min_lines=args.min_lines, max_verses=args.max_verses
    )
    args.out.write_text(json.dumps(plan, indent=1) + "\n")

    verses = tour_verses(segments, min_lines=args.min_lines)
    print(f"verse tour: {track['artist']} — {track['title']} ({track['bpm']:.1f} BPM)")
    for i, verse in enumerate(verses[: args.max_verses] if args.max_verses else verses, 1):
        deck = 1 if i % 2 == 1 else 2
        print(f"  {i}. deck {deck} @ {verse['bar_start']:7.1f}s (beat {verse['beat_index']}): “{verse['first_line']}”")
    print(f"plan -> {args.out}")
    print(f"dry-run: uv run python -m hands.run_mix_plan --plan {args.out} --dry-run")


if __name__ == "__main__":
    main()
