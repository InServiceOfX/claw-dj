# DJ Style Guide — craft lessons for building mix plans

A living reference of what actually sounds good, learned by ear across real
mixes. Meant to be read before building a NEW mix plan (by a human, by
Claude, or by an LLM engine driving `brain.mix_directives`/
`brain.pick_candidates`), and grown over time as more feedback comes in —
add to it, don't just re-derive these lessons from scratch each session.

## Universal principles (any genre)

- **Never start a cue mid-word.** The beatgrid/energy phrase-picker has no
  idea where words start — left alone, it can and does land mid-syllable.
  `brain.build_mix_plan.snap_to_lyric_line()` already fixes this
  automatically whenever synced lyrics exist; it's a structural rule, not
  something to re-litigate per track.
- **Ground every cue/ride/landing claim in real synced lyrics** (LRCLIB via
  `brain.lyric_timeline`), not memory of the song. Verify the exact
  `track_id` against `playlist.json` before writing dj_notes — the crate
  has duplicate copies of the same song across different album/compilation
  folders, and writing to the wrong copy is a silent no-op.
- **Openers need special handling.** Even a lyric-clean cue sounds abrupt
  as the very first thing anyone hears — there's no context to arrive
  into. Either start from the true beginning (`cue_seconds=0`), or use a
  dedicated opener style (`opener_style=echo_tease_drop` /
  `juggle_intro` / `juggle_brake_intro`).
- **`cue_seconds` on an opener with any `opener_style` is not just "where
  the ride starts counting from" — it's the exact load position AND the
  point the juggle/brake/tease mechanism rewinds to and resumes from.**
  Broke this live, 2026-07-19: extending an opener's ride by moving
  `cue_seconds` forward (to skip to a verse) silently pulled the whole
  juggle-brake-rewind drama into the middle of the song instead of the
  true instrumental intro, and the actual intro material never played.
  To extend an opener's ride, change `ride_beats` ONLY — recompute it
  from the *true* entry beat_index (almost always 0) to reach the same
  target ending, and never move `cue_seconds` away from the track's real
  start for as long as an `opener_style` directive is present.
- **Always dry-run before committing a new dj_notes/reorder batch.**
  Rebuild, inspect the actual `mix_plan.json` events (not just the
  console summary), and run the test suite. Several bugs in this
  project were only caught by reading the literal event JSON, not by
  trusting the plan-builder's own printed reasoning.
- **Show a diff before applying anything an LLM engine (NemoClaw/H-agent/
  generic) proposes.** A live test of the `mix_directives` pipeline
  caught a real instruction-following miss (told not to touch a track's
  BPM, it added a `play_bpm` directive anyway) — dry-run-first is
  load-bearing, not decorative.

## The #1 recurring bug: beatsync tempo bleed-through

