# Live mini-experiments

How any agent (Claude Code, Codex, Grok Build, Hermes Agent, or another)
lets Ernest try **one piece of a mix live in Mixxx**, iterate on it with
flags, and keep only what he likes. Story:
[`user_stories/story__live_mini_experiments_on_a_section_of_a_mix.md`](../user_stories/story__live_mini_experiments_on_a_section_of_a_mix.md).

Until the harness has a built-in experiment command, an experiment is a
small Python script built on **`hands/live_kit.py`**, the shared toolkit of
the live moves Ernest has approved (prompt:
`prompts/hands/live_kit_Python.prompt`). Use it instead of copying code
between scripts.

> "It was a lot of FUN to do it like this." (Ernest, 2026-10-02, after nine
> live rounds found the Diana Ross reprise-first handoff)

## When to offer one

Offer an experiment instead of editing the full plan when the idea is new or
uncertain. For example:

- a transition or handoff you want to tune,
- a section to loop or re-enter,
- a layer on 2, 3 or more decks,
- a same-song trick such as the reprise first and then the intro.

A failed experiment is a good result. It costs a minute and leaves the full
mix untouched.

## Hard rules

- **Live only.** Mixxx plays the original files. Never render a WAV or any
  other audio file to audition an idea, and don't substitute an offline
  render.
- **Never touch the full mix while experimenting.** Don't change plan files,
  notes or `mix_plan.json` until Ernest says he likes the result.
- **Ernest runs it in his own terminal** so Ctrl-C works and he can rerun it
  with different flags. An agent should only start one itself if he asks,
  and should tell him how to stop it.
- **Leave Mixxx as you found it.** Save every control you change and restore
  it in `finally:`, on Ctrl-C too.

## Where scripts live

- **Per-plan scratch:** `brain/data/plans/<slug>/authoring/<name>.py`. It is
  gitignored, next to that plan's data. Use it for each new experiment.
- **Checked-in patterns:** `docs/live_experiments/*.py`. Copy one of
  these to start:
  - [`reprise_to_intro.py`](live_experiments/reprise_to_intro.py):
    a 2-deck same-song handoff with blend or jump mode, a source skip, and a
    full-song play-through, built on `hands.live_kit`. Ernest liked the
    result. Start here.
  - [`three_deck_layer.py`](live_experiments/three_deck_layer.py):
    3 decks at one tempo with per-deck pitch, low EQ, an entry time and
    shift flags. The idea was dropped, but the pattern is sound. It predates
    the toolkit, so it still carries its own helpers.

### What the toolkit gives you (`hands.live_kit`)

| Need | Use |
|---|---|
| Find a song without a drive path | `library_track(artist, title, hint)`, `track_from_library(...)` (grid from the library) |
| Grid beat <-> source seconds | `Track(...).at(beat)`, `.beat_at(seconds)` |
| Refuse playing decks, clean slate, put everything back | `Live.prepare(decks)` ... `finally: live.restore()` |
| Load and cue, tempo, pitch | `live.load(deck, track, beat, bpm=..., pitch=...)`, `live.start(deck)` |
| Timing by play position | `live.wait(deck, seconds)`, `live.automate(clock, track, b0, b1, lanes)` |
| Click-free in/out cuts | `live.cut([(group, key, target), ...])` |
| Skip or re-enter a song without a jump | `same_song_handoff(...)` |
| Blend two decks carrying the same riff | `eq_split_crossover(..., hold_beats=8, cross_beats=8)` |
| Loops, including tuned fractional ones | `exact_loop(live, deck=..., track=..., start_beat=..., beats=31.5)` |
| Bar-by-bar in/out patterns | `play_bar_pattern(...)` |
| Record the run | `with live.recording(): ...` |
| Fade a song out gently | `fade_out(live, deck=..., clock_deck=..., clock_track=..., start_beat=...)` (16 counts, linear) |

Find the repo root by walking up to `pyproject.toml` (see the examples), so
a copied script runs from either location.

## Script checklist

1. **Docstring.** Say what plays on which deck, in source times and grid
   beats, plus the run command and the flags.
