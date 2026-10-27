# Lessons from hand-building a live mix

From the Mo Money segment, built live with Ernest over 2026-10-01..04: Diana
Ross *I'm Coming Out* -> *Mo Money Mo Problems* -> Ariana Grande *Break Your
Heart Right Back* -> back to Ross. Script:
`brain/data/plans/segment-notorious-big-mo-money-mo-problems/authoring/mix_reprise_first_full.py`.
These apply to any claw-dj mix, in any agent harness (Claude, Codex, Grok,
Hermes, ...). Each lesson cost at least one "that doesn't sound right".

## Working with Ernest on a mix

**Pairing comes before timing repair (Ernest, 2026-10-21).** He kept Robin
Thicke *Sex Therapy* → Janet Jackson *Would You Mind* → Jesse Powell *You*
because both handoffs match in **energy and vibe**, "more of a feel". This is
distinct from hearing/confirming count 1, backbeat or snare alignment. Shared
key, grid BPM, drum share and technical scores cannot establish that musical
fit, and a quiet-intro prediction cannot overrule a handoff he has heard and
liked. First choose neighbours whose felt pace, vocal character, density and
mood belong together; then work on their timing and vocal space. Ernest
reaffirmed this on 2026-10-22, keeping Pacifico → Sorry → The-Dream Ghetto
for complementary energy, vibe and **percussion themes** that sound pleasant,
without claiming perfect beat/backbeat matching. Record which
kind of approval was actually given. Preserve approved musical decisions when
refining other seams; do not force a rejected pair to work with cuts or nudges.

1. **Audition one piece, live, before touching the full mix.** Write a short
   flagged script (`docs/LIVE_MINI_EXPERIMENTS.md`). Ernest runs it in his own
   terminal and reports what he hears. Failed ideas are useful; keep their
   lessons, not their code.
2. **Keep one total-mix script.** Delete superseded working copies when a
   direction is chosen. Several "mix" scripts confused everyone.
