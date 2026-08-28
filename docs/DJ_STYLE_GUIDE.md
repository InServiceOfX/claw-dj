# DJ Style Guide — craft lessons for building mix plans

A living reference of what actually sounds good, learned by ear across real
mixes. Meant to be read before building a NEW mix plan (by a human, by
Claude, or by an LLM engine driving `brain.mix_directives`/
`brain.pick_candidates`), and grown over time as more feedback comes in —
add to it, don't just re-derive these lessons from scratch each session.

This guide is advisory craft knowledge. Versioned expert transition
grammars with hard, machine-enforced rules live separately under
`docs/dj-formats/` and in `brain/dj_formats.py`; see
`docs/dj-formats/HIP_HOP_RNB_8_BAR.md` for the first one.

## Universal principles (any genre)

- **Ride length is a judgment, never a rule — in any format or profile.**
  Ernest, 2026-07-31: "some songs have long interesting parts and should
  get more play, but some songs have very interesting and exciting parts
  but are short." How long a song plays should follow where its genuinely
  interesting material actually is, not a position in a rotation and not a
  fixed bar count. This is deliberately hard: judging what's worth playing
  is subjective and aesthetic, and no current signal in this repo measures
  it directly.
  Practical consequences:
  - Any ride number the builder produces is a **default to be overridden**,
    not an answer. `dj_notes` (`ride_beats`, `ride_phrases`, `full_track`,
    `trust_ride_beats`) always outrank it — the long by-ear tuning rounds
    recorded in `PROGRESS.md` are the real product, not a workaround.
  - `mix_profiles.ride_phrases_pattern` is a rotation indexed by position
    in the set, so track N gets its length because of *where it sits*, not
    because of anything in the music. Treat it as a placeholder for
    judgment, not a model of taste.
  - Prefer per-song structural evidence over pattern arithmetic when it
    exists: `lyric_timelines` chorus/verse boundaries say where a hook
    actually ends, which is a real reason to keep playing or to leave.
  - Never make a length constraint fail-closed. A format may legitimately
    constrain *where* a transition lands (bar downbeat, beat 1); it must
    not dictate *how long* a song plays. Conflating those two is exactly
    the bug fixed on 2026-07-31 (`format_min_ride_beats`).
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
- **Remix Report is a crate of mix-in/out recipes, not just ep.12.**
  Channel archive (335 videos, descriptions, irregular chorus counts):
  `Data/Public/youtube-transcripts/remixreport/INDEX.md`. Highest-value
  next lessons: choruses that are not 8 bars. Whisper of eps 088/093/096/099
  is now in `Data/Public/Videos/Youtube/parsed-{CtA3yOULp7k,MXz0B05_z0o,aaRsbpfAan8,H9TB81qM34s}/`.
  Rule: an 8-bar intro on an 8-bar chorus is the “perfect mix.” A 10-bar
  chorus waits 2 bars then intros (`chorus_bars=10`). A 6-bar chorus skips
  2 bars of the incoming intro (`chorus_bars=6` — *Magic Stick*). *Get Low*
  is 12 the whole way; mix from the start of that chorus, not the 3-6-9
  middle. *Over* is 9.5 — treat as 10; verse often leaks a half-bar early,
  so fade the outgoing before bar 10 ends. 24/40-bar pop choruses mix out
  *early*, they do not earn a longer ride. Remixes have different counts
  than the radio version. Jay-Z *PSA* also does not start on 1; opening
  sets are BPM-banded. Do not assume `phrase_beats=32` is the song.