2. **`--dry-run`.** Print the timeline (cues, entry and handoff times, blend
   end, skips) without connecting to Mixxx. Warn when a distance between two
   positions is not a whole number of bars (multiple of 4 beats), and when a
   handoff runs past a known fade or end.
3. **Refuse to start** if a deck you need is already playing. Check that the
   decks exist (`[Channel3]` needs 4 decks shown in Mixxx).
4. **Clean slate on every used deck:** filter `[QuickEffectRack1_[ChannelN]]
   super1 = 0.5`, EQ `parameter1..3 = 1.0` (Mixxx unity), `pitch_adjust`,
   `volume`, `orientation = 1` (center). An interrupted mix can leave a
   filter closed, which made one experiment sound muffled (2026-10-02).
5. **Find tracks in the library, never by path.** Look up the exact `track_id`
   by artist and title in the library DB (`library_track()` in the patterns).
   When the library holds several copies (Ariana's song is on two deluxe
   editions), pass a folder hint and match the copy in the plan's
   `playlist.json`; the helper refuses to guess.
   A hardcoded `/Volumes/<drive>/...` breaks on other machines and fails
   `tests/test_collection.py` (it scans everything under `brain/`, including
   `authoring/` scripts).
6. **Load and cue** with `hands.run_mix_plan.load_deck(mixxx, deck, path,
   cue_seconds=..., expected_bpm=native_bpm)`. It verifies the cue and sets
   keylock and quantize on. Change tempo with `set_bpm_target`.
7. **Start in phase:** press play about 0.05 s before the target bar of the
   deck already playing, then set `beatsync_phase`. Quantize lands it on the
   beat. Time entries by polling `playposition * duration` against source
   seconds. Don't count beats.
8. **Skips and re-entries** use `beatjump_size` plus `beatjump_forward` or
   `beatjump_backward` with a multiple of 4 beats, so bars carry across.
9. **Blends** fade the outgoing song's channel fader **gently**: a steady
   (linear) ramp over about 16 counts or more (`fade_out`, `GENTLE_FADE_BEATS`),
   never a 4-8 count drop, except for beat juggling, deliberate cuts and
   same-song handoffs. Bring the incoming song up with a smoothstep, and swap bass by
   moving `parameter1` (incoming at 0 until halfway). Treat a zero-length
   blend as an on-beat cut. Never divide by it.
10. **Print a word at each event** (`reprise`, `intro in`, `bass swap`, …) so
   Ernest can tell what he's hearing.

## Make every musical guess a flag

The flags are what make iterating fast. Expose at least:

| Flag | Why |
|---|---|
| `--handoff-beat` / entry beat | where the change happens, in that source's grid beats |
| `--blend-beats` (0 = cut) | how long the overlap is |
| `--<deck>-shift N` | whole-beat shift of one deck against the bed. Weak snare analysis often leaves the backbeat **one count off**, and `--ariana-shift -1` fixed exactly that |
| `--mode blend\|jump\|…` | two decks versus a jump on one deck |
| pitch / EQ / volume constants or flags | tuning a layer |
| `--no-full-song` | stop shortly after the interesting part, for quick repeats |

Default to the best values found so far, and put them in the docstring with
the date.

## Grid math

`seconds = first_beat_seconds + beat * 60 / bpm`, using the library DB's
`beat_phase` (or `phrases`) row for that exact `track_id`:

```python
from contextlib import closing
from brain import library_index
with closing(library_index.connect(library_index.current_index_path())) as db:
    row = db.execute("SELECT bpm, first_beat_seconds FROM beat_phase WHERE track_id=?", (tid,)).fetchone()
```

Snap Ernest's timestamps to the grid, keep jumps a multiple of 4 beats, and
prefer landing a little early (in the section before) over clipping a vocal
pickup. Live-drummed records can drift from a constant grid over minutes, so
offer a shift flag rather than trusting the grid blindly.

Trust Ernest's timestamps and the DJ notes over synced lyrics. The *I'm
Coming Out* lyric file shows singing in an intro that is instrumental to
0:43.

## Find where a sample comes from (sample-source alignment)

