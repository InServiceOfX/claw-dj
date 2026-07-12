"""Builds the sample-lineage demo playlist from the scanned crate
(brain/data/crate.json): golden-era hip-hop picked for well-documented
sample relationships, plus the classic RnB records that generation sampled.
Writes brain/data/lineage_set.json and .m3u (both gitignored, like all of
brain/data/).

Picks are matched by case-insensitive substring on (artist, title); among
matching files the shortest title wins (canonical release over remixes and
edits), after rejecting alternate versions outright.

Usage: uv run python -m brain.build_lineage_set
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from brain.library import load_crate

DATA_DIR = Path(__file__).parent / "data"
OUT_JSON = DATA_DIR / "lineage_set.json"
OUT_M3U = DATA_DIR / "lineage_set.m3u"

# Substrings that mark a file as a non-canonical version of the song.
REJECT_TITLE_SUBSTRINGS = (
    "instrumental",
    "cappella",
    "acapella",
    "radio",
    "remix",
    "club mix",
    "dance mix",
    "disco mix",
    "single version",
    "video mix",
    "snippet",
    "interlude",
    "live",
    "demo",
    "clean",
    "edit",
    "call out",
    "mix)",
    "(part 2",
    "(pt. 1",
    "pt. 1",
    "extended",
)

# (artist substring, title substring) — order is the intended set order,
# alternating eras/energies is left to the Brain at mix time.
PICKS: tuple[tuple[str, str], ...] = (
    # Hip-hop side: every one of these has a famous, documented sample source.
    ("Dr. Dre", "Nuthin' But A"),
    ("Dr. Dre", "Let Me Ride"),
    ("Dr. Dre", "The Next Episode"),
    ("Dr. Dre", "California Love"),
    ("Dr. Dre", "Deep Cover"),
    ("Wu-Tang Clan", "C.R.E.A.M."),
    ("Wu-Tang Clan", "Can It Be All So Simple"),
    ("Wu-Tang Clan", "Protect Ya Neck"),
    ("Nas", "N.Y. State Of Mind"),
    ("Nas", "The World Is Yours"),
    ("Nas", "Memory Lane"),
    ("Nas", "Represent"),
    ("The Notorious B.I.G.", "Juicy"),
    ("The Notorious B.I.G.", "Big Poppa"),
    ("The Notorious B.I.G.", "Hypnotize"),
    ("The Notorious B.I.G.", "Warning"),
    ("The Notorious B.I.G.", "Going Back To Cali"),
    ("Gang Starr", "Mass Appeal"),
    ("Gang Starr", "DWYCK"),
    ("Gang Starr", "Above The Clouds"),
    ("Gang Starr", "Full Clip"),
    ("Mobb Deep", "Shook Ones Pt. II"),
    ("Mobb Deep", "Survival Of The Fittest"),
    ("Mobb Deep", "Quiet Storm"),
    ("Lord Finesse", "Hip 2 Da Game"),
    # RnB side: the sampled generation — originals that hip-hop mined.
    ("Evelyn", "Shame"),
    ("Evelyn", "Love Come Down"),
    ("Evelyn", "I'm In Love"),
    ("Lisa Lisa", "I Wonder If I Take You Home"),
    ("Lisa Lisa", "Can You Feel the Beat"),
)


_LIVE_ALBUM = re.compile(r"\blive\b", re.IGNORECASE)


def _is_live_recording(track_id: str) -> bool:
    """Live albums ('Live In London...') are wrong for beat-matched mixing;
    the tags rarely say so but the album directory name does."""
    return bool(_LIVE_ALBUM.search(Path(track_id).parent.name))


def pick_canonical(tracks: list, artist_sub: str, title_sub: str):
    candidates = [
        t
        for t in tracks
        if artist_sub.lower() in t.artist.lower()
        and title_sub.lower() in t.title.lower()
        and not any(rej in t.title.lower() for rej in REJECT_TITLE_SUBSTRINGS)
        and not _is_live_recording(t.track_id)
        and Path(t.track_id).suffix.lower() == ".mp3"
    ]
    if not candidates:
        return None
    # Shortest title = fewest qualifiers = the canonical cut; path as tiebreak
    # so reruns are deterministic.
    return min(candidates, key=lambda t: (len(t.title), t.track_id))


def main() -> None:
    tracks = load_crate()
    selected = []
    missing = []
    for artist_sub, title_sub in PICKS:
        track = pick_canonical(tracks, artist_sub, title_sub)
        if track is None:
            missing.append((artist_sub, title_sub))
        else:
            selected.append(track)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            [
                {
                    "track_id": t.track_id,
                    "title": t.title,
                    "artist": t.artist,
                    "genre": t.genre,
                    "bpm": t.bpm,
                    "key": t.key,
                }
                for t in selected
            ],
            indent=2,
        )
    )
    OUT_M3U.write_text(
        "#EXTM3U\n"
        + "".join(
            f"#EXTINF:-1,{t.artist} - {t.title}\n{t.track_id}\n" for t in selected
        )
    )

    print(f"selected {len(selected)}/{len(PICKS)} -> {OUT_JSON} and {OUT_M3U}")
    for t in selected:
        print(f"  {t.artist} - {t.title}")
    if missing:
        print("MISSING (no canonical match):")
        for artist_sub, title_sub in missing:
            print(f"  {artist_sub} / {title_sub}")


if __name__ == "__main__":
    main()
