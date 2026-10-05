# AGENTS.md — claw-dj

## Mission

Build and operate `claw-dj`: an autonomous or semi-autonomous DJ that plays Mixxx like an instrument. Selection matters, but the defining work is phrase-aware transitions, beat-accurate execution, EQ, loops, cueing, effects, and a recognizable hip-hop/R&B DJ style. Do not reduce the project to playlist generation plus automatic crossfades.

## Start every session

1. Run `git status --short --branch` and confirm work is not happening on `master`.
2. Read `PROGRESS.md` for current commands and priorities.
3. Read `docs/HANDOFF.md` for architecture, implementation history, and known gaps.
   Start with the latest resume summary in `PROGRESS.md`; newer dated song
   requirements supersede older timings in historical sections. Recheck live
   active-plan identity and staleness instead of assuming the summary is current.
4. Read the specific docs for the task. In particular:
   - `docs/ARCHITECTURE.md` — brain/hands split.
   - `docs/MIXXX_CONTROL_SURFACE.md` — reachable Mixxx controls.
   - `docs/DJ_TRANSITIONS_PLAYBOOK.md` and `docs/DJ_STYLE_GUIDE.md` — mixing craft.
   - `docs/LIVE_MINI_EXPERIMENTS.md` — try one piece of a mix live in Mixxx with a flagged script before touching the full plan.
   - `docs/ANTHOLOGY_AND_SHORT_FORM_PROGRAM.md` — named anthology slate,
     editorial standard, short-form research, and promotion lifecycle.
   - `docs/SETUP_NEW_MACHINE.md` — music/database portability.
   - `docs/HERMES_AGENT_SETUP.md` — lightweight Hermes reconstruction.
5. In Hermes, load the repository skill from `agent/hermes-skill/` (installed as `clawdj`). Load `agent/pdd-skill/` (installed as `prompt-driven-development`) for PDD work.

Do not ask the user to repeat context that is already in these files.

## Git discipline

- Work on a feature or documentation branch, never directly on `master`.
- Ernest reviews and merges to `master`; do not commit, push, open a PR, or merge unless he asks.
- Check the active branch again before every commit because Ernest may switch or merge branches himself.
- Preserve unrelated working-tree changes. Do not stage `.DS_Store`, generated media, personal library data, or credentials.

## Architecture discipline

The project contains multiple generations of similar code. Do not assume the newest-looking implementation is live.

- `brain/` performs judgment, analysis, curation, and planning.
- `hands/` and the Rust core execute deterministic, timing-sensitive Mixxx actions.
- `core-rust/` and `agent/` contain mature prior work integrated into this repository.
- `docs/HANDOFF.md` decides which implementation is current when alternatives coexist.

Trace a symbol and its usages before changing behavior. Validate DJ changes with dry runs, tests, transition previews, and live Mixxx only when appropriate.

Before composing or revising a mix, read every included track's effective DJ
notes (global library notes plus plan overrides). Honor all relevant cue,
exclusion, source-end, layering, order, and performance instructions. Mandatory
recording exclusions take precedence over a general mix brief or older ride
counts. Keep these notes in the brief supplied to every comparison harness.

For offline multi-plan edits, use `python -m brain.plan_cli`. `note` is
track-scoped; transition notes and effects use `transition get|set|clear` with
an explicit `--author`. `mark` writes `wip|ready|archived`; `status` only reads
artifact staleness. Mutations require `--base-rev` from `show --json` or an
intentional `--force`.

Use **backbeat matching** as the primary musical term. Accept "match the
snare" and "beat parity" as user synonyms; preserve existing `snare_align`
and `snare_parity` machine identifiers.

Human-confirmed verse observation: **K-Dot — Who Shot Ya (Freestyle), Training
Day**, final verse ends at source **2:31 (151s)**. Read its global DJ note
(`observed_final_verse_end_seconds=151`) even when a plan has an older override.
Future agents/mixes may begin blending out there without cutting the final
verse. This is an optional exit opportunity based on a firm fact, not a hard
cutoff; audio after 151s remains allowed. See the verse-respect user story.

For **Jadakiss — Who Shot Ya, The Champ Is Here Pt. 3**, the final verse ends
at source **2:29 (149s)** and a DJ rewind/replay occurs around **2:39 (159s)**.
Read this exact recording's global note even with older plan overrides. Prefer
starting the outgoing blend around **2:29–2:30**, completing the handoff before
the rewind when practical. These are observations and an advisory exit choice,
not a mandatory cutoff or excluded region. The separate hard entry minimum of
**0:32** remains unchanged. Preserve this guidance in future mix briefs.
For **The_Notorious_BIG — Who_Shot_Ya (Club Mix), Promo VLS**, Biggie's first
verse starts at source **0:43 (43 seconds)**. Read
`observed_first_verse_start_seconds=43` in that recording's global DJ note.
A blend may enter on a later part of the intro, before this verse, instead of
at 0:00. This is an observed fact and an available entry choice, not a
mandatory cue or an excluded opening. Audio before 43s remains allowed. The
separate mandatory skip inside the recording stays in force.

