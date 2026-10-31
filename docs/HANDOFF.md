# Handoff / continuation notes

## 2026-10-30 — Three TikTok DJ references archived (research only)

See `docs/research/tiktok/README.md`: @lilianbilottaa (one-beat acapella loop/reverb/rhythmic crossfader), @djaystayhigh (scratch practice progression), @tayxsounds (drop swap/drop alignment/low-EQ handoff). Downloaded public media outside Git, inspected semantic keyframes, recorded URLs/hashes/timestamps and caption availability. Only tayxsounds supplied captions; no independent audio transcription or listening verdict. No product code, saved mix, library note, playback or Mixxx-control changes. References do not override gentle faders, no-abrupt-exit rules, source boundaries or human-approved mixes. Next is audio verification and selection of one opt-in experiment, not automatic adoption. Branch `docs/tiktok-learning-intake`; committed locally to preserve this pass during integration with the latest master. No push.


## 2026-10-26 — Worktree audited and committed; artist-footage R&B videos ready

Ernest explicitly requested review/commits of every accumulated modified and
untracked source file, especially the no-abrupt-cutoff and original-source
pitch-play stories, plus finished promotional MP4s using related artist footage.

Reviewed all54 original dirty/untracked files; kept the relevant implementations,
tests, prompts, accepted intents, dated listening records and reusable demo kit.
No new ignore rule, discarded user work, generated media or secret was staged.
Three existing test files were updated for broader isolated coverage and stale
fixtures. File-by-file disposition and limitations:
`docs/reviews/WORKTREE_AUDIT_2026-10-26.md`.
Source commits on `feat/review-backbeat-audition`:
`99cd95d` gentle exits/evidence-gated counts;
`8965dd1` isolated opt-in pitch-play experiment;
`1a344ce` profile display;
`fc3a9f9` provisional sourced popup candidates;
`e1ed711` reusable original-music demo toolkit;
`5fc2642` regression coverage/fixtures.
This documentation commit completes the audit. No push, tag or merge requested.
The dated cutoff-story example now reflects the approved2026-10-22
Pacifico→Sorry→Ghetto placement, Sorry cue0, never next to SWV.

Verification: full isolated Python suite681 tests OK, one optional export test
skipped because this FFmpeg lacks libsoxr; expanded DJ workflow419 pass;
Rust46 pass, fmt and Clippy(-D warnings) pass; six strict deterministic managed
prompt checks have0 errors/0 warnings; diff/credential-pattern checks pass.
`.env` stays ignored/untracked; `.env.example` stays tracked. Pitch play remains
an approved **first-scope experiment**, NOT live-auditioned/audio-measured and
NOT a generic Build gesture. Provisional popup facts remain verified:false.
Demo copy no longer promises instant plans or automatic future-plan learning.

**Finished artist-footage gallery, replacing the prior title-card pictures:**
`Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/promotion-2026-10-26/production/index.html`.
Four short MP4s55.70/53.41/58.17/30.74s, three longer TikTok alternatives
70.50/68.21/72.97s; total363.2MB. Same stable finished filenames.
Real Mixxx music from the seven saved captures is unchanged by the picture edit
(decoded PCM MD5 verified for all7). Complete32-count blends, labeled montage
jumps, concise hooks, viewer questions and twitch.tv/clawdj/LA business-hours
CTA. Related music-video footage is publicly sourced from Apple promotional
previews after public YouTube CDN downloads returned403. No cookies/DRM bypass.
Janet Again/Sisqo Thong Song/Ginuwine Pony/Ashanti Rock Wit U/Majid Body Talk
are explicitly **related artist footage** where the mix uses another song;
no lip-sync, endorsement or rights-clearance claim. Sources/hashes/shot timings
in `footage-sources.json`; readable `CREDITS.md` and `UPLOAD_NOTES.md` beside
outputs. Followed Monoclaw short-form-viral-content/Noe hook-retention guidance;
no reach guarantee or fabricated listening verdict.

All7 outputs full-decoded, probed1080×1920 H.264High30fps/AAC48kHz stereo,
checked picture boundaries, absence of unintended ≥200ms internal silence,
retained measured audio levels, inspected opening/middle/end frames.
Verification/gallery/current storyboards updated; temporary render folders and
partial downloads absent. Private production recipes/assets stay outside Git.
No upload/publication, new live playback or OBS write in this picture-edit pass.
R&B saved plan SHA remains
`ef58a4264382389bd00fd291ca8a91cb735985758b884d5098adbeb2cc20a061`.

## 2026-10-26 — R&B clips COMPLETE: fresh Mixxx captures and seven musical videos

Ernest clarified explicitly: **make the recordings from
RnB-cooldown-mix-vol-02; you have access to Mixxx**. This supersedes the prior
existing-recording blocker below. Do not ask him for an old VOD again.

Used idle Mixxx control API9995 and its native WAV recorder. Checked all decks
stopped, recorder idle, and OBS stream/record outputs inactive before each
capture. Read all11 effective notes for included sources. Captured saved
transitions222/223,174/175,65/66,106 via the unchanged real audition runner
(4bar lead/tail, same cues/sync/EQ/backbeat/faders). Seven original source WAVs
in Mixxx's configured container recording directory; exact paths/hashes in
capture-manifest. The recorder flushes one final~43ms block after status falls:
final evidence uses closed-file durations/hashes. Controls restored; recorder
and decks stopped. No OBS writes, generic Build, plan edits or uploads.

**Finished listening/download gallery:**
`Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/promotion-2026-10-26/production/index.html`.
Four Shorts: Sorry-neighbors55.70s; Robin/Janet/Jesse53.41s;
BodyTalk/Sisqo/Ginuwine58.15s; Ashanti/Say I30.74s.
Three longer TikTok edits:70.50/68.21/72.95s. All include real recorded music,
motion/title cards, confirmed twitch.tv/clawdj + LA business-hours CTA, and
YouTube destination. Two-handoff montages explicitly say “Later in the set”.
They retain each full32-count blend. Say I remains requested0:00.

Final7 MP4s total~35.5MB:1080×1920 H.264 High30fps/yuv420p,
stereoAAC48kHz320kbps target. Every output full-decoded; audio loudness/true-peak,
absence of unintended internal ≥200ms silence, intended picture boundaries,
and exported frames checked. All7 source lead-ins independently matched the
original songs by waveform correlation0.9597–0.9965; corrected control-clock
timestamps to the recorded audio. Source recordings retained unmodified.
No new human listening verdict is claimed; these are fresh executions of the
saved approved recipes. `verification.json`, `edit-manifest.json`,
`capture-manifest.json` and final storyboards provide evidence. Current
lossless recording reel `recorded-handoffs.wav` is4:58 of seven independent
takes, NOT a full270-track continuous mix. Removed superseded silent previews.

R&B source artifact remains byte-identical:
`ef58a4264382389bd00fd291ca8a91cb735985758b884d5098adbeb2cc20a061`.
No commit/push/publication. Private production scripts retained beside outputs;
no product implementation or prompt/manifest/Pi changes.

## 2026-10-26 — R&B promotion production follow-up: picture previews ready

Ernest authorized making the proposed promotional clips. Four 12s
1080×1920 H.264/30fps **picture-only** motion previews, source cards,
captions, edit manifest, assembly script, storyboard and local preview page:
`Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/promotion-2026-10-26/production/`.
Each preview explicitly says recording needed and has no audio stream.
Full decode/probe checks pass; extracted frames inspected; picture edits at4s
and8s confirmed. These are NOT finished musical clips; no listening/levels
claim applies to silent previews. Actual A/V assembly path unexercised.

Confirmed Twitch URL **https://www.twitch.tv/clawdj** from Ernest's direct
original request in docs/intents/intent__pop-up-music-facts-and-ernest-s-commentary-over--71fbe377.md.
Public past-broadcast listing via yt-dlp returned zero entries. Local Mixxx
recordings stop September2; Movies/candidate/export/likely download searches
found no verified October vol-02 recording. OBS read-only status unavailable;
no writes attempted. Async question asks Ernest for actual recording path or
VOD URL. This missing source blocks musical clips, not a new approval gate.
Do not silently reconstruct approved live audio from originals or substitute
an old set. Assembly is prepared to retain full32-count transitions and label
the middle montage cuts; targets ~55.6/53.3/57.9/30.6s.

R&B plan SHA remains
`ef58a4264382389bd00fd291ca8a91cb735985758b884d5098adbeb2cc20a061`.
No playback, recording, live plan edits, upload, publication, commit or push.
Keep source missing status explicit; once media supplied, locate and verify
the actual handoffs, render/inspect/listen, then report finished files.

## 2026-10-26 — Hip-hop Anthology vol-01 reviewed; R&B promotion briefs ready

Ernest requested musical refinement of his already-built 98-track
Hip-hop-Anthology-Vol-01, advice on external verse/chorus timestamps, and
R&B vol-02 short-form ideas using Monoclaw/Noe Murillo guidance.

Installed a revision-checked **WIP listening candidate** in the same named
hip-hop-anthology-vol-01 artifact; SHA
`7ef0e8ac30ef81a139bd2410ef8b788ea97fc2e43f723aa08c4685e017aec17c`.
All 98 recordings retained, 97 transitions / 296 events. All 98 effective
notes read through a stable read-only library snapshot: currently empty.
Moved faster records into the closing chapter to remove the 115.7→86.8 BPM
Juice/Right Back At You reset; 16 new adjacencies remain explicitly unverified.
Nas Album Intro now requests 0:00 with strict20ms cue; spoken opener handoff
uses native tempos without forced sync. Kept other cues, removed unmeasured
pitch/filter bridge recipes, retained gentle fades including double-time
count budgets. Eight cached-lyric-guided exit edits are provisional, NOT
human/audio-verified section boundaries. Reading LRC found Black Girl Lost /
Fa Ha outros mislabeled verse and a Throw Your Guns chorus inside a heuristic
verse. No library/cache metadata changed. No new guessed count shifts.

Private report, candidate, full dry-run log, manifest, installer and verified
pre-edit state backup:
`Data/claw-dj-candidates/hip-hop-anthology-vol-01/`.
Report `REVIEW_2026-10-26.md` lists all tracks, edits and priority auditions:
1 opener, 38 Throw Your Guns, 40 Imagine That, 61 Black Girl Lost,
84 Fa Ha, 89 Feel My Pain, 96 Terrordome, 97 Follow The Leader.
Full296-event dry-run, deck/load/preload identity checks, source fade budgets
and98 runner/double-time/alignment regression tests pass. No Mixxx playback,
recording, heavy analysis, provider call, commit or push. Plan inputs still
match source_revs; no freshness stamp on unrelated plans. Generic Build may
replace these authored artifact decisions; refine/audition the same artifact.

GUI selection remains **rnb-cooldown-mix-vol-02**, byte-for-byte unchanged;
current R&B SHA `ef58a4264382389bd00fd291ca8a91cb735985758b884d5098adbeb2cc20a061`.
Its hand_edit_2026_10_25 field is present; earlier Q-running notes below are
historical, not today's verified active identity. To run the reviewed Hip-hop
mix explicitly: `./scripts/run_mix.sh --plan brain/data/plans/hip-hop-anthology-vol-01/mix_plan.json`.
It still needs listening; simulation does not certify pleasant sound.

Private R&B campaign:
`Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/promotion-2026-10-26/CLIP_BRIEFS.md`.
Four Noe-framework briefs: Pacifico→Sorry→Ghetto, Robin→Janet→Jesse,
Body Talk→Sisqo→Ginuwine, Ashanti→Say I from0. Preserve heard recipes;
Janet/Sorry approvals concern energy/vibe, not perfect backbeat claims.
45–59s two-handoff montages require clearly labeled middle cuts; continuous
two-handoff cuts are ~3–4min, not90s. Platform sources checked2026-10-26:
YT Shorts max3min, claimed >1min Shorts blocked per current official help;
TikTok route/account limits differ. YouTube Related video + channel profile
Twitch link is the intended funnel, not nonclickable Shorts comment URLs.
Actual October recording/VOD and confirmed Twitch URL still needed for
timecodes/rendering; async question sent. No media rendered or published.

External lyrics/section timestamps should be priors mapped to the exact
recording with local alignment/version evidence, confidence and human
overrides. Current LRC last-line times are not true vocal ends. No enrichment
product feature was added. Preserve all unrelated Pi/Claude edits.

## 2026-10-25 — actual Hey Lover/Shanice repair S ready; active Q still running

Ernest repeated that live transition2 remains off1 count and explicitly asked
**please fix**. Earlier10-24 diagnosis wrapper never changed the active plan;
its +/-2grid trials were too coarse for the measured local phase. User now
wants the supported saved-plan correction, not another A/B-only handoff.

Read actual short source blend windows at nice19/single-thread, no playback,
render, cache/library writes or model calls. `hey-shanice.10-25-source-windows.json`:
Hey Lover at grid292/308 has snare parity1/confidence.944/.788. Shanice cue
window32 and follow-on64 both show real beats on ODD grid ticks (phase1),
snare parity1 in real beats, confidence.720/.915 versus other.155/.309. Cue32
starts on the offbeat half of the double-time grid. **Post-sync +1GRID tick to33**
puts Shanice on a real non-snare; next snare35 is1real beat after start, matching
Hey Lover309 after fadeanchor308. +2grid (one audible count) leaves the offbeat
phase wrong. This is source-based local backbeat correction, not new perfect
count1 detection or human listening approval. Correct prior coarse advice.

Prepared full supported S outside repo:
`Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/mix_plan.10-25-S-hey-lover-shanice.json`,
SHA `0e4aef9bdfade32f69f42afdc85f09afc6e9010169de5a536a982cb1346b4ccc`.
- Actual transition2 adds existing `snare_align` after sync, not a private
  adapter/unsupported directive. 32-count gentle blend/EQ/native tempo unchanged.
- Shanice cue stays10.265s/grid32, now strict20ms to reject silent wrong seeks.
- Shanice body534→533 compensates the +1grid advance; outgoing anchor599 and
  Shanice→SWV transition unchanged. Bar-guard compensation tested over20 first
  counted indices. Hey Lover fade308/source210.247816s remains unchanged.
- Only these execution changes plus Hey Lover assessment metadata. All268
  other transition events and31 active pair audition recipes preserved; all270
  effective notes read and hashed. All8 heard Janet/Sorry/Say I/Sisqo control
  sequences still match; full812-event fake runner and dry-run pass. Repaired
  seam emits exactly one beatjump_1_forward immediately after beatsync, strict
  cue forwarded; both decks stop in simulation. Fifteen safety regressions pass.
- No product Python/prompt/manifest or Pi edits needed; existing supported
  behavior suffices. No generic Build or fresh LLM review.

**NOT INSTALLED YET:** actual full Q still running when checked (do not rely on
old PID17456/17457; recheck). Live SHA remains
`16c4700f6f9ccd920fe17a82792ebb5d2d5b3420ef6c82571d323fdd04d4626e`.
All active state/notes/locks/journal bytes untouched. Source revisions already
stale from prior inputs; no blanket freshness restamp. Unrelated Maxwell R still
private/uninstalled. An async status question asks Ernest to report when he
stops the mix; never infer elapsed time as approval or kill his playback.

Private `tools-2026-10-25/install_S.py` is ready: verifies base/input/effective-note
hashes and simulation evidence, refuses active runners, then verified external
backup of all state files, two pending AGENT note overlays/pair intent (not fake
human approval), atomic S publication and journal. --check-only verified ready/
busy; fake busy refusal proves no plan/state/journal writes. No new audition
required before installation under repeated explicit request. Once run stops,
agent should execute installer and run normal run_mix.sh --dry-run, update this
status to installed with new SHA/backup. Can also be human-run from repo root:
`.venv/bin/python "$HOME/.openclaw/workspace/Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/tools-2026-10-25/install_S.py"`
Then normal `./scripts/run_mix.sh`. No old R/N/P/Q installers.

## 2026-10-24 — Hey Lover → Shanice off1 count; isolated diagnosis ready

