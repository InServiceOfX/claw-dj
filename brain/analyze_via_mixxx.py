"""Drives Mixxx's own BPM/key analysis for a playlist through the control
API: loads each playlist track into a (muted) deck, waits for the analyzer
to report a BPM, and moves on. Afterwards Mixxx's database holds real
beatgrids/keys for every track — run brain.sync_mixxx_analysis to merge them
into the crate cache.

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
    args = parser.parse_args()

    records = json.loads(args.tracks.read_text())
    group = deck_group(args.deck)
    analyzed = 0
    with MixxxControl(port=args.port, timeout_s=ANALYZE_TIMEOUT_S + 10) as mixxx:
        mixxx.set(group, "volume", 0.0)
        for r in records:
            label = f"{r['artist']} - {r['title']}" if "artist" in r else r["track_id"]
            print(label)
            # Eject so the bpm control drops to 0 before the next load — a
            # stale non-zero reading otherwise satisfies wait_for_bpm
            # immediately and the track never gets analyzed. Ejecting also
            # forces Mixxx to flush the previous track's analysis to the DB.
            mixxx.set(group, "eject", 1)
            time.sleep(1.0)
            mixxx.set(group, "eject", 0)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and mixxx.get(group, "bpm") > 0:
                time.sleep(0.5)
            mixxx.load(args.deck, r["track_id"])
            bpm = wait_for_bpm(mixxx, group, ANALYZE_TIMEOUT_S)
            if bpm is None:
                print("    analyzer produced no bpm (timeout)")
            else:
                print(f"    mixxx bpm: {bpm:.2f}")
                analyzed += 1
    print(f"\n{analyzed}/{len(records)} analyzed into Mixxx's DB.")
    print("Next: uv run python -m brain.sync_mixxx_analysis")


if __name__ == "__main__":
    main()
