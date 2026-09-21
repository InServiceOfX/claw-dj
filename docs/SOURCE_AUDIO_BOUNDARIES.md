# Mandatory source audio boundaries

`mandatory_end_seconds=N` in a track's global DJ notes defines an exclusive
source boundary: only samples with source time less than N may be used. It
applies to every plan, agent, renderer, playback rate, fade, and supporting
layer. A plan overlay cannot extend the latest global boundary. `full_track`
means the full **allowed** region. A trusted ride cannot override it.

The planner caps effective duration and reserves the outgoing fade plus four
beats before the boundary. When a ride must shorten, it removes whole bars to
retain the planned backbeat position. An incompatible verified format fails
explicitly instead of claiming that a relocated exit is still verified.

Before connecting to Mixxx, the runner rechecks the current library notes,
including for older built plans. Direct source loads use lossless WAV copies
physically trimmed before the boundary. FFmpeg/ffprobe must be available;
failure refuses playback, without falling back to the uncut file. Copies
live under the system temporary directory's `claw-dj/bounded-audio/`, outside
the repository. Originals and stored library identities are unchanged.

Rendered masters cannot be fixed by trimming their first N seconds: N refers
to the individual recording, not the mix timeline. Their source recipe must
prove that every segment and support loop for the bounded recording respects
N, and the recipe/master hashes must match the playback artifact. Rerender
any noncompliant mix. Arbitrary external players and independent renderers
do not run these checks; agents must carry the rule into their render source
and verify the resulting artifact.

## Human recording knowledge, 2026-09-20

- Recording: **50 Cent — WHO SHOT YA**, **24 Shots** (2003), track **06**.
- Library directive: **`mandatory_end_seconds=92`**.
- Forbidden interval: **[1:32, end of recording)**, in source time.
- Reason: abrupt beat/instrumental change already audible around 1:33;
  possible poorly spliced tracks (user observation, not independently proven).
- Complete the outgoing fade before 1:32. Overlaying the clean instrumental
  does not permit keeping the forbidden source underneath it.
- The Astra correction uses source end 91.95 seconds, trimmed before rate
  conversion, and shifts subsequent entries by 24 beats at 91.68 BPM.

Library notes live in local, ignored collection data. This versioned record
and AGENTS.md preserve the accepted intent across harnesses and setups;
reapply the directive to the matching recording when importing a collection.
Do not apply the cutoff to other recordings solely because the title matches.
