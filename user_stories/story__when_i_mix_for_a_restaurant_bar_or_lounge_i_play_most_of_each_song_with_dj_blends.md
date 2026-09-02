<!-- pdd-story-status: drafted-2026-08-31 -->
<!-- pdd-story-areas: mix_profiles, build_mix_plan, plan_mix_build, mix_graph -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Restaurant / bar / lounge mix feel plays most of each song with DJ blends

## Story

As a DJ programming a **restaurant, bar, or lounge** that would
otherwise run a sequential playlist (song starts, song ends, silence,
next file), I want claw-dj to play **most of each song** and still
**mix like a DJ between them**: smooth blends, not start/stop.

This is Mix feel on `#mix` (pacing), not DJ transition format
(hiphop-rnb-8bar / guided). It is a **new preset**, not a retune of
Club set or Mix to listen.

- **DJ showcase** — short, varied clips and flourishes. Wrong room.
- **Club set** — dancefloor: energy lock, beat never stops, ~75s
  rides, occasional tricks. Wrong room.
- **Mix to listen** — a listening mix that plays the *best part* at
  whatever length earns it. That can still clip a song to ~85s / a
  few phrases. A dining room wants the record, not the highlight.

For this feel, given a finalized playlist, claw-dj **chooses the order
that blends best** (BPM / key / lineage / existing mix-graph), cues
near the start when that is legal, rides **most of the duration**
(leave the last phrase or so for the outgoing blend), and uses long
smooth blends. No showcase chops. Verses still get respected.

## Acceptance criteria (observable)

1. **Its own Mix feel.** `#mix` grows a fourth preset (working name
   `lounge-set`, GUI label **Lounge / bar**) with copy that names
   restaurant, bar, and lounge. Selecting it is visually highlighted
   like the other three. Club set and Mix to listen keep their current
   meaning and numbers.
2. **Most of the song.** Default ride is derived from each track's
   duration minus the outgoing blend (about 24–48 beats), not from
   `seconds_per_track=85` or a 2–4 phrase pattern. A 5-minute album
   cut is not a 90-second clip. `trust_ride_beats` is not required
   for that default — it is the profile.
3. **Smooth DJ joins, not playlist gaps.** Transitions are beat-matched
   blends. Hard cuts / brakes / flourishes are off. `avoid_silence`
   is on: the next song is already in before the last one ends.
4. **Order is mix quality, not crate order.** The finalized list is a
   pool. Deterministic local ordering (BPM / key / lineage) still
   runs. Human bunches and opener locks still win. Feel-only (no LLM)
   is enough.
5. **Verse rules still apply.** Do not enter or leave mid-verse to
   make the blend fit. Cue 0:00 or verse bar 1; fade after the verse /
   on the hook. Instrumentals have no verse.
6. **Example.** Who Shot Ya variations in a lounge: Biggie album
   version from 0:00 through the verses, then a blend — not a 85s
   body and not a club-energy chop.

## Must not

- Do not retune Club set to mean "restaurant." Club set stays a
  dancefloor profile.
- Do not silently change Mix to listen's 85s / best-part behavior.
  Sets that already use it keep that meaning.
- Do not play files end-to-end with a gap of silence (that is the
  sequential playlist we are replacing).
- Do not require an expert DJ format (8-bar / guided) for this feel.
  Format stays an independent control, default none.
- Do not start Mixxx to prove ride length. Duration math + dry-run
  beat counts are the check; ear is the venue check.

## Source

Ernest, 2026-08-31, on `#mix` Mix feel:

> we have these 3 "formats": Mix feel — pacing and performance
> density DJ showcase / Club set / Mix to listen we want to target a
> restaurant, bar, lounge, that would otherwise be playing a playlist
> sequentially, start and stop. but while we want to allow for most of
> the song to play, but still allow for smooth mixes and blends like a
> DJ between songs. So how much we ride a song will be for most of the
> song, and it'll, given a playlist of songs, choose which songs
> blends best together in what order.
