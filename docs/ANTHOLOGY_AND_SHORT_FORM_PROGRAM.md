# Anthology and short-form program

## Purpose

`claw-dj` is building more than isolated sets. A long-term aim is a definitive,
living anthology in mix form for important eras, scenes, artists, and lineages
in hip-hop and R&B. Each anthology should use the named multi-plan workspace as
its durable working surface and should be performed as DJ work: researched
selection, purposeful sequencing, phrase-aware transitions, cue points, EQ,
loops, effects, samples, lyrical relationships, energy, and narrative.

A playlist that happens to be chronological is not an anthology, and an
automatic crossfade is not the performance.

## Initial anthology slate

This is a living slate, not an exhaustive taxonomy or a promised release order.
Names can change as the musical thesis becomes sharper.

1. **Foundational West Coast / early Death Row era** — the period around Dr.
   Dre's *The Chronic*, Snoop Doggy Dogg's *Doggystyle*, Tha Dogg Pound, and
   the artists, producers, records, and regional sounds that make that era
   intelligible.
2. **The *2001* expanded lineage anthology** — Dr. Dre's *2001* in conversation
   with the records it sampled, interpolated, or drew from and later records
   that sampled or reinterpreted it. Sample lineage should be audible in the
   sequence and transitions rather than reduced to liner notes.
3. **Conscious rap** — a broad, deliberately researched arc including Arrested
   Development, Public Enemy, Ras Kass, and related artists, while preserving
   the important differences among political, social, Afrocentric, street,
   and philosophical rap.
4. **Wu-Tang and its East Coast orbit** — Wu-Tang Clan, solo and affiliated
   work, and related East Coast rap from the era.
5. **The Notorious B.I.G. and Shyne tribute** — a coherent tribute rather than
   a simple artist shuffle, including production, lyrical, and era connections.
6. **East Coast jazz-informed hip-hop** — Pete Rock & CL Smooth, Guru, DJ
   Premier and Gang Starr, A Tribe Called Quest, De La Soul, Grand Puba, Keith
   Murray, and adjacent records connected by production language, musicianship,
   rhythm, and scene.
7. **The Shiny Suit era** — Puff Daddy & the Family, The LOX, Mase, Harlem
   World, LL Cool J's work in that period, Fabolous, G. Dep, Loon, and adjacent
   Bad Boy, New York, and crossover records.
8. **Drake season** — an anthology whose exact time boundaries and thesis are
   developed through research rather than assuming that every Drake-era record
   belongs in one undifferentiated set.

## How anthologies live in claw-dj

- Create each anthology as a colloquially named plan in the existing multi-plan
  system. The frozen slug is storage identity; the human-facing name carries
  the project identity.
- Keep unfinished anthologies as `wip`, promote them to `ready` only after
  musical and factual review, and retain superseded explorations as `archived`
  when they remain useful.
- Use plan-scoped track notes, transition notes, effects, exact-order bunches,
  and constraints to preserve decisions. Do not leave essential musical intent
  only in an agent chat.
- Research chronology, credits, regional context, sample/interpolation lineage,
  lyrical references, remixes, and versions. Distinguish verified facts from
  hypotheses and aesthetic associations.
- Plan a dramatic and musical argument: opening statement, chapters, bridges,
  peaks, breathers, callbacks, and ending. Chronology is one possible device,
  not the default substitute for judgment.
- Make source-to-sample and sample-to-descendant relationships audible where
  useful through adjacency, loops, doubles, instrumental/acapella layering,
  or transition design. Never invent a sample relationship because two records
  merely sound related.
- Validate the resulting mix through dry runs, transition previews, cue-sheet
  inspection, and human listening. “Definitive” is an editorial ambition earned
  through iteration, not a label the software can certify.

Personal music-library contents, derived analysis, recordings, and rendered
media remain outside Git. The repository stores the program, procedures, and
reusable tooling; named plan data remains in the existing ignored local data
area unless a separate privacy-safe export format is intentionally designed.

## Promotion is part of the product lifecycle

An anthology is not complete merely because a full mix exists. `claw-dj` agents
also help Ernest package, test, and promote the work. Short-form video is a
primary discovery surface for this program, especially TikTok, Instagram Reels,
and YouTube Shorts. X posts, written posts, long-form YouTube, and full-song or
full-mix releases can support the campaign, but agents must not assume those are
the primary discovery mechanism.

Agents may help direct OpenClaw and media tools such as OpenCut, Hyperframes, or
other reviewed tools, but deterministic FFmpeg-based rendering remains the
batch and verification backbone. An optional editor must not become a fragile
critical dependency.

