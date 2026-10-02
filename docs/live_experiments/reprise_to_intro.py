"""Live experiment: Diana Ross "I'm Coming Out" reprise first, then back to the intro.

Nothing is rendered; Mixxx plays the original file live at its native 109.25 BPM.

  1. Deck 1 starts at the 2:55 reprise (grid beat 318, 175.10 s).
  2. At --handoff-beat (default 368, 3:22.6: 50 beats in, before the ~3:45
     fade) the song goes back to 0:00:
       --mode blend  (default) deck 2 starts the intro beat-matched and the
                     two decks crossfade over --blend-beats with a bass swap.
       --mode jump   deck 1 beat-jumps straight back to the intro, no overlap.
  3. The intro deck then plays the whole song through, jumping over the
     trumpet solo (2:28.7 -> 2:55.1, 48 beats, keeps phase), to the end.

The handoff beat and the intro beat are 384 grid beats apart (12 x 32), so
bar and phrase positions carry across if Mixxx's grid holds over the song.
Ross is live-drummed, so if the intro lands off the bar, rerun with
--intro-shift 1 / -1 (or 2) to move the intro by whole beats.

Ernest's pick after 9 live rounds (2026-10-02): --handoff-beat 368 --blend-beats 4.
Off-bar handoffs (362, 366) are flagged; 352/360/384 with 16-24 beat blends were
less exciting than a short 4-beat blend on beat 368.

Worked example for docs/LIVE_MINI_EXPERIMENTS.md (a 2-deck, same-song handoff
that Ernest liked). Run with Mixxx open and decks 1-2 stopped:
    uv run python docs/live_experiments/reprise_to_intro.py
    ... --dry-run | --mode jump | --handoff-beat 352 | --blend-beats 32 | --no-full-song
Ctrl-C stops both decks and restores every control this touched.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT))

from hands.mixxx_control import DEFAULT_PORT, MixxxControl  # noqa: E402
from hands.run_mix_plan import deck_group, eq_group, filter_group, load_deck  # noqa: E402

ROSS = "/Volumes/USB322FD/Music/RnB/Diana Ross & The Supremes/The No. 1's/22 I'm Coming Out.mp3"
BPM = 109.25
FIRST_BEAT = 0.452948
PERIOD = 60.0 / BPM

REPRISE_BEAT = 318             # 2:55.1, Ernest's reprise start
FADE_BEAT = 409                # ~3:45, the record starts fading out
TRUMPET_FROM_BEAT = 270        # 2:28.7, just before the 2:29 solo
TRUMPET_TO_BEAT = 318          # 2:55.1
INTRO_BEAT = 0                 # 0:00.45, the iconic instrumental intro
EQ_UNITY = 1.0                 # Mixxx EQ gain at unity (0 = kill, 4 = max)


def at(beat: float) -> float:
    return FIRST_BEAT + beat * PERIOD


def position(mixxx: MixxxControl, deck: int) -> float:
    group = deck_group(deck)
    return mixxx.get(group, "playposition") * mixxx.get(group, "duration")


def wait_until(mixxx: MixxxControl, deck: int, seconds: float, *, lead: float = 0.0) -> None:
    while position(mixxx, deck) < seconds - lead:
        if mixxx.get(deck_group(deck), "play") < 0.5:
            raise RuntimeError(f"deck {deck} stopped before {seconds:.2f}s")
        time.sleep(0.01)


def smooth(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=("blend", "jump"), default="blend")
    parser.add_argument("--handoff-beat", type=int, default=368,  # Ernest's pick, 2026-10-02
                        help="reprise grid beat where the intro takes over (368 = 3:22.6)")
    parser.add_argument("--blend-beats", type=int, default=4,
                        help="crossfade length; 4 is Ernest's pick (2026-10-02), 0 is an on-beat cut")
    parser.add_argument("--intro-shift", type=int, default=0,
                        help="whole beats to move the intro against the reprise if it lands off the bar")
    parser.add_argument("--no-full-song", action="store_true",
                        help="stop 16 beats after the handoff instead of playing the song through")
    args = parser.parse_args()

    intro_beat = INTRO_BEAT + args.intro_shift
    handoff_s = at(args.handoff_beat)
    blend_end_beat = args.handoff_beat + (args.blend_beats if args.mode == "blend" else 0)
    print(f"reprise from {at(REPRISE_BEAT):.2f}s (beat {REPRISE_BEAT}), "
          f"{args.handoff_beat - REPRISE_BEAT} beats, handoff at {handoff_s:.2f}s (beat {args.handoff_beat})")
    print(f"mode {args.mode}: intro from beat {intro_beat} ({at(intro_beat):.2f}s)"
          + (f", {args.blend_beats}-beat blend ends at reprise {at(blend_end_beat):.2f}s" if args.mode == "blend" else ""))
    if blend_end_beat > FADE_BEAT:
        print(f"WARNING: handoff finishes after the ~3:45 fade (beat {FADE_BEAT})")
    print("then " + ("16 beats and stop" if args.no_full_song else
          f"the whole song, trumpet solo skipped {at(TRUMPET_FROM_BEAT):.2f}s -> {at(TRUMPET_TO_BEAT):.2f}s, to the end"))
    if args.dry_run:
        return
    if (args.handoff_beat - intro_beat) % 4:
        print("note: reprise->intro distance is not a whole number of bars")

    saved: list[tuple[str, str, float]] = []
    decks = (1, 2) if args.mode == "blend" else (1,)
    with MixxxControl(port=args.port, timeout_s=20) as mixxx:
        def save_set(group: str, key: str, value: float) -> None:
            saved.append((group, key, mixxx.get(group, key)))
            mixxx.set(group, key, value)

        for deck in (1, 2):
            if mixxx.get(deck_group(deck), "play") > 0.5:
                raise SystemExit(f"deck {deck} is playing; stop it before this experiment")
        try:
            save_set("[Master]", "crossfader", 0.0)
            for deck in decks:
                save_set(deck_group(deck), "orientation", 1)   # center: faders do the blend
                save_set(deck_group(deck), "volume", 0.0)
                # Start bright and unfiltered: an interrupted mix can leave a
                # deck's filter closed (2026-10-02: deck 1 sat at super1 0.13,
                # a heavy low-pass) or its EQ cut.
                save_set(filter_group(deck), "super1", 0.5)
                for band in (1, 2, 3):
                    save_set(eq_group(deck), f"parameter{band}", EQ_UNITY)
            low_unity = EQ_UNITY

            load_deck(mixxx, 1, ROSS, cue_seconds=at(REPRISE_BEAT), expected_bpm=BPM)
            if args.mode == "blend":
                load_deck(mixxx, 2, ROSS, cue_seconds=at(intro_beat), expected_bpm=BPM)
                mixxx.set(deck_group(2), "volume", 0.0)
                mixxx.set(eq_group(2), "parameter1", 0.0)      # incoming bass waits for the swap
            mixxx.set(deck_group(1), "volume", 1.0)
            mixxx.set(deck_group(1), "play", 1)
            print("reprise", flush=True)

            live = 1
            if args.mode == "jump":
                wait_until(mixxx, 1, handoff_s)
                mixxx.set(deck_group(1), "beatjump_size", float(args.handoff_beat - intro_beat))
                mixxx.set(deck_group(1), "beatjump_backward", 1)
                print(f"jumped back {args.handoff_beat - intro_beat} beats to the intro", flush=True)
            else:
                wait_until(mixxx, 1, handoff_s, lead=0.05)   # quantize lands it on deck 1's beat
                mixxx.set(deck_group(2), "play", 1)
                mixxx.set(deck_group(2), "beatsync_phase", 1)
                print("intro in", flush=True)
                blend_s = args.blend_beats * PERIOD
                t0 = time.monotonic()
                swapped = blend_s <= 0       # --blend-beats 0: an on-beat cut
                if swapped:
                    mixxx.set(eq_group(2), "parameter1", low_unity)
                while blend_s > 0 and (x := (time.monotonic() - t0) / blend_s) < 1.0:
                    mixxx.set(deck_group(2), "volume", smooth(x / 0.5))
                    mixxx.set(deck_group(1), "volume", 1.0 - smooth((x - 0.5) / 0.5))
                    if not swapped and x >= 0.5:
                        mixxx.set(eq_group(2), "parameter1", low_unity)
                        mixxx.set(eq_group(1), "parameter1", 0.0)
                        swapped = True
                        print("bass swap", flush=True)
                    time.sleep(0.02)
                mixxx.set(deck_group(2), "volume", 1.0)
                mixxx.set(deck_group(1), "volume", 0.0)
                mixxx.set(deck_group(1), "play", 0)
                live = 2
                print("intro deck alone", flush=True)

            if args.no_full_song:
                time.sleep(16 * PERIOD)
            else:
                wait_until(mixxx, live, at(TRUMPET_FROM_BEAT))
                mixxx.set(deck_group(live), "beatjump_size", float(TRUMPET_TO_BEAT - TRUMPET_FROM_BEAT))
                mixxx.set(deck_group(live), "beatjump_forward", 1)
                print("skipped the trumpet solo -> 2:55 reprise", flush=True)
                group = deck_group(live)
                while mixxx.get(group, "play") > 0.5 and mixxx.get(group, "playposition") < 0.999:
                    time.sleep(0.25)
            print("done", flush=True)
        except KeyboardInterrupt:
            print("\nstopped")
        finally:
            for deck in (1, 2):
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