Ernest hears live Q transition2 (#10/812), Boyz II Men Hey Lover → Shanice
I Love Your Smile, **off by1 count**. Treat this as a human negative verdict,
not approval of any correction. Later Shanice body534→531 bar-guard message
occurs after the handoff; it does not establish the cause of the earlier error.
Direction (early/late) remains unknown. Keep this musical pairing for now;
no re-order/cut/filter exit proposed.

Live active Q SHA `16c4700f6f9ccd920fe17a82792ebb5d2d5b3420ef6c82571d323fdd04d4626e`
remains unchanged. Current input revisions differ from its historical source
revisions; no freshness stamp or input/journal write was made. Pending Maxwell
R remains private/uninstalled. Read both current effective song notes read-only.
Shanice has a double-time187.881 BPM grid, real~94:1 audible count=2gridbeats
(~0.639source seconds), not the fixed one-grid snare_align jump (~halfcount).
Hey Lover fade anchor remains308/source210.2478s; Shanice cue10.265s/grid32.
Shanice → SWV exit599, SWV approved400-start/44-count/12-hold, other approved
pairings and all active plan/notes/locks/journal bytes are untouched.

Prepared private unheard `audition.10-24-hey-lover-shanice.json` and
`audition_hey_lover_shanice.py` in Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/.
Use **the private wrapper**, not JSON alone: the wrapper inserts an explicit
post-sync2-grid jump on incoming deck2 for flags+1/-1. JSON contains only the
original smooth32-count gentle blend. No production move/runner feature was
added. Existing run_audition handles port validation, busy runner/deck refusal,
4bar lead/tail, real event path and Ctrl-C/stop/neutralize cleanup. Private setup
adds strict20ms cues on both decks (outgoing setup normally drops source-load
cue options; wrapper forces them for this experiment only). Direct2-grid
forward/backward controls avoid changing persistent beatjump_size, no millisecond
nudge or incoming cue offset. No original track/cue/exit is modified.

First test --shift-counts0: precise requested cues with NO phase jump. If it
aligns, do not add a shift. If stilloff, compare --shift-counts1 and-1. Neither
direction is claimed correct. Lead-in setup and all musical events exactly
match full Q transition2, except experiment-only strictcue verification and
explicit optional count jump. All three dry-runs and fake-control executions
pass with real sockets forbidden; verify one2-grid jump immediately after
incoming beatsync only for+/-1, strict options forwarded, both decks stopped.
Control/load/discovery/clock mocks do not prove audible alignment. Mini and
wrapper hashes/checks are in adjacent .checks.json; reconstruction under
`tools-2026-10-24/`. No analysis/render, model calls, playback, live install,
source-code/Pi edits or commits. Await Ernest's ear before saving a correction.

From repo root, after stopping the full mix in Ernest's terminal:
`D="$HOME/.openclaw/workspace/Data/claw-dj-candidates/rnb-cooldown-mix-vol-02"`
`h() { .venv/bin/python "$D/audition_hey_lover_shanice.py" --shift-counts "$1"; }`
`h 0`, then only if stilloff `h 1` and `h -1`. No LLM review requested.

## 2026-10-23 — Python count/cue safeguards; do not interrupt current Q

Latest PROGRESS section is authoritative. Ernest authorized implementation and
backup without auditions, then started the current full mix. Active plan/input
bytes remain Q (`16c4700f6f9c...`); do NOT install a new artifact over the run.

Planner now withholds ambiguous +/-1 and weak-read corrections, including
ambiguous real-beat/double-time choices; no inferred snare_align bypass.
Existing explicit human directives remain. Runner/audition support optional
per-load cue_tolerance_ms (finite (0,250], nonboolean), stopped-deck strict
quantize-off seek/restore/recheck, preflight and fail-closed cleanup. Omission
preserves legacy heard cue behavior. This fixes unsafe decision/verification
contracts, NOT automatic musical count-1 identification. A pilot suggesting SWV
419 was later rejected by ear; preserve the accepted400-start/44-count/12-hold
recipe, not old pilot comments or speculative parity shifts.

Backup: `Data/claw-dj-backups/rnb-cooldown-mix-vol-02/build-R-2026-10-23_081400/`.
New full UNHEARD R and manifest live privately in the candidate directory:
`mix_plan.10-23-R-maxwell-file-head.json` SHA
`48c65efe0acb0dc22b23473362068f085727f63cad5c5d9c44fa3619bc9593c4`.
Urban Theme alone enters0.000s with strict20ms; body+16 counts retains its own
outgoing source anchor232/139.254464s. No guessed nudge, order change or human
approval. All269 transition events and31 active pair recipes preserved.
Pending plan-only notes/keep-pair intent is in manifest; active notes/locks
were not mutated mid-run. Reconstruct with private tools-2026-10-23/build_R.py.

211 selected tests pass (15 new); eight heard Q seam control traces still match,
and full Q/R812-event fake-control simulations pass. No real sockets/playback,
render or generic Build. See docs/requirements/backbeat-start-safety.md for
request, scope, tests and limitations. Test when Ernest returns; installation
needs current source-revision checks and a stopped full runner. Do not run an
old Q/N installer or claim the new Maxwell timing has been heard.

## 2026-10-22 — LIVE Q ready for run_mix.sh: approved Say I file-head entry

Ernest heard `audition.10-22-say-i-from-zero.json` and said **save this this
works**, then explicitly requested all approved changes ready in
`./scripts/run_mix.sh`. Saved his verdict, updated only the Ashanti → Say I
pair lock and Ashanti/Say I plan-note overlays, retaining earlier notes as
history. This supersedes the19.568617s entry for this mix.

**Active full Q is installed** at
`brain/data/plans/rnb-cooldown-mix-vol-02/mix_plan.json`:270tracks,812events,
269transitions; SHA `16c4700f6f9ccd920fe17a82792ebb5d2d5b3420ef6c82571d323fdd04d4626e`.
It includes all four reinserted songs and every approved Janet/Sorry/Say I/Sisqo
placement plus prior Claude edits. `run_mix.sh` resolves it and its dry-run
passes. All8 approved seam control sequences match their heard auditions;
full812-event fake-control simulation passes with real sockets forbidden.
Source revisions current. All269 transition events are unchanged from P.
Only Say I preload entry and its body count change: requestedcue0.000s,
body239→271 (+32counts) preserves the approved outgoing fade at grid304 /
source182.768617s into Fabolous, whose cue remains0.1803s. Other three recent
transitions, Ashanti fadegrid320/source200.380728s, older approved settings and
all source exclusions/skip handoffs remain unchanged.

**Record requested versus observed accurately:** Ernest's heard log says
`cue0.00s verified at0.37s` for Say I. The approved control request is0.000s;
Mixxx's reported position was approximately analyzed beat0 (0.368617s), not
proven literal sample zero. Preserve the exact heard request and existing
runner behavior; do not force a new cueing/quantize workaround. The immutable
heard mini SHA is `b870a391866abba04be1ffb7e1456f09a9f9762b02246586d82e0f98ec4fab91`.
Human approval and installation details are in its adjacent verdict file.

Verified backup before install:
`Data/claw-dj-backups/rnb-cooldown-mix-vol-02/install-Q-2026-10-22_073423/`.
Earlier P and exact heard minis remain saved. Private full Q and reconstruction
scripts `save_say_i_zero.py`, `verify_approved_Q.py`, `install_approved_Q.py`
live under the candidate directory. No active mix/audition runner at install;
backup verified, atomic write and human-authorized journal entry completed.
No playback, generic Build, model calls, render, OBS/Pi/source-code changes or
commits. Inherited base Claude review is not a new review of human hand edits.
No pending entry experiment remains. Run normally with `./scripts/run_mix.sh`.

## 2026-10-22 — LIVE P: all four reinserts kept; Say I zero-entry test pending

Ernest heard all four new seams and said **keep all4**, the song selections and
backbeat matching when needed were good. Saved four human pair locks and six
track-note overlays, retaining prior notes. This is positive human listening
approval, not independent measurement of perfect beat/count accuracy.

**Active vol-02 is now full P**, 270 tracks / 812 events / 269 transitions,
SHA `fc1b414e6a8ab6bc100e482b0bf07dbc465dcd6297f71698c46d4cad71124d8a`.
`./scripts/run_mix.sh` uses it. Saved private exact full baseline:
`Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/mix_plan.10-22-P-all-four-approved.json`.
- #65/#66 Body Talk → So Sexual → Ginuwine So Anxious. Body Talk fade grid276 /
  180.102517s; Sisqo cue0.424036s, fadegrid336 /208.437794s; Ginuwine cue20.0982s.
- #106/#107 Ashanti Take Me Tonight → Say I (Clean) → Fabolous Trade It All Part2.
  Ashanti fadegrid320 /200.380728s; **approved Say I cue19.568617s/grid32**,
  fadegrid304 /182.768617s; Fabolous cue0.1803s.
All four exact heard32-count standard blends retained; native pitch, sync,
light EQ/gradual bass swap, no nudge or extra center hold. The earlier Janet
and Sorry seams are now #174/#175 and #222/#223; their musical settings remain
unchanged. All265 unrelated O transitions, all27 existing live pair records,
other cues/body/fade anchors and Suite Theme skip handoff preserved; deck
ownership changes only as needed after insertions. Ashanti and Body Talk bodies
are adjusted to reproduce their newly approved earlier fade anchors. Full812-event
fake-control simulation and runner dry-run pass. All8 newly approved seams
(including Janet/Sorry) match exact heard control sequences after deck remapping;
fixed-order stop/neutralize cleanup is compared independently. Source revisions
current, all270 effective notes read/hashed, historical locks retained and
active/orphaned labels reconciled. Install journaled with human authorization.

Verified backup before P: `Data/claw-dj-backups/rnb-cooldown-mix-vol-02/install-P-2026-10-22_072939/`
contains full O and note/lock/playlist/selection snapshots. Private scripts
`approve_remaining.py`, `assemble_approved_P.py`, `verify_approved_P.py`,
`install_approved_P.py` preserve reconstruction. No generic Build, model calls,
render, playback, OBS/Pi edits or commits. Inherited Claude review belongs to
base order; no fresh model review for human-approved hand edits.

**Say I did NOT start at0:00 in the approved audition: it entered19.568617s.**
Ernest asked to save/keep everything and try just that incoming entry at0:00;
other three transitions must stay exactly as heard. Prepared separate two-song
`audition.10-22-say-i-from-zero.json` (SHA `b870a391866abba04be1ffb7e1456f09a9f9762b02246586d82e0f98ec4fab91`).
Only Say I load cue changes to exactly0.000s; outgoing Ashanti seek/fade anchor,
32-count blend, moves and native pitch/tempo behavior are identical. No other
transition in this miniature. Its count relationship and softer opening are
UNHEARD; do not replace the approved baseline without Ernest's verdict. Both
approved three-song minis are immutable, with human verdict/installation
sidecars. Whole-mini and transition1 dry-runs and fake-control execution pass;
load receives exactly0.0s and both decks stop; active plan/input bytes unchanged.
No LLM review requested. User runs from repo, full mix stopped:
`.venv/bin/python -m hands.audition_transition --plan "$HOME/.openclaw/workspace/Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/audition.10-22-say-i-from-zero.json" --transition 1 --lead-bars 4 --tail-bars 4`.
Await this single entry verdict. Do not alter the other three kept transitions.

## 2026-10-22 — LIVE O installed; remaining auditions ready

Ernest heard and kept **Pacifico → Sorry → The-Dream Ghetto**. His approval is
for complementary energy, vibe and percussion themes, pleasant rather than
dissonant, not certification of perfect beat/backbeat/count alignment. Exact
heard miniature SHA `2b5c581add28` is immutable. Both pair locks and all three
note overlays saved with human attribution; previous notes retained as history,
with newer placements explicitly superseding SWV → Sorry and Sorry → Say I.

At Ernest's request to make `./scripts/run_mix.sh` ready, installed full O into
active `brain/data/plans/rnb-cooldown-mix-vol-02/mix_plan.json`: **268 tracks,
806 events, 267 transitions**, SHA
`2c7408fa2172446c9b4142878fe962276084779e707a87960291d2fd043db121`.
O = Claude's live M plus the four exact heard Janet/Sorry seams: **#172/#173
Robin Sex Therapy → Janet Would You Mind → Jesse You**, **#220/#221 Pacifico →
Sorry → Ghetto**. Other 263 transitions and all 23 existing live pair records
are preserved; original cues/bodies/fade anchors retained, adjusting deck
ownership only where insertions require it. Existing Suite Theme same-song
skip handoff, historical Claude edits and SWV → 112 at 36 counts are retained.
Backbeat assessment metadata on new seams is unverified, reflecting what Ernest
actually approved. All effective notes read and hashed. Source revisions current;
active/orphaned pair labels reconciled without deleting historical records.

Backup: `Data/claw-dj-backups/rnb-cooldown-mix-vol-02/install-O-2026-10-22_071622/`
includes prior M, notes, locks, playlist and selection; hashes verified. Journal
records installation/human authorization. Private authoring/installer/checks in
candidate `tools-2026-10-21/`. Full runner dry-run and 806-event fake-control
simulation passed (real sockets forbidden); four full-context audition control
sequences exactly match the heard minis. `scripts/run_mix.sh --dry-run` resolves
the correct active plan and passes. No playback, generic Build, render, model
call, OBS/Pi file edits or commits. Original accepted Claude review belongs to
base M, not a fresh review of these hand edits. Janet-only N installer is now
obsolete and will refuse changed live/input revisions; do not run it.

Ernest next requested auditions for **Say I** and **So Sexual**. Both remain OUT
of live O pending verdict. Private UNHEARD files under
`Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/`:
- `audition.10-22-say-i-ashanti-fabolous.json`: a1 Ashanti Take Me Tonight →
  Say I (Clean), a2 Say I → Fabolous Trade It All Part 2. Say I cue grid32 /
  19.568617s per effective note; fades Ashanti 200.381s and Say I 182.769s.
- `audition.10-22-so-sexual-body-talk-ginuwine.json`: a1 Body Talk → So Sexual,
  a2 So Sexual → Ginuwine So Anxious. Sisqo cue0.424036s, Ginuwine pinned20.0982s;
  fades Body Talk180.103s and Sisqo208.438s.
Both use gentle32-count standard blends, sync/light EQ/gradual bass swap,
native pitch, no filter exit/inferred snare jump. Private timing brought earlier
in whole bars to finish before own quiet outros; existing LIVE cues/anchors are
unchanged. Cached lyric sections are incomplete (especially Sisqo); no claim of
instrumental entries or certified clean vocal overlap/count alignment. So Sexual
intro is softer (-26..-18dBFS versus Body Talk -16..-11); listen for level handoff.
Only short clipped windows checked with single-thread analysis, no audio export.
Each full-mini and both audition dry-runs and fake-control executions/cleanup
pass. No LLM review requested. Use four-bar lead/tail; collect each verdict and
save human note/lock before splicing. Do not use Generic Build. New private
source/checked manifests/commands in `AUDITIONS_REMAINING_2026-10-22.txt`.

## Demo video kit (2026-10-18, made public-safe 2026-10-19)

- `scripts/demo/demo_kit.py`, `demo_music.py` and `storyboard.json` render the public short. Doc: `docs/marketing/DEMO_SHORT.md`.
- **Public-safe means:**
  - only original music (`demo_music.py`, numpy synthesis, seed 7);
  - GUI stills from a clean sandbox plan;
  - the agent shot replays a real `plan_cli` session;
  - the end card is the GitHub repo, with no ask.
  - Keep it that way. Don't reintroduce commercial audio, and don't say "raising" (Ernest, 2026-10-19).
- The pipeline is PIL frames piped into ffmpeg. There's no drawtext or libass: the homebrew ffmpeg lacks them.
- Stills come from headless Chrome. For clean screens, run a private editor copy on another port with a scratch `brain/data`; never switch the live `active.json` for a screenshot.
- The payoff shot is either a drawn two-deck visualization tagged BLEND PREVIEW, or Ernest's OBS footage of Mixxx playing the demo plan (`--obs`), tagged LIVE IN MIXXX.
- Don't render video while Ernest streams: x264 plus PIL compete with Mixxx and OBS for CPU.

## vol-02 candidate I is live; double-time grids and quiet outros (2026-10-20)

- Live plan rev 3f41321b55c6 (from `mix_plan.10-19-I.json`). Backup: `Data/claw-dj-backups/rnb-cooldown-mix-vol-02/mix_plan.2026-10-20_073155.before-10-19-I.json`. Installed before audition, at Ernest's request. Changed: #1, #2, #3, #4, #6, #192. Numbers #2–#191 shifted +1.
- **Double-time grids:** with a 2×-tempo grid such as Shanice at 187.88, the beat-domain `xcorr.py`/`xcorr_wide.py` compare equal beat counts that cover different lengths of time. Their result is wrong; use a snare fold in seconds instead. One grid beat is an 8th note.
- **"Not blended enough" with no cut:**
  - check the outgoing song's own outro level (Sorry drops 8 dB at 188 s);
  - check the incoming intro level (Say I sits at −15 dB for 20 s).
  - Fix with a whole-bar earlier ride and a later cue; don't echo or cut.
- **2026-10-20 08:08: candidate J is live** (rev e65f6e1d4b12, 270 tracks).
  - Six new songs were hand-inserted with `scratchpad/fixes1020/mini.py` + `splice9.py`.
  - For a new song in a hand-edited plan:
    1. Compose a 3-track mini plan, neighbour → new → neighbour, with the left neighbour's cue and anchor pinned (`cue_seconds=…; trust_cue_seconds; ride_beats=…; trust_ride_beats`) and the right neighbour's cue pinned.
    2. Splice in the new song's cue, body and both blends, and re-fit the right neighbour to keep its anchor.
    3. Check each blend window's loudness for an outro that fades during the blend, or a near-silent intro.
- Pending: candidate H (Keith Sweat between End Of The Road and Violet) has to be re-spliced onto J, as #39/#40/#94.

## vol-02 candidate M is live; pairing by Ernest's ear (2026-10-21)

- Later audition: **Sex Therapy → Would You Mind** is human-verified and kept
  as Ernest's best effort so far. Exact miniature:
  `Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/audition.10-21-janet-robin-jesse.json`
  (SHA 600ced8aebc8), transition 1: 32 counts, Robin grid 401 / 215.016 s,
  Janet source 0.066916 s / grid 0, sync/light EQ/gradual faders and bass swap.
  Saved the pair lock (pending/orphaned) and both DJ-note overlays with prior
  notes retained. Keep this incoming blend unchanged. Ernest then heard and liked
  transition 2, Janet → Jesse Powell **You**, too: 32 counts, Janet grid336 /
  199.279s, Jesse cue17.3787s / grid32. Both approvals are for **energy and vibe**,
  not proof of beat/snare/count matching. All three plan notes and both locks
  preserve that distinction. The theoretical quiet-intro warning did not prevent
  Ernest liking the handoff; do not overrule his ear with meter scores.
- Full candidate N `Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/mix_plan.10-21-N-janet.json`
  (SHA 7b138171102a) adds only Janet: 267 songs / 803 events, blends #172/#173.
  The other 264 blends, all 23 prior locks and existing cue/fade/body decisions
  are retained, with deck ownership exchanged after the single insertion.
  Dry runs and full-context fake-control comparisons pass. The user-run
  `tools-2026-10-21/install_janet_N.py --install-after-stream` checks hashes/notes,
  refuses busy runners, verifies a backup outside the repo, atomically replaces
  only mix_plan.json and journals it. Tested only in an isolated temporary plan.
  **Live M is unchanged**. Never install the three-song miniature. No Generic Build.

- **Live:** `brain/data/plans/rnb-cooldown-mix-vol-02/mix_plan.json` = candidate M (rev 42a74d4c63e8, 266 tracks). It's J plus:
  - #4 SWV remix → "I'm So Into You": 44 beats from 400 with `center_hold_beats` 12. Accepted and locked; don't touch.
  - #5 → 112 "Be With You": 36 beats.
- **Out of vol-02:** Sorry, Say I, Would You Mind and So Sexual. Every computed spot for them (K, K-b, L) was rejected by ear. Ernest decides next: leave them out, name their neighbours, or keep Sorry → Say I together.
- **Lesson:** key, BPM and percussive/kick share don't predict his "energy" match. Prefer pairs he's already streamed, and boom bap with boom bap. When the backbeats line up, a longer blend may hold both songs at full (`center_hold_beats`, Mixxx's additive crossfader), but keep it clear of the verses: map vocals first (scratchpad `fixes1021/vocals.py`) and change length one bar at a time.
- **New runner field:** `center_hold_beats` on a transition (`hands/run_mix_plan.py`, `tests/test_center_hold.py`). Build doesn't write it yet, and transitions.json overrides can't hold it, so it lives only in the hand-edited plan and is recorded in the override note.
- **Scripts** (scratchpad `fixes1021/`): `mini3.py` and `splice11.py` for multi-block re-pairs keyed "Artist|Title"; `swv4*.py` for #4 variants; `buildM.py`.
- **The four songs stay in the library and playlist, not deleted.** Ernest wants another AI harness to find their pairings with him. Its prompt is `~/.openclaw/workspace/Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/PAIRING_PROMPT_2026-10-21.md`, and its tools are copied to `tools-2026-10-21/` next to it.

## Guessed bar counts: the shared "off by one count" bug (2026-10-21)

- `count_shift_beats` (`brain/onset_analysis.py`) assumes every Mixxx grid's beat 0 is count 1.
  - When the two songs' snare parities disagree, one grid isn't on count 1. Both +1 and −1 then match the snares, and the code always picks +1.
  - So the count is a coin flip. Remixes are prone to it: their intros and pickups move beat 0.
  - A 2-beat grid offset goes unnoticed entirely (Cherry Pie → Paradise).
- `bar_count_guessed()` now marks these blends `backbeat.status: "bar_guessed"`; previously they were "matched". Treat them as the first thing to check by ear.
- A real fix needs a reliable count-1 measurement. The pilot (kick 1/3, snare 2/4, chord change on 1, folded over the middle of the song) agreed with 9 of 14 ear-approved blends: not enough to move rides automatically. Next tries: downbeat tracking (madmom-style), and harmony over longer phrases.
- When a seam is `bar_guessed`, build both sides (±1) and let Ernest pick, as with candidates K / K-b.

## No abrupt cut-offs (2026-10-17)

Ernest rejected an agent's 4-beat echo-out "fix": "I hate the sharp cut off of Sade's song. DO NOT DO THAT AGAIN."
- Echo-out, cut, brake, spinback and filter-drop exits play only with his recorded `abrupt_reason`. Build never chooses one, and the runner and audition refuse unmarked ones.
- When a pair won't blend, re-pair it (see `user_stories/story__never_end_a_song_with_an_abrupt_cut_off.md`).
- Known gaps:
  - `pdd intent apply`'s prompt step failed on the local model, so the prompts were updated by hand.
  - No story regression tests have been generated yet (`pdd test --from-story` needs a model).
  - The live vol-02 plan refuses at #35 until candidate C (or another #35 fix) is copied in.

## Grid drift inside a blend is a known gap (2026-10-17)

Ernest's 10-17 "off by one beat" and "jumbled" notes came from songs drifting away from their constant Mixxx grids. These were Sade "Cherry Pie" (a vinyl rip with a live drummer) and R. Kelly "Only The Loot Can Make Me Happy" (about 0.36% faster than its grid after beat 100).
- **How it was measured:** for each 16-beat block, find the onset offset (±300 ms) that best fits the grid ticks, then read snare and kick energy per bar slot at those shifted positions.
- **What Build gets wrong:**
  - It doesn't measure drift.
  - Its blend-window snare read can flip parity when it is taken on off-grid beats; R. Kelly's flipped at exactly the 0.25 gate.
- **Current fix:** per-blend `incoming_nudge_ms` (±250 ms) plus a ride re-fit, in hand-edited candidates. See PROGRESS.
- **Possible Build fix (not started):** measure the offset in each blend window and either propose a nudge or refuse to align on a drifting window.

## vol-02: inserting songs into a hand-edited plan instead of rebuilding (2026-10-16)

`plan_mix_build.build` overwrites `mix_plan.json` (no archive). The only things that survive a rebuild are bunches (they keep songs adjacent), pair overrides in `transitions.json` (technique, beats, showcase_move, effects, note) and per-track notes. None of these can reproduce an exact fade-start beat (it depends on the previous transition's length) or `incoming_nudge_ms`. So for vol-02, Ernest chose to splice the two new "Betcha By Golly, Wow" versions in after Gino Vannelli (#98–#100).

Method:
1. Run `compose_mix_plan` on the four-song excerpt [outgoing, new, new, following], with `fixed_groups=[ids]`, the plan's profile and seconds, and the cues of the neighbouring songs pinned via `dj_notes_lookup`.
2. Flip the excerpt's decks to match the full plan.
3. Shift the preloads one slot along.
4. Re-fit the following song's ride so its fade-start beat is unchanged.

Details, the backup and the verification are in PROGRESS.md. Transition numbers after #98 moved by +2.

## Use Ernest's named experiment, not a detached source path (2026-10-16)

Active plan confirmed `experiment-play-cues-like-notes-01`, with the two exact
studio selections. User authorizes plan edits (“it says experiment in its
name”), but no explicit request to start audio was made. Added revision-checked
plan-only source/destination notes and transition intent. Local authoring script
`brain/data/plans/experiment-play-cues-like-notes-01/authoring/play_cues_like_notes.py`
reads this pinned named plan, refuses changed/ambiguous selection or hard plan
limits, and calls existing shared pitch-play runner. Modes repeats (four zero-
shift attacks) then steps (six pitches 0,0,0,1,2,0), default note clock 85 BPM,
original native rate. 0–2s is still technical, NOT a verified cue. README includes
commands; five mock cases and two real-source dry runs pass. No audio started.
GUI remains stale because there is no mix artifact; generic Build/Start does
NOT yet represent this gesture. Do not generate an ordinary crossfade merely
to clear stale. Next is user-run live audition and cue/rhythm iteration, then
explicit full-performance integration. Global library notes/cues untouched.

## Executable first pitch-play scope (2026-10-15)

Approval received. Read `PITCH_PLAY_EXPERIMENT.md` before running anything.
`hands/pitch_play.py` owns original-source restrictions, empty deck setup and
cleanup; `core-rust/clawdj/src/pitch_play.rs` owns absolute-deadline monophonic
notes using existing Mixxx DSP. CLI release built; default dry-run connects to
nothing. Requires explicit `--live`, all four decks stopped, AutoDJ off and an
empty selected deck (default 3); no saved hotcue edits, playback during development,
reference score inference or generic-plan integration. The source guard stays
active until confirmed ejection, even during cleanup failures. Persistent API
outages cannot guarantee silence/restoration; failures are surfaced.
18 Python + 8 Rust unit + 3 CLI tests pass; selected Python 46 and Rust workspace
46 pass. Broader performance checks have two unrelated errors (stale plan fixture
and missing FFmpeg soxr). Strict prompt checks/build/Clippy/format/diff pass.
PDD apply timed out after intent capture; scoped artifacts maintained directly,
no automatic semantic/story-contract success claimed. Next is a human-run live
cue audition and measured known-tone capture. Preserve unrelated dirty mix work.

## Pitch-play reference / next bounded experiment (2026-10-15)

Read `PITCH_PLAY_RESEARCH.md` and `requirements/pitch-play.md`. Reference media,
caption, measurements and a local viewer are outside Git under workspace
`Data/Public/Videos/TikTok/numark-dj_7671346273600998686_dj-ktime_mixtrack-go_pitch-play_analysis/`.
The sibling MP4 is the hash-verified unchanged Downloads original.
Local Mixxx source has genuine pitch-play mappings; `pitch_adjust` knob's nominal
±3 range is not a hard DSP limit (`allowOutOfBounds=true`). Start narrow anyway.
Reuse existing Rust TCP control client; do not follow historical “Rust MIDI only”
notes. No engine rebuild, exact score transcription or live test was done.
Next: human review of the draft's meaning, then scoped PDD source/test work for
an opt-in monophonic cue/pitch experiment with safe cleanup and a real audio
latency/pitch-attack check. Preserve unrelated dirty backbeat/audition edits.
No generated story/contract or semantic acceptance claimed. Do not imitate or
transcribe DJ shoutouts; the original reference audio itself remains unchanged.

## Ear fixes in rnb-cooldown-mix-vol-02; incoming_nudge_ms (2026-10-15)

Six transitions (24, 25, 35, 49, 62, 85) were hand-edited in `mix_plan.json`
from `docs/transition-log-2026-10-15.md`; a rebuild discards them. The runner
now honours a transition's `incoming_nudge_ms` (millisecond seek after sync).
Open: Build still cannot see half-time grooves on double-tempo grids (both
songs ~1:1), the cause of most "off by 1 count" notes.

## Double-time grids (2026-10-15)

A pair whose grids differ about 2x (`double_time_side`) no longer uses the
odd/even snare test. Build reads the double-time song's real beats
(`measure_real_beats`, table `real_beat_windows`) and aligns with
`double_time_shifts`; unclear reads are `unverified`. Found on Shanice ->
SWV in rnb-cooldown-mix-vol-02. Rebuild that plan to apply it.

## Live transition audition in Mixxx; render preview deprecated (2026-10-14)

Ernest: "I'd rather have Live in Mixxx and see about 'sunsetting' the render
method ... skip forward or backward transitions so we could edit and audit."

- `hands/audition_transition.py` plays ONE transition of the built
  `mix_plan.json` live in Mixxx: the outgoing song from a lead-in (default 8
  bars) before its planned fade start, the real transition, a short tail of
  the incoming song (default 16 bars), then both decks stop. The lead-in is
  placed from the plan's `phase_anchor` (`planned_anchor_beat_index` on the
  outgoing grid already counts the previous fade, skips and backbeat nudges);
  the incoming song is cued from the plan's own load/preload event; the
  outgoing deck gets the tempo/pitch the runner would be holding (play_bpm
  hold, keep_blend_tempo, settle target, start bpm_target). Then
  `hands.run_mix_plan._run_events` runs start -> play_body -> transition ->
  finale -> stop_all, so sync/beatsync_phase, `snare_align`, EQ/fader curves
  and the runtime bar guard are the full mix's own code, not a copy.
- CLI: `uv run python -m hands.audition_transition --plan <slug> --list`,
  `--transition N [--lead-bars 8] [--tail-bars 16] [--dry-run] [--take-over]`.
  Dry runs never connect to Mixxx. Ctrl-C stops both decks and resets EQ/filter.
- GUI: Arrange (`http://127.0.0.1:8787/#arrange`) — each transition has
  "Audition in Mixxx"; the audition bar shows which transition is playing
  (number of total, lead-in / transition / tail) with Previous, Replay, Next
  and Stop. Nothing plays until a button is pressed. Every press reads the
  built plan fresh, so edit -> rebuild (2 · Create the mix) -> Replay hears
  the change; the bar says so after a transition edit and while the plan has
  unbuilt edits. Runs in a child process (`AuditionSession`) so Stop always
  works; stepping stops the previous audition first.
- Refusals: a full mix run (GUI thread or a `hands.run_mix_plan` process) or
  another audition is active; any Mixxx deck already playing (the GUI offers
  "Take over the decks"); performance plans (`execution_mode`).
- Approximate, flagged in the output: transitions right after a
  vocal-over-bed layer (no ride of their own), after a same-song handoff, and
  artifacts without `phase_anchor`. The real Mixxx state before the lead-in
  (sync-leader, exact live rate after a settle glide, beatgrid drift) is
  re-created from the plan, not captured from a real run.
- `brain/preview_transitions.py` is DEPRECATED (docstring + runtime notice):
  it ignores previous-fade beats, skips, the +1 anchor, `snare_align` and grid
  alignment. Not deleted: remove it after Ernest confirms the live audition.
- PDD: story
  `user_stories/story__when_i_audit_a_mix_i_audition_one_transition_live_in_mixxx_and_step_between_them.md`,
  prompt `prompts/hands/audition_transition_Python.prompt` (new architecture
  entry), `arrange_JavaScript.prompt` and `plan_client_JavaScript.prompt`
  updated by hand (local `pdd` generation was failing).
- Verification: `tests/test_audition_transition.py` (fake Mixxx only) covers
  lead-in seek math, incoming cue, snare_align + phase_anchor through the real
  `_run_events`, play_bpm hold carry-over, skip/entry clamps, vocal-layer
  chain, prev/next bounds, refusals, dry-run/CLI, the child-process session
  and the Arrange controls (node). No live Mixxx playback was run.
  Not yet heard by Ernest; nothing committed.

## Model answer limit raised to 15 minutes (2026-10-14)

- `brain.llm_providers.ask` now waits up to 900 s (was 600 s) for every
  provider. The 257-song review took ~8.5 min, too close to the old limit for
  bigger sets. A timeout still falls back to the optimizer order with
  "review skipped" in the order notes.

## Backbeat measured at each blend window (2026-10-13)

Ernest: backbeat matching is "near perfect", with at most one or two misses
out of hundreds of transitions — could Build find those?

- The song-wide snare read comes from a song's first minutes; Mix to listen
  blends out late, where an extra half-bar or live-drum drift can put the
  snare on the other beats. Build now measures the drum-only snare parity of
  each actual blend window (outgoing: 16 beats before the fade start;
  incoming: from its cue; 64 beats each) and aligns on it when confidence
  ≥ 0.25 (`BLEND_WINDOW_GATE`); otherwise the song-wide read stands.
  `trust_ride_beats` blends are left alone.
- `compose_mix_plan` builds once silently to learn the windows, measures the
  uncached ones in parallel at low priority (`BlendWindowReader`), then builds
  with them. Reads are cached in the library index table
  `beat_phase_windows` and reused while the song's grid is unchanged.
  Each blend records `backbeat.blend_window`; the reason gains
  "(blend-window read)" when a window read flipped or upgraded a side.
- Test build of `rnb-cooldown-mix-vol-02` (optimizer only, same order):
  216 snare-matched (was 208), 39 bar count only (was 47); first build
  +~2.7 min for 508 windows, near zero after. Flipped and corrected: #4 New
  Edition "If It Isn't Love" → Cassie (the clearest case), #87 Jagged Edge
  "Heartbreak" → Aaliyah, plus #91, #116, #160. Listen-check #4 and #87.

## Build review sees the locked pairs (2026-10-13)

- The review's mix sheet now carries a `locked` list, by song id: required
  opener/closer, keep-together pairs (and their order), placements ("first
  half"), and mashup payoffs (a remix that teases a hit followed directly by
  the original). `locked_rules` in `brain/mix_llm_refine.py` computes it
  before the model call; `brain/llm_prompts/build_review.md` tells the model
  to check every line and move a locked pair together.
- Why: on the 257-song `rnb-cooldown-mix-vol-02`, Claude's review was rejected
  for breaking the Best Of Me remix → original payoff it could not see. With
  the list shown: "claude-cli review accepted (blend 0.80 → 0.80)", the lock
  held, and Claude broke up long same-artist runs (six Joe songs, three
  Jodeci, Sade blocks). It took ~8.5 min (prompt ~220k characters).

## Harness-neutral OBS integration (2026-10-11)

Use `.venv/bin/claw-obs capabilities` or `python -m hands.obs_cli` and read
`OBS_AGENT_CONTROL.md`. `hands.obs_control.OBSControl.execute` is the one
transport/schema boundary; CLI and any future MCP share it. Optional dependency
is the `obs` extra. OBS retains its Twitch login, which does NOT grant separate
Twitch chat/moderation API access. Client rejects non-local hosts, unknown/raw
RPCs, service settings and ungated mutations/outputs. No output toggles.

31 OBS tests, 6 existing control-port and 22 live-toolkit tests pass.
Broader isolated DJ-workflow verification also passes 286 synthetic tests.
Both new prompt contracts pass strict checks; syntax/diff checks pass.
Synthetic CLI tests now isolate credentials instead of reading personal files.
A deadline-aware socket enforces the shared budget through TCP, HTTP upgrade
and fragmented-frame I/O; slow-trickle and reused-client regressions pass.
Real authenticated version/status/scenes/inputs now succeed on port 4455:
OBS 32.2.2, obs-websocket 5.7.4, RPC 1. The user enabled the server and saved the
password through the hidden local prompt. Current program scene is Scene;
inputs are empty and stream/record outputs are inactive. Local OBS API access
is verified; actual scene mutations, audio capture/routing and Twitch broadcast
remain untested. Keep authentication enabled.
Password hidden-input setup must be run in the user's own terminal, not captured
agent stdin. Do not read the saved OBS password without explicit permission.
No stream/recording/scene/Mixxx mutations or Twitch credential reads occurred.

User approved Python library + JSON CLI with public/output actions explicitly
gated, and clarified live Mixxx mixing is not VOD playback. Keep policy discussion
separate from this local integration. Exact PDD intake persisted; architecture
inference stalled and picked Rust, then was stopped. Accepted Python scope,
prompts, story and manifest are maintained directly; no automatic generation
or semantic certification claim. See `intents/OBS_CONTROL_APPROVAL.md`.

## Startup mix-duration estimate (2026-10-08)

`scripts/run_mix.sh` prints `Estimated total mix length: about ...` in its plan
summary before either live or dry-run execution. `hands/mix_duration.py` counts
sequential beat-based rides/blends with planned BPM holds/settles/ramps and
seconds-based finales; simultaneous `performance` timelines use their last
clip end, counting supporting beds once. Rounded to minutes, approximate:
live source clamps, beat alignment, loading and effect timing can vary. Even
with `--max-events` this is the full-plan estimate. No Mixxx connection, audio
reads, or plan changes during estimation. Shell summary reads the plan path
from an argument so quotes/spaces are safe. Regression tests use synthetic
plans and stub the live executor; no real playback is needed.
Verified: 61 existing runner tests, eight new tests, shell syntax/diff checks,
and a full 47-event Smooth R&B shell dry-run (estimated about 1 hr 7 min).
The selected `chill-afternoon-rnb-vol-01` currently lacks a built mix_plan.json;
its selection and all personal plan artifacts remain unchanged.

## One-shot first pass and agent refinement (2026-10-06)

Read docs/MIX_WORKFLOW.md and the independent stories
story__one_shot_mix_without_direction.md / story__refine_current_mix_with_any_agent.md.
The selected provider now reviews two-song sets too; blank direction skips only
constraint interpretation, and review receives effective profile settings and
untruncated effective DJ notes. Model choreography is restricted to DJ showcase.
Club set/Mix to listen use model order review plus established ordinary planning.
The panel explains these defaults and how an agent can continue the same plan.

plan_cli build now supports --provider, --brief and optional --base-rev (checked
before model calls/writes); defaults remain optimizer-only and empty direction.
Agents should use named scope and fresh revisions for edits, preserve approved
parts, and compile authored performances through performance_cli. Generic Build
still protects hand-authored timelines. Existing approved advanced_mix.json is
used automatically; arbitrary evidence generation/approval remains future work.

Verification: 281 focused synthetic tests pass without skips, desktop/mobile
mocked browser checks pass, four affected prompts pass strict structural checks.
No new real mix/listening audition or playback. Exact authorization recorded by
PDD; local architecture inference failed, so source prompts/manifest maintained
directly without automatic regeneration/semantic certification claims. Implemented
on feat/shared-dj-brain-providers. Idle editor restarted as
PID 34519 on 8787/control 9995; active plan identity/readiness stayed unchanged.

## Advanced generic builder, completed measured-set stages (2026-10-06)

Stage one: 6738000 / advanced-builder-stage1-v1. Stage two: addbb34 /
advanced-builder-stage2-v1. Stage three adds one continuous instrumental support
bed beneath one/consecutive full mixes using the existing native source engine.
See ADVANCED_GENERIC_BUILDER.md for the reviewed local recipe schema. All
foregrounds need measured data for one common clock; this is not arbitrary
automatic generation of new measurement evidence. No real recipe/plan was
created or played during this task. The same GUI/plan-aware CLI Build upgrades
when evidence is present, otherwise retains conventional events with a reason.

Generic-generated provenance permits rebuilding its own performance, while
authored timelines remain protected. Recipe revisions enter staleness. Native
performance retains finalized foreground identities/order; a supporting source
is a separate clip, never an extra selected song or an acapella reclassification.
Bed source hashes/current effective notes, whole-body coverage, loop phase,
pitch/alignment and complementary EQ are enforced. One bed at a time. Native
deck allocator, source guards, drift/stop monitor and normal/failure/interruption
cleanup are reused. Native eased different-song fades take 24+ counts to meet
the sixteen-count linear peak-speed rule. Explicit styles/formats/tempo/pitch
holds/pair overrides retain conventional execution. Confirmed final verse exits
cannot move earlier and play-to-end re-entry preserves the original endpoint.

Verification: 36 advanced tests, 23 existing Python performance tests and 12
Rust performance tests pass. Known FFmpeg lacking soxr still prevents the one
real-decoder test; it is excluded from that subset only. Final focused suite:
264 tests; synthetic desktop/mobile browser flows and strict prompt checks pass.
Manual edits remove generic ownership even after performance recompilation.
PDD intent is durable;
its architecture inference could not reach sandbox localhost. No automatic
regeneration or semantic certification is claimed. Musical quality of these
new generated arrangements still requires a short live audition.

The idle editor was restarted with these stages loaded on port 8787, retaining
Mixxx control port 9995. The existing personal plan remains ready/non-stale;
no Build/Apply/Start was run on it. Reload the browser for the updated UI.

## Advanced generic builder, stage two (2026-10-06)

Stage one commit 6738000 / tag advanced-builder-stage1-v1: 243 focused tests
plus browser checks. Stage two adds measured sample/source unison through
brain.advanced_mix. Explicit notes, adjacent pair, exact sampled-bar cues,
whole-blend backbeat/pitch/alignment evidence and source hashes are required.
The native runner already sets keylock off and pitch_adjust zero, restoring
turntable sample pitch with the measured rate. Foreground order is preserved;
sample bar repeats shift later clips by whole pattern periods. Twenty advanced
tests pass, including source limits, both sample directions and failed evidence.

## Advanced generic builder, stage one (2026-10-06)

Ernest authorized commit/tag/push and implementation of the advanced stages.
The shared-provider commit 87aea34 and tag shared-dj-brain-providers-v1 are on
origin; master e589b06 has master-before-advanced-builder-2026-10-06. No merge.
The latest H flagship is holo4-27b, now in .env.example; Holo4 requires funded
access and the key-only runtime still defaults to free-tier Holo3.1.

brain.advanced_mix upgrades the conventional finalized plan only when a local
approved advanced_mix.json covers every foreground with compatible measured
tempo/pattern/pitch evidence and source hashes. It reuses the existing native
performance compiler/runner, including deck allocation, bounded original-source
loops and drift/stop cleanup. First-stage features: independent-copy forward
skips/re-entry and pre-verse intro extension. Invalid recipes preserve original
events with a reason. Explicit notes/formats win; authored performance guard
remains. Recipe revisions make old builds stale. See ADVANCED_GENERIC_BUILDER.md.

## DJ brain provider unification and mix controls (2026-10-06)

`feat/shared-dj-brain-providers` starts from latest master `e589b06`, not the
old `feat/build-mix-plan-refactor` checkout. Curation and DJ-note interpretation
now call `brain.llm_providers.ask`; no NemoClaw, generic endpoint or H managed
planning agent is launched. The direct H Models API is the new `hcompany-api`
provider (HAI_API_KEY in ignored .env; optional CLAWDJ_HCOMPANY_MODEL, default
holo3-1-35b-a3b). See `H_COMPANY_MODELS_API.md` for official sources and limits.
No key is currently set here, and H's actual DJ quality/account access remains
untested. Local llama-server passed a synthetic text curation call.

The two mix selectors previously chose independent providers for order review
and DJ-note interpretation. `#order-engine` is now the single shared choice;
`#directives-engine` was removed. `#engine` on Curate has the same provider
options from `/api/providers`. Both pages offer Refresh models; .env reload
updates/removes file-owned values while preserving shell settings. Keys never
enter status payloads. Optimizer-only disables note interpretation, and no
available model disables Ask without blocking deterministic Build.

Mix controls now form a responsive panel: feel cards, model, multiline brief,
readiness, primary Build action and the existing musical protections. Advanced
contains experimental formats and review-only note edits. Idle polls preserve
the selected feel. A missing-BPM finalized track stops Build before model calls
or plan writes. This refactor preserves the existing optimizer, effective notes,
phrase/verse/stem/backbeat/gentle-fade/source-limit code and authored performance
protection; it does not turn unimplemented advanced techniques into automatic
planning options. Candidate order, warnings and confirmed Start remain separate.

Verification: `python tests/run_dj_workflow_checks.py` isolates the mounted
library for 228 passing focused checks. The Playwright fixture under
`tests/browser/dj_brain_workflow.cjs` uses synthetic songs and mocked HTTP,
checks desktop/mobile layout, shared requests, no Apply/Start side effects,
profile/provider persistence, refresh and errors. Use a temporary Playwright
installation and Google Chrome; no browser dependency was added to the app.
Extended performance verification has one environment failure: FFmpeg has no
soxr resampler. Strict contracts pass on the three affected prompts. PDD's
architecture inference failed to reach sandboxed localhost; source/manifest
changes were made by hand, with no generation or semantic-certification claim.

The original request is durably recorded by `pdd intent apply`; Product Intent
and `story__shared_dj_brain_providers_and_simple_mix_build.md` describe current
meaning. The follow-up about advanced techniques was answered with a staged
recommendation, not treated as implementation authorization. No commit/push/merge
or private-library mix build was performed during this refactor.

The idle editor was restarted with the updated backend on 127.0.0.1:8787,
Mixxx control port 9995. Its existing plan remained ready, with no running mix.
Read-only live Chrome checks passed on Mix and Curate: eight shared providers,
optimizer-only as the ninth mix choice, no old note selector and no page errors.
Reload the already-open browser page to use the revised panel.

## Same-beat measurement tools and EQ controls (Opus 5.5, 2026-09-27)

Any harness can now measure, author and verify a one-beat continuous mix from
the repo: `brain/performance_measure.py` (fit, pitch, lags, vocals, hooks,
align, verify; evidence refused inside the checkout), `brain/performance_author.py`
(`Grid`: pattern points, aligned starts, clips, loop, bed), guide
`docs/SAME_BEAT_CONTINUOUS_MIX.md`. The reference tempo is found independently
(sharpest pattern fold), and pattern zeros are sub-bin interpolated. On the nine
Who Shot Ya sources the repo tools reproduce the Opus 5.5 findings (all within
±2 cents after rate, lag 0 beats beats ±1 for all eight vocal records, album and
Club Mix the same vocal take at 0 ms, Ja Rule's hook not). Re-verifying the
recorded Opus pass 2 render: every clip locks at 0 beats, all within a 4.4 ms spread.

Format additions, all optional and backward compatible (Python validator,
Rust executor and offline export share one EQ curve, `shared.performance.clip_eq`):
per-clip `eq_automation` ({at, scale:[low, mid, high]}, eased), bed `support.mid_gain`,
and pulses as `{at, gain, width_seconds}`. Offline export now applies a 3-band
EQ (246 Hz / 2484 Hz) from that curve instead of the old 145 Hz low subtraction,
and a support bed switches to its loop at takeover like the live runner.
Release executor rebuilt. Tests: 24 performance, 7 new measure/author, 34 Rust;
full Python suite 366 with one pre-existing failure (`test_collection`
`test_index_predating_data_dir_migrates_and_re_registers`, fails on clean HEAD too).
Not changed: live deck-to-deck timing (start-only correction, 80 ms stop); a
drift-correcting runner needs a live Mixxx test.

## Grok 4.7 Who Shot Ya pass 2 (2026-09-21)

Pass 1 was liked. Pass 2 does not move clips through the Jim Jones entry.
Club Mix enters at source 35.485s, before the verse at 43s. The instrumental
is a 16-beat third deck under Jim→K-Dot and the bass bed from 8 beats before
Club Mix through Club Mix's end. Duration 1283.508s. Listening of pass 2 is
still open. `observed_first_verse_start_seconds=43` is on the Club Mix global
DJ note.

## Grok 4.7 Who Shot Ya pass 1 (2026-09-21)

Live plan only: `brain/data/plans/notorious-big-who-shot-ya-variations-grok-4-7`.
22:00.157, 59 events, 91.68 BPM, album-pattern backbeat. Instrumental bed covers
DMX, 50 Cent, and Ja Rule, then stops. No rendered master. Preflight passed;
Ernest has not listened. Same `./scripts/run_mix.sh --plan <that mix_plan.json>`
command. Do not treat the Astra plan's timings or its "sounded pretty good" note
as a verdict on this mix.

## Current Astra outros follow verse observations (2026-09-21)

Ernest says the live mix sounded pretty good through K-Dot before the earlier
Jadakiss load failure and asks for small outro adjustments based on new DJ notes.
The same named plan now lasts **22:10.582 / 1330.581852s**, with 52 live events.
Preserve the earlier arrangement: clips 0–5 are unchanged, and K-Dot's entry,
rate, gain and incoming fade stay unchanged.

- K-Dot source fade: **2:35.231–2:39.764**, after the confirmed last verse ends
  at 2:31. Jadakiss still enters at source32s, now at mix **16:14.501**.
- Jadakiss final verse ends at source **2:29**. A rewind/replay around **2:39**
  sounds like an edit/splice to Ernest. Global/current DJ notes now preserve
  observed_final_verse_end_seconds=149, observed_rewind_seconds=159 and
  recommended_blend_out_seconds=150. Prefer beginning around 2:29–2:30 and
  handing off before the rewind when practical; advisory, no mandatory end.
- Current Astra chooses the next matching eight-beat pattern after the verse,
  retaining Club Mix's existing source0 entry: Jadakiss fades **2:33.174–2:38.469**.
  Club Mix starts at mix **18:19.589**. Its body, mandatory skit skip and ending
  are unchanged. These plan-specific exits are not new global exclusions.

Both revised handoffs passed short muted original-source Mixxx tests (maximum
observed source-position errors 65.2ms and 73.8ms); all decks stopped and master
volume restored. Full plan dry-run, phase/exclusion checks and original hashes
pass. Named plan is fresh. No audio export or full-set listening approval is
claimed; the previous loading fix and all-source preflight remain installed.
Current plan-local full_track/trusted-ride hints for these two outros were
removed so they cannot contradict the new explicit performance timing.


## Jadakiss EOF fix and K-Dot verse observation (2026-09-21)

The Astra run stopped while loading Jadakiss after K-Dot. Reproduced the exact
mismatch: planned endpoint 183.827951563s versus Mixxx 183.826666666s; 1.285 ms
exceeded the old 1 ms check. Rust accepts at most 5 ms of endpoint rounding while
clamping the actual source guard to decoded EOF. It never extends a declared
cutoff, accepts a larger overrun, or shortens a rhythmic instrumental loop.
Errors identify clip/path and both lengths. Guards are installed after cue
recall settles, fixing a reload timing issue caught in the integration check.

The supervisor runs Rust `perform --preflight-only` on every original before
playback or a new recording. Every segment/support loop is checked, including
repeated uses of one source. Performance still revalidates each actual load.
All nine Astra originals / twelve live clips passed Mixxx preflight. A muted
16.68-second Jadakiss-tail → Club Mix performance passed at the formerly rejected
EOF, max observed position error 50.7 ms; all decks stopped and master volume
restored. Release executor rebuilt; same run_mix.sh command and --record work.
Full-set replay after this fix remains untested.

K-Dot — Who Shot Ya (Freestyle), Training Day: human-confirmed final verse ends
at source 2:31 (151s). Saved observed_final_verse_end_seconds=151 in its global DJ
note and current override, plus AGENTS and verse-respect story. This is a firm
observation offering an optional blend-out point, not a mandatory cutoff. Later
audio remains allowed. Musical timing is unchanged; the named plan was recompiled
and is fresh after the note update. Read global notes even with older overrides.

Regression tests cover the exact discrepancy, larger-overrun rejection, bounded
guards/seeks, unchanged rhythmic-loop length, preflight failure before recording
or performance, and observation-versus-cutoff semantics. 136 Python tests passed;
Rust formatting, Clippy and workspace tests passed.


## Native source performance replaces master playback (2026-09-21)

Ernest rejected rendered-master playback and prepared-track live substitutes:
DJ effects must occur while original music plays. `mix_plan.json.performance`
now holds the shared musical decisions; 52 compiled events execute nine original
sources plus instrumental covers through Rust + Mixxx rate/EQ/loops/faders.
Same run_mix.sh command. Offline export is optional and cannot rewrite live
execution. See docs/SHARED_PERFORMANCE.md (SHARED_PERFORMANCE.md from docs/).
This supersedes the rendered-master/current-audio instructions below.

Astra duration 22:41.995 at 91.68 BPM. Ja Rule enters at mix 7:14.177 from source
0:10; gradual incoming fade reaches full level around source 0:50. DMX's approved
soft-outro fade remains source 134.212–139.185s. The 50 Cent source ends 91.95s,
Jadakiss begins 32s, and album/Ja Rule/Club Mix exclusions remain enforced.
Global Ja Rule/Jadakiss notes now also encode mandatory_start_seconds=10/32.
The supporting instrumental covers DMX and 50 Cent and fades into Ja Rule.

Verified: synthetic three-deck native playback including loop and source skip;
39-second muted real-source four-deck run (instrumental, DMX, 50 Cent, Ja Rule),
maximum observed source-position error 66.3 ms; all decks stopped and master
volume restored. Numerical source alignment is NOT a human listening verdict.
A complete 22:42 live listening pass remains pending. No new Mixxx audio-engine
feature or live vocal extraction was necessary.

Reusable modules: shared/performance.py; brain/performance_cli.py and
brain/audio_patterns.py; hands/performance_validation.py, performance_runner.py,
offline_mix.py; core-rust/clawdj/src/performance.rs. Rust is the timed executor;
Python validates/setup/restores; Mixxx owns live DSP. Generic Build refuses to
overwrite authored performances. Source hashes and allowed-region loops guard
original playback; no required prepared audio. Optional export verified on
synthetic sources without changing its live plan; temporary files removed.

PDD: accepted intent/story and matching builder prompt updated. Read-only intent
planning was run; no remote/paid architecture generation or sync is claimed.
Ernest authorized committing the relevant implementation, tests, prompts and
documentation locally on the feature branch. No push requested.

Cleanup: removed 424,588,521 bytes of obsolete WAV/MP3, recipe/package scripts
and generated reports. The external current directory retains README.md and
compact analysis-evidence.json only; no current listening render is required.
Ctrl-C was exercised during muted playback: Rust exited, all four decks stopped,
and master volume restored. Rust formatting, warning-free Clippy and 27 tests
passed; Python runner/plan/constraint/export checks passed. No full-set listening
acceptance is claimed.



**Resume from the latest dated summary at the top of `../PROGRESS.md`.**
This file includes historical decisions. The September 21 and September 20 song requirements
below supersede earlier timing values, and the live active-plan state must be
checked before editing or rebuilding. New sessions use these saved documents;
they do not need this chat transcript or another harness's private memory.

Written 2026-07-11 mid-hackathon so work can resume on a different machine
(Linux desktop) with full context. See also [HACKATHON.md](HACKATHON.md)
(event rules/links) and [ARCHITECTURE.md](ARCHITECTURE.md) (system design).

## Ja Rule entry note and execution-mode discussion (2026-09-21)

Latest instruction: omit Ja Rule's source 0:00–0:10, including incoming blend
and pre-roll. Verse begins around 0:50; use 0:10–0:50 as available space for a
long, gradual incoming blend. This does not require exactly 40 seconds of
overlap. Saved in the exact Shady Records V.S. The World (Vol. 3) recording's
global note and Astra override, with cue_seconds=10 and trust_cue_seconds;
the mandatory middle skip 209–227s remains. Current master still uses cue 0
and was deliberately not rerendered during the requested discussion. The
artifact is now stale against notes; earlier validation/freshness applies to
the previous brief only. Do not silently bless the old WAV as compliant.

Ernest expected mix_plan.json to execute the actual transitions and asks for
an explanation of the five-event master-playback approach. Current production
uses external performance-plan.json → Python/FFmpeg offline render → WAV/MP3;
the named mix_plan.json only resets, loads, starts, waits, and stops Mixxx.
Discuss this distinction and the live implementation gaps before choosing the
next execution approach. No live conversion or audio revision made here.

## Current DMX outro revision (2026-09-21)

Ernest's observation for DMX — Who Shot Ya (Freestyle), The Early Years
(Bootleg): by source 2:12 the interesting section is essentially over, so one
can start blending into the next track, slowly if useful. This is explicitly
soft guidance, not an exclusion or mandatory end. The exact recording's global
DJ note and current Astra override contain it; no hard-end directive was added.
The DJ style guide preserves the distinction for other harnesses/setups.

The current render starts an eight-beat DMX → 50 Cent fade at source 2:14.212
and finishes at 2:19.185. In the mix this is 6:05.326–6:10.562. Entries from
50 Cent onward move earlier by 32 beats (20.942 seconds), preserving shared
backbeat/pattern and instrumental-loop phase. Other source spans and all
mandatory exclusions remain unchanged. Duration is now 23:13.409; the Club Mix
starts 19:22.416. Use these timings over the older sections below.

Both files fully decode at -16.12 LUFS; true peaks are -1.98 dBTP WAV and
-1.95 dBTP MP3. Source hashes are unchanged, layer reconstruction is exact,
mandatory source boundaries and recipe/master hashes pass, and plan is fresh.
Temporary reconstruction audio was deleted after publishing the verified mix.

Keep the same named plan and `current/Who-Shot-Ya-Astra.wav`, MP3, and player
paths. No new listening version is retained. The local packaging script now
derives displayed duration and layer/compliance metadata from the current
recipe instead of retaining old literal values. Human listening acceptance of
this handoff remains pending.

## Current Astra comparison entry (2026-09-20)

Ernest requests a single current listening copy and no retained output versions.
The cleanup removed ~2.99 GiB of older render packages, temporary audio, and
analysis caches. Preserve original songs, the current plan/notes, the current
WAV/MP3, and small reconstruction scripts/evidence. Update the named plan and
stable export filenames in place for future revisions; remove intermediates
after verification. Historical paths in older sections no longer exist.

The renewed mix request, including the added requirement to follow every
song's relevant DJ notes, now points to the finalized external package:
`~/Music/claw-dj/exports/notorious-big-who-shot-ya-variations-gpt-6-astra/current/`.
Earlier listening editions have been deleted at Ernest's request.
Open index.html for the player/jump points or Who-Shot-Ya-Astra.mp3 directly.
The 24-bit WAV is the same mix, used for master playback. Both audio hashes are
unchanged by cleanup; the relocated recipe/master checks pass.
The current named plan references this master and is not stale. Playback mode
remains explicitly offline rendered master, not nine live source transitions.

All nine source versions remain in the supplied order at91.68BPM; duration is
23:34.351. The DJ-note audit found/fixed a brief exposed instrumental gap by
moving DMX and following foreground entries one eight-beat pattern earlier.
DMX now starts3:44.027 before the original Biggie fade finishes. Jadakiss's
full_track instruction now retains source32s through the decoded file ending
at183.82795156s. The Club Mix's pattern-aligned entry remains19:43.359.
The bed spans DMX and50 Cent; 50 Cent ends source91.95s. Existing album,
Ja Rule, Jadakiss, and Club Mix exclusions are preserved at exact source bounds.

Both delivered files fully decode: -16.12LUFS, WAV peak-1.98dBTP / MP3-1.97dBTP.
Source hashes equal the prior edition. Early/late pattern comparisons for all
nine versions favor the planned alignment over a one-beat-wrong control.
Full-layer PCM reconstruction is exact. Compliance/evidence and production
scripts are beside the exports. No new engine code change or playback occurred.
For review, listen especially at3:44,6:26,7:57,and19:43; collect timestamp plus
issue and make a focused next pass. Numerical evidence is not human acceptance.

## Whole-body instrumental support research (2026-09-20)

Ernest requests a distinct story for highlighting vocals in an existing full
mix while an instrumental supports the whole body. Canonical pair: 50 Cent /
Tony Yayo on WHO SHOT YA (24 Shots) over the supplied Promo VLS instrumental.
Keep the full-mix classification, matching backbeat/pattern, complementary EQ,
and hard 92s source boundary. Same-song support is appropriate here; acapella
pairing and short exposed-bridge preferences are separate contracts.

Read `docs/FULL_MIX_INSTRUMENTAL_LAYERING.md` and
`user_stories/story__when_i_highlight_vocals_in_a_full_mix_i_keep_an_instrumental_underneath.md`.
They contain primary-source research, a concrete Mixxx control/deck design,
future negative-test requirements, and a clear current/pending distinction.
Build-prompt source, style guidance, global song notes, and Astra plan notes
carry the intent. General live automation was not implemented in this research
turn; the existing Astra offline render already contains the requested bed.

Independent reconstruction of its two layers in mix 405–475s matches every
premaster sample (maximum error 0.0). Bed coverage spans the complete foreground
source 0–91.95s, mix 391.504–483.863s. In 35–145Hz the combined body is 4.48dB above
original foreground at the same gain; this is not a loudness-matched quality
verdict. The existing causal-lowpass subtraction is not a calibrated low-shelf
cut; do not describe its coefficient as uniform bass attenuation. Audit script
and JSON are in the external Astra package. No audio was changed; current
master/recipe hashes still validate, and the playback artifact is current.

Live implementation needs explicit full-mix/bed pairing, sustained coverage,
independent EQ/levels, live drift/backbeat checks, and ownership-aware deck
allocation/cleanup. A two-deck body is possible; the three-source overlapping
handoffs require a third deck. The existing vocal_over_bed path returns before
normal snare_align handling and is not a complete substitute.

Control calibration finding: local controlapiserver.cpp forwards raw values
via ControlObject::set; built-in EQ manifests use neutral 1.0 while normalized
knob center is 0.5. The runner currently sends 0.5 in EQ reset/restore paths.
Read-only live state confirmed decks 1/2 at 0.5, decks 3/4 at 1.0, all stopped.
Record this as pending calibration work, with tests, before claiming a live
layer recipe works. No user control values were changed during the audit.

## Mandatory 50 Cent source cutoff and Astra correction (2026-09-20)

Ernest identified an abrupt instrumental change around source 1:33 in **50
Cent — WHO SHOT YA, 24 Shots (2003), track 06**. Hard rule for every future
mix and AI harness: **no source audio at or after 1:32 (92 seconds)**, even
under an instrumental overlay. Finish the fade before that time. Exact
recording only. Global notes use `mandatory_end_seconds=92`; both matching
named plans carry it. AGENTS.md and `docs/SOURCE_AUDIO_BOUNDARIES.md` preserve
this knowledge in Git source for other setups; personal SQLite/plan state
remains ignored and must be backed up separately.

Implementation: global mandatory ends survive conflicting overlays;
`build_mix_plan` caps effective duration and reserves complete fades, shortening
by whole bars or rejecting incompatible verified format exits. Before Mixxx
connection, `hands/source_cutoffs.py` rereads global notes, builds lossless
source copies physically ending at the limit, and refuses stale rendered
masters whose recipe violates the boundary or whose recipe/master hashes
mismatch. Generated copies are outside the checkout. Missing encoding tools
fail closed. This protects the standard runner; external players/renderers
still need the explicit source constraint. The idle editor was restarted to
load the changes. No playback was started for this correction.

The corrected Astra export is **23:34.351 at 91.68 BPM** in the same external
`astra-pass-1` directory. 50 Cent ends at source **91.95s**, before rate
conversion. Ja Rule and all later entries move 24 beats earlier; no backbeat
phase changes. The 50 Cent → Ja Rule fade lasts 2.09567s, starting at mix
8:01.767 and ending at 8:03.863; instrumental support continues through the
handoff. Superseded masters are labeled non-playback audit backups. Current
Astra artifact is fresh and hashes match. The other matching named plan is
stale and needs rebuilding after the new note; its musical choices were not
otherwise changed.

Validation: six new cutoff regressions; 137 focused tests pass. Both final
outputs fully decoded; -16.13 LUFS, true peak -1.99 dBTP WAV/-1.94 dBTP MP3;
source exclusions, common-pattern alignment, hashes, and dry-run pass. Broad
suite ran 335 tests with three skips and one unrelated existing collection
schema migration failure, reproduced against unmodified HEAD `86c0f48`.
Local read-only PDD intent planning and prompt backpropagation were performed;
no paid/model-backed PDD generation or live-audio certification is claimed.

## Astra Who Shot Ya first listening pass (2026-09-20)

The current Astra plan is a **23:34 offline rendered edition at 91.68 BPM**.
Its `mix_plan.json` explicitly uses `execution_mode=rendered_master_playback`:
Mixxx plays the completed master; this is not nine live deck transitions.
The artifact is current and its five supported runner events dry-run correctly.
The existing nine-source order is preserved, with Jadakiss before Club Mix.

Read `README.md` in the local Astra export directory before modifying
or rebuilding it. Audio, editable `performance-plan.json`, compiled
`render-plan.json`, scripts, verification evidence, source/output hashes, and
an HTML handoff-jump player are outside the checkout at
`~/Music/claw-dj/exports/notorious-big-who-shot-ya-variations-gpt-6-astra/astra-pass-1/`.
`before/` preserves the pre-pass workspace JSON. A generic Build operation
would replace this edition with a different live performance; reproduce it
using the edition-specific production recipe instead.

The render applies all three skit exclusions and starts Jadakiss at source 32s
without earlier pre-roll. Clean instrumental bridges cover the excisions.
The provided instrumental supports DMX and 50 Cent using an explicit 32-beat
loop, with reduced competing bass and restrained upper-band reinforcement.
The 50 Cent source measures near 92.088 BPM rather than its stored 93; cached
lyrics for it and Club Mix were wrong-song matches and were not used.

Both outputs fully decoded, approximately -16.14 LUFS; true peaks WAV -1.99 /
MP3 -1.94 dBTP. Source interval, phase placement, deliberately wrong one-beat
comparison, and interior-silence checks passed. Existing runner suite: 53 tests
passed. These are technical checks; **Ernest's first listening pass is pending**.
No audible certification or attended live performance is claimed.

Backbeat matching is the primary musical term in AGENTS.md, the story, and the
matching prompt; "snare matching" remains accepted user vocabulary and existing
machine identifiers stay unchanged. No application engine code changed.

Ernest requested keeping generated output outside the universal source repo.
The entire 1.5 GB production package and its mix-specific write-up were moved;
active playback and recipe paths were updated, final audio hashes are unchanged,
and the plan still reports current. The existing plan-state resolver remains
repo-relative. All `brain/data/` state is ignored and currently untracked, but
human notes/approved plans need backups independently of Git.

## The two goals, simultaneously

1. Win the H Company Computer Use Hackathon (SF, 2026-07-11/12) — Computer
   Use track, must use H Company's agent.
2. Seed a longer-running personal project: an autonomous/semi-autonomous DJ
   that mixes like a hip-hop DJ (beat juggling, crate selection, reading a
   crowd), controlling Mixxx.

Both goals point at the same architecture, so there's one codebase.

## Live toolkit, EQ unity, interrupt cleanup (2026-10-03)

`hands/live_kit.py` is now the shared library for live experiments and
hand-built live mixes (see `docs/LIVE_MINI_EXPERIMENTS.md`). Mixxx's deck EQ
unity is 1.0, not 0.5: confirmed live with `parameterN_set_default` on an idle
deck, and the runner now uses `EQ_UNITY`. Interrupted mixes reset filter and EQ.
The enrich test no longer writes real data files. Known gaps still open:
- the plan builder cannot schedule a same-song handoff, a loop-then-drop or a
  third deck;
- the verse guard ignores skip notes;
- the skip math falls back to cue 0.0 when a track's cue is missing.

## Live mini-experiments and same-song re-entry (2026-10-02)

Ernest tries one piece of a mix live with a small flagged script rather than
rebuilding a full plan (`docs/LIVE_MINI_EXPERIMENTS.md`, patterns in
`docs/live_experiments/`). The first kept result is a same-song move: the
*I'm Coming Out* 2:55 reprise on deck 1, the 0:00 intro on deck 2 at grid
beat 368 with a 4-beat blend, then the song with the trumpet solo skipped.

Known gaps this exposed:

- **The plan builder can't express it.** It cannot schedule a same-song
  second-deck re-entry or a third deck, so a liked experiment is recorded in
  DJ notes with its exact flags until it can.
- **Test pollution.** `tests/test_enrich_set.py` writes the real
  `brain/data/phrase_analysis.json` (`enrich_set.PHRASE_OUT`); after a test
  run every cue falls back to 10%.
- **Filter left closed.** `filter_sweep_out` closes the outgoing deck's
  filter, and only the post-transition `filter_reset` reopens it. An
  interrupted mix leaves it closed (seen at `super1` 0.13).
- **EQ unity mismatch.** `reset_instrument` sets EQ bands to 0.5, while
  Mixxx's default/unity is 1.0.

## Build mix plan: whole-set optimizer + model providers (2026-09-30)

Ernest's verdict after the Who Shot Ya three-model mix: keep the Curate and
Create-the-mix GUI (stories added/amended for plan picker, collection
chooser, New music scan, search/add, Archive first + Clear set, preview,
Finalize, enrich log, Candidate playback order), but Build mix plan ignored
backbeat matching in practice and leaned on hard-to-run engines.

What is live now:

- **Ordering** — `brain/mix_order_brief.apply_constraints` calls
  `brain.mix_optimizer.optimize_order` (replaces `greedy_mix_order` there;
  `greedy_mix_order` remains for `/api/mix-order` on Curate). Edge weight =
  `pair_score` + tempo direction − unverified (0.06) / blind (0.10) backbeat
  penalties. Deterministic by track_id.
- **Why backbeat "failed"** — not ordering: blends touching a song with snare
  confidence < 0.15 (`onset_analysis.SNARE_CONFIDENCE_GATE`) silently fell
  back to bar-count alignment. On the R&B set that was 27–28 of 55 blends.
  Now labelled per blend (`play_body.backbeat`), surfaced in the GUI, and
  `enrich_set.remeasure_weak_beat_phase` retries weak reads once on
  harmonic/percussive-separated windows (`agree_on_parity`: ≥2 windows, same
  parity, stored confidence = weakest passing window).
- **Models** — `brain/llm_providers.py`; GUI dropdown fed by
  `GET /api/providers` (cached 60 s). Order engine values: `none` or a
  provider name; `nemoclaw`/`h-agent` map to `none` with a note.
  `brain/mix_llm_refine.py` validates a model's reorder (same songs, opener,
  pairings/regions, no new blind blend, ≤1 new unverified, objective within
  3%). In the first live run Claude's reorder was rejected for adding
  unverified blends — the guardrail working as intended.
- **Removed** — Shuffle opener button, `/api/mix/shuffle-opener`,
  `PlaylistApp.reshuffle_opener`.
- **PDD** — new prompts `llm_providers`, `mix_optimizer`, `mix_llm_refine`
  (+ `.pddrc`, `architecture.json`); `plan_mix_build_Python.prompt` updated.
  Code was hand-written against those prompts, not generated. `pdd intent
  apply` recorded the intent, but its architecture step needs the local
  llama-server (PDD's configured model) and did not run.

### Follow-ups the same day (2026-09-30)

- **Mix to listen = most of each song.** `MixProfile.ride_most_of_song`;
  `build_plan.most_of_song_ride` (intro/first-beat entry, verse-safe exit in
  the last 40%, bar-aligned rounding up, skip-note aware, capped so verse
  extensions cannot pass the song end). `respect_verse_exit` now measures
  from the real ride origin (cue + previous fade + anchor). The Lounge/bar
  preset story is superseded in part.
- **DJ notes authoritative everywhere.** `mix_order_brief.apply_note_endpoints`
  pins `opener_style` first and `full_track` last; refine rejects moving
  them. Plan-notes tests now patch `current_index_path` (they were reading
  the active Elements DB).
- **DJ showcase choreography.** `build_mix_plan.choreograph_showcase` →
  `brain.showcase_moves`; `build_plan(showcase_plan=…)` replaces the flourish
  rotation and may set an `exit_style` (echo_out / filter_drop) only where no
  human note did. Segments carry `showcase_source: model` + `showcase_why`;
  GUI marks them ✦.

## Arrange saved bunches (2026-09-20)

Fixed `brain/web/arrange.js`: a module-level toolbar helper referenced the
initializer's private `state`, crashing all Arrange rendering when a bunch
was enabled. It now receives the selection count explicitly. Transitions
inside bunches also render, preserving the group as one movable unit. Use
Leave bunch or Un-bunch before independently reordering grouped tracks.
Reload the page to pick up the served JS; no mix rebuild or server restart.

The Node runtime regression in `tests/test_plan_frontend.py` reproduces both
pre-fix failures and covers selection/reset, grouped/ungrouped rendering, and
transition visibility. All 24 focused frontend/collection/integration/preview
tests pass with localhost access. Live isolated headless Chrome renders the
active plan's 9 tracks and 8 transitions. Prompt source updated alongside
the repair. PDD CLI help inspected (0.0.310.dev0); model-backed bug/fix/sync
was not run because no remote model call was authorized. This was a local
tested repair, not a claim of PDD regeneration/certification.

## Mandatory Club Mix skip correction (2026-09-20)

Ernest moved the Promo VLS `Who_Shot_Ya (Club Mix)` / `The_Notorious_BIG`
skip start to the empty beat at 3:17 (197s), before the skit around 3:18–3:19.
The existing landing remains 223.7s. Library note and both variation-plan
overlays updated with human attribution. Ending at/after 3:36 is acceptable;
shots are allowed. This is permission, not a forced end or changed skip landing.
Other Club Mix recordings were not changed.

`brain/plan_notes.py` now recognizes `mandatory_skip` in library notes and
appends the latest library skip bounds after conflicting plan tokens so the
planner's last-match parser enforces them. Ordinary optional skips retain
plan precedence. Effective-note reads do not rewrite stored overlays or global
notes. Prompt source updated; new regression fails before the repair and
passes after. 142 foundation/integration/mix-plan/runner tests passed.
This was a local tested repair; no model-backed PDD regeneration was run.
The idle editor was restarted and its live Arrange response confirmed the
mandatory bounds. Existing artifacts are stale and need a rebuild; no live
audio audition or artifact rebuild was performed.

Related human song-note requirements saved on the same date:

- Jadakiss, *Who Shot Ya* (The Champ Is Here Pt. 3): start and blend in at
  0:32 or later, after the DJ rewind, with no earlier pre-roll. Library and
  both variation-plan notes use `cue_seconds=32; trust_cue_seconds`.
- Ja Rule, *Who Shot Ya* (Shady Records V.S. The World Vol. 3): mandatory
  skip 209→227s (3:29→3:47); shots from 3:47 onward are allowed. Library
  and both variation-plan notes use `mandatory_skip` and those skip bounds.

Actual library SQLite and plan-note JSON remain ignored local data, outside
Git. These timing requirements are recorded here for cross-machine continuity;
checking out this commit alone does not install the local note data.

## Who Shot Ya variations (2026-08-31)

Active named plan: `notorious-big-who-shot-ya-variations`. Editorial
lock, not a planner rewrite: Notorious B.I.G. album *Who Shot Ya*
(Ready to Die remaster) opens from 0:00, skips the gun-in-mouth /
victim-squeal skit (`skip_from_seconds=203.5; skip_to_seconds=224.5`,
also in global `dj_notes` for every mix), and blends out on the
chorus. VLS instrumental is not a solo song (`ride_beats=0`) — a
32-beat gentle blend into DMX so beat and vocal play together. Club
Mix sits after the interpolators, not after the album, and skips the
same gun-in-mouth skit (historically 202.0→223.7s; superseded on September 20
by the mandatory 197.0→223.7s skip above).
Ear 2026-09-05: album → instrumental was off by one count (`snare_align`
on the incoming instrumental only — do not full-rebuild this plan on
`feat/snare-align-blends`, auto-align would jump already-good blends).
Ja Rule → Jim Jones and Jim Jones → K-Dot are the gold-standard
same-instrumental blends. Rebuild with `--profile mix-to-listen` only
after auto `snare_align` is gated.

## Anthology and short-form program (2026-08-02)

The long-running product direction is now explicit in
`docs/ANTHOLOGY_AND_SHORT_FORM_PROGRAM.md`. Named multi-plan workspaces are not
only convenient parallel sets: they are the working surface for definitive,
living anthologies in mix form. The initial slate covers the early
Chronic/Doggystyle/Dogg Pound West Coast era, an expanded *2001* sample-lineage
mix, conscious rap, Wu-Tang and its East Coast orbit, Biggie/Shyne, East Coast
jazz-informed hip-hop, the Shiny Suit era, and a researched Drake-season arc.
The standard is an editorial and performed musical argument—lineage, lyrics,
chapters, phrase-aware transitions, cueing, EQ, loops, effects, and human ear
review—not a chronological playlist with automatic crossfades.

Promotion is part of the same lifecycle. Agents are expected to help research
current TikTok/Reels/Shorts conventions and comparable music/DJ performance,
mine recordings for attention-earning transitions and historical revelations,
direct reviewed tools such as OpenCut or Hyperframes where useful, and keep
FFmpeg-based rendering and verification as the deterministic backbone. View
count is the easiest reach measure, not a complete quality measure; compare
retention/completion, rewatches, shares, saves, follows, and anthology
click-through when those metrics are available. Keep variants attributable,
do not infer a universal viral formula from one post, keep generated media out
of Git, and confirmation-gate uploads and all publication.

This is portfolio-level strategy, so it lives in normal repository Markdown
and is linked from `AGENTS.md`. Each anthology itself lives in a named plan.
Future bounded automation—such as cue-sheet clip extraction, campaign
manifests, or metrics ingestion—belongs in the affected PDD `.prompt` and tests
when its observable behavior is concrete; a user story is selective acceptance
coverage, not a substitute for that prompt.

## Mix runner count/EOF invariants (2026-08-03)

`brain/build_mix_plan.py` phase correction must model the executor's actual
anchor: after N `play_body` beat events, `perform_transition` waits for the next
beat, so the anchor is N+1. `hands/run_mix_plan.py` treats remaining audio as a
hard runtime constraint: a body ride reserves the next anchor, the complete
outgoing transition, any in-play skip jump, and four safety beats using live
Mixxx duration and playposition. A clamp preserves the requested mod-4 count.
After a skip, remaining wait is re-clamped against live playposition. If a
ride still hits end-of-track, `wait_for_beats` warns and returns instead of
aborting the set. If a stale artifact still reaches a stopped outgoing deck,
transition execution starts the cued incoming deck and moves the crossfader
instead of aborting the whole set.

Listener-locked `trust_ride_beats` values block planner auto-nudges of ride
length, but the trusted count still defines a planned `phase_anchor` so runtime
can absorb preload/settle jitter without abandoning the 1-2-3-4 target.
Snare lock is a separate move: `snare_align` after Mixxx `beatsync` jumps the
incoming deck one beat. Ticks can lock while kick sits on snare; changing
`ride_beats` or `cue_seconds` by one is the wrong lever. Incoming `snare_align`
in dj_notes, or a high-confidence phase mismatch, emits that move.
Transition beat overrides must enter `build_plan` before previous-fade math;
post-build event patching alone left anchors assuming the default fade while
the runner executed longer human blends (one-count lineage defects on
2026-08-04). For energy holds after a true-synced blend, prefer `settle_bpm`
over midpoint `play_bpm` / `incoming_bpm_target`.

Variable loading and rate-settle time can still make an automatic body's first
counted edge differ from cue arithmetic. Automatic and trusted events therefore
retain a `phase_anchor` targeting the complete modulo-four bar position.

The active `imported-working-mix` build following the latest ear pass keeps
Tell Me at 192 and Keni Burke at 80 with phase anchors, ANL/SO/ATWG at
279/103/111 with anchors 280/168/176 after 64-beat override-aware previous-fade
math, and Around→Tell Me as settle_bpm=96.5 with no incoming_bpm_target. Camp
Lo instrumental remains on beat 101 (`73.237s`). The plan reports current with
56 events; live listening remains the acceptance gate.

## Current-path ordering and flexible control port (2026-07-31)

The recurring “Analyze always leaves exactly one track without a beatgrid” gap
had two reinforcing causes. `brain.enrich_set.status()` correctly treated a
positive tag-derived BPM as enough for ordinary planning, but `run_enrich()`
then used that same status to decide whether to invoke Mixxx—even when phrase
analysis proved no persisted Mixxx `BeatGrid-2.0` existed. Separately, Mixxx
does not commit the final analyzed deck's grid on eject or quit; measured
behavior requires loading a different track. `run_enrich()` now adds
phrase-missing tracks with absent Mixxx grids to its muted-deck analysis
targets regardless of tag BPM, and `brain.analyze_via_mixxx.analyze_tracks()`
performs and verifies a different-track flush after the final successful
target. Regression coverage is in `tests/test_enrich_set.py` and
`tests/test_analyze_via_mixxx.py`.

The standalone runner now follows the active named plan selected in the GUI.
Before 2026-08-02, running `uv run python ./hands/run_mix_plan.py --record`
without `--plan` always opened the legacy `brain/data/mix_plan.json`; this could
record a completely different historical set even though the browser showed a
current named plan. `hands.run_mix_plan.default_plan_path()` now delegates to
`brain.plan_paths.resolve()`, preserving legacy fallback only for an actual
legacy workspace. An explicit `--plan` remains available for archived or
non-active artifacts. If named plans exist but none is active, the runner stops
with a selection/build instruction instead of guessing.

## Multi-plan foundation implementation (2026-07-31)

Architecture entries 1–31 are now materialized under `brain/plan_*.py`,
`brain/api_router.py`, and `brain/api/`, plus `bunch_store.py`,
`transition_overrides.py`, and `order_constraints.py`.
Plans live at `brain/data/plans/<frozen-slug>/`; `active.json` is only a pointer
and listing is always a directory scan. Writes use content-hash optimistic
concurrency and atomic same-directory replacement. Global `tracks.dj_notes`
remain untouched beneath sparse per-plan overrides. Library bunches may overlap,
but enabled bunches in one plan must be disjoint and retain exact internal
order. `plan_mix_build` writes version-3 artifacts with plan/source provenance,
transition attribution, bunch evidence, and the effective Mixxx port; v2 remains
readable. `python -m brain.plan_migration` promotes legacy singleton files
without removing them and is guarded for repeat runs. The stdlib server now
registers plan APIs without changing legacy endpoints; mutations use composite
revision guards and Arrange is one disk-consistent snapshot. `brain.plan_cli`
is the offline agent contract: `note` is track-scoped,
`transition get|set|clear` is transition-scoped, `mark` writes lifecycle, and
`status` reads staleness. Plan-scoped build/start/enrich/refresh retain the
effective Mixxx port. Browser modules 32–35 are now implemented as vanilla ES
modules under `brain/web/`. `plan_client.js` owns revision threading,
structured conflicts, and the one-shot Arrange read; `plan_picker.js` keeps
frozen slugs internal while switching colloquial names above the workflow tabs;
`arrange.js` adds accessible order/bunch/track/journal controls; and
`transition_editor.js` owns sparse human overrides and explicit clearing.
`playlist.html` retains its Curate and Create code and exposes only a refresh
hook after plan switches. The browser never chooses or submits a Mixxx port.
`tests/test_plan_frontend.py` starts a temporary loopback editor server and
verifies HTML, JavaScript MIME responses, and real plan/Arrange GETs; the
top-level suite is 211/211.

## Per-volume music collections (2026-08-06)

The local playlist editor can now switch between independent music volumes
without restarting. `brain/collection_registry.py` keeps a versioned atomic
registry at gitignored `brain/data/collections.json`; it records collection
identity, mount/data/database paths, and the last-used active pointer. The
pointer is deliberately machine-local. The portable identity marker remains
on the collection at `<data-dir>/collection.json`. Startup reads the last-used
choice without prompting, scanning volumes, or creating a replacement
database. If that active volume/database is missing, access fails visibly and
does not fall back to another collection.

`brain.library_index.current_index_path()` is the sole default resolution
boundary. An explicit SQLite path still has absolute precedence for tests,
migrations and portable import/export. An omitted path resolves the active
collection at call time, so a running `PlaylistApp`, enrichment workflow,
DJ-note writer, bunch store, and plan hydration follow an explicit switch.
`brain.scan_library.incremental_scan()` freezes that resolved path once at
scan start; a later switch cannot redirect the in-flight scan, and legacy
crate bootstrap data is never imported into a per-volume database.

The shared lifecycle in `brain.collection` creates or reuses the collection
marker and SQLite, initializes only schema and chosen roots, preserves a
pre-existing local `brain/data/library.sqlite3` as the switchable “Legacy
local library,” and does not scan unless explicitly requested. Its path-only
estimate opens no tags and performs no external calls. CLI and GUI both use
this lifecycle:

```bash
uv run python -m brain.collection list
uv run python -m brain.collection status
uv run python -m brain.collection new /path/to/volume \
  --root /path/to/volume/Music --name "Collection name"
uv run python -m brain.collection new /path/to/volume \
  --root /path/to/volume/Music --scan
uv run python -m brain.collection use <collection-id>
```

On `#curate`, the collection panel lists known/mounted state and keeps the old
Add music folder / Check for new music controls scoped to the active database.
Starting a collection first gets `/api/collections` estimate results, shows
the count/time estimate, and requires browser confirmation. Clearing “Scan
after creating” registers and activates without scanning. A confirmed initial
scan is ordinary local Mutagen metadata ingest only: no lyrics, chroma, Mixxx,
playback or network enrichment is triggered.

The two approved PDD amendments are implemented in the working brownfield
application and the multi-plan graph is now wired through the local server and
offline CLI. `brain.build_mix_plan.compose_mix_plan` always runs the deterministic
mix graph, even with no model or an empty brief. Optional NemoClaw/H Company
responses are constraint interpretation only, invalid/failed responses preserve
the full pool and fall back locally, and H planning uses a non-desktop agent
(cloud web env in text mode — the platform rejects `environments=[]` unless
the agent is a pure orchestrator with subagents) rather than
`brain.agent.Brain` or a local desktop bridge. The playlist editor dry-run now
lists the complete candidate playback order before Start mix.

Port 9995 is now preferred rather than required. `hands.mixxx_control` discovers
only the preferred port and TCP listeners owned by detected Mixxx processes,
then requires the patched JSON `ping` response. `scripts/start.sh` reuses a
validated non-default listener, reports running-Mixxx/no-control-API distinctly,
and passes one effective port into playlist-editor server state. Analyze &
enrich, plan metadata, Start mix, `scripts/run_mix.sh`, and the live runner reuse
that value; explicit overrides remain highest priority. Browser requests no
longer contain their own 9995 default.

## Portable Hermes agent and publishing state (2026-07-23)

The dedicated `clawdj` Hermes agent is now reproducible from a small reviewed
Git kit instead of a full personal-profile export:

- `AGENTS.md` — canonical cross-agent repository rules;
- `agent/hermes-profile/SOUL.md` — TARS/clawdj identity template;
- `agent/hermes-skill/SKILL.md` plus `references/` — operational workflows;
- `agent/pdd-skill/SKILL.md` — PDD intent, brownfield-adoption, approval, and
  evidence workflow backed by the workspace's canonical Monoclaw policy;
- `agent/hermes-skill/scripts/` — deterministic 9:16 teaser rendering;
- `docs/HERMES_AGENT_SETUP.md` — exact new-Mac bootstrap.

This intentionally excludes Hermes history/state databases, caches, logs,
binaries, credentials, personal media, and Mixxx application state. Those are
machine-local and must be installed, transferred, or reauthorized separately.

PDD integration is workflow-ready but does not declare the entire brownfield
repository generated. The workspace router is `../../PDD.md`; canonical policy
is in `../Monoclaw/docs/pdd/`; the executable is the editable fork at
`../PromptDrivenDevelopment/pdd` (remote `InServiceOfX/pdd`). The first
read-only planner classified this repository as conventional brownfield; the
now-characterized multi-plan subsystem is the bounded adopted slice. Its 37
architecture entries have matching `.prompt` sources under `prompts/`, including
dedicated runtime prompts for Mixxx discovery and `scripts/start.sh`, and
`pdd contracts check prompts/ --stories user_stories/` is clean. The current
211-test implementation is the reviewed baseline. Future changes still require
exact intent planning, meaning approval, focused negative tests, and reviewed
sync output. Saying “do PDD” loads this procedure; it is not permission for
whole-project regeneration.

YouTube OAuth is still open work. Ernest is creating the Google Cloud project
and Desktop OAuth client for `https://www.youtube.com/@claw-dj`. Continue from
`agent/hermes-skill/references/youtube-channel-oauth.md`; the currently verified
channel ID is `UClafA-9ft1J1iAKo1JMZmwQ`. The first API upload must be private,
and publication or other public writes require explicit confirmation.

### Synced-lyric timelines (2026-07-13, `brain/lyric_timeline.py`)

First slice of the post-hackathon arc is live. `brain/lyrics.py` now keeps
LRCLIB's `syncedLyrics` (raw LRC with per-line `[mm:ss.xx]` timestamps —
it used to strip them). `brain/lyric_timeline.py` parses the LRC, detects
chorus vs verse by line repetition (choruses recur near-verbatim; ≥3-word
lines repeating ≥2×), splits segments on ≥12s silent gaps (instrumental
breaks), and snaps each vocal onset to the nearest beatgrid bar (4 beats)
via Mixxx's BeatGrid-2.0. Persisted in `lyric_timelines`
(track_id, lrc, segments JSON); wired into `enrich_set` as the `timeline`
step (check-before-fetch; no-synced tracks get an empty row so they aren't
refetched every run). CLI: `uv run python -m brain.lyric_timeline`
(finalized set) / `--show <path substring>` to print a track's map.

Real coverage on the current 24-track set: **17 with full verse/chorus
maps, 7 without synced lyrics on LRCLIB** (fallback plan: whisperX forced
alignment against the plain lyrics, offline). Quality check — 21 Questions
decomposed exactly right: 3 choruses ("Girl, it's easy to love me now") at
32.7/94.6/156.6s, verse onsets at 53.2/115.0s, all bar-snapped with beat
indices. **Verse tour is built and live-validated (2026-07-13,
`brain/build_verse_tour.py`).** Same track loaded on decks 1+2, on-beat
`hard_cut` slams verse→verse, every chorus skipped, freed deck re-cued to
the verse after next. Emits the standard plan schema — `hands.run_mix_plan
--plan brain/data/verse_tour_plan.json` runs it unchanged (only runner
tweak: `wait_for_beats` timeout now scales with ride length, since full
verses outlast the old fixed 90s at slow tempos). Live run: 21 Questions,
3 verses (beats 4/80/176 at 93.1 BPM), both cuts anchored clean, stop_all.
No `sync` in verse cuts on purpose — beatsync's phase-pull would fight the
lyric cue; quantize keeps the slam on grid. Jay-Z "Watcher 2" (Ernest's
target example: Jay/Dre/Rakim verses back to back) is NOT on the drive —
only Dre's "The Watcher"; when the file lands, it's
`uv run python -m brain.build_verse_tour --track "Watcher 2"` after
Mixxx analysis + `brain.lyric_timeline`.

**DB portability Mac→Mac (asked 2026-07-13):** copy
`brain/data/library.sqlite3` into the other clone's `brain/data/` (keep a
backup copy on the USB itself so it travels); macOS mounts the stick at
the same `/Volumes/USB322FD` path so absolute track_ids resolve unchanged
(check `ls /Volumes` for a name collision → "USB322FD 1" breaks paths).
Then one incremental scan regenerates crate/catalog in seconds. Mixxx
beatgrids do NOT travel (they're in that machine's mixxxdb.sqlite) —
import + analyze the finalized set there once; `enrich_set --status`
shows exactly what's missing.

**Hackathon outcome (2026-07-13): FINALIST** — no top-3/NVIDIA prize (PVLA
won). Goal 2 is now the project. NemoClaw/H-agent engines stay while the
free credits last, but are no longer required. Focus per Ernest:
**transitions and mix quality** (songs are already chosen). Agreed next
arc: keep LRCLIB *synced* lyrics (the fetcher strips timestamps today) →
chorus/verse detection from line repetition, snapped to beatgrids →
"verse tour" plan technique (same track on both decks, cut verse-to-verse,
skip choruses; test case: Jay-Z "Watcher 2" — Dre/Jay/Rakim verses back to
back) → offline transition-preview rendering → generic OpenAI-compatible
LLM engine (covers xAI + local models + hermes with one client) → Rust
(core-rust) gesture executor for sub-beat cuts/juggles. Database stays
SQLite; cross-machine portability = relative-path identity + per-machine
roots (optionally ship the sqlite file on the USB), not PostgreSQL.

## Repos

- **`claw-dj`** (this repo) — `git@github.com:InServiceOfX/claw-dj.git`.
  Work happens on feature branches (`master` gets fast-forward-merged by
  Ernest after review — check `git log --oneline` for the current tip, not
  a specific branch name; branch names here will go stale as work continues).
- **`holo-desktop-cli`** — `https://github.com/hcompai/holo-desktop-cli`,
  cloned locally at `repos/holo-desktop-cli` on the Mac this was built on
  (and later on Linux, where its managed runtime turned out not to work).
  H Company's open-source client drives the closed-source
  `hai-agent-runtime` binary over loopback. `claw-dj` no longer uses it on
  Linux; `brain/agent.py` imports `hai_agents`/`hai_agents_local` directly.
- **`Monoclaw`** — private repo, `InServiceOfX/Monoclaw`. Contains an
  **earlier, more advanced attempt at this exact project** under
  `Projects/clawdj/` (2026-04-25 through 2026-07-08, branches
  `feat/clawdj-mixxx-harness` / `feat/clawdj-core-rust-skeleton`, later
  merged to `master`). Ported wholesale into this repo on 2026-07-11 — see
  the next section. Monoclaw's copy is intentionally left to go stale;
  don't look there for the current state, look here.

## holo-desktop-cli vs the `hai_agents.Client()` SDK — ended up needing both

An H Company engineer's first answer to "how do I do local desktop control"
was this SDK snippet:

```python
from hai_agents import Client
client = Client()
agent = client.agents.create_agent(
    name="local-desktop",
    environments=[{"id": "my-laptop", "kind": "desktop", "host": "user_device"}],
)
```

A second H Company engineer pointed at `holo-desktop-cli` instead. Both are
legitimate paths to local-desktop control, so the first macOS build used
`holo-desktop-cli`: `holo run "task"` one-liners, `holo doctor` for setup,
and a documented Python API (`holo_desktop.agent_client`).

On Linux, the SDK path became mandatory. `holo-desktop-cli`'s managed
runtime binary is not published for Linux, while `hai-agents[desktop]`
provides a pure-Python local bridge. `brain/agent.py` now follows the SDK
pattern directly; this is the only path confirmed working on this machine.
Keep holo in mind as a possible macOS/Windows path.

Also learned: H Company's computer-use agent is a screenshot →
vision-model → click/type/scroll loop with multi-second latency per action
(confirmed via `hub.hcompany.ai/computer-use-agents/introduction` and the
`computer-use-agents-demos` repo before building anything). That's fine for
judgment calls and visible GUI actions, hopeless for beat-accurate DJ
timing — hence the brain/hands split in ARCHITECTURE.md.

## Ported prior work from Monoclaw (2026-07-11)

While starting on `hands/mixxx_mapping/` (see "known gaps" below, as it
stood before this port), a stray `clawdj.midi.xml`/`.js` was found already
installed in Mixxx's controllers directory, dated April — from an earlier,
separate effort in a different repo (`Monoclaw`, private,
`Projects/clawdj/`) that got substantially further than today's session had
independently: a working Rust core (`cargo fmt`/`test`/`clippy` clean), a
proven Mixxx-integration design, a Python MIDI bridge, and real research
confirming stock Mixxx has no TCP/HTTP/WebSocket API (only the MIDI/JS
controller-mapping surface). Decision: **port it all into `claw-dj` rather
than rebuild it, let Monoclaw's copy go stale.**

What moved, and where:

| From Monoclaw (`Projects/clawdj/`) | To `claw-dj` |
| --- | --- |
| `core-rust/` (Rust workspace: `clawdj` lib + `clawdj-cli` binary) | `core-rust/` — builds, tests (5/5) and runs clean on this machine, verified 2026-07-11 |
| `agent/midi_bridge.py`, `agent/hermes-skill/SKILL.md` | `agent/` — Python MIDI bridge using `mido`, and a Hermes agent-skill definition |
| `mixxx-mapping/clawdj.midi.xml`, `.js` | `hands/mixxx_mapping/` — the actual mapping (replaces the empty placeholder), reinstalled over the stale April copy |
| `scripts/install-mapping-macos.sh` | `hands/mixxx_mapping/install-mapping-macos.sh` — path fixed for its new location |
| `docs/*.md`, `planning/*.md`, `research/*.md` | `docs/prior-research/` — see its own README for what's there and what was deliberately left out (personal-narrative files, one example path scrubbed) |

**This surfaced a real compliance question for the hackathon rule "build
entirely during the event, no prior commits to the repo"** — this code
predates the event (some of it by months). Ernest made the call explicitly:
port it in anyway, Monoclaw can go stale. Worth being able to explain this
choice if asked during judging.

**Two "hands" implementations now coexist and are not yet reconciled:**
this repo's own `hands/midi_engine.py` (written today, uses a made-up
note/CC map) and the ported, more complete `agent/midi_bridge.py` +
`core-rust/` (real note/CC map matching the actual installed mapping,
already has volume/rate/EQ control `hands/midi_engine.py` doesn't). Next
session should pick one — most likely retire `hands/midi_engine.py` in
favor of the ported code — rather than maintaining both. Not done yet
because it wasn't clear which direction was wanted until this port
happened.

**DONE 2026-07-11 (evening, Linux laptop): the end-to-end MIDI loop is
closed.** The validation the prior effort never reached (April and July
both stalled at "ready to test") now passes: a Note On / CC sent from
Python arrives in Mixxx, runs `clawdj.scripts.js`, and changes the live
engine — verified by reading `[Master],crossfader` over the control API
before (0) and after (1) sending `cc 0x00 127`. Notes on how, because the
Linux setup differs from the macOS IAC design:

- **Linux has no IAC driver; some process must own the virtual ALSA port.**
  `mido.open_output("clawdj", virtual=True)` creates it; when that process
  dies the port vanishes and Mixxx loses the device (restart Mixxx after
  recreating it — PortMidi only scans at startup). `hands/midi_port_server.py`
  is that owner: it holds the port and relays commands written to
  `/tmp/clawdj.fifo` (`note 2` = play deck 1, `cc 0 64` = crossfader
  center). `agent/midi_bridge.py`'s `mido.open_output(name)` (no
  `virtual=True`) is the macOS model and can't create the port on Linux —
  send through the port owner instead.
