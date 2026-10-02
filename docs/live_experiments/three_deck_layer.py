"""Worked example for docs/LIVE_MINI_EXPERIMENTS.md: a 3-deck layer that was DROPPED.

Kept because it shows the pattern for 3 decks, per-deck pitch, and the
backbeat shift flags (--ariana-shift -1 fixed a one-count offset).

Live 3-deck audition for idea 1: Ross's "I'm coming out" over Ariana + the Mo Money bed.

Nothing is rendered. Mixxx plays the three original files live:
  deck 1  Mo Money, Mo Problems (Instrumental)   bed, 104.37 BPM
  deck 2  Ariana Grande, Break Your Heart...      104.37 BPM, pitch +0.6 st
  deck 3  Diana Ross, I'm Coming Out              104.37 BPM, pitch -0.5 st, lows cut

Decks 1 and 2 start together at the same bar relation the mix plan uses
(Ariana beat 0 = instrumental beat 51). Ross starts 28 bed beats later from
0:33.4, still in his instrumental intro; his first sung chorus starts at 0:43
(Ernest's note) and runs to 1:01. Ross plays to beat 112 (~1:02),
fades out over 4 beats, then the bed and Ariana ride 8 more beats.

Pitch values come from `performance_measure pitch` at 104.37 with keylock
on (Ariana -59 cents, Ross +53 cents against the instrumental). Your ear
decides; change the constants below and run again.

Run with Mixxx open, 4 decks shown, and nothing playing:
    cd repos/claw-dj
    uv run python docs/live_experiments/three_deck_layer.py
    ... --dry-run   prints the timeline without touching Mixxx
Ctrl-C stops all three decks and restores every control this touched.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT))

from hands.mixxx_control import DEFAULT_PORT, MixxxControl  # noqa: E402
from hands.run_mix_plan import deck_group, eq_group, filter_group, load_deck, set_bpm_target  # noqa: E402


def library_track(artist: str, title: str, hint: str = "") -> str:
    """Exact track_id from the current library, so no drive name is hardcoded.

    hint is a folder/album fragment that picks one copy when the library
    holds several (Ariana's song is on two deluxe editions)."""
    from contextlib import closing
    from brain import library_index
    with closing(library_index.connect(library_index.current_index_path())) as db:
        rows = [r[0] for r in db.execute(
            "SELECT track_id FROM tracks WHERE artist LIKE ? AND title = ? AND available = 1"
            " AND track_id LIKE ?",
            (f"%{artist}%", title, f"%{hint}%"))]
    if len(rows) != 1:
        raise SystemExit(f"expected one available '{artist} - {title}' in the library, found {len(rows)}: {rows}")
    return rows[0]

TEMPO = 104.37

INST = {
    "artist": "Notorious B.I.G.", "title": "Mo Money, Mo Problems (Instrumental)",
    "bpm": 104.37240124740124, "first_beat": 0.390635,
}
ARIANA = {
    "artist": "Ariana Grande", "title": "Break Your Heart Right Back (Feat. Childish Gambino)",
    "hint": "Japanese Deluxe Edition",  # the copy the Mo Money plan uses
    "bpm": 94.0, "first_beat": 0.178005,
}
ROSS = {
    "artist": "Diana Ross", "title": "I'm Coming Out",
    "bpm": 109.25, "first_beat": 0.452948,
}

# --- what to listen to (edit and rerun) ---------------------------------
ARIANA_START_BEAT = 292        # her ~3:06.6, 32 beats before the outro section
BED_OFFSET_BEATS = 51          # mix plan: instrumental beat = Ariana beat + 51
ROSS_ENTER_AFTER_BEATS = 28    # bed beats after the start (a whole number of bars)
ROSS_START_BEAT = 60           # 4-beat lead-in; hook vocal at Ross beat 64 (0:35.5)
ROSS_END_BEAT = 112            # end of the 12-bar hook, before "There's a new me"
ROSS_FADE_BEATS = 4
TAIL_BEATS = 8

ARIANA_PITCH = +0.6            # semitones, keylock on
ROSS_PITCH = -0.5
ROSS_LOW_EQ = 0.35             # Mixxx EQ gain, 1.0 = unity: bed carries the bass
VOLUMES = {1: 0.85, 2: 1.0, 3: 0.9}
MASTER_GAIN = 0.6              # headroom for three full-range decks
# -------------------------------------------------------------------------


def at_beat(track: dict, beat: float) -> float:
    return track["first_beat"] + beat * 60.0 / track["bpm"]


def position_seconds(mixxx: MixxxControl, deck: int) -> float:
    group = deck_group(deck)
    return mixxx.get(group, "playposition") * mixxx.get(group, "duration")


def wait_until_source(mixxx: MixxxControl, deck: int, seconds: float, *, lead: float = 0.0) -> None:
    while position_seconds(mixxx, deck) < seconds - lead:
        if mixxx.get(deck_group(deck), "play") < 0.5:
            raise RuntimeError(f"deck {deck} stopped before {seconds:.2f}s")
        time.sleep(0.01)


def timeline(ross_shift: int = 0, ariana_shift: int = 0) -> dict:
    """Shifts move that source by whole beats against the bed (backbeat fix)."""
    bed_start_beat = ARIANA_START_BEAT + BED_OFFSET_BEATS
    bed_period = 60.0 / INST["bpm"]
    plan = {
        "inst_cue": at_beat(INST, bed_start_beat),
        "ariana_cue": at_beat(ARIANA, ARIANA_START_BEAT + ariana_shift),
        "ross_cue": at_beat(ROSS, ROSS_START_BEAT + ross_shift),
        "ross_enter_bed_seconds": at_beat(INST, bed_start_beat + ROSS_ENTER_AFTER_BEATS),
        "ross_fade_at": at_beat(ROSS, ROSS_END_BEAT + ross_shift),
        "ross_fade_seconds": ROSS_FADE_BEATS * 60.0 / TEMPO,
        "tail_seconds": TAIL_BEATS * 60.0 / TEMPO,
    }
    hook_ariana_beat = ARIANA_START_BEAT + ROSS_ENTER_AFTER_BEATS + (64 - ROSS_START_BEAT)
    plan["hook_lands_on_ariana"] = at_beat(ARIANA, hook_ariana_beat)
    remaining_beats = ROSS_END_BEAT - ROSS_START_BEAT + ROSS_FADE_BEATS + TAIL_BEATS
    plan["bed_needed_until"] = plan["ross_enter_bed_seconds"] + remaining_beats * bed_period
    return plan


def fade(mixxx: MixxxControl, deck: int, start: float, end: float, seconds: float) -> None:
    t0 = time.monotonic()
    while (elapsed := time.monotonic() - t0) < seconds:
        x = elapsed / seconds
        x = x * x * (3 - 2 * x)
        mixxx.set(deck_group(deck), "volume", start + (end - start) * x)
        time.sleep(0.02)
    mixxx.set(deck_group(deck), "volume", end)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ross-shift", type=int, default=0,
                        help="whole beats to move Ross against the bed, e.g. 1 or -1 when its backbeat is one count off")
    parser.add_argument("--ariana-shift", type=int, default=0,
                        help="whole beats to move Ariana against the bed")
    args = parser.parse_args()
    plan = timeline(args.ross_shift, args.ariana_shift)
    print(f"shifts: Ross {args.ross_shift:+d} beats, Ariana {args.ariana_shift:+d} beats")
    print(f"bed (deck 1)    cue {plan['inst_cue']:.2f}s   at {TEMPO} BPM")
    print(f"Ariana (deck 2) cue {plan['ariana_cue']:.2f}s at {TEMPO} BPM, pitch {ARIANA_PITCH:+g} st")
    print(f"Ross (deck 3)   cue {plan['ross_cue']:.2f}s, enters at bed {plan['ross_enter_bed_seconds']:.2f}s, "
          f"hook lands on Ariana {plan['hook_lands_on_ariana']:.2f}s, fades at Ross {plan['ross_fade_at']:.2f}s, "
          f"pitch {ROSS_PITCH:+g} st, low EQ {ROSS_LOW_EQ}")
    print(f"bed needs audio until ~{plan['bed_needed_until']:.1f}s of 259.7s")
    if args.dry_run:
        return

    decks = (1, 2, 3)
    saved: list[tuple[str, str, float]] = []

    with MixxxControl(port=args.port, timeout_s=20) as mixxx:
        def save_set(group: str, key: str, value: float) -> None:
            saved.append((group, key, mixxx.get(group, key)))
            mixxx.set(group, key, value)

        for deck in decks:
            try:
                playing = mixxx.get(deck_group(deck), "play")
            except Exception as exc:
                raise SystemExit(f"Mixxx has no {deck_group(deck)}: show 4 decks in Mixxx first ({exc})")
            if playing > 0.5:
                raise SystemExit(f"deck {deck} is playing; stop it before this audition")
        try:
            save_set("[Master]", "gain", MASTER_GAIN)
            save_set("[Master]", "crossfader", 0.0)
            for deck in decks:
                group = deck_group(deck)
                save_set(group, "orientation", 1)      # center: crossfader ignores it
                save_set(group, "volume", 0.0)
                save_set(group, "pitch_adjust", 0.0)
                save_set(filter_group(deck), "super1", 0.5)   # an interrupted mix can leave it closed
                for band in (1, 2, 3):
                    save_set(eq_group(deck), f"parameter{band}", 1.0)

            load_deck(mixxx, 1, library_track(INST["artist"], INST["title"], INST.get("hint", "")), cue_seconds=plan["inst_cue"], expected_bpm=INST["bpm"])
            load_deck(mixxx, 2, library_track(ARIANA["artist"], ARIANA["title"], ARIANA.get("hint", "")), cue_seconds=plan["ariana_cue"], expected_bpm=ARIANA["bpm"])
            load_deck(mixxx, 3, library_track(ROSS["artist"], ROSS["title"], ROSS.get("hint", "")), cue_seconds=plan["ross_cue"], expected_bpm=ROSS["bpm"])
            for deck in decks:
                set_bpm_target(mixxx, deck, TEMPO)     # keylock stays on (load_deck)
                mixxx.set(deck_group(deck), "volume", 0.0)
            mixxx.set(deck_group(2), "pitch_adjust", ARIANA_PITCH)
            mixxx.set(deck_group(3), "pitch_adjust", ROSS_PITCH)
            mixxx.set(eq_group(3), "parameter1", ROSS_LOW_EQ)
            mixxx.set(deck_group(1), "volume", VOLUMES[1])
            mixxx.set(deck_group(2), "volume", VOLUMES[2])

            print("bed + Ariana", flush=True)
            mixxx.set(deck_group(1), "play", 1)
            mixxx.set(deck_group(2), "play", 1)        # quantize keeps it on the bed's beat
            mixxx.set(deck_group(2), "beatsync_phase", 1)

            # Press play a hair early; quantize lands Ross's beat on the bed's beat.
            wait_until_source(mixxx, 1, plan["ross_enter_bed_seconds"], lead=0.05)
            mixxx.set(deck_group(3), "play", 1)
            mixxx.set(deck_group(3), "beatsync_phase", 1)
            print("Ross in", flush=True)
            fade(mixxx, 3, 0.0, VOLUMES[3], (64 - ROSS_START_BEAT) * 60.0 / TEMPO)

            wait_until_source(mixxx, 3, plan["ross_fade_at"])
            print("Ross out", flush=True)
            fade(mixxx, 3, VOLUMES[3], 0.0, plan["ross_fade_seconds"])
            mixxx.set(deck_group(3), "play", 0)
            time.sleep(plan["tail_seconds"])
            fade(mixxx, 2, VOLUMES[2], 0.0, 2.0)
            fade(mixxx, 1, VOLUMES[1], 0.0, 2.0)
            print("done", flush=True)
        except KeyboardInterrupt:
            print("\nstopped")
        finally:
            for deck in decks:
                try:
                    mixxx.set(deck_group(deck), "play", 0)
                except Exception:
                    pass
            for group, key, value in reversed(saved):
                try:
                    mixxx.set(group, key, value)
                except Exception:
                    pass


if __name__ == "__main__":
    main()
