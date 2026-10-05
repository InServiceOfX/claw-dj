<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-04 -->
<!-- pdd-story-intent: docs/intents/intent__when-i-layer-another-record-under-a-song-one-lay-3090ed69.md -->

# User Story: When I layer another record under a song, one layer at a time, lined up by harmony

## Story

When I layer another record under a different song (an instrumental, a
sample source), claw-dj keeps the song clear and unmuddled. It never stacks
more than one supporting layer, and it lines each layered section up by
measured harmony, section by section.

## Acceptance criteria (observable)

1. **One layer at most.** At any moment at most one supporting layer plays
   under the song. Two instrumentals never play at once.
2. **No second bass.** Under a section that already has its own bass (a
   chorus, say), the layer does not add more bass. It uses its riff or hook
   part with its bass cut, a little under full (channel fader about 0.85).
3. **Lined up per section.** Each layered section is lined up by measured
   harmony (beat-synced chroma), separately. A short odd-length break in the
   song shifts it against the layer's harmony loop. One fixed offset for the
   whole song is wrong after such a break.
4. **The part is measured, not guessed.** Which part of the layer plays is
   chosen by measurement: its bass-only part, its chorus bars, or the bar
   with a sampled hook.
5. **Clean moves.** Layers come in and go out on short EQ ramps over a
   running bed. A deck only jumps to a new section while it is silent.
   Filters are brief 1-2 beat accents, never held.
6. **Selective vs continuous.** A same-beat lineage over its own
   instrumental may keep a continuous bed
   (`story__when_i_highlight_vocals_in_a_full_mix_i_keep_an_instrumental_underneath.md`).
   A different song gets selective layers.

## Examples

1. **Mo Money Mo Problems instrumental under Ariana Grande's *Break Your
   Heart Right Back*, 2026-10-04.**
   - Rejected: two instrumentals at once, and the instrumental's bass under
     her second chorus, were "too much" and "muddled".
   - Accepted: under the chorus, one layer (the instrumental's part with Ross's
     sampled "I'm") with its bass cut, at fader 0.85.
2. **Per-section offsets for the same pair.** Her 4-beat break at 1:07 shifts
   her song against Mo Money's 4-bar harmony loop:
   - before the break: instrumental beat = her beat + 8 (mod 16);
   - after it: + 4 (mod 16).

   The old single offset was a bar off from 1:07 on.
3. **Bass-only part, chosen by measurement.** The instrumental's "all bass
   part" (beats 288-304, 2:46) matches her 1:10 bass part best of anywhere.
   It is layered there alone.

## Must not

- Do not stack two supporting layers under a song.
- Do not add a second bass under a section that has its own.
- Do not use one fixed offset for a whole song without checking each section.
- Do not hold a filter through a section.

## Source

Ernest, 2026-10-04, on the Ariana section: "reducing the number of layers to
her track and one layer, let's try to make it unmuddled; we want to have at
least one layer along with her track but no more ... just use 1 of the
instrumentals, not 2, it's too much". Then: "by the second time Ariana Grande
sings her chorus, we shouldn't be layering on too much, just 1 layer and a
little more in the background, maybe play with channel fader to not be 100%
but almost 100% ... we shouldn't have the muddled bass version of the mo money
mo problems instrumental play during her 2nd time CHORUS".

Measurement and recipe: `docs/LIVE_MIX_LESSONS.md`.
