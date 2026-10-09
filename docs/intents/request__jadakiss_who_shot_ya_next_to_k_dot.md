# Put Jadakiss's Who Shot Ya next to K.Dot's version

Received: 2026-09-05. Scope: editorial order for the next build of
`heavy-rotation-vol-1`, using the existing plan storage/revision workflow.
This is not a runtime or generated product-code change.

## Exact user request

> move this song [74/110] play_body
>   riding Jadakiss — Who Shot Ya for 96 live beats
>   hints: ['Optional: tweak [ChannelN] filterHighEq mid-phrase', 'Optional: beatjump_1_forward to skip to chorus', 'Optional: beatloop_4_toggle for a loop-roll fill']
>   runtime bar guard: first counted grid beat 43; body 96 -> 94 so the transition keeps its planned 1-2-3-4 position
>  to the other versions of who shot ya either before or after K.Dot's version

## Required outcome and boundaries

- Move the existing Jadakiss recording immediately before or after K.Dot's
  Who Shot Ya (Freestyle), keeping all 36 recordings exactly once.
- Preserve all unrelated order constraints, notes, cues and transition data.
- Do not change the loaded/running mix, active `mix_plan.json`, runtime code,
  Mixxx controls, shared library database, or existing rhythm candidate.
- A subsequent Build is needed before a newly ordered artifact can be played.

## Constraint review before any plan-data mutation

The active artifact currently places K.Dot sixth and Jadakiss twenty-fourth.
K.Dot is inside the explicit ordered opening bunch
`6d002843-d3e0-42cd-86ba-2f57b6c52ab5`:

Wall to Wall → On Fire → Biggie Who Shot Ya → 50 Cent WHO SHOT YA →
Ja Rule Who Shot Ya → K.Dot Who Shot Ya → Aaliyah Rock The Boat →
Mario Just a Friend 2002.

An ordinary move on either side of K.Dot would split that bunch. The proposed
minimal change is to include Jadakiss **after K.Dot** in this plan's activated
member list, keeping every existing bunch member's relative order and leaving
the shared library bunch unchanged. This preserves Ja Rule → K.Dot's existing
transition; the old K.Dot → Aaliyah transition override must remain stored as
orphaned history when they stop being neighbors.

The main agent authorized that minimal plan-local constraint adaptation as a
necessary step of the user's explicit move. No shared library bunch was edited.

## Applied to next-build inputs

Status: completed for plan order; a new executable artifact still needs Build.

- K.Dot remains position 6; Jadakiss moves from position 24 to position 7,
  immediately after K.Dot and before Aaliyah. The former Jadakiss location now
  goes directly from Heartbeat (12' Party Version) to Ja Rule Caught Up.
- The plan-local opening bunch contains its eight original members in the
  same relative order, plus Jadakiss. Both other active bunches are unchanged.
- Selection and playlist now contain all 36 recordings exactly once in the
  requested order; all playlist track metadata is preserved.
- All ten transition overrides remain stored. Nine are unchanged, including
  Ja Rule Who Shot Ya → K.Dot. K.Dot → Aaliyah is retained as orphaned history.
- Changed derived plan files: `bunches.json`, `selection.json`, `playlist.json`,
  `transitions.json`, and the append-only `journal.jsonl`.
- The operation used the existing optimistic-revision writer and plan-order
  API, rehearsed first in an isolated temporary plan. Library bunch lookups
  used SQLite read-only/query-only connections; no library schema or data was
  written.

Before workspace revision:
`5703e0fd68903930c4dfbd32d9ff6e79c1b44f55ff273e603f93d2f49df0205a`.
After workspace revision:
`f153b307580bbec79f5d0514b0eeabcaada57f0fec76262f22e0340a4aa5750f`.

The active `mix_plan.json` is unchanged, SHA-256
`1826e5e2ddb51079bd23e4a48d5a1a4605183ae98fb0c4554efbb9550678263d`.
Its source inputs are now deliberately stale (`selection`, `playlist`,
`bunches`, `transitions`). Neither loaded playback nor that existing executable
plan has moved Jadakiss. The earlier `candidates/backbeat-grid-2026-09-05.json`
is also unchanged and retains the old order; a future candidate must incorporate
these new order inputs. No automatic Build or live playback was started.
