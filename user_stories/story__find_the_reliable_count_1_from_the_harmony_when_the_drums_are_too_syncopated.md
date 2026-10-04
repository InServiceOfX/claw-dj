<!-- pdd-story-prompts: prompts/hands/live_kit_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-03 -->
<!-- pdd-story-intent: docs/intents/intent__find-the-reliable-count-1-from-the-harmony-when--2ec65b5e.md -->

# User Story: Find the reliable count 1 from the harmony when the drums are too syncopated to count

## Story

When records are heavily syncopated or live-drummed, the drums are a poor
guide to where count 1 is, and Mixxx's constant beat grid drifts away from
a live drummer. claw-dj stops trusting drum onsets and the grid to decide
count 1. It finds the reliable count 1, and the matching bar between two
songs, from the **harmony**: chroma, which notes are sounding, with the
drums mostly ignored.

Count 1 is then where the blend lands: the first beat to drop on and sync
to.

## Acceptance criteria (observable)

1. **Count 1 within a song.** From chroma, find where the song's harmonic
   loop or phrase restarts, and the song's real local tempo there. Use that
   as the bar and phrase grid for cueing and blending, instead of a constant
   grid that drifts on live drums.
2. **Matching bar between songs.** When two songs share harmonic material (a
   sample, an interpolation, a remix, a cover, the same riff), compare their
   chroma at several speed ratios. That finds which bar of one plays the
   same music as which bar of the other, and how much one was slowed.
3. **Blend on it.** Start the incoming song exactly on that matched count 1:
   - at the outgoing song's live tempo;
   - with one deck tuned so the shared material agrees in pitch;
   - with no quantize snap on that start;
   - with the outgoing deck fading out slowly, in unison (gentle channel
     fader, 16+ counts).
4. **Human anchor.** A count 1 the DJ names by ear (for example a sung word)
   is cross-checked against the measurement. Disagreement is reported, never
   silently overridden.
5. **Remembered.** Verified count-1 positions, matched bars, live tempos and
   pitch offsets go into both songs' DJ notes, so any agent harness reuses
   them in any mix.
6. **Report the alignment.** A live run reports how far the incoming count 1
   landed from the target, in milliseconds, so a drift is visible rather
   than guessed by ear.
7. **Analysis only.** The measurement decodes audio to produce numbers,
   never audio to play. The blend itself is live in Mixxx on the original
   files.

## Examples

1. **I'm Coming Out (Diana Ross) → Mo Money Mo Problems (Life After Death
   CD1).** Both records are heavily syncopated, and count-based blends kept
   landing off. Her reprise really plays at about 110.73 BPM against a
   109.25 grid. Chroma cross-correlation showed Mo Money's 0:00 is her
   reprise at 175.59 s (2:55.6), slowed from ~110.7 to 104.4 BPM (match
   0.953 slowed vs 0.923 unslowed), with the phrase repeating every 4 bars.
   Mo Money's count 1 starts when her reprise reaches 175.59 s, Mo Money at
   110.73 BPM at its natural pitch, the Ross deck down 0.5 semitones, her
   channel fader fading over 40 counts. Ernest, 2026-10-03: "this sounds
   great, let's roll with this ... whatever you did by examining the
   beatport or whatever, that was key".
2. **Human anchor on the same blend.** Ernest named her sung "I'm" as count
   1 (downbeats at 184.885 s and 191.370 s), and Mo Money's "I'm" at 0:00
   and 0:09. These are the anchors a future measurement must be checked
   against; the cross-check itself is not built yet.

## Must not

- Do not decide count 1 for a syncopated or live-drummed record from drum
  onsets or the constant grid alone.
- Do not let quantize snap a measured start back onto the drifting grid.
- Do not override a count 1 the DJ named by ear without reporting the
  disagreement.
- Do not render audio to make or test the blend.

## Related

- `story__when_i_mix_the_same_beat_or_sample_lineage_i_use_the_instrumental_as_a_short_bridge.md`
  (sample lineage; this story finds *where* the lineage lines up).
- `story__when_i_blend_i_match_the_snare_not_just_the_beat.md` (the drum
  answer, when the drums are steady enough to trust).
- `docs/LIVE_MINI_EXPERIMENTS.md`, "Find where a sample comes from
  (sample-source alignment)", has the measurement recipe.

## Source

Ernest, 2026-10-03, after the unison blend:

> is it possible to generalize it to how you used chrona to essentially
> find the beat matching, because clearly for example on both I'm Coming
> Out and Mo Money Mo Problems, they're both so highly syncopated that we
> needed to find the reliable count 1, the first beat to drop to sync on?