- **No GUI clicking needed to enable the controller.** Mixxx reads two
  config entries from `~/.mixxx/mixxx.cfg` (written while Mixxx is not
  running; it saves config only on clean quit, not SIGTERM):
  `[Controller]\nclawdj 1` and `[ControllerPreset]\nclawdj clawdj.midi.xml`.
  Device name is whatever PortMidi reports (here exactly `clawdj`),
  sanitized spaces→underscores (`controllermanager.cpp`).
- **Run the patched Mixxx** (fork at `repos/mixxxes/mixxx`, built in
  `BuildGcc/`, binary verified) as
  `./mixxx --developer --controller-debug --control-api-port 9995`; log
  should show `[clawdj] init: clawdj mapping loaded`. The control API
  (`hands/mixxx_control.py` client) is the readback/deterministic-action
  channel; MIDI stays the beat-accurate channel.
- Deck `play` won't hold 1 while the deck is empty — load a track first
  (control API `load` op) before using play for validation.
- **Build note for this laptop (16 cores, 15 GiB RAM):** never `make -j16`
  in `BuildGcc` — RelWithDebInfo link jobs OOM-freeze the machine (that
  caused the 2026-07-11 freeze). Use `nice -n19 make -j4`. The `mixxx`
  binary is already built; only `mixxx-test` was never finished (not
  needed).

