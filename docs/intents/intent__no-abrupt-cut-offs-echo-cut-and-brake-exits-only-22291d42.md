# Intent: No abrupt cut-offs: echo, cut and brake exits only when Ernest asks

<!-- pdd-intent-id: no-abrupt-cut-offs-echo-cut-and-brake-exits-only-22291d42 -->
<!-- pdd-intent-sha256: 22291d42516d682d220a37db4023cc23ecafba41fefb7f2145f70bc64c577f50 -->

## Record

- Intent ID: `no-abrupt-cut-offs-echo-cut-and-brake-exits-only-22291d42`
- Kind: `add`
- Supersedes: none
- Approval ID: `no-abrupt-cut-offs-echo-cut-and-brake-exits-only-22291d42`
- Source kind: `file`
- Source reference: `external-local-file:intent_no_cutoffs.txt`
- Request SHA-256: `22291d42516d682d220a37db4023cc23ecafba41fefb7f2145f70bc64c577f50`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> Ernest, 2026-10-17, after auditioning an agent's 4-beat echo-out "fix" for Sade - Turn My Back -> Justin Bieber - Sorry in rnb-cooldown-mix-vol-02: "202 is terrible. I hate the sharp cut off of Sade's song. DO NOT DO THAT. Does it warrant a user story or do we have a user story that we do not do abrupt cut offs like that except very rarely and with a lot of care when we want to highlight a drop or do some interesting pitch play work? DO NOT DO THAT AGAIN Icannot emphasize. Please." Then: "go ahead with those user story amends".
> Amend the gentle-faders story (it listed platter/echo/filter exits and deliberate on-beat cuts as allowed exemptions, and Build could pick an echo-out or a hard cut by itself):
> 1. A song never ends with an abrupt cut-off: no echo-out exit, hard or on-beat cut, half-time-or-cut, brake, spinback or filter-drop exit.
> 2. Such an exit is allowed only very rarely, when Ernest deliberately asks for one to highlight a drop or for pitch-play work, recorded in the plan with his reason.
> 3. An abrupt exit is never the fix for a pair that does not blend (tempo gap, syncopation, grid drift). Re-pair or reorder instead so a gentle blend of at least 16 counts works.
> 4. The plan builder never chooses one by itself: not from a model's review, not for a large tempo gap.
> 5. The live runner refuses a plan containing an abrupt exit that is not marked as Ernest's deliberate request, naming each transition, before anything plays.
> Beat juggling and same-song handoffs of identical material keep their existing exemptions.

## Must Stay Unchanged

- DO NOT DO THAT.
- Does it warrant a user story or do we have a user story that we do not do abrupt cut offs like that except very rarely and with a lot of care when we want to highlight a drop or do some interesting pitch play work?
- DO NOT DO THAT AGAIN Icannot emphasize.
- A song never ends with an abrupt cut-off: no echo-out exit, hard or on-beat cut, half-time-or-cut, brake, spinback or filter-drop exit.
- An abrupt exit is never the fix for a pair that does not blend (tempo gap, syncopation, grid drift).

## Examples

- Does it warrant a user story or do we have a user story that we do not do abrupt cut offs like that except very rarely and with a lot of care when we want to highlight a drop or do some interesting pitch play work?
- Such an exit is allowed only very rarely, when Ernest deliberately asks for one to highlight a drop or for pitch-play work, recorded in the plan with his reason.

## Candidate Product Areas

- Live audition of one built transition: lead-in placed from the ride's phase_anchor on the outgoing grid (previous fade, skips and...
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Reusable live Mixxx moves for live mini-experiments and hand-built live mixes: library lookup by artist/title (folder hint for duplicate...
- Sparse override layer at plans/<slug>/transitions.json, stored as a list KEYED BY THE (from_track_id, to_track_id) PAIR rather than by...
- Standalone opt-in monophonic cue instrument wrapper.