When one record samples, interpolates or remixes another, matching drum counts
is not enough: two decks blend as "the same instrumental" only when both play
**the same bar of the same riff at the same moment**. Measure it instead of
guessing (2026-10-03, Diana Ross *I'm Coming Out* -> *Mo Money Mo Problems*:
after many count-based attempts failed, this found the blend Ernest kept):

1. Decode both files (analysis only; nothing is played or published).
2. Compute chroma (which notes sound, drums mostly ignored) with
   `librosa.feature.chroma_cqt` (hop 512 at 22.05 kHz), normalised per frame.
3. Take the sampling record's sample-only stretch (e.g. Mo Money's intro,
   0:00-0:17.5, before the rap) and slide it across the source song.
4. Try several speed ratios: un-slowed, slowed to the sampling record's BPM, and
   slowed from the source's *live* local tempo. Old samples were usually slowed
   turntable-style. The best mean similarity gives **where** (source second for
   the sample's 0:00) and **how much** it was slowed. Repeats spaced by whole
   phrases (here every 4 bars) confirm it.
5. Blend in **unison**: start the sampling record at that point exactly when the
   source reaches the matched second (quantize off), at the source's live tempo;
   tune one deck so the riff pitches agree (here the source down 0.5 st, keylock
   on); then fade the outgoing deck slowly (Ernest liked 40 counts).

Result for this pair: Mo Money's 0:00 = *I'm Coming Out* 175.59 s (2:55.6), her
reprise at ~110.7 BPM slowed to 104.38 (score 0.953 vs 0.923 un-slowed). Live-drummed
sources drift from a constant Mixxx grid, so measure the source's live tempo
(here 110.73 BPM vs the grid's 109.25) and time the blend by it.

## The loop

1. The agent writes the script, runs `--dry-run`, and gives Ernest the
   command.
2. Ernest runs variants and reports what he hears, or pastes his terminal.
3. The agent adjusts defaults or adds a flag. Repeat.
4. **When he likes it, record it right away:**
   - **In DJ notes.** About the song in every mix → library note
     (`tracks.dj_notes`). Only this mix → the plan's note overlay. Write it
     as prose:
     - mark it human-verified, with the date,
     - give the source seconds and grid beats,
     - give the exact flags and the script path,
     - list what was tried and rejected.
     Don't write live `key=value` directive tokens unless the planner should
     act on them; the parser reads them anywhere in a note.
   - **In the script.** Make the winners its defaults.
5. **Fold it into the full mix only when Ernest asks.** Use existing
   directives where they fit. When the plan builder can't express the move
   yet (a same-song second-deck re-entry, a third deck), say so and record it
   as a gap in `docs/HANDOFF.md` rather than forcing it.

## Log

| Date | Experiment | Result |
|---|---|---|
| 2026-10-01 | Diana Ross hook over Ariana + Mo Money instrumental (3 decks) | Backbeat one count off; `--ariana-shift -1` fixed it; still dropped. The same shift was carried into the full mix's Ariana layer. |
| 2026-10-02 | *I'm Coming Out*: 2:55 reprise first, then the 0:00 intro on deck 2, then the song with the trumpet solo skipped | **Kept.** `--handoff-beat 368 --blend-beats 4` after nine rounds; recorded in the song's library note. |
| 2026-10-02 | Mo Money segment creative pass (Diana Ross bookends, Ariana in segments) | Diana Ross into Mo Money: an 8-bar loop with a filter thin-out did not work; a long 32-beat blend under her chorus was jumbled and jarring. Ariana 12 beats earlier on the instrumental (`--ariana-shift 12`) with the instrumental under verse 1 and chorus 1 alone: good. Full-range instrumental slam at chorus 2: not good. Gambino in-and-out pattern: in progress. |
| 2026-10-03 | *I'm Coming Out* -> *Mo Money Mo Problems*: riff crossovers, loop-drop, "I'm"-cued 2-deck blends | Did not sound right; loop-drop "sounds terrible" (the 1-bar loop is an effect on its own). **Kept: the unison blend** from sample-source alignment (Mo Money 0:00 = her 2:55.6, 110.73 BPM, her deck -0.5 st, 40-count fade). |
