# Repair three R&B backbeats — 2026-10-29

Status: accepted explicit request to implement; live listening pending.

Read-only PDD intake: repair-three-r-b-backbeats-without-changing-appr-d8708bee.
Presented exact tracks, findings and proposed shared source-time start before edits.
Automatic apply/sync is not run: its lexical target list also includes unrelated
static assets and Arrange UI; broad regeneration would violate the frozen scope.
The existing conventional runtime/onset helpers are changed directly with tests;
managed caller prompts are updated narrowly. No model semantic certification.

## Original request

Read ~/Desktop/transition-log-2026-10-28.md (and ~/Desktop/transition-log-2026-10-22.md for history). Fix these transitions in R&B Cooldown Mix Vol 2. Don't touch any other transition; approved ones stay as they are.

1. Maxwell (song ?) → Maxwell "The Urban Theme" (Urban Hang Suite intro): off by 1 count. This is the same transition I flagged on Oct 22, so check whether that fix was ever applied. Keep the pairing. Fix the alignment so the backbeats and snares land together.

2. (previous song ?) → Joe "Sweeter Than Sugar": off by 1 count. Keep the pairing and fix the alignment.

3. New Edition "If It Isn't Love" → Lloyd "You" (remix): the backbeat doesn't match at all. This isn't off by one. Check the BPM and beatgrid on both tracks, especially the remix, then line up the snares on 2 and 4. If it still clashes, propose a different Lloyd version or a re-pair before changing it.

Root cause: off-by-one-count problems keep coming back (Oct 15, Oct 17 Sade → Paradise, Oct 20 SWV remix → original, Oct 22 Maxwell, and now #1 again plus #2). Look for one shared bug in how downbeats or phrase counts are detected, especially for intros or remixes where the first downbeat comes late, and fix it at the source instead of nudging each pair.

Standing rules: tight backbeat/snare matching comes first. Never blend a percussive, groovy track straight into a ballad. Songs with iconic or late-snare intros start from 0:00. Never pair SWV with Bieber "Sorry".

Before editing, tell me: the exact tracks you found for each transition, the cause, and your planned fix. After, show me what changed and how to test each transition.

## Evidence

The October23 Maxwell file-head proposal was a separate candidate, never
installed in the current ef58a426 plan. Cached weak/ordinary parity did not
establish downbeat identity; Joe uses75/154 grid BPM with77 musical BPM incoming.
Both New Edition/Lloyd current grids remain98; short-window transients support
that cadence. Mixxx source SyncControl/BpmControl confirms full beatsync may
seek a playing deck to a neighboring grid beat. Legacy cue verification may
accept a whole second of source-position error. New opt-in source-time starts
leave all other approved recipes on the old path, with regression coverage.

Story: user_stories/story__preserve_intro_and_measured_backbeat_at_start.md


Live-clock correction (2026-10-29): audition109 failed at +32.3 ms against the
unchanged 30 ms limit. Local Mixxx enginebuffer.cpp sets playposition updates
at 15 Hz (about67 ms); bpmcontrol.cpp updates beat_distance on each audio
callback. Do not launch or verify a millisecond start using the display slider.
Require exact first_beat_seconds on both measured models; unwrap the callback
phase with the coarse beat number and that grid origin. Timestamp each phase
read and project both deck samples to one instant before comparing. Reject
invalid/stale clocks or excessive read latency. Preserve the 0:00 source head
and wait until its first grid tick before checking phase; never seek past it.
The 30 ms guard, three pairings/cues, gentle fades and all266 other audition
recipes are unchanged. CueVerificationError prints a concise CLI error and
uses the existing stop-both-decks cleanup. Live listening remains pending.


2026-10-29 listening update (supersedes prior pending statuses): Ernest approved159: "a159 is good keep it";109 remains approved. He rejected235: "still off, i think by1 count." Saved exact human verdicts/private recipe records and journal entries; installed plan SHA14b67bf975c7e5296cc8c1edcbfab98fb52c67ed760142f753241b2d8fbf9fcc remains byte-identical. All other seams frozen.

For235, a bounded multiband/HPSS recheck supports strong periodic transients but does not establish snare identity; do not report a verified1-count correction. Private audition_235_one_count_comparison.py delays only235's launch one beat (~612ms at98BPM), retaining cue19.6337s and32-beat gentle fade. Process-local explicit hypothesis; no production code/model/artifact changes, no after-start seek or installation. Its30ms residual is against the TEST TARGET, not proof of matching snares. CLI dry-run/fake helper/full-transition checks pass; normal audition preflight/cleanup retained. At8ms simulated TCP latency a full trial could safely refuse36.2ms; guard retained. Await human verdict before any promotion. No playback/recording, rebuild, commit or push. Private snapshot mix_plan.10-29-approved-109-and-159-235-rejected.json preserves exact current artifact.

Read-only intake: a-159-is-good-keep-it-a-235-is-still-off-i-think-8c0073e5. Automatic target bunch_store is unrelated; no apply/regeneration.


Human-approved launch timing (2026-10-29): Ernest kept109 and159, then
approved the private235 one-count-later comparison and requested the entire
current mix ready for run_mix.sh. Preserve all268 other audition recipes.
An optional approved_launch_delay object on backbeat_start records beats=1,
author=human, approved=true and a nonempty quote. Reject missing approval,
bools, larger/arbitrary offsets or agent approvals. Add exactly one outgoing
real musical beat to the existing next-start result (including its normal
next-cycle choice), without altering the original cue, detector phases or
confidence. Verify phase against that explicitly heard target with the
existing30ms guard. Label it human-approved launch/error-vs-heard-target,
not a newly measured snare identity. No after-start seek, full/phase sync,
rebuild, reorder or hidden fallback. Absent approval metadata preserves all
existing behavior. Keep exact provenance and pending/approved states.


Deadline-based start scheduling (2026-10-30): full-run109 stopped with+38.8ms
against the30ms limit. A synchronous poll that first sees position>=launch
already starts late. Project each timestamped outgoing source sample to the
current host time before selecting the next approved phase. Refresh the host
launch deadline ahead of time, estimate command delivery from half a bounded
preflight control-write round trip, then wait/send Play without blocking TCP
reads in the final interval. Reject excessive write latency or scheduler
stalls before play; retain post-start phase/tempo checks, original cues,
quantize restoration, source-window bounds and30ms limit. No post-start seek
or new inferred count correction. Keep109/159/235 approvals and all plan
artifacts byte-identical. Test transport writes, engine queuing, callback
phase sampling and multiple launch positions, not only instantaneous writes.
Full CLI CueVerificationError should exit with a concise stopped-safely
message using existing cleanup, without a traceback. Validate --start-at109
against this actual plan; it restarts the outgoing song from its cue and then
continues the remaining original event sequence. No automatic live playback.
