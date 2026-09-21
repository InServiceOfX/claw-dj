# Accepted: one musical plan for offline rendering and live transitions

Ernest approved preserving/generalizing the offline mixer and unifying the plan
representation on 2026-09-21, then confirmed: “the unify the plan representation
makes sense, take a try at it please”.

One named mix_plan.json must preserve source edits, tempo/backbeat placement,
layering, and transition envelopes. Offline rendering consumes this plan without
replacing its live events with finished-master playback. The existing run_mix.sh
launcher must execute transitions; finished-render playback must be explicit.
Reusable implementation, specifications, documentation, synthetic tests and
analysis tools belong in source control. Personal plans/audio remain local.
Keep one current export and clean temporary audio; never modify originals.

Live execution loads the original recordings directly. Rust schedules Mixxx's
native rate, EQ, loops, seeks and faders. It MUST NOT require rendered masters,
processed-track copies, offline filtering, or vocal extraction. Mixxx's audio
engine performs the DSP while music plays. Offline export remains optional;
its mastering and filter response need not be bit-identical to live output.
Refuse stale, unsupported, deck-overcommitted or boundary-violating plans before
playback. Stop every owned deck on failure or interruption.

Latest musical notes remain authoritative: Ja Rule excludes source 0–10s and
provides an incoming blend window from 10 to approximately 50s; 50 Cent excludes
source >=92s; DMX's 132s outro observation is advisory, not a hard end. Preserve
all previously accepted source exclusions.

PDD routing: read-only intent planning completed. Existing mapped plan modules
are not being regenerated. The new execution modules and existing conventional
runner adapter are implemented locally with independent tests. No paid/remote
PDD architecture or synchronization run is claimed. The accepted specification
is maintained alongside the implementation for future scoped adoption.