## Environment setup on a new machine

### 1a. macOS / Windows: `holo-desktop-cli`

```bash
git clone https://github.com/hcompai/holo-desktop-cli
cd holo-desktop-cli
make setup        # uv sync --all-groups + pre-commit hooks
make install-dev   # uv tool install --editable . --force -> global `holo` command
holo login          # opens browser to portal.hcompany.ai — use the SAME account
                     # that has the hackathon's hk-... API key on platform.hcompany.ai
holo doctor         # checks binary/login/permissions
```

**Platform-specific gotchas found on macOS, unverified on Linux:**

- macOS: the runtime needs Accessibility + Screen Recording granted in
  System Settings → Privacy & Security, and a restart after granting.
  `holo doctor` can't query these automatically, only reminds you.
- macOS `mixxxdb.sqlite` lives at
  `~/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/mixxxdb.sqlite`
  (Mixxx is sandboxed there, not directly under `~/Library/Application
  Support/`). On Linux it should be the simpler `~/.mixxx/mixxxdb.sqlite` —
  `shared/mixxx_db.py` already has both as candidate paths, but the Linux
  path is unverified, confirm it there.
- The double-Esc kill switch relies on a global key listener; per holo's own
  README, **Wayland has no global key listener** — use `holo stop` bound to
  a compositor hotkey instead.
