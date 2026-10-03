<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-03 -->
<!-- pdd-story-intent: docs/intents/intent__skip-a-section-by-handing-off-to-the-same-song-o-4a636e8b.md -->

# User Story: Skip a section by handing off to the same song on another deck

## Story

When a section of a song must not play (a guest verse, a skit, a solo), or
the mix should re-enter the song somewhere else, claw-dj does **not** jump
on the playing deck: an instant jump is audible. A **second copy of the
same recording** on another deck comes in beat-matched and takes over with
a short blend.

This is how a skip from the DJ notes (`skip_from_seconds` /
`skip_to_seconds`, `mandatory_skip`) is performed live. It complements
`story__when_a_track_opens_with_a_skit_i_skip_it.md`, which decides *what*
to skip; this story decides *how* the skip sounds.

## Acceptance criteria (observable)

1. **Same point of the music.** The second copy is cued so the repeated
   material continues seamlessly across the handoff. When a chorus or hook
   repeats, the distance between the copies is measured from the vocal, not
   assumed from the beat grid.
2. **Let the section before it play.** The handoff happens late in the
   section before the skip (most of that chorus plays), not at its first
   bar.
3. **Short blend, bass swapped halfway.** About 4 beats. The blend finishes
   before the excluded section starts, so none of it is ever heard.
4. **Bars and backbeat carry across.** The distance between the copies is a
   whole number of bars.
5. **Mandatory skips still hold.** The technique never plays any part of a
   mandatory exclusion and never weakens one.
6. **Live only.** Both copies play the original file in Mixxx. No rendered
   audio.

## Examples

1. **Mo Money Mo Problems (Life After Death CD1), Diddy's verse.** Chorus 2
   repeats chorus 1's vocal exactly 96 beats later (55.31 s; a 100-beat
   distance audibly jumped the lyric about 4 beats). Deck 1 plays chorus 1
   to 66.7 s (grid beat 116); the second copy takes over at 121.9 s (grid
   beat 212) with a 4-beat blend, finished before Diddy's verse at 71.3 s.
   Ernest, 2026-10-03: "this just sounds great and a lot better than the
   skip before."
2. **I'm Coming Out (Diana Ross), reprise first.** The 2:55 reprise hands
   off to the same song's 0:00 intro at grid beat 368 with a 4-beat blend
   (Ernest, 2026-10-02: "This sounds GREAT").

## Must not

- Do not perform a skip as an instant beat jump when a second deck is free.
- Do not align the copies by grid arithmetic alone when the music repeats;
  measure or let the human confirm.

## Source

Ernest, 2026-10-03. The instant beat jump over Diddy's verse was audible
("you can hear the skip"). He suggested blending the current deck into
another deck playing the same song, cued a little before Biggie's verse.
After the live run:

> this sounds great! ... great job! is there a way to generalize this, or
> make this a user story ... this just sounds great and a lot better than
> the skip before