### Clip candidates

Mine each mix for moments that can work without requiring the viewer to know the
whole set:

- a recognizable source record revealing the sampled record, or the reverse;
- an unusually clean bass handoff, blend, cut, loop, scratch, echo, or lyric
  landing;
- a before/after transition with enough setup for the payoff to register;
- a short era, production, or sample-lineage explanation supported by the audio;
- a contrast, surprise, callback, or chapter turn in the anthology;
- a strong human reaction or listening insight, when Ernest chooses to include
  it.

Do not mechanically cut every fixed interval and call that a campaign. Clip
selection is editorial judgment, just as track selection is not DJing by itself.

### Research and experimentation loop

For campaign planning, agents should conduct fresh, dated research into current
short-form formats, platform conventions, editing patterns, discovery behavior,
and comparable music/DJ accounts. Online advice and platform behavior change;
do not preserve a temporary trend as timeless fact.

1. Record the research date, sources, platform, account/category, observed
   format, clip duration, opening device, pacing, caption/text treatment,
   audiovisual payoff, and visible performance metrics.
2. Treat view count as the easiest reach metric, not a complete quality metric.
   When available, also compare retention/completion, rewatches, shares, saves,
   comments, follows, and click-through to the anthology.
3. Form a testable hypothesis for each clip variant. Examples include changing
   the opening second, moving the musical payoff earlier, adding or removing a
   spoken setup, or changing on-screen context while holding the audio window
   constant.
4. Render small, attributable variants rather than changing every variable at
   once. Preserve the source mix time range, transition point, copy, aspect
   ratio, render settings, and posting date beside the batch.
5. Compare results within the same platform and audience context. Do not claim a
   causal “viral formula” from one high-view post or compare unlike accounts as
   if reach were controlled.
6. Feed durable findings back into this program, the media-export workflow, or
   a bounded implementation prompt/test when automation behavior is added.

The aim is not trend imitation for its own sake. The hook earns attention; the
mixing, musical history, and point of view must reward it.

## Repeatable production pipeline

1. Finish or checkpoint a named anthology plan and preserve its current plan
   revision.
2. Record the mix and retain its cue sheet or other timing evidence.
3. Identify candidate windows from real musical events, then listen to the full
   lead-in and payoff before choosing clip boundaries.
4. Produce a clip brief containing source time range, intended hook, transition
   or narrative payoff, platform/aspect ratio, required artwork/copy, and any
   factual claims that need sourcing.
5. Render deterministic 9:16 masters using
   `agent/hermes-skill/references/media-export.md` and the checked-in renderer;
   use a reviewed interactive editor only for intentional refinements.
6. Verify codec, dimensions, duration, full decode, audio level/integrity, scene
   timing, captions/text safe areas, and visual composition.
7. Keep generated media outside Git. Preserve a privacy-safe batch manifest with
   source windows, variants, and posting order beside the local renders.
8. Obtain Ernest's approval before upload, scheduling, publication, public
   metadata edits, comments, or moderation. YouTube API uploads default to
   private.
9. After enough observation time, record platform metrics and the limitations of
   the comparison. Use the evidence to choose the next experiments.

Commercial recordings may trigger platform rights systems, muting, blocking,
demonetization, or territorial restrictions. Never promise clearance or evade a
platform's rights controls. Report restrictions honestly and let Ernest decide
whether to revise, dispute through legitimate channels, or not publish.

## Which durable artifact to use

This document is the right home for the portfolio-level creative and promotion
strategy because it spans many future mixes, tools, and product parts.

- Use a **named mix plan** for each anthology's track order and musical work in
  progress.
- Use this **program Markdown** for the enduring slate, editorial standard,
  campaign workflow, and cross-agent responsibilities.
- Use a **PDD `.prompt`** when a bounded software component must implement or
  change observable behavior, such as automatic cue-sheet clip extraction,
  campaign manifests, or metrics ingestion. Update the relevant prompt and
  tests rather than leaving such behavior only here.
- Use a **user story** selectively when an important user-visible outcome or
  cross-component acceptance rule needs an independent human-readable oracle.
  A story does not replace the component prompt.
- `docs/PRODUCT_INTENT.md` is maintained by the PDD intent workflow. Do not hand
  edit it merely to duplicate this strategy; route a later bounded product
  behavior through PDD when implementation is requested.

In short: the anthology program belongs in repository Markdown now; each
anthology belongs in a named plan; automation earns a prompt and tests when its
interface and behavior become concrete.