- Watch for focus-stealing: in this session, other apps popping to the
  front (a stray permission dialog, the user nudging the mouse mid-run)
  repeatedly caused the agent to click the wrong app's menu bar. Worth
  keeping hands off the mouse/keyboard while a `holo run` is active.

### 1b. Linux: `hai-agents[desktop]`

`holo-desktop-cli` itself installs on Linux, but its closed-source
`hai-agent-runtime` binary has no published Linux x86_64 build as of v0.0.2.
The supported alternative from H Company's local-control docs is the
pure-Python desktop bridge used by `brain/agent.py`:

```bash
pip install "hai-agents[cli,desktop]"  # [cli] supplies the hai command
hai login                              # writes ~/.config/hai/.env
hai whoami
sudo apt install gnome-screenshot      # required by pyautogui on GNOME/X11
```

`holo login` and `hai login` are easy to conflate: they authenticate
different H Company products and write different keys (`~/.holo/.env` and
`~/.config/hai/.env`). A key valid for one may return 403 for the other. If
Agent Platform calls return an explicit-deny 403, try a freshly generated
key from `platform.hcompany.ai`; when escalating, include the request ID,
timestamp, and endpoint.

Creating an agent is not idempotent: a duplicate name returns 409.
`brain/agent.py` handles this by fetching the existing agent. A session can
also stall before dispatching any local command, so the Brain defaults to a
180-second timeout rather than hanging forever.

