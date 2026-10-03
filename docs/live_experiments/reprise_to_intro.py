"""Live experiment: Diana Ross "I'm Coming Out" reprise first, then back to the intro.

Worked example for docs/LIVE_MINI_EXPERIMENTS.md, built on hands.live_kit (a
2-deck, same-song handoff that Ernest liked). Nothing is rendered; Mixxx plays
the original file live at its native 109.25 BPM.

  1. Deck 1 starts at the 2:55 reprise (grid beat 318, 175.10 s).
  2. At --handoff-beat (default 368, 3:22.6) the song goes back to 0:00:
       --mode blend  (default) deck 2 starts the intro beat-matched; a
                     --blend-beats crossfade with a bass swap (same_song_handoff).
       --mode jump   deck 1 beat-jumps straight back to the intro.
  3. The intro deck plays the song through, jumping the trumpet solo
     (148.737 -> 175.098 s, 48 beats, keeps phase), to the end.

Ernest's pick after 9 live rounds (2026-10-02): --handoff-beat 368 --blend-beats 4
(the defaults). If the intro lands off the bar, --intro-shift 1 / -1 / 2.

Run with Mixxx open and decks 1-2 stopped:
    uv run python docs/live_experiments/reprise_to_intro.py
    ... --dry-run | --mode jump | --handoff-beat 352 | --blend-beats 0 (cut) | --no-full-song
Ctrl-C stops both decks and restores every control this touched.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT))

from hands.live_kit import Live, Track, same_song_handoff  # noqa: E402
from hands.mixxx_control import DEFAULT_PORT, MixxxControl  # noqa: E402
from hands.run_mix_plan import deck_group  # noqa: E402

ROSS = Track("Diana Ross", "I'm Coming Out", 109.25, 0.452948)
REPRISE, FADE = 318, 409                    # 2:55.1; the record fades from ~3:45
TRUMPET_FROM, TRUMPET_TO = 270, 318         # 2:28.7 -> 2:55.1


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--mode", choices=("blend", "jump"), default="blend")
    p.add_argument("--handoff-beat", type=int, default=368, help="reprise grid beat where the intro takes over")
    p.add_argument("--blend-beats", type=int, default=4, help="0 is an on-beat cut")
    p.add_argument("--intro-shift", type=int, default=0, help="beats to move the intro if it lands off the bar")
    p.add_argument("--no-full-song", action="store_true", help="stop 16 beats after the handoff")
    a = p.parse_args()

    intro = a.intro_shift
    print(f"reprise {ROSS.at(REPRISE):.2f}s (beat {REPRISE}), handoff at {ROSS.at(a.handoff_beat):.2f}s "
          f"(beat {a.handoff_beat}) to the intro (beat {intro}), {a.mode}"
          + (f", {a.blend_beats}-beat blend" if a.mode == "blend" else ""))
    if a.handoff_beat + a.blend_beats > FADE:
        print(f"WARNING: handoff finishes after the ~3:45 fade (beat {FADE})")
    if (a.handoff_beat - intro) % 4:
        print("note: reprise -> intro distance is not a whole number of bars")
    if a.dry_run:
        return

    decks = (1, 2) if a.mode == "blend" else (1,)
    with MixxxControl(port=a.port, timeout_s=20) as mixxx:
        live = Live(mixxx)
        live.prepare(decks)
        try:
            live.load(1, ROSS, REPRISE)
            if a.mode == "blend":
                live.load(2, ROSS, intro)
            live.start(1)
            print("  reprise", flush=True)
            if a.mode == "jump":
                live.wait(1, ROSS.at(a.handoff_beat))
                mixxx.set(deck_group(1), "beatjump_size", float(a.handoff_beat - intro))
                mixxx.set(deck_group(1), "beatjump_backward", 1)
                deck = 1
            else:
                same_song_handoff(live, out_deck=1, in_deck=2, track=ROSS,
                                  at_beat=a.handoff_beat, blend_beats=a.blend_beats)
                deck = 2
            print("  intro", flush=True)
            if a.no_full_song:
                time.sleep(16 * 60.0 / ROSS.bpm)
            else:
                live.wait(deck, ROSS.at(TRUMPET_FROM))
                mixxx.set(deck_group(deck), "beatjump_size", float(TRUMPET_TO - TRUMPET_FROM))
                mixxx.set(deck_group(deck), "beatjump_forward", 1)
                print("  trumpet solo skipped", flush=True)
                group = deck_group(deck)
                while mixxx.get(group, "play") > 0.5 and mixxx.get(group, "playposition") < 0.999:
                    time.sleep(0.25)
            print("done", flush=True)
        except KeyboardInterrupt:
            print("\nstopped")
        finally:
            live.restore()


if __name__ == "__main__":
    main()