If a live blend is "on beat but off the backbeat / off by one count," put
`snare_align` on the incoming track. The runner jumps one beat after
Mixxx beatsync. Do not slide the incoming cue one beat later, and do not
treat outgoing `ride_beats` ±1 as the snare lock. Story:
`user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md`.

## Continuous instrumental support beneath a full mix

For sustained reinforcement of a vocal **full mix**, read
`user_stories/story__when_i_highlight_vocals_in_a_full_mix_i_keep_an_instrumental_underneath.md`
and `docs/FULL_MIX_INSTRUMENTAL_LAYERING.md`. Keep the instrumental under the
whole chosen body; this is distinct from dry-acapella layering and a short
exposed instrumental bridge. Preserve full-mix identity and backbeat matching.
The matching instrumental is appropriate for the 50 Cent / Who Shot Ya repair.
The current Astra render already has this support; the general live feature
still needs dedicated deck/EQ/monitoring work. Do not label it implemented merely
by adding an unrecognized directive or reusing the acapella branch.

## Mandatory recording boundary — every harness and future mix

**50 Cent — WHO SHOT YA, compilation `24 Shots` (2003), track 06:**
exclude **all source audio at or after 1:32 (92.000 seconds)**. Ernest hears
an abrupt instrumental change by 1:33, possibly a bad splice. Finish the
outgoing fade before 1:32; no blend, instrumental overlay, outro, trusted ride,
or `full_track` instruction may expose that tail. This is source time before
tempo changes. Identify this exact recording, not every song with this title.
Store `mandatory_end_seconds=92` in its global library DJ notes and preserve
it when importing the collection on another machine. Existing rendered audio
must be cut again; adding a note cannot change an already exported waveform.
The runner checks current global boundaries and uses bounded audio copies
for direct source playback. Rendered masters require compliant source recipes
and matching hashes. Details: `docs/SOURCE_AUDIO_BOUNDARIES.md`.

## Data and secrets

- Keep generated audio/video, render intermediates, analysis exports, and
  mix-specific production packages **outside the source checkout**, in an
  explicitly chosen local output directory. On Ernest's Mac the current export
  location is `~/Music/claw-dj/exports/`; do not hardcode that machine-specific
  location into shared application code. Reusable code, prompts, schemas, tests,
  and synthetic fixtures belong in Git; personal outputs do not.
- `brain/data/` is intentionally ignored because it contains derived personal-library state.
- No files under `brain/data/` are currently Git-tracked. Plan state remains
  there under the current resolver, but human notes and approved plans are
  durable user data, not disposable build output; preserve the current state.
- Keep **one current export per mix**, with stable filenames and one clearly
  identified listening page. Update the existing named plan in place. Ernest
  explicitly requests no retained output versions: after successful verification,
  delete superseded renders, per-pass packages, temporary audio, and analysis
  caches instead of archiving them. Keep original songs, current deliverables,
  current plan/notes, and small reconstruction scripts and evidence. WAV and MP3
  may represent the same current mix; do not present them as separate versions.
- Music, recordings, generated videos, OAuth credentials, API tokens, browser cookies, Mixxx databases, and Hermes state databases must not be committed.
- Regenerate or transfer library state using `docs/SETUP_NEW_MACHINE.md`.
- Reauthorize model providers and external services separately on each machine.

## Media publishing

Treat promotion as part of the anthology lifecycle, not an afterthought. Follow
`docs/ANTHOLOGY_AND_SHORT_FORM_PROGRAM.md` for campaign intent, clip selection,
current-platform research, experiments, and metrics.

For Mixxx WAV-to-video masters and 9:16 promotional clips, follow:

`agent/hermes-skill/references/media-export.md`

Use the checked-in renderer under `agent/hermes-skill/scripts/` for repeatable social clips. Keep rendered media outside Git unless the user explicitly wants a small reviewed asset committed.

Before reporting completion, probe every output, fully decode it, verify scene timing, inspect audio levels, and visually inspect at least one frame.

## YouTube integration

The dedicated channel is `https://www.youtube.com/@claw-dj`; its currently verified channel ID is `UClafA-9ft1J1iAKo1JMZmwQ`.

YouTube OAuth/API setup remains an active cross-machine priority. Follow:

`agent/hermes-skill/references/youtube-channel-oauth.md`

Never request a Google password, 2FA code, recovery code, browser cookie, raw access token, or refresh token. Default API uploads to private. Require explicit confirmation for uploads, publication/scheduling, public metadata edits, comment writes/moderation, and deletion.

## Prompt-Driven Development

Before PDD adoption or PDD-managed product work, read the workspace router at
`../../PDD.md` and the mandatory Monoclaw playbooks it names. The installed
`pdd` executable and its command help are authoritative; on this workspace it
comes from the editable fork at `../PromptDrivenDevelopment/pdd`.