Confirmed environment: Ubuntu/GNOME on X11. Without `gnome-screenshot`,
observations silently fail and the agent runs blind. The model may also try
`hotkey("super")`, which pyautogui does not recognize; prompts that use
direct clicks instead are more reliable. Wayland remains unverified.

### 2. `claw-dj`

```bash
git clone git@github.com:InServiceOfX/claw-dj.git
cd claw-dj
uv venv --python 3.13
uv sync   # installs hai-agents[desktop], mido, python-rtmidi, and mutagen
```

### 3. Mixxx

Install Mixxx (mixxx.org) for real — needed for both the GUI the Brain
drives and the analyzed-track database Hands reads BPM/key from.

### 4. Music library

The demo crate was built from a real drive: `/Volumes/USB322FD/Music/HipHop`
(a Mac-specific mount path — irrelevant on Linux). None of that data is
committed (see below), so on a new machine:

```bash
uv run python -m brain.scan_library /path/to/your/music
uv run python -m brain.build_demo_subset   # edit the artist/filter criteria
                                             # in brain/build_demo_subset.py
                                             # first if the crate differs
```

## What's built so far

| File | Purpose |
| --- | --- |
| `docs/ARCHITECTURE.md` | Brain/Hands design, MVP cut-list, judging-criteria mapping |
| `brain/agent.py` | `Brain` class — registers/reuses a `hai-agents` desktop agent and drives Mixxx through `hai_agents_local` (confirmed on Linux/X11) |
| `brain/library.py` | `Track`/`Energy` types, `CRATE` loaded from `brain/data/crate.json` |
| `brain/scan_library.py` | Scans one or more music directories' ID3 tags (mutagen) into the crate cache |
| `brain/sync_mixxx_analysis.py` | Merges Mixxx's analyzed bpm/key (read from its own DB) into the crate cache |
| `brain/build_demo_subset.py` | Picks a curated subset from the crate, writes `.m3u` for one-shot Mixxx import |
| `hands/audition_transition.py` | Live audition of one built transition in Mixxx (lead-in from the plan's `phase_anchor`, the full runner's own transition code, short tail); CLI + Arrange "Audition in Mixxx" / Previous / Next / Replay / Stop. Replaces the deprecated `brain/preview_transitions.py` render |
| `brain/build_lineage_set.py` | Builds the sample-lineage playlist from canonical hip-hop/RnB tracks in the crate |
| `brain/analyze_bpm.py` / `brain/analyze_via_mixxx.py` | Provisional librosa BPM analysis and deterministic Mixxx analysis for the lineage set |
| `brain/playlist_editor.py` | Local browser UI for searching the crate, enabling/disabling tracks, applying the researched R&B/West Coast hit seed, exporting a Mixxx playlist without dropping BPM/key metadata, "Ask the DJ brain", post-finalize **Create the mix** (profile + brief → plan → confirmed live start), and **in-tab preview** via native `<audio>` + `GET /api/preview` (not Mixxx) |
| `brain/mix_profiles.py` | Named mix-feel presets + free-text brief → profile overrides |
| `brain/dj_formats.py` | Versioned expert transition grammars, strict phrase requirements, and format provenance |
| `brain/mix_order_brief.py` | Free-text order intent → agent constraints → greedy + forced adjacency/regions |
| `brain/build_mix_plan.py` | Continuous mix plan builder; `compose_mix_plan` / `plan_summary` shared by CLI and editor |
| `brain/playlist.py` | Playlist selection persistence, normalized seed matching, and JSON/`.m3u8` export logic |
| `brain/quick_mix.py` | H-agent-optional six-track sample-lineage planner and live Mixxx quick-mix runner |
| `hands/beatgrid.py` | Reads bpm from Mixxx's DB for a given track path (schema confirmed against a real install) |
| `hands/midi_engine.py` | MIDI execution stub via `python-rtmidi`, made-up note/CC map — **superseded by the ported code below, not yet retired** |
| `hands/midi_port_server.py` | Owns Linux's virtual `clawdj` ALSA MIDI port and relays FIFO commands |
| `hands/mixxx_control.py` / `hands/transition.py` | Client and beat-anchored transition engine for the patched Mixxx JSON control API |
| `hands/mixxx_mapping/` | Real mapping (`clawdj.midi.xml`/`.js`) — **live-validated 2026-07-11**: enabled in Mixxx, commands audibly move decks, beat-tick feedback flows back |
| `core-rust/` | Rust workspace (`clawdj` lib + `clawdj-cli`) — commands, queue, **plus the real-time layer** (`live.rs`): `BeatClock` reads Mixxx's live beat ticks, `clawdj monitor` shows live BPM, `clawdj transition --from 1 --to 2 --beats 16` does a measured-BPM, beat-anchored smoothstep crossfade (validated live: measured 91.47 BPM, 10.5s fade = exactly 16 beats) |
| `brain/set_player.py` | Short-set orchestrator with agent, manual, or control-API loading and MIDI or control-API transitions; BPM-chained set planning |
| `agent/midi_bridge.py` | Ported Python MIDI bridge (`mido`-based), matches the real mapping's note/CC map |
| `agent/hermes-skill/SKILL.md` | Ported Hermes agent-skill definition for a dedicated clawdj dev session |
| `shared/commands.py` | Brain→Hands command schema (intent only, no MIDI/timing) — not yet wired to either MIDI implementation |
| `shared/mixxx_db.py` | Locates + read-only-opens `mixxxdb.sqlite` across platforms |

