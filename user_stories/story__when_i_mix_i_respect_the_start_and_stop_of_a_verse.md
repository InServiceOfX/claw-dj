<!-- pdd-story-status: drafted-2026-08-28 -->
<!-- pdd-story-areas: verse, build_mix_plan, mix_directives, lyric_timeline -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: A mix respects the start and stop of an artist's verse

## Story

As a DJ, when I blend into or out of a song I want the mix to **respect
the start and stop of a verse** — rapped or sung. The planner must not
drop the incoming track after the verse has already begun, and it must
not cut away while that verse is still going.

The default energy picker (`phrase_body`) hunts a loud phrase past ~30
seconds. In hip-hop that is usually **mid first verse**. Lyric-line snap
then makes it worse: it lands on a *word* in the middle of that verse
(On Fire 41.35s “Running your bitch…”, Gunz 43.27s, Stunt 101 42.64s).
That is not a mix-in.

When a proposed cue sits inside a verse, the legal entries are:

1. **The beginning** (`cue_seconds=0` / first beat) — an iconic intro or
   opening hook is a good blend target. Starting from 0:00 is allowed
   and often what we want.
2. **Verse landing** — pre-roll so the fader *completes* on bar 1 of the
   verse (`entry_style=verse_landing`). The artist’s first line is the
   landing, not something already in progress.

The automatic default, when lyrics prove the cue is mid-verse and there
is intro/hook before that verse, is **start from the top**. A human note
can still choose verse-landing or an explicit `cue_seconds` with
`trust_cue_seconds`.

On the way out: if the planned fade **or the outgoing blend window**
would sit inside a verse, extend the ride so the whole crossfade
starts at that verse’s end (the hook / next chorus) unless
`trust_ride_beats` locked the length.

**mix-to-listen vs showcase.** mix-to-listen must not eat a verse to
make a 32-beat blend fit. A DJ-showcase profile may still cut mid-verse
when the point of the move is the transition itself.

A **function** (`brain.verse` / `clawdj verse cue`) is the right
enforcement — verse boundaries are timestamps + beat math. A subagent
would re-guess lyrics we already have. `audit_mix_plan` reports leftover
violations after a build. Lyrics JSON fills sqlite gaps so the guard
actually runs.

## Acceptance criteria (observable)

1. **Classify.** Given lyric segments (verse / chorus) and a proposed
   cue, `clawdj verse cue` / `brain.verse.respect_verse_entry` reports
   whether the cue is intro, verse start, mid-verse, chorus, or unknown.
2. **Do not enter mid-verse.** An automatic `phrase_body` (or lyric-snap)
   cue inside a verse, more than ~2 seconds after that verse started,
   is illegal. The planner rewrites it to 0:00 when the track has
   intro/hook before that verse, otherwise to a pre-roll onto the
   verse start. Source is tagged `+verse_guard`.
3. **Do not exit mid-verse.** An automatic ride whose fade-in-time sits
   inside a verse is extended to that verse’s end. `trust_ride_beats`
   is the opt-out.
4. **Human locks win.** `trust_cue_seconds` / explicit `cue_seconds` and
   `entry_style=verse_landing` are not rewritten.
5. **No lyrics → no rewrite.** Unknown is legal; do not invent timestamps.
5b. **No vocals → no rewrite.** Instrumental-only / no-vocal tracks have no
    verse. See `story__when_a_track_has_no_vocals_verse_boundaries_do_not_apply.md`.
6. **Example (50centgunitera).** Lloyd Banks *On Fire (Feat. 50 Cent)*:
   old cue 41.35 was mid verse 1. Iconic NYC / “We on fire” intro is
   0:00–0:27. Cue 0. 32-beat blend covers the intro; verse 1 at 0:33
   starts after the fader. Ride through verse 1; fade on the hook.
7. **Example (Best Friend).** Opening “If I was your best friend”
   (0:27) is the **chorus**, not a verse. Land on 50’s verse
   “First we get the talkin” (0:49), or later. A 96-beat ride from the
   chorus landing still cuts mid-verse 1 on the way into Outta Control
   Instrumental — finish verse 2 and fade on the last hook.

## Must not

- Do not keep `phrase_body` at ~40s just because the energy jumped there.
- Do not snap forward to a lyric *line* that is still mid-verse and call
  that fixed.
- Do not treat an opening **chorus** as a verse landing. Best Friend
  starts with “If I was your best friend” (chorus); 50’s verse is
  “First we get the talkin” (~0:49). Land on the verse, or later; the
  chorus is a legal blend-in, not “verse 1.”
- Do not treat a spoken **skit** as a verse to protect, and do not cue
  0:00 through it. G.O.D. Pt. III window skit is not Prodigy’s verse.
  See `story__when_a_track_opens_with_a_skit_i_skip_it.md`.
- Do not require the user to remember `verse_landing` on every hip-hop
  record — the default must stop landing mid-verse on its own.
- Do not start Mixxx to prove a cue.

## Source

Ernest, 2026-08-28, after On Fire mixed in at 41s (Banks already rapping)
and the same pattern on Gunz Come Out and Stunt 101:

> I notice that you, upon an initial mix, tend to blend while someone's
> verse has already started, when we really want to respect the start
> and stop of an artist's verse, whether singing or rapping. If you
> agree it should be a user story, let's make it so and then create the
> subsequent, derived code/Rust function or Python function.
>
> same with On Fire. start much earlier, even the beginning, from 0:00
> is iconic so it's ok to start from the beginning to blend.