`claw-dj` is conventional brownfield until matching `.pddrc`,
`architecture.json`, and prompt ownership say otherwise. Adopt one bounded,
stable-interface unit at a time. Characterize current behavior and important
negative boundaries before passing `--characterized` or regenerating code.

Treat ordinary product requests, corrections, removals, examples, and
constraints as intent input for PDD-managed parts. The agent runs `pdd intent
plan` with the exact request and project scope, presents meaning for approval,
then runs the approved apply/story/synchronization workflow. Do not require the
user to choose commands, dev-unit names, prompt paths, flags, or filenames.
Keep accepted behavior in versioned `.prompt` source and executable tests; a
PRD, story, chat transcript, or generated code does not replace prompt source.

The detailed Hermes adapter is `agent/pdd-skill/SKILL.md`.

## Definition of done

A task is complete only when:

- the requested artifact or behavior exists;
- relevant tests/builds or media verification pass;
- no unrelated user work was overwritten;
- `PROGRESS.md` and `docs/HANDOFF.md` are updated when project state or operational knowledge changed;
- the final report names exact files, commands, and any remaining blocker without invented results.

## Live source performances

Ernest explicitly rejects replacing a DJ plan with finished-master playback or
requiring prepared audio copies for live effects. Authored `performance` plans
load original recordings and use Rust-timed native Mixxx rate/EQ/loops/faders.
Offline exports are optional consumers of the same musical decisions and MUST
NOT overwrite live events or originals. Preserve the explicit performance when
working on generic builders. See docs/SHARED_PERFORMANCE.md. Keep backbeat
alignment and every source exclusion through loops, skips, fades and pre-roll.

## Lessons from hand-built live mixes

Before building or editing a live mix, read `docs/LIVE_MIX_LESSONS.md`:
- how to work with Ernest: audition first, one total-mix script, "don't touch"
  means unchanged, simulate before handing over;
- timing: grid vs live tempo, millisecond nudges, count loop passes on the deck;
- pitch: keylock and turntable-slowed samples;
- long blends, and stretching short intros;
- layering: one layer at a time, lined up by harmony per section.

## Keylock off when a sample meets its source

Mixxx keylock is on by default here. When a record that samples another (e.g.
Mo Money Mo Problems -> Diana Ross *I'm Coming Out*) is sped back up to blend
with its source, turn **keylock off and pitch_adjust to 0** on the sampling
deck. Old samples were slowed turntable-style (slower *and* lower), so the
speed-up restores the source's exact pitch. With keylock on plus a guessed
pitch_adjust, the riffs were half a semitone apart and sounded tinny (Ernest,
2026-10-04: with keylock off it "sounds so much better"). Measure the pitch
relation (chroma semitone shift + tuning cents) before tuning anything. Details:
`docs/LIVE_MINI_EXPERIMENTS.md`, "Pitch: undo a turntable slowdown with keylock OFF".

## Gentle channel faders

Unless you are beat juggling (which must be judicious) or making a deliberate
cut, fade a song out gently: ramp its channel fader (the vertical per-deck
volume fader) down steadily over about 16 counts or more, not 4-8, and let the
fader do the fading instead of slamming EQ to zero. Ernest, 2026-10-03: agents
"move that vertical knob down TOO FAST ... channel fader needs to be gentler."
Short 4-beat blends are only for same-song handoffs of identical material. In
code: `hands.live_kit.fade_out(...)`, `GENTLE_FADE_BEATS`, `automate(..., curve="linear")`.

This is **enforced in code**, not just advice (Ernest, 2026-10-03: "You and any
other AI agent, AI harness has to STOP doing that"). Fading **in** counts too.
- `shared/gentle_faders.py` holds the one rule: `GENTLE_BLEND_BEATS = 16`.
- `hands.live_kit.Live.automate` raises `ValueError` when a channel fader would
  sweep faster than full travel per 16 counts (an S-curve's steepest point counts).
  `fast=True` is only for juggling, deliberate cuts and same-song handoffs; write
  the reason next to it.
- `hands.run_mix_plan` refuses a plan with a blend shorter than 16 counts before
  anything plays, and moves the crossfader on a linear ramp.
- `brain.build_mix_plan` never schedules a blend below 16 counts, even for a
  "quick" brief or a per-pair override.
- Story: `user_stories/story__blend_with_gentle_faders_never_fast.md`.
Do not lower the constant or sprinkle `fast=True` to get a script running;
lengthen the move instead.

## Live mini-experiments

For a new or uncertain idea (a transition, a loop or re-entry, a 2/3+ deck
layer), offer a short live experiment before editing the full plan: a script
in `brain/data/plans/<slug>/authoring/` that drives Mixxx through
`hands.run_mix_plan` helpers, with `--dry-run` and a flag for every musical
guess (entry/handoff beat, blend beats, per-deck beat shift, mode). Ernest
runs it in his own terminal and iterates. Live only, never a rendered file.
Restore every Mixxx control it touched. When he likes a result, record it in
DJ notes with the exact flags. Method, checklist and worked examples:
`docs/LIVE_MINI_EXPERIMENTS.md` and `docs/live_experiments/*.py`.