3. **"Don't touch" means unchanged.** When he approves a part ("everything
   before was great"), later passes must leave it exactly as it is. Back up the
   script before every pass, outside the repo, and say where the backup is.
4. **Before handing over a command,** run `--dry-run`, then run the script
   end to end against a fake Mixxx. That catches crashes, hangs and refused
   moves; it says nothing about sound. Tell him plainly what has not been
   heard yet.
5. **Record what he approves right away** in DJ notes: source seconds, grid
   beats, the exact flags and the script path, marked human-verified with the
   date.
6. **Old constants can be wrong,** even ones commented "measured". Here
   `ROSS_SHARP` and `ARIANA_PITCH` did not match a fresh chroma measurement.
   When something sounds off, re-measure instead of tuning around it.

## Timing and beat matching

1. **The grid is not the tempo.** Mixxx gives a live-drummed record one
   constant BPM. *I'm Coming Out*'s reprise really plays at 110.73 against a
   109.25 grid. Mixxx's BPM display is grid x rate, so a deck slowed to match
   that reprise shows 107.79 while the music runs at 109.25.
2. **Find count 1 from the harmony** when drums are syncopated or live
   (`user_stories/story__find_the_reliable_count_1_from_the_harmony_when_the_drums_are_too_syncopated.md`).
3. **Whole-beat or phrase shift flags are too coarse.** Offer a millisecond
   nudge (`--outro-nudge-ms`) and print the measured offset after each start.
   Trust his ears over the meter: the match he picked read "25 ms early".
4. **Time events from each deck's play position,** never from timers or beat
   counters. Count loop passes from the deck's own wraps: a timed release let
   one pass too many through.
5. **A "half-a-count-off" blend is often grid drift, not a wrong count.**
   Sade *Cherry Pie* (vinyl rip, live drummer) → *Paradise*, approved
   2026-10-17. Both grids were "right", but in the blend window Cherry Pie's
   hits came about 100 ms early and Paradise's about 40 ms late. That's 140 ms
   apart, close to a sixteenth note, and Ernest heard it as "off by an eighth
   note plus a little". The fix was a +140 ms incoming nudge. No new count,
   order or cut was needed. How to handle it:
   - Measure each song's real hits against its own grid, **in the blend
     window**. A live or vinyl record wanders, so a reading from elsewhere
     in the song doesn't hold.
   - Nudge the incoming by the difference.
   - Check the runner's `measured lead … ms after sync` line. Mixxx's
     quantize used to snap the nudge back without anyone noticing.
   - Two syncopated songs can blend well if their backbeats really line up.
     Here both were the same band and key at about 99 BPM.
   - When one side has no steady backbeat in that window (*Sorry*'s intro),
     there's nothing to line up. Re-pair instead.

## Pitch

1. **Keylock off when a sample is sped back to its source** (AGENTS.md;
   `docs/LIVE_MINI_EXPERIMENTS.md`). Keylock is on by default here. Old samples
   were slowed turntable-style, so speeding the sampling deck back up with
   keylock off restores the source's exact pitch, with no processing. Keylock
   on plus a guessed pitch_adjust was half a semitone off and tinny.
2. **Measure the pitch relation before tuning.** Use the beat-synced chroma
   semitone shift between the two songs, plus `librosa.estimate_tuning` for
   cents. Use pitch_adjust only for what is left over.

## Blends between songs

1. **Long and gentle.** Song-to-song blends of about 32-40 counts, steady
   linear fader ramps. The code refuses anything under 16
   (`user_stories/story__blend_with_gentle_faders_never_fast.md`).
2. **When the incoming intro is too short, stretch it; don't shorten the
   blend.** Ariana's verse starts by 0:04. Repeating her second 4 counts
   (3 plays in all) while her fader came up worked. Four passes of a bar never
   sounded good.
3. **A 1-bar loop is a feature, not a blend device.** The Ross "fire" loop
   works as an opener; looping into a different song and dropping out sounded
   terrible.
4. **Sample lineage: blend in unison on the sampled bar.** Start the source
   exactly on the bar the sample took, at the same tempo and pitch. Loop the
   length the sample used (here 4 bars, 2 passes) while the faders cross. A hard
   break and a slowed source were both rejected for this pair.
5. **Skip a section with the same song on another deck,** blended over 4 beats
   (Diddy's verse, the trumpet solo). Never an audible beat jump.

## Layering another record under a song

See `user_stories/story__when_i_layer_another_record_under_a_song_one_layer_at_a_time_lined_up_by_harmony.md`.

1. **At most one supporting layer at a time.** Two instrumentals under a song
   is "too much". Under a chorus that has its own bass, don't add a second
   bass ("muddled"). Use the layer's riff or hook part with its bass cut, a
   little under full (channel fader about 0.85).
2. **Line each section up by harmony, separately.** A short odd-length break
   (Ariana's 4-beat break at 1:07) shifts one song against the other's 4-bar
   harmony loop. A single offset for the whole song was a bar off from there
   on. Measure the offset per section with beat-synced chroma.
3. **Choose which part of the layer plays by measurement.** Chroma found the
   instrumental's "all bass part" (beats 288-304), its chorus bars, and the
   bar with Ross's sampled "I'm", and where each matches the song.
4. **Move layers on EQ over a running bed.** A layer comes in and goes out on
   short EQ ramps (a bass swap). A deck only jumps to a new section while it is
   silent.
5. **Filters are brief accents,** 1-2 beats into a downbeat, snapped off on
   count 1. A filter held through a chorus sounded muffled.
6. **Selective vs continuous.** A different song gets selective layers, one at
   a time. A same-beat lineage (Who Shot Ya over its own instrumental) can
   carry a continuous bed (`docs/FULL_MIX_INSTRUMENTAL_LAYERING.md`).

## Measuring with beat-synced chroma (analysis only)

Decode each file (nothing is played or written as audio). Compute
`librosa.feature.chroma_cqt` (22.05 kHz, hop 512) and average it over each grid
beat (bpm and first beat from the library's `beat_phase`), so songs at
different tempos compare beat for beat. Slide one song's section over the
other's beats and roll the 12 pitch classes by -2..2. The best mean cosine gives
the beat offset and the semitone shift. Repeats spaced by whole phrases (here
every 16 beats) confirm it. Per-beat low-band share (< 150 Hz) and level find
"bass-only" parts.