- **The pickup is not beat 1.** Remix Report ep.12 (Holla Boyz *Show Me
  Love In Da Club*, https://youtu.be/hu_Y3dt2JWU): a vinyl-brake / “put
  your damn hands up” bar *before* the In Da Club beat is one full bar of
  anticipation. **Wrong:** start as if that brake is on 1. **Right:**
  start the brake early so the real beat arrives on 1. In dj_notes that is
  `pickup_beats=4` (or however many pickup beats the record actually has).
  Do not “fix” this by moving `cue_seconds` to the downbeat — that *is*
  the wrong way. Cue stays at 0; the downbeat is the landing.
- **If you tease a hit, play the hit.** A party break / mashup that sits
  on another song in the same set (Show Me Love In Da Club → In Da Club)
  is followed by that original, unless the original already played. The
  planner does this automatically (`mashup_payoff_pairs`). Same-song
  versions (instrumental, explicit remix of the same title) are not
  teases. Drop the original on its iconic first line when you have a
  verified lyric timestamp (`entry_style=verse_landing`; for In Da Club
  that line is “Go shorty”) — do not invent the second from memory.
- **Interpolation lineage plays the original first, then the tribute, on
  the matching lyric — not the whole album cut.** G-Unit *Straight Outta
  Southside* interpolates Ice Cube’s *Straight Outta Compton* couplet
  (“Straight outta …, crazy motherfucker named …”). Cue Compton on the
  bar-1 before Cube’s first word (synced LRC 12.52s, grid beat 20 at
  12.24s); ride his verse only; land Southside on Banks’s matching line
  (11.36s). Tempo gap here is ~10.6 BPM / 11.5% — pin the incoming
  `play_bpm` to native so Mixxx does not stretch the tribute onto 102.
  `no_flourish` on the handoff. An ordered bunch locks original → tribute
  so greedy rebuilds cannot reverse the torch-pass.
- **Same for Case → 50 Touch Me.** *Touch Me, Tease Me* (1996, Case / Foxy
  / Mary J.) is the original; Forever King *Touch Me* (2009) is 50’s
  abbreviated remake of that hook (Wikipedia; Genius sample credit). Play
  Case first. Local Case file is a Lord Finesse mix excerpt (~87s), not
  the 4:31 album cut — ride through the first “Touch me, tease me”
  (synced LRC 0:54) and blend; do not plan a 3-minute Case body. Crate
  LRCLIB for 50 *Touch Me* is *Just a Touch* — do not invent 50
  `landing_seconds` from it. Cue 50 from the 1 and pin native (~87.6)
  against Case (~88.4).
- **Vocals-only and instrumental-only are stems to layer, not songs to
  sequence.** Identify them from version tags (`Acapella` / `A Cappella` /
  `Instrumental`), not from “Vocal Remix” or a folder named Instrumentals.
  Default: beat-match the dry vocal **over** an interesting instrumental
  bed or a short break in another full song — not necessarily the matching
  instrumental (that stack *is* the original record). Do **not** ride an
  acapella end-to-end as its own slot unless a human note showcases a
  slice. Put the bed immediately before the vocal and mark the vocal
  `entry_style=vocal_over_bed` so Mixxx keeps the bed playing (two decks;
  no extra Rust gesture). A sung hook (Akon on *Still Will*) needs a
  key-safe bed — relative major/minor of the same song is legal when a
  more interesting bed would clash. Prefer **Dirty / Album / explicit**
  vocal stems in a hip-hop set. A radio retitle plus a CDS acapella that
  sits next to `(Clean)` is the clean vocal — *Still Will* is *I'll Still
  Kill* with the title and the curses taken off. Do not layer that. Use
  the Promo VLS / Album acappella, or just play the Dirty mix. Lloyd
  Banks dry vocals holding attention (*On Fire* / *Warrior* in
  50centgunitera) is an ear-certified exception, not the rule.
  Story: `user_stories/story__when_i_add_vocals_only_and_instrumental_only_tracks_i_layer_them_i_do_not_play_the_acapella_in_full.md`
- **Same-beat remixes play the original first.** G-Unit *Soldier* (No Mercy,
  No Fear) is Eminem’s *Soldier* instrumental with G-Unit verses over the
  “I’m a soldier” chorus — same BPM/key, not a different song from
  *G-Unit Soldiers*. Cue Em from the 1 of the opening hook; ride his first
  verse into the chorus; blend the remix in on that shared hook. Do not
  invent G-Unit landing timestamps (the crate’s LRCLIB match is the wrong
  Young Buck cut).
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

## The other half of `play_bpm`: riding a track hot on purpose

Everything above treats a deck sitting above its native tempo as a bug to
be corrected. It usually is. But `play_bpm` is a **tempo hold, not a bug
fix**, and the same directive has a legitimate affirmative use: keeping a
track *above* its own native tempo because the sped-up version genuinely
sounds better and carries the set's energy forward.

Do not "correct" a hot deck back to native just because you found one. If a
track's dj_notes hold it above native and say why, that is a decision, not
drift.

**When this applies:** a track gets pulled up during a blend, and the
sped-up version sounds good on its own terms — the lift keeps the energy
and tempo going instead of the mix sagging at the handoff. Without a hold,
`settle_rate` glides it back down to native right after the landing and
that energy is lost.

- **This is per-track human judgment and must stay that way.** There is no
  metric, waveform feature, or BPM-gap threshold that predicts which songs
  survive being sped up. It's a handful of songs, and which ones is an ear
  call. Never invent a global rule (`allow up to +N%`), a profile setting,
  or a computed heuristic for it — record the decision in that one track's
  dj_notes and nowhere else.
- **The blend tempo is not automatically the right hold.** How hot a track
  rode during an overlap is whatever the outgoing deck happened to be at.
  Ask what the track should sit at, not what it got dragged to. Observed
  case: Groove Theory — Tell Me (native 93.04) was pulled to LL Cool J's
  101.08 and sounded good, but Ernest's call was ~96.5 (+3.7%) for the
  body — "slightly sped up," not the full +8.6% of the blend.
- **A hot hold changes what the NEXT track syncs to.** This is the same
  chaining described above, just entered deliberately. Before holding a
  track hot, check the following track: if it has no `play_bpm` of its own,
  it will beatsync onto the held tempo instead of the native one, and a
  clean match can quietly become a stretch. Either pin the next track to
  its own native BPM, or listen first and decide — but know it's a live
  consequence, not a detail.
- Record the reasoning in the note, not just the number. "Ernest ok'd
  up-tempoing this to match Escapade exactly (both are the same high
  energy)" tells the next agent why the hold exists; a bare
  `play_bpm=115.24` invites someone to "fix" it later.

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
