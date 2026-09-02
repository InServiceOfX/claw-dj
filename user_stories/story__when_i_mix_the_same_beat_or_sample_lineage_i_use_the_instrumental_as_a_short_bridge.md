<!-- pdd-story-status: drafted-2026-08-31 -->
<!-- pdd-story-areas: stems, build_mix_plan, plan_mix_build, mix_directives, mix_order_brief -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Same-beat / sample-lineage mixes use the instrumental as a short bridge

## Story

As a DJ building a mix that shows **sampling lineage** or **the same
beat used by different artists**, when I also have that beat's
**instrumental-only** version in the set, I want claw-dj to **use it as
a bridge** between two vocals that sit on that instrumental — not as
the next full song.

Load the instrumental on the free deck and blend. Typical uses:

1. **Short solo helper** — 8–32 live beats of the naked beat between
   two vocals (or between verses), then blend into the incoming rapper
   from bar 1 / 0:00.
2. **Simultaneously mixed** — both decks live, crossfader near the
   middle: the instrumental plays *with* a full-mix vocal, not after
   it. The rapper sits on the isolated beat instead of colliding with
   the outgoing vocal.
3. **Persistent bed** — keep that instrumental on a deck across more
   than one vocal. Fade the outgoing rapper out, load the next vocal
   on the freed deck, blend it in; the beat never leaves. That is how
   the same file is used more than once without cloning it in the
   playlist.

The instrumental **may be used more than once** in the same mix. Each
solo helper is short; a persistent bed may stay up across several
songs. Playing it end-to-end as a sequential title after its own vocal
is still the boring same-beat strip already forbidden for *Patiently
Waiting* → *Patiently Waiting (Instrumental)*.

This is a different object from `vocal_over_bed` (an **acapella**
layered over a bed). Here the neighbors are **full mixes with vocals**;
the instrumental is a helper or a bed, not the next song. With the
current two-deck runner, simultaneous means instrumental + one vocal
(or a two-vocal blend without a third layer). A three-way stack
(vocal A + vocal B + instrumental) would need a third Mixxx deck;
that is later, not required for this story.

## Acceptance criteria (observable)

1. **When it applies.** The finalized set contains an instrumental-only
   stem **and** at least two full-mix vocals that use that same beat
   (same-song interpolations, freestyles, remixes, or documented sample
   lineage). Unrelated instrumentals in the crate do not fire.
2. **Helper, not a song.** An automatic `play_body` on that instrumental
   is short (about 8–32 beats unless a human locked a longer ride). It
   is not mix-to-listen's default 85-second clip, and it is not
   `full_track`.
3. **Reuse is legal.** The Arrange / playlist list still shows the
   instrumental **once**. The executable mix may load it again, recut
   it, or keep it live under later vocals. Duplicate `track_id`s in
   `playlist.json` remain illegal; the planner injects helper / bed
   events, it does not clone the selection. "Used more than once in
   the mix" is not "listed more than once in the crate."
4. **Vocals still get their verses.** Bridging with the instrumental
   does not clip the outgoing or incoming rapped/sung verse. Cue the
   incoming vocal at 0:00 or on verse bar 1; fade the outgoing vocal
   after its verse / on the hook, then (or while) the instrumental is
   up.
5. **Human locks win.** An explicit note that this instrumental *is*
   the next song (`trust_ride_beats` with a long ride, or
   `showcase_instrumental`) is honored. Default is helper.
6. **Example (Who Shot Ya variations, 2026-08-31).** Notorious B.I.G.
   album *Who Shot Ya* (Ready to Die) opens from 0:00 through the
   verses. The 1995 VLS instrumental is a short helper into the Club
   Mix / later interpolations (50 Cent, Ja Rule, Jim Jones, K-Dot,
   DMX, Jadakiss). It is not a 3-minute pallette-cleanser chapter.

## Must not

- Do not ride the matching instrumental as the next full song after its
  own vocal (same-beat strip).
- Do not require the DJ to duplicate the instrumental file in the
  playlist in order to use it twice.
- Do not treat this as `vocal_over_bed` or as a dry acapella showcase.
- Do not invent a lineage pair from similar BPM/key alone. Title,
  filename, and known same-song / interpolation evidence first.
- Do not start Mixxx to prove a bridge.
- Do not skip this helper on mix-to-listen just because the profile
  prefers long vocal rides — the *vocals* stay long; the *instrumental*
  stays short.

## Source

Ernest, 2026-08-31, while fixing `notorious-big-who-shot-ya-variations`:

> If we're having a mix showing either sampling lineage or the same
> beat (i.e. instrumental) but used by different artists, *and* we have
> the instrumental at hand, use, as necessary, when 'bridging' or mixing
> between two of the songs that use the instrumental, feel free to load
> the instrumental into the deck and blend the 2 songs together. Use the
> instrumental to help bridge between 2 songs with literally the same
> instrumental. Thus, this implies the instrumental can be used more
> than once in the mix and typically, playing it for only short periods
> of time on its own, or blending it together with another song using
> the same instrumental to play (i.e. or for example the crossfader
> right in the middle blending each together).