`brain/data/` (scanned crate, demo subset, `.m3u`) is **gitignored on
purpose** — it's derived from a personal media library with scene-rip-style
folder naming (`.torrent` files, "by Hillside" tags were spotted in the
source directory), not something to commit to a public hackathon repo.
Regenerate it locally with the scripts above.

The hackathon-length live path is documented in `docs/QUICK_MIX_DEMO.md`.
It was validated on 2026-07-11 with one on-beat lineage cut and four
beat-synced blends across six tracks; the final deck stopped cleanly.

## Demo subset — analyzed, real BPM/key in hand

Criteria chosen this session: **Snoop Dogg-centric, ~30 tracks, studio
albums only** (excludes mixtapes/soundtracks/promo singles/interludes/skits;
includes both `Snoop Dogg` and `Snoop Doggy Dogg` ID3 artist tags since
early albums are tagged with his original stage name). Generated via
`brain/build_demo_subset.py`, output at `brain/data/demo_set.{json,m3u}`
(gitignored — rerun the script to regenerate).

**Status: done.** Three `holo run` attempts at driving Mixxx failed —
first from losing window focus to other apps mid-task, then from a wrong
UI target (the agent, and an early version of these instructions, assumed
File → Import Playlist; Mixxx's actual path is **right-click "Playlists"
in the sidebar → Import Playlist**, confirmed against the official manual:
https://manual.mixxx.org/2.3/en/chapters/library.html). Given the repeated
failures, Ernest did the import + select-all + right-click → Analyze by
hand instead — a couple of clicks, faster than debugging the agent further.
`brain/sync_mixxx_analysis.py` confirmed all 30/30 demo-subset tracks now
have real bpm/key (e.g. "Gin And Juice" 94.62 BPM / Bbm, "Drop It Like
It's Hot" 92 BPM / Cm).

**Lesson for next time a playlist needs importing:** tell `holo` to
right-click "Playlists" in the sidebar directly, don't send it hunting
through menus.

**One thing to sanity-check before relying on it for beat-juggling:**
"Don Doggy" (149 BPM) and "Trust Me" (~160 BPM) look like they might be
double-time detections (Mixxx's beat detector sometimes locks onto 2x/0.5x
the real tempo on hip-hop/rap) rather than the track's actual BPM — worth
eyeballing against the actual songs before scheduling beat-accurate moves
against them.

## Live-validated 2026-07-11 (the loop is closed)

The gap that stalled the April and July prior efforts is done: mapping
enabled in Mixxx (`[clawdj] init` in its log), `clawdj cmd play` audibly
started a deck, `clawdj demo-juggle` beat-juggled two copies of "Drop It
Like It's Hot", and the new real-time layer measured live BPM off Mixxx's
beat-tick feedback and executed a beat-anchored 16-beat crossfade
(measured 91.47 BPM → 10.5s fade, exactly right). Two operational gotchas
worth knowing:

- A deck parked at end-of-track accepts `play` but emits no beats — send
  `cue` first (set_player does this).
- The demo-* subcommands originally created a *new* virtual MIDI port and
  demanded a Mixxx restart; fixed to attach to the live port instead
  (commit `a282541`). Don't reintroduce `create_virtual` on macOS.
- One real-world false alarm: "deck 2 is silent" turned out to be **Mixxx
  audio routing**, not the bridge or mapping. `Preferences -> Sound
  Hardware` fixed it. On a new machine, verify master/headphone outputs and
  deck routing early before debugging MIDI, crossfader logic, or deck-2
  commands.
- See `docs/MIX_TWO_TRACKS.md` for the shortest attended runbook (commands
  only, no explanation) when you just need a live transition working fast.

**holo can load a track through Mixxx's real GUI — confirmed working,
unattended.** Backgrounded task: told holo to open the `demo_set` playlist,
pick a track, and load it into deck 2. It took ~15 steps and repeatedly
misclicked the dock (opened Terminal/other apps instead of Mixxx — the dock
icon is unreliable, always click the Mixxx window itself instead) and had
to cancel a stray Controller Setup dialog that grabbed focus, but it
self-corrected every time and finished correctly: right-click a track ->
"Load to" -> "Deck" -> "Deck 2" (three nested submenus), loaded "Press
Play" by Snoop Dogg (85 BPM, key C) into deck 2, and accurately reported
what it did. `brain/set_player.py`'s `LOAD_TASK` prompt now states this
exact menu path explicitly rather than leaving holo to discover it, which
should cut the step count. Net takeaway: holo's GUI actions work, just
budget real wall-clock time and expect some flailing before it lands —
don't read early misclicks as failure, let it keep going unless it's
genuinely stuck (bouncing between the same 2-3 wrong targets 5+ times).

## Patched Mixxx on the Mac (2026-07-12) — control API live, default app

The patched Mixxx (fork branch `localhost-control-api` at
`repos/mixxxes/mixxx`, Mixxx 2.7.0-alpha base) is now built natively for
arm64 and installed as **the default `/Applications/Mixxx.app`**; stock
2.5.3 is kept at `/Applications/Mixxx-stock.app`. Verified end-to-end:
`hands.mixxx_control.MixxxControl` get/set round-trips against the live app
on port 9995. Launch it as:

```bash
open -a /Applications/Mixxx.app --args --control-api-port 9995
```

Build notes (all verified on this MacBook Pro M5, macOS 26):

- `source tools/macos_buildenv.sh setup` with `BUILDENV_RELEASE=1`, then
  cmake with the CI's arm64 args (`-DMACOS_BUNDLE=ON -DQML=ON` etc.,
  triplet `arm64-osx-min1100-release`) and `cmake --build`. Do NOT call
  `tools/macos_release_buildenv.sh` directly — it's CI-only and exits.
  Full build ≈ 25 min on 10 cores; deps zip auto-downloads during configure.
- The build-tree `Mixxx.app` is NOT self-contained; run
  `cmake --install . --prefix stage` to get the bundled, ad-hoc-signed app.
- **macOS gotcha that cost an hour:** Mixxx's bundle is App-Sandboxed, and
  without `com.apple.security.network.server` in the entitlements the
  control API's listen() dies with "Unknown error" (EPERM) — port never
  opens even though `--control-api-port` parses fine. Fixed in fork commit
  `722eac1bce` (entitlement added + re-sign). Also: `--` is illegal inside
  XML comments; codesign rejects the whole entitlements file with a cryptic
  AMFIUnserializeXML error.
- Because the app is sandboxed, it uses the **container** settings/DB
  (`~/Library/Containers/org.mixxx.mixxx/...`) — same data stock used, so
  the analyzed library and clawdj mapping carried over with zero work. The
  2.7 first launch upgraded that DB's schema in place; a pristine
  pre-upgrade copy sits at `~/Library/Application Support/Mixxx` if stock
  2.5.3 ever balks at the upgraded container DB.

Production demo assets (2026-07-12, all `brain/data/`, gitignored): 58-track
curated set (brief: "Hip-hop and RnB hits that mix well together in a DJ
showcase"), all tracks Mixxx-analyzed, phrase analysis done, 57-transition
~39-minute mix plan built, `hands.run_mix_plan --dry-run` passes (176
events). **First live run 2026-07-12: 103/176 events through the HomePod
before Ernest stopped it (sounding great).** Output chain: Mac + Mixxx both
on the Office HomePod via AirPlay ("AirPlay" CoreAudio device; constant
~2s latency, harmless to the beat-anchored mix, waveforms just lead audio).

DJ-craft feedback from that run, now encoded as defaults (Ernest,
2026-07-12):

- **Tempo direction**: keep energy up — equal-or-slightly-faster transitions
  preferred, at most 2 consecutive slow-downs (`mix_graph.greedy_mix_order`,
  `max_consecutive_slowdowns`). Observed live failure mode: beatsync chained
  track 1's 101 BPM through the entire set; `run_mix_plan.settle_rate` now
  glides each landed track back to native tempo (keylock on) so tempo
  direction is audible.
- **Entry points**: don't open every track from its intro — default to a
  high-energy body phrase (chorus/first verse; `phrase_analysis` now emits
  `intro`/`body` candidates, no 90s cue cap), with roughly every 4th slot
  taking the intro for texture (`build_mix_plan.cue_fields`). Latest plan:
  46 body entries / 12 intro entries.
- **Genre continuity**: dramatic genre switches are a statement, used
  sparingly — same-artist/same-genre transitions get a bonus, an *unbacked*
  cross-genre jump pays a toll plus a cooldown in the greedy tour. A jump is
  "earned" (exempt) when sample lineage or chromagram texture backs it
  (`mix_graph.genre_of`/`load_chroma_pairs`; chroma coverage is currently
  just the 12-track lineage set — extend with `clawdj chroma`).
- **Sample lineage is the foundation**: a researched sample/cover edge
  floors the pair score at 0.92, nearly overriding everything — mixing the
  original into the song that samples it (across genres) is the showcase.
  **`mix_lineage.json` was pruned 40 → 10 edges**: the agent-researched file
  had padded real samples with "era pairing"/"continuum" vibes (that fake
  lineage is exactly what made Beautiful→Bernard Wright look backed — Ernest
  heard it as jarring, and the data was the bug). Same-artist/genre bonuses
  now cover what the soft edges faked. Three originals found on the drive
  and added to the set: Marvin Gaye "T Plays It Cool" (→ Erick Sermon
  "Music"), Isaac Hayes "A Few More Kisses To Go" (→ Ain't No Fun), James
  Brown "Papa Don't Take No Mess" (→ That's the Way Love Goes) — all three
  place adjacent at the 0.92 floor. Remaining lineage edges cite originals
  not on the drive (verify "Beautiful ↔ Mr. Lonely" with a real
  whosampled-style lookup sometime; it smells like more agent hallucination).
- **Segment variety**: rides are no longer uniform — slot rotation gives
  1/2/3-phrase segments (opener gets 2; a confident phrase pick earns an
  extra), so key parts play out while staying showcase-length.
- `brain.analyze_via_mixxx` fix: eject + wait for bpm to drop before each
  load — the deck's stale bpm otherwise satisfies the wait instantly and
  every track after the first silently skips analysis. Mixxx flushes
  analysis to the DB lazily (sometimes ~a minute after eject) — re-run
  `sync_mixxx_analysis` if bpm comes back None right after analyzing.

## NemoClaw (Nvidia challenge) status

Source-installed on the Mac from `repos/NemoClaw` (`npm install` →
`nemoclaw v0.0.80` linked on PATH). Integration path researched and
documented in `docs/LINUX_PORT.md` §5: serve H Company's open-weight
Holo3 via vLLM on the NVIDIA box, `nemoclaw onboard` with the
"Other OpenAI-compatible endpoint" provider → the sandboxed agent runs on
H Company models through NemoClaw's routed inference. Onboarding is an
interactive wizard — run with Ernest present. `holo install nemoclaw`
(sandbox bridge MCP) is the optional extra leg, untested.

## Known gaps / next steps, roughly in priority order

00. **Confirm the live transition audition by ear, then delete the render
    (2026-10-14).** `hands/audition_transition.py` / Arrange "Audition in
    Mixxx" replaces `brain/preview_transitions.py` (deprecated, kept until
    Ernest confirms). Listen for: lead-in lands on the planned bar, snare_align
    transitions lock, play_bpm holds sound like the full mix.
0. **Gentle faders: one path still unchecked (2026-10-03).** The live toolkit,
   the normal runner and the plan builder now refuse blends faster than 16
   counts (`shared/gentle_faders.py`, story
   `story__blend_with_gentle_faders_never_fast.md`). The explicit-performance
   path (`execution_mode=live_source_tracks`, Rust `clawdj perform`, clip
   `fade_in`/`fade_out` in seconds) is **not** checked yet. Its smoothstep
   gain envelopes and 2-beat loop edges need the same rule, with explicit
   exemptions for juggles and loop edges.
1. **Run the full set-player demo end to end**
   (`uv run python -m brain.set_player --tracks 3 --seconds 45`) with the
   hai-agents desktop bridge doing the loads — each piece is validated but
   the whole loop has not run attended yet. GUI reliability is the weak
   link (dock misclicks, focus loss); `--no-agent` is the fallback.
2. **Linux port + NemoClaw/vLLM** — follow `docs/LINUX_PORT.md`.
3. **Retire the superseded Python MIDI stubs** — `hands/midi_engine.py`
   (made-up note/CC map) and possibly `agent/midi_bridge.py` are both
   superseded by `core-rust/`; `shared/commands.py` isn't wired to anything.
4. `Track.energy` is still a placeholder (`MEDIUM` for everything scanned);
   `brain/agent.py`'s `_next_free_deck()` is hardcoded — set_player tracks
   deck alternation itself instead.
5. Double-time BPM suspects ("Don Doggy" 149, "Trust Me" ~160) — set_player
   sidesteps them by BPM-chaining, but verify before juggling on them.

## Linux drive scan + transfer-safe scanning (2026-07-12, `feat/complete-scan-dedupe`)

`brain.scan_library` is now safe to run against a drive with active
downloads/copies: it skips sibling partial-download markers
(`.part`/`.crdownload`/`.!qB`/`.aria2`), zero-byte placeholders, and files
modified within `--min-age-seconds` (default 300), writing the skipped list
to `brain/data/scan_skipped.json` for a later rescan. Records gain
`duration_seconds` + `size_bytes`; `brain.catalog` reports duplicate groups
(normalized artist+title, then split by duration ±4 s so every album's
"Intro" doesn't collapse into one pile). `brain.analyze_via_mixxx` takes
`--tracks <playlist.json>` so the muted-deck BPM/key analysis runs on any
subset, not just the lineage set.

Tag reads are threaded (`--workers`, default 8) — measured serial rate on
the contended USB drive (`/media/ernest/E8D6-7CB8`, exFAT, downloads
running) was ~1 file/s ≈ 3 h for the crate; threaded took 14.5 min.
Result on the Linux box: **9,105 HipHop tracks, 540 artists, 627
duration-confirmed duplicate groups, 2 files skipped mid-download**
(`brain/data/{crate,catalog}.json`, gitignored as always).

Mac rescan 2026-07-12 (`/Volumes/USB322FD/Music/{HipHop,RnB}`, 16 workers,
~600 files/s, 33.6 s): **19,624 tracks (5,859 HipHop + 13,765 RnB), 815
artist tags, 2,275 duplicate groups, 0 skipped** — no transfers were
running, so this scan is complete. The 77 previously Mixxx-analyzed tracks
carried their bpm/key forward; 57/58 hit-seed rows now match the crate.

## Playlist curator branch (2026-07-11)

Work on `feat/playlist-curator-ui` adds a localhost playlist picker and a
researched 50-track starting seed covering Ernest's requested West Coast cuts,
each top-level R&B-folder artist, and eight Sade tracks. On the Mac USB library,
all 50 seed entries matched real audio files. The generated selection and
exports remain gitignored in `brain/data/`.

`brain.scan_library` now accepts multiple roots and carries forward existing
`bpm`, `key`, and `energy` values by absolute path. A real rescan of HipHop +
R&B produced 14,518 tracks and retained all 30 previously analyzed Snoop
tracks. After importing and analyzing the curated playlist, Mixxx had 77 crate
matches; all 49 tracks in the current enabled set have both BPM and key. The
current set intentionally differs from the 50-track seed: two seed tracks were
disabled and The-Dream's "Falsetto" was added.

## Available catalog + agent curation (2026-07-11 evening)

Playlist selection is constrained to **songs physically available** under the
user-chosen roots (e.g. `/Volumes/USB322FD/Music/RnB` + `.../HipHop`).

| Module | Role |
| --- | --- |
| `brain/scan_library.py` | Multi-root **metadata-only** scan (mutagen tags: title/artist/album/genre). ~few ms/file; no BPM analysis. Optional `--catalog`. |
| `brain/catalog.py` | Slim agent index (`catalog.json`) + path-stripped `agent_view` for NemoClaw upload. |
| `brain/playlist_seeds/*.json` | Wikipedia/chart **hit seeds** per folder artist + sample-lineage edges. |
| `brain/mix_graph.py` | Transition scores: BPM (rate-adjust tolerant), Camelot key, sample lineage, title tokens. **No full-library waveform** (too heavy; use Mixxx beatgrids). |
| `brain/curate_playlist.py` | Pipeline: keep user selection → match researched hits to crate → mix-order → optional H-agent **reorder only** (never invents deep cuts). Subjective asks (genre/region/era/mood) are **per-playlist input** via `--brief` and `--seed`, not rules — the default brief is neutral (Ernest, 2026-07-12: the earlier West Coast slant was a one-time ask, don't hardcode it). |
| `brain/playlist_edit.py` | Structured selection edits (`--remove-artist`/`--remove-title`) — the tool surface a NemoClaw/H-agent chat front end calls for asks like "drop the Alicia Keys songs"; re-order afterward with `--mode selection`. **Known gap:** removals aren't sticky — a later `--mode hits` run re-adds seed matches; a persisted exclusion list is the fix. |
| playlist UI | "Add researched hits" + "Order for mixes" (reorder enabled set; never drops picks). |

**Hackathon demo line:** "Yes — H agents curate researched hits from *your*
library; we enrich with sample lineage + lyrics + chromagram; Hands perform a
continuous set playing Mixxx like an instrument."

**Waveform policy:** no full-crate waveform decode. Optional Rust chromagram
on ≤12–16 ordered hits (`clawdj chroma` / `enrich_playlist --chroma`). Mixxx
owns beatgrids for beatmatch.

**Continuous mix path:** `enrich_playlist` → `build_mix_plan` →
`hands.run_mix_plan` (control API). Knobs/docs: `docs/MIX_INSTRUMENT.md`.

### Incremental new-music ingestion (2026-07-12)

`brain/data/library.sqlite3` is now the local source of scan state. It stores
configured roots plus each file's path, size, nanosecond mtime, embedded tags,
availability, first/last-seen times, and analysis fields. `brain.scan_library`
still writes `crate.json` and optional `catalog.json`, so existing curation is
unchanged, but repeat scans only open new or changed files with Mutagen.
Removed files are marked unavailable rather than erasing their history.

Run the CLI once with the desired roots. After that, the playlist editor's
**Check for new music** button reuses those roots, scans in a background thread,
and reports new/changed/unchanged/missing-tag counts. Expensive BPM/key, phrase,
lyrics, and chromagram work remains downstream and scoped to selected tracks.

**Migration caveat (fixed post-hoc 2026-07-12):** the first migration
stamped every row with the same `first_seen_at`, so "which tracks are new"
survived only as a count. Reconstructed exactly via file birthtimes (a
4.5-hour copy gap sat precisely at the 2,695 boundary) and backfilled into
the index; future scans persist real first-seen times naturally.
`sync_mixxx_analysis` now writes bpm/key into the index too and exports
full-fidelity records from it (review fix — crate rewrites used to drop
album/duration and revert re-analyzed bpm on the next scan).

**New-music batch 2026-07-12 (2,695 tracks: 1,817 RnB / 878 HipHop):**
dominated by Charles Aznavour (~1,416 — chanson, in the RnB folder), 50
Cent (332), Fat Joe (177), Aaliyah (170), Keith Murray (193), G-Unit,
Terror Squad; 46 tracks untagged. Agent-facing candidates file:
`brain/data/new_music_agent.json` (path-stripped, short `n####` ids,
metadata only) + `new_music_ids.json` (id → path resolution, stays local).
This is the input for the NemoClaw / H-agent "pick playlist candidates
from the new music" conversation; resolve returned ids locally, never let
the agent touch paths.

**Both agent engines wired and validated live (2026-07-12) —
`brain/pick_candidates.py`:**

- `--engine nemoclaw`: hermes sandbox (NVIDIA Nemotron 3 Super 120B) via
  its OpenAI-compatible API. Plumbing: Docker Desktop must be running
  (gateway silently fails without it — `nemoclaw hermes doctor --fix`
  repairs once Docker is up), then
  `openshell forward start --background 8642 hermes`; auth is
  `nemoclaw hermes gateway-token --quiet` as a Bearer token, model id
  `hermes-agent`. Note `nemoclaw hermes agent` does NOT work for this
  sandbox (hermes runtime exposes the API instead).
- `--engine h-agent`: H Company Agent Platform via `hai_agents`
  planning-only task (Brain, max_steps=4). Auths fine on this Mac via the
  `~/.holo/.env` key fallback.

Real run, same 2,695-track view + brief: Nemotron returned 20 picks with
some junk (a French charity single, G-Unit filler); Holo returned 14
tighter picks and honored "fewer is fine". Picks land in
`brain/data/new_music_picks*.json`; `--add-to-selection` merges them into
the selection for the normal curate → analyze → plan flow.

**"Ask the DJ brain" is in the playlist editor UI (2026-07-12).** Panel
under New music: brief + engine (NemoClaw/H Company) + count → background
agent call (`run_pick`) → picks rendered as checkboxes (pre-checked,
already-in-set and not-in-crate flagged) → "Add checked to set". Endpoints:
GET `/api/brain`, POST `/api/brain/ask`, POST `/api/brain/apply`. Validated
end-to-end with a real NemoClaw call through the HTTP API. Note hermes
agent turns take 1–7 minutes (it's an agent loop, not a raw model); the UI
polls and survives page reloads mid-call. NemoClaw prereqs: Docker Desktop
up + `openshell forward start --background 8642 hermes` once per boot.

UI workflow semantics (Ernest, 2026-07-12): Library = every track on the
drive; Enabled set = the working playlist (user edits are authoritative);
**unchecking = durable exclusion** (`playlist_exclusions.json`) that seed
merges, agent picks, hits-mode curation, and suggestions all respect until
re-enabled; **Finalize for Mixxx** = the lock-in step before analysis.
"Ask the DJ brain" supports Both engines with per-engine cached results
(`brain_picks_{engine}.json`); "Suggest blends" deterministically scores
analyzed/unselected/non-excluded tracks against the current set. Scans
that find new music rebuild `new_music_agent.json` automatically.

**"Create the mix" is page 2 of the playlist editor (2026-07-12).** Hash
routes: `#curate` (crate / enabled set) and `#mix` (create the mix).
**Finalize for Mixxx** writes `playlist.json` and **navigates to `#mix`**,
which always reloads the finalized snapshot (track list + BPM/key status).
A **stale-plan banner** appears when the dry-run no longer matches the
finalized analyzed set (e.g. you added Many Man); Start mix is disabled
until rebuild. Tracks missing BPM/key show in red and are skipped by the
plan builder until Mixxx-analyzed (sync crate afterward).

**Suggest blends** always returns a `message` (set already blends well /
weak links / unanalyzed in set / no candidates) and the UI scrolls to the
brain picks panel so results aren't silent.

**Analyze & enrich from the mix page (2026-07-12):** GUI Mixxx Analyze
often leaves `library.bpm=0` / empty key (verified on Many Man (Wish
Death)) and never reaches claw-dj until something writes the crate. The
mix page now has **Sync from Mixxx** (pull bpm>0 from mixxxdb → index +
crate + re-export playlist.json), **Analyze & enrich missing** (muted-deck
control-API analysis via `brain.enrich_set` → lyrics/chroma/phrases, then
re-export so Build mix plan sees the new BPM/key), and **Refresh list**.
No Holo/GUI agent required when the patched Mixxx control API is up on
9995. Endpoints: POST `/api/mix/sync`, `/api/mix/enrich`, `/api/mix/refresh`.

**Rename + mix graph opener (2026-07-12):** File rename to `Many Men…mp3`
left ID3 as "Many Man"; path was already new. Mix page **Rescan titles/paths**
re-reads tags and prefers filename when it fixes man→men-style typos.
**Shuffle opener** re-runs `greedy_mix_order` from a random (or chosen)
start so the blend graph unfolds differently while keeping adjacent pairs
mixable; then rebuild the plan.

**BPM control-API vs Mixxx DB lag (Many Man case, 2026-07-12):** muted-deck
analysis printed `mixxx bpm: 97.14` but mixxxdb stayed `bpm=0` / no beatgrid
even after 45s + re-sync — so claw-dj stayed empty. Fix: `analyze_via_mixxx`
now **returns live API bpm/key** and `apply_analysis` writes them straight
into `library.sqlite3` + crate (do not wait on Mixxx flush for plan
eligibility). Phrases still need a Mixxx beatgrid blob (may lag or need a
later re-enrich). **Lyrics typo:** ID3/filename "Many Man (Wish Death)" is
wrong chart title; LRCLIB only hits **Many Men** — `lyrics.title_search_variants`
retries that correction without renaming the file.

Profile presets + free-text brief + order engine → `compose_mix_plan` →
dry-run → **Start mix** (double confirm + Mixxx ping). Endpoints: GET
`/api/mix` (includes `finalized`, `plan_stale`), POST `/api/mix/build`,
POST `/api/mix/start`.

**Order briefs are real now (not just feel keywords).** Example that used
to be ignored: *"mix Parce Que Tu Crois next to What's The Difference in
the first half"*. Flow: NemoClaw or H-agent returns structured
**constraints** (adjacent pairs, region windows, optional `use_only`
subset, optional opener) → local mix-graph greedy tour + forced
adjacency/region placement (`brain/mix_order_brief.py`) → plan events.
Agent never invents tracks; unknown ids are dropped. Provenance stores
`order_engine`, `order_notes`, and the constraint object. Feel keywords
still go through `mix_profiles.apply_brief` in parallel. Empty brief
skips the agent. Agent turns can take 1–7 min (same as Ask the DJ brain).

### Mix profiles (2026-07-12, `brain/mix_profiles.py`)

Architecture decision (Ernest asked "should run_mix_plan be very
configurable?"): **configure the plan BUILDER, keep the plan format and
runner deliberately boring.** The plan stays a declarative event list;
every feel knob lives in a `MixProfile` (ride-phrase pattern, transition
scale, flourish density, intro-entry rate) behind named presets:
`dj-showcase` (default; today's tuned values), `club-set`, `warm-up`.
`build_mix_plan --profile <name> --mix-brief "<free text>"
--order-engine nemoclaw|h-agent|none` — the brief maps onto (1) feel
overrides via keyword pass and (2) order constraints via the chosen
engine. Every adjustment is named in the plan's `profile` provenance
block. Gotcha fixed: negation keywords ("no tricks") must be checked
exclusively before positives ("tricks"). Only knobs validated by real
runs get added — grow one at a time.

### DJ formats (2026-07-24, `brain/dj_formats.py`)

DJ formats are a second, independent planning axis:

- **mix profile** = feel/pacing/performance density;
- **DJ format** = allowed transition grammar and hard phrase rules.

The first format, `hiphop-rnb-8bar`, records advice Ernest obtained from a
practicing hip-hop/R&B DJ. The canonical, human-readable source is
`docs/dj-formats/HIP_HOP_RNB_8_BAR.md`; the typed registry is
`brain/dj_formats.py`. It can be paired with any existing profile in the
`#mix` UI or CLI:

```bash
uv run python -m brain.build_mix_plan \
  --profile club-set \
  --dj-format hiphop-rnb-8bar
```

This format is strict and optional: the default is `--dj-format none`.
Incoming cues and outgoing chorus/hook anchors must
resolve to beat 1 of a four-beat bar, its intro/chorus phrase is 8 bars
(32 beats), and missing evidence raises a build error. `chorus_to_intro`
can use beatgrid + lyric-timeline evidence. `acapella_hook_swap` requires
human `hook_acapella_seconds`; lyrics alone cannot prove “no music.”
`intro_loop_under_entry` jumps the outgoing deck to its verified intro,
engages `beatloop_32_activate`, starts the incoming deck on beat 1, and
hands off over the loop. Format-specific annotations live in persistent
`dj_notes`; the full vocabulary is in the spec.

The separate `hiphop-rnb-guided` format is the practical library-scale
option. It keeps the expert's universal “everything enters on the 1” rule
hard, uses the strict recipe when intro+chorus evidence is actually present,
and otherwise retains a tempo-safe ordinary technique at analyzed downbeats.
Every transition carries `format_compliance=expert_recipe` or
`format_compliance=guided_fallback`; a fallback also records its reason and
is never presented as expert-certified. Its spec is
`docs/dj-formats/HIP_HOP_RNB_GUIDED.md`.

The 2026-07-24 15-track playlist builds in guided mode and dry-runs 47 events
with all 14 transitions honestly labeled as guided fallbacks. Party And
Bullshit initially lacked a persisted beatgrid; loading it and then a second
track through `brain.analyze_via_mixxx --apply`, followed by
`brain.enrich_set`, produced its phrase and beat-phase rows. The strict mode
still correctly stops on Ten Crack Commandments because that album recording
does not have a provable conventional 8-bar incoming intro. CLI structural
failures are now concise `mix plan build stopped: …` messages rather than
tracebacks.

A four-track strict proving set (Who Shot Ya → Give It To Me - Remix → Young
Wild And Free → I Love The Dough) and six exact 32-beat audition clips are
described in `docs/dj-formats/STRICT_PILOT_2026-07-24.md`. The local ignored
playlist is `brain/data/strict_pilot_playlist.json`; clips are under
`brain/data/strict_pilot_auditions/`. The proposed annotations were tested
only in a temporary simulation: they build three 32-beat
`dj_format_chorus_to_intro` transitions and dry-run 14 events. Do not persist
those annotations until Ernest confirms each clip by ear.

When adding another expert recommendation, add another spec under
`docs/dj-formats/` and a separate registry entry. Do not overload the three
mix-feel profiles or weaken an existing strict format with silent fallback.

### Post-finalize enrichment (2026-07-12, `brain/enrich_set.py`)

Runs over the finalized playlist only, check-before-fetch at every step,
persists into `library.sqlite3` (`lyrics`/`chroma`/`phrases` tables +
bpm/key on `tracks`): muted-deck Mixxx bpm/key for whatever's missing;
full lyrics from LRCLIB (free API, disk-cached); Rust `clawdj chroma`
12-dim fingerprints per track, with `chroma_similarity.json` rewritten as
the full-set pairwise cosine matrix (so ordering/plan techniques get real
texture coverage, not the stale 12-track set); phrase/cue analysis into
the DB + `phrase_analysis.json` export for the planner. First run on the
48-track set: 48/48 enriched, 44 with lyrics (one miss is an instrumental).

**Mixxx analysis-persistence gotcha, worse than the flush lag:** some
tracks' engine analysis (bpm readable over the API) takes many MINUTES to
land in `mixxxdb.sqlite` — clean quit does NOT force it, and a 45s settle
before eject doesn't either; it seems to persist when a LATER track gets
analyzed. If a track stays `bpm=0.0/beats NULL`, keep working and re-check
a few minutes later, or right-click → Analyze in the GUI (always
persists). Cost ~30 min on "In Da Club" before the row appeared on its own.

**NemoClaw:** sandbox `hermes` Ready on this Mac (NVIDIA Nemotron inference).
Separate from host Hermes (`~/.hermes`). Holo3-via-vLLM still `LINUX_PORT.md` §5.

## Phrase-aware full demo mix (2026-07-11)

Branch `feat/phrase-aware-demo-mix` closes the gap between a compatible order
and a performed set. `brain/phrase_analysis.py` decodes Mixxx's
`BeatGrid-2.0` protobuf (BPM plus exact first-beat frame), uses local `ffmpeg`
to rank 16-beat-aligned energy changes in only the selected demo tracks, and
writes cue timestamps to gitignored `brain/data/phrase_analysis.json`.

`brain.build_mix_plan` version 2 consumes those cues and expresses excerpts in
beats. `hands.run_mix_plan` preloads alternating decks, counts live
`beat_active` edges, anchors cuts and blends on beats, respects unsynced cuts,
and performs continuous crossfader/EQ/filter curves. Showcase gestures rotate
instead of firing on every compatible pair: bass swap, scratch preview, loop
roll, and transformer cut.

The generated six-track Mac plan is roughly two minutes: Beautiful -> Fallin'
-> Off the Books -> Round & Round -> Regulate -> Love's Theme. All six cue
points came from Mixxx grids plus local energy scoring. Live autonomous
execution requires the patched Mixxx control API; port 9995 was not listening
on the Mac during this implementation, so the plan was dry-run verified there.

## Key-adjusted blends (2026-07-14, `feat/post-hackathon-direction`)

`brain.build_mix_plan.pick_technique` now turns close-BPM key clashes into
`key_adjusted_blend` when the incoming key can reach a same, relative, or
Camelot-neighbor key with a bounded ±1–2-semitone move. The plan records
`pitch_adjust_semitones` and `pitch_adjust_target`; no key metadata means no
guessed shift and falls back to the filtered `key_clash_blend` recipe.

`hands.run_mix_plan` applies Mixxx `[ChannelN],pitch_adjust` before the
incoming deck starts, holds it through the first half of the overlap, then
smoothly returns to native key as the outgoing deck disappears. Instrument
reset and every deck load zero stale pitch adjustment defensively. Unit tests
cover planner selection, bounded harmonic targets, runner apply/restore, and
rejection of shifts beyond the plan's ±2-semitone safety limit. Audible live
validation is still pending.

Do **not** infer that verse-tour cuts should now use `beatsync_phase`: the tour
was live-validated without sync because phase-pull can move its lyric-aligned
cue. Phase-only alignment remains a separate A/B experiment for ordinary hard
cuts before it becomes planner vocabulary.

## Mix-brief -> dj_notes edits, and set recording (2026-07-15)

A detailed by-hand DJ-craft editing pass on 2026-07-14 (verse landings, cue
timing, reordering — see PROGRESS.md) motivated building the pipeline it had
been standing in for: `brain/mix_directives.py`. Given a free-text brief and
the current finalized track order, it asks an LLM (reusing
`pick_candidates.py`'s engine functions) for structured
`{notes: {id: dj_notes}, reorder: [id,...] | null}` edits, grounding any
brief-mentioned track in its real raw synced lyrics (`lyric_timelines` table)
rather than letting the model guess a timestamp. IDs in the prompt/response
are short synthetic ones (`t000`-style), never real paths — so a hallucinated
or wrong-file-copy path structurally cannot reach the write path. A reorder
must be an exact permutation of the current set or it's rejected outright.
Dry-run by default; `--apply` (or the web UI's "Apply these edits" button)
writes dj_notes into `library.sqlite3` and patches `playlist.json`'s rows in
place directly — **not** a `load_crate()`/`export_playlist()` round trip,
because `crate.json` is only refreshed on scan/analyze/sync and would serve
stale dj_notes back into playlist.json otherwise. Wired into the web UI
(`playlist_editor.py`: `ask_directives`/`apply_directives`, background-thread
pattern matching `ask_brain`; `playlist.html`: "Interpret as DJ notes…"
button right before "Build mix plan", reusing the `#mix-brief` textbox).

Real end-to-end test against the live 28-track set (nemoclaw engine) both
validated the pipeline (correctly grounded a verse-landing ask in actual
lyrics) and demonstrated why the dry-run/confirm step is load-bearing: asked
not to touch one track's BPM, the model added a `play_bpm` directive anyway.
Nothing gets written without a human looking at the diff first — by design,
not as a stopgap.

Separately, `hands/run_mix_plan.py` gained `--record`, toggling Mixxx's
`[Recording]` control group (`toggle_recording`/`status`, confirmed against
the patched fork's `recording/defs_recording.h`) around the plan run inside
a `try/finally`, and never touching a recording that was already running.
Current build has no mp3 encoder (`docs/BUILD_MIXXX.md`'s macOS recipe omits
`-DFFMPEG=ON`), so this records WAV; convert with `ffmpeg` after, or rebuild
with FFMPEG support for native mp3.

## 2026-10-22 — next pairing audition, Sorry (unheard)

Live vol-02 is still M, SHA `42a74d4c63e855c3a12474083859d3b5dc63ce8cad68e8d299858c9f6185bdbe`; Janet N is approved but not installed. Prepared private `Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/audition.10-22-sorry-pacifico-ghetto.json`: Pacifico → Sorry → Ghetto, two 32-count gentle standard blends, native pitch, no filter exit/inferred snare jump. Sorry cue exactly 0:00, outgoing fade 166.209–185.409s to avoid its quiet outro. Pacifico cue/fade anchor and Ghetto cue pinned. Timing pins are not human approval; energy/vibe, vocal overlap, harmonic fit and count alignment remain unheard. No model review requested. Full mini and both audition dry-runs plus fake-control real-runner execution/cleanup passed, real sockets forbidden. No live playback/install, plan/playlist/note/lock mutations or commits. Source and checks retained privately; keep one audition/verdict round at a time. SWV → 112 at 36 counts still awaits ear.
