<!-- pdd-story-status: drafted-2026-09-27; authored performances do this live on Mixxx (Opus 5.5 Who Shot Ya pass 2); the generic planner does not place layers yet -->
<!-- pdd-story-areas: shared_performance, performance_author, performance_measure, plan_mix_build, mix_directives, playback -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Three or more decks, every deck has a job and one backbeat

## Story

As a DJ, I want to play three or four decks at once, not only to blend one
song into the next. I want to layer records that share a beat for a fuller,
more creative sound: melodies, percussion, bass and vocals combined in ways a
two-deck blend cannot. For example:

- a vocal over an instrumental bed that carries the bass;
- a double of the same recorded vocal from a second copy (a **same-take
  double**);
- a full copy of a record taking the mix back while another fades out.

These layers can run a whole section. They can also come in as **very short
bursts in the middle of a mix**.

A **same-take double** is when two different files contain the exact same
recorded vocal performance. The Biggie album *Who Shot Ya* and the *Club Mix*
are an example: same vocal, different mixdown. Played together on the beat, one
voice sounds twice and thicker. A different vocal is not a double. Ja Rule's
hook over Biggie's is two voices talking over each other.

## Acceptance criteria (observable)

1. **Every deck has a named job:** lead vocal, bass bed, double, incoming,
   outgoing or skip cover. The live log names each deck's song, job and EQ.
2. **One backbeat.** All playing decks share the plan's pattern clock. A
   rendered check (`brain.performance_measure verify`) shows every window
   with three or more decks locking at 0 beats, never ±1 beat.
3. **The low end has one owner.** At most one deck carries full bass. The
   others have their lows turned down.
4. **One vocal at a time.** The exceptions are a proven same-take double
   (`brain.performance_measure align` reports `same_take_likely`) or a
   call-and-response that a DJ note asks for.
5. **Short bursts are allowed:** 4–16 beats, starting and ending on beat or
   8-beat boundaries.
6. **The planner places layers itself. A DJ note takes precedence.** Build
   proposes layers where the measurements support them. A human DJ note that
   asks for, moves or forbids a layer wins over the planner's choice.
7. **At most four decks.** A plan that needs more fails outright. It never
   quietly drops a layer.
8. **Every deck respects the hard cutoffs:** mandatory skips, starts and ends,
   on the layer deck too.
9. **Measurements support, the ear decides.** Numbers pick and check the
   placement. Ernest's listening pass accepts it.

## Must not

- Add complete records together at full gain.
- Stack two different vocals by accident.
- Claim a layer that the runner cannot actually play.
- Fix a layer frequency in code. How often layers appear is not yet known.

## How often: still being learned

Ernest, 2026-09-27: how often to layer is not decided. Keep experimenting,
and learn it from:

- these user stories;
- DJ notes;
- external YouTube videos, audio files and instructions found on the web.

Record what is learned here or in DJ notes. Do not hard-code a rate.

## Example

Opus 5.5 *Who Shot Ya* variations, pass 2
(`notorious-big-who-shot-ya-variations-opus-5-5`):

- **Double-up, 19:42–20:03.** The album copy of Biggie's hook is stacked on
  the Club Mix's hook, with its bass off.
- **Four-deck finale, 21:53–21:58.** Instrumental bed, Club Mix, album
  double, and a full album copy taking over. The Club Mix fades. The mix
  closes on the album it opened with.

Ernest recorded it and liked the ending. The render check locks every window
at 0 beats.

## Relationship to existing stories

- [Highlight vocals over an instrumental](story__when_i_highlight_vocals_in_a_full_mix_i_keep_an_instrumental_underneath.md):
  the two-deck vocal-plus-bed case. This story adds more decks.
- [Backbeat matching](story__when_i_blend_i_match_the_snare_not_just_the_beat.md)
  applies to every deck at once.
- [Mandatory source ends](story__mandatory_source_end_survives_every_mix.md)
  applies to layer decks.

## Tools

The authoring and measurement workflow is in
[docs/SAME_BEAT_CONTINUOUS_MIX.md](../docs/SAME_BEAT_CONTINUOUS_MIX.md).

## Source

Ernest, 2026-09-24/26: "take advantage of the 3 decks … create incredible
sounds and blended tracks and melodies and percussion, bass, like never before".
Later: "we uncovered some new techniques: 3 or more decks mixing". On the
ending: "maybe it could be a technique to be used in the future and in very
short intervals in the middle of the mix".

Ernest, 2026-09-27, on the draft: "planner place layers itself, and then if DJ
note asks then it'll take precedence". On frequency: "let's keep
experimenting and gaining insight from my user stories, DJ notes, and external
youtube videos, audio files and instructions you find on the web".
