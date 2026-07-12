"""Structured playlist edits — the tool surface for conversational agents.

A NemoClaw / H-agent front end turns a user ask ("drop the Alicia Keys
songs") into one call here; this module owns the actual selection change so
the agent never edits JSON by hand or invents track ids. Humans can call it
directly too.

Usage:
    uv run python -m brain.playlist_edit --remove-artist "Alicia Keys" --remove-artist "702"
    uv run python -m brain.playlist_edit --remove-title "Not Tonight (Remix)"
    uv run python -m brain.playlist_edit --list

After removing, re-order and re-export with:
    uv run python -m brain.curate_playlist --mode selection --planner mix-graph
"""
from __future__ import annotations

import argparse

from brain.library import load_crate
from brain.playlist import load_selection, normalize, save_selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--remove-artist",
        action="append",
        default=[],
        help="remove every selected track whose artist tag matches (repeatable)",
    )
    parser.add_argument(
        "--remove-title",
        action="append",
        default=[],
        help="remove selected tracks whose title matches (repeatable)",
    )
    parser.add_argument("--list", action="store_true", help="print the current selection and exit")
    args = parser.parse_args()

    crate = {track.track_id: track for track in load_crate()}
    selection = load_selection()
    if args.list or not (args.remove_artist or args.remove_title):
        for track_id in selection:
            track = crate.get(track_id)
            label = f"{track.artist} — {track.title}" if track else track_id
            print(f"  {label}")
        print(f"{len(selection)} tracks selected")
        return

    wanted_artists = [normalize(a) for a in args.remove_artist]
    wanted_titles = [normalize(t) for t in args.remove_title]

    kept: list[str] = []
    removed: list[str] = []
    for track_id in selection:
        track = crate.get(track_id)
        artist = normalize(track.artist) if track else ""
        title = normalize(track.title) if track else ""
        hit = any(w == artist or w in artist for w in wanted_artists) or any(
            w == title or w in title for w in wanted_titles
        )
        if hit:
            removed.append(f"{track.artist} — {track.title}" if track else track_id)
        else:
            kept.append(track_id)

    if not removed:
        raise SystemExit("nothing matched — selection unchanged")
    save_selection(kept)
    for label in removed:
        print(f"removed: {label}")
    print(f"selection: {len(selection)} -> {len(kept)} tracks")
    print("re-order + export: uv run python -m brain.curate_playlist --mode selection --planner mix-graph")


if __name__ == "__main__":
    main()