**What happens:** Mixxx's `sync`/`beatsync` matches the *incoming* deck to
whatever the *outgoing* deck is **actually playing at** — not either
track's real/native BPM. If the outgoing deck was itself holding a
deliberately bumped or slowed tempo (from an earlier `play_bpm` directive,
or just because sync pulled it there and it hasn't settled back yet), that
gets silently inherited by the next track, and the next, potentially
chaining through several transitions.

**What it sounds like:** "this track got sped up/slowed down for no
reason", "why is the tempo whiplashing", "the speed up sounds terrible".
Confirmed live across many tracks in one session (2026-07-16) — Tha
Shiznit, Cassie → Wall to Wall, Love Will Never Do, Smooth Operator →
Sweetest Taboo → Hang On To Your Love, Amazing, Escapade, Jane Child, All
for You, Toni Braxton all hit this same bug via different technique paths.

**The fix, already built, always the same shape:** set
`play_bpm=<the track's own real analyzed bpm>` in that track's dj_notes.
This sets `incoming_bpm_target` for the transition, which makes the runner
(`hands.run_mix_plan`) skip the `beatsync` call entirely and hold the deck
at its own real tempo instead. It works this way *by design* even when the
technique's `moves` list still literally contains `"sync"` — the runner's
sync-skip check is independent of the plan's move list.

- Use this on **any track whose entry sounds artificially fast/slow**,
  regardless of how big the underlying BPM gap actually is — even
  "nearly identical" pairs can bleed if the outgoing deck wasn't at its
  own native rate for some other reason.
- This does **not** fix a genuine, large BPM gap between two tracks —
  it just stops one from *pretending* to match the other. A big gap will
  still sound like a big gap (an honest tempo-mismatched blend), which is
  usually the more honest, better-sounding choice than a fake full sync
  across a huge ratio anyway.
- `tempo_gap_blend` (the technique chosen for genuinely large gaps) had
  "sync" in its own moves list despite its docstring promising a gentler
  rate-nudge instead — fixed 2026-07-16, `sync` removed from that
  technique specifically. If a *different* technique (`standard_blend`,
  `smooth_blend`, `key_adjusted_blend`, etc.) is chosen for a gap that
  still sounds bad, the per-track `play_bpm=native` hold above is the
  right tool, not another technique-level code change — those techniques'
  use of `sync` is fine for the close-tempo pairs they're normally chosen
  for.

## Showcase flourishes (scratch-in, loop-roll, transformer-cut, stutter/censor)

These rotate automatically per the profile's `flourish_every` setting and
are meant to be a light seasoning, not something on every transition. A
`transformer_cut` (rapid crossfader chop, reads as a "beat juggle") landing
on the wrong track can sound genuinely bad — if a specific transition
needs to be a plain fade regardless of what the rotation would otherwise
pick, set `no_flourish` (bare flag) in the **incoming** track's dj_notes.

## Genre notes

### West coast hip-hop / G-funk (early 90s Dre/Snoop/Warren G era)

- Dramatic, showy openers are wanted and fit the culture: `juggle_intro`
  (juggle a second copy over the instrumental intro) and
  `juggle_brake_intro` (juggle, then an abrupt vinyl-brake stop, rewind,
  replay the cue) both work well here. Keep the brake itself snappy for a
  tease-and-replay (`brake_seconds≈0.7`) — the *separate* `brake_out` used
  for genuine outlier-BPM hard beat-drops (see below) can stay closer to
  the default ~1.4s, since that's a different, less rapid-fire moment.
- A genuine BPM outlier with no real match anywhere in the set (e.g. a
  track analyzed at ~180bpm against a set that's mostly 90-100bpm — likely
  a double-time misdetection, a separate unfixed backlog item) is exactly
  where `entry_style=beat_drop` (the vinyl brake-stop hard cut) earns its
  keep. Validated and liked live on "Murder Was The Case."
- Protect full verses/choruses precisely by landing on the actual next
  lyric line after a monologue/spoken intro, not just "somewhere past the
  intro" — several tracks in the West Coast mix needed this
  (Regulate, Lil' Ghetto Boy, Stranded On Death Row).

### R&B / Soul (early 90s–2000s, Sade/Janet Jackson/George Michael era)

- **Smooth blending is the priority — avoid abrupt endings and showcase
  tricks unless explicitly asked.** Set the mix-brief to
  `"use hard cuts sparingly, avoid abrupt endings, keep it blending"`
  (maps to `avoid_silence=True` in `brain.mix_profiles.apply_brief`) as a
  sensible default starting point for this genre, and reach for
  `no_flourish` liberally on individual transitions that don't need a
  trick.
- Ride full verses **and** most of the chorus before transitioning out —
  cutting right as the chorus starts (rather than through it) reads as
  premature even when the cue itself lands cleanly on a word boundary.
- A handful of "liberal tempo" tracks a user explicitly designates (in
  this session: the Al B. Sure! tracks) can be pushed further off their
  native tempo than usual to serve as bridges between otherwise-mismatched
  neighbors — but only tracks explicitly given that latitude, not as a
  general default.
- Even when BPM and key both score well on paper, a pairing can still
  "sound terrible" — likely a genuine production-era/style mismatch
  (e.g. an 80s synth-pop crossover hit next to 2000s dance-pop) that no
  compatibility score captures. When this happens after tempo-bleed and
  flourish fixes are already ruled out, the honest move is reconsidering
  the neighbor/order, not another directive on the same pair.

## Applying this to LLM-driven builds

`brain.mix_directives.build_prompt()` and `brain.pick_candidates`'s prompt
builders are the natural injection points if this file's relevant genre
section should constrain a NemoClaw/H-agent/generic-engine call — not yet
wired in as of 2026-07-16. Worth doing once this guide has enough real
mileage behind it to be worth hard-coding into a prompt.
