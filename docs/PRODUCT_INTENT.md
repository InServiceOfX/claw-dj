# Product Intent (PRD)

This current product-intent record is maintained by `pdd intent apply`.
Each accepted change links to an immutable intent event.

## Listening follow-up: notes, parity and Who Shot Ya order (2026-09-05)

Save recording-specific playback intent in Arrange through plan-scoped notes;
saving text does not imply arbitrary-prose execution or live changes. Protect
drafts and plan identity. Skit requests include reviewed opening/middle/ending
regions; Biggie's approximate scene bounds still need verification.

Weak entrance evidence must not discard usable alternating-backbeat evidence
later inside the same overlap. Preserve cues and full gradual fades, report
limited evidence honestly, and test actual recorded entrances as well as
synthetic fixtures. The Ja→Jealous correction does not close unrelated audible
failures. Jadakiss's Who Shot Ya belongs immediately after K.Dot's version in
the current plan's next-build order. Implementation/remaining gaps and the
non-active checked listening candidate are in [HANDOFF.md](HANDOFF.md).

## Listening correction: gradual crossfader blends (2026-09-04)

Request: [original feedback](intents/request__gradual_seamless_crossfader_blends.md).
Story: [gradual and seamless crossfades](../user_stories/story__when_i_blend_tracks_the_crossfader_moves_gradually_and_seamlessly.md).

Ernest reports that backbeat matching seems fine in the new live run, but
many fades are too fast. Ordinary transitions should blend progressively and
seamlessly; deliberate DJ-performance cuts remain exceptions. The 32-beat
On Fire → Who Shot Ya fade was acceptable, and longer is welcome when the
musical material permits. Wall → On Fire's verification-triggered two-beat
handoff was too abrupt. This is new feedback against the blanket short-handoff
policy recorded below, not approval to ignore known mismatches. Ernest approved
[implementation](intents/request__implement_gradual_blend_recovery.md), now
implemented and independently reviewed: weak/missing/lost evidence preserves
the planned gradual fade. Ernest's subsequent
[zero-short-handoff correction](intents/request__zero_automatic_short_handoffs.md)
also removes the proposed eight-beat mismatch recovery: mismatch is reported
honestly without shortening. Only corroborated physical remaining-audio limits
can force an early fade; deliberate DJ cuts remain separate.
The prompt, stories and regressions reflect this correction. Current playback
and the active artifact were not modified; the user must restart the old CLI
process to load the code. Audible acceptance remains pending.

<!-- pdd-intent-entry:through-the-browser-gui-http-127-0-0-1-8787-cura-88023c99:start -->
## Preview a track quickly from the browser GUI

- Intent event: [`docs/intents/intent__preview-a-track-quickly-from-the-browser-gui-88023c99.md`](intents/intent__preview-a-track-quickly-from-the-browser-gui-88023c99.md)
- Change kind: `add`
- Scope: playlist GUI (not Mixxx hands)

> From `#curate` and `#mix`, preview a library track in the same browser tab with the native HTML5 audio element. Do not use Mixxx for this listen, do not require a browser plugin, and do not stream files that are not already in the loaded library index.
<!-- pdd-intent-entry:through-the-browser-gui-http-127-0-0-1-8787-cura-88023c99:end -->

<!-- pdd-intent-entry:portable-music-collection-no-hardcoded-volume-la-288cef1d:start -->
## Portable music collection: no hardcoded volume label, safe availability, deferred relative identity

- Intent event: [`docs/intents/intent__portable-music-collection-no-hardcoded-volume-la-288cef1d.md`](intents/intent__portable-music-collection-no-hardcoded-volume-la-288cef1d.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_project_adoption`
- Technology: `not stated`

> claw-dj must not hardcode a volume label or machine-specific mount prefix in code or configuration defaults. The user's music collection lives on an external USB stick that they specify; each machine resolves where that collection is currently mounted, and scan roots stay user-specified relative to it. Record the collection's mount base and a stable collection id in the library index so identity is re-derivable without reading code. Track identity remains the absolute file path for now; because of that, the volume label is part of the collection contract and a replacement volume must be named identically, which must be documented. A root that exists but suddenly returns no files must not mass-mark its tracks unavailable and orphan their enrichment and human dj_notes; an unmounted collection must never be read as deleted. Initial metadata population stays available three ways (command-line script, GUI Check-new-music button, and agent-run) with the same result, and must never re-read tags for already-indexed unchanged files. If track identity is ever migrated to collection-relative paths, the stored keys and the scan's identity function must change atomically, and a partial migration must fail loudly rather than silently duplicate rows or drop lookups.
<!-- pdd-intent-entry:portable-music-collection-no-hardcoded-volume-la-288cef1d:end -->

<!-- pdd-intent-entry:i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160:start -->
## I need a way to plan out multiple mix plans that can be "work in...

- Intent event: [`docs/intents/intent__i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160.md`](intents/intent__i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_project_adoption`
- Technology: `not stated`

> I need a way to plan out multiple mix plans that can be "work in progress" and easy way to switch between existing mix plans i'm still working on and then create new ones. Once I've chosen a mix plan I want to work on (of course each mix plan will be "colloqujially" named such as the "2001 expanded 25th anniversary mix" or the "Notorious BIG tribute mix" , I want to be able to easily add and remove songs and also easily work with a LLM or whatever to add dj notes on transitions, adjust transitions and effects bujt through speaking with an LLM, like we could load the mix plan, but when changes gets made by an AI agent harness or something like you hermes-agent, or cluade, codex, I can press "refresh" and see the refreshed order of the songs and transitions between each in a nice GUI way. Also, I wanna specify like 2, 3, 4, or some small n number of songs should be "bunched together", should follow an exact order, transition between them, because they sound very good with each other and be able to move them all together as a "unit". Should we have another tab for this page in http://127.0.0.1:8787/#curate because right now we only have 1 · Curate set
> 2 · Create the mix at the top of the GUI. I'm really surprised the claude session I had on my Macbook Pro right before starting up this session again didn't already implement or start to implement this feature, but now please help me. See if there was any mention of this effort in this repo: /Users/ernestyeung/.openclaw/workspace/repos/claw-dj
<!-- pdd-intent-entry:i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160:end -->

<!-- pdd-intent-entry:when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36:start -->
## When Build mix plan runs, every option — NemoClaw order, H Company...

- Intent event: [`docs/intents/intent__when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36.md`](intents/intent__when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `not stated`

> When Build mix plan runs, every option — NemoClaw order, H Company order, and Feel only — must be free to reorder the finalized playlist as necessary so the mix blends and sounds as good as possible. The order in which the user selected tracks is not a required playback order; the user is only declaring which songs are available for the mix. An LLM may be used to interpret natural-language ordering constraints, but mix-quality ordering itself must not require an LLM and must work in every mode. Preserve every available track exactly once unless the user explicitly requests a subset, and preview the resulting order before Start mix. H Company planning-only ordering must not require or start a local desktop bridge.
<!-- pdd-intent-entry:when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36:end -->

<!-- pdd-intent-entry:when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0:start -->
## When scripts/start.sh starts claw-dj, Mixxx control API port 9995 is...

- Intent event: [`docs/intents/intent__when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0.md`](intents/intent__when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `not stated`

> When scripts/start.sh starts claw-dj, Mixxx control API port 9995 is the preferred default, not a strict requirement. If a patched Mixxx instance is already running with its control API on another localhost port, discover that actual port, validate it with the Mixxx control API ping protocol rather than accepting an arbitrary open TCP port, reuse that Mixxx instance, and propagate the selected port consistently to the playlist editor, Analyze & enrich, Start mix, and command-line live mix execution. Do not tell the user to quit a usable running Mixxx merely because it is not on 9995. Preserve an explicit port override as the highest-priority choice. If Mixxx is running without any reachable control API, report that distinct condition honestly; do not connect to an unrelated service or silently start a second Mixxx instance.
<!-- pdd-intent-entry:when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0:end -->

<!-- pdd-intent-entry:load-a-new-music-collection-from-a-chosen-volume-1830f5e2:start -->
## Load a new music collection from a chosen volume

- Intent event: [`docs/intents/intent__load-a-new-music-collection-from-a-chosen-volume-1830f5e2.md`](intents/intent__load-a-new-music-collection-from-a-chosen-volume-1830f5e2.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `bash, python, sqlite`

> I want to be able to mount a new Volume if on Mac OS, or similarly on Linux, with a bunch of audio files that is a new collection of music. I want to be able to do this 2 ways but both ways must achieve the same exact outcome:
>
> 1. Through the GUI, I can choose a new "Volume" (the GUI currently knows where the music is; that has to become choosable), and then the user has the option to do an initial "scan" and "metadata" population for the music there. A new sqlite database is likely needed, since the sqlite data is carried with the music collection, so it makes sense for the sqlite database to be per-volume. The GUI asks the user whether it is OK to scan and which "root" directories to use for the music collection, gives an estimate of how long it will take, and asks the user to confirm before proceeding.
>
> 2. A command line script (bash shell or Python) to run the same thing if the user prefers that.
>
> Finally, enough markdown file(s) should be provided so an AI agent can do this for the user when asked.
>
> We cannot and should not do the Analyze-and-Enrich-song step (lyrics, chromagraph, etc.) for all songs on the drive. But for the parts of that procedure that do NOT require an API call -- so we do not hit API limits and get banned -- anything else that can be done on all the songs to add metadata without an API call should be offered to the user as an option during this initial process.
>
> Also: when we do Analyze and Enrich songs, Mixxx asks for file permission for some songs and I have to manually click, whereas for other songs it happens automatically. I want to understand why, and to fix -- or ask the user for permission to fix -- these file permission problems before starting up Mixxx to find key and BPM data via Mixxx.
<!-- pdd-intent-entry:load-a-new-music-collection-from-a-chosen-volume-1830f5e2:end -->

<!-- pdd-intent-entry:if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58:start -->
## If you're able to scan and see I have a volume called "Elements". In...

- Intent event: [`docs/intents/intent__if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58.md`](intents/intent__if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `sqlite`

> If you're able to scan and see I have a volume called "Elements". In the GUI I have, http://127.0.0.1:8787/#curate is there a way to "switch" to the new music collection and restart "the scan" of the music collection for useful metadata? Also would need to create a new sqlite on the volume if it's not there. It's ok upon start.sh or start of GUI to default to the previously used music collection. so that start up isn't asking use which music collection. But help me implement ability to start a new music collection while saving the previous music collection "settings" if any.
<!-- pdd-intent-entry:if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58:end -->

<!-- pdd-intent-entry:when-i-blend-i-match-the-snare-not-just-the-beat:start -->
## A blend matches the snare, not just Mixxx beat ticks

- Intent event: [`docs/intents/intent__when_i_blend_i_match_the_snare_not_just_the_beat.md`](intents/intent__when_i_blend_i_match_the_snare_not_just_the_beat.md)
- Change kind: `add`
- Story: [`user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md`](../user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md)
- Scope: mix planner + Mixxx runner

Backbeat means the snare/clap accents, usually beats 2 and 4 in 4/4.
The approved September 4 implementation supersedes the earlier ±1 jump
workaround: analyze local cadence and onset timing, preserve the incoming
cue, solve the entrance from actual outgoing position, verify before opening
the fader and monitor the overlap. Build this into every applicable profile,
including Club set and Mix to listen. The later gradual-blend correction
supersedes the original short-handoff policy: unknown rhythm keeps an explicit
unverified gradual blend; confirmed mismatch is reported without shortening.
Never claim an uncertain long blend is aligned.
Reviewed timestamps, cache provenance, previews and live position logs make
corrections reproducible. Position verification is not an audio recording.
<!-- pdd-intent-entry:when-i-blend-i-match-the-snare-not-just-the-beat:end -->

<!-- pdd-intent-entry:ok-great-amend-the-user-story-please-also-just-r-34e4a77f:start -->
## Ok great! Amend the user story please, also just remind the user that...

- Intent event: [`docs/intents/intent__ok-great-amend-the-user-story-please-also-just-r-34e4a77f.md`](intents/intent__ok-great-amend-the-user-story-please-also-just-r-34e4a77f.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `python, rust`

> Ok great! Amend the user story please, also just remind the user that beat back is what we've been calling "snare" or clap. (because I'll probably keep saying it but we want to start saying backbeat (see i need to get used to it). For the recommendations, can youj go ahead and implement all of this? Go ahead and implement the necessary PYthon and Rust code too (Rust preferred, but if necessary, use Python). (for 2, 3 for analysis of rhytm by section and filtering). Basically implement all those 4 recommendations and we'll give it a try, because we want to get the backbeat matching working from the beginning, especially for those DJ format options, like here: http://127.0.0.1:8787/#mix Club set
> Mix to listen like once the mix is Built that it follows backbeat matching from the beginning
<!-- pdd-intent-entry:ok-great-amend-the-user-story-please-also-just-r-34e4a77f:end -->

<!-- pdd-intent-entry:backbeat-analysis-during-enrichment-2026-09-04-d4ec329b:start -->
## Backbeat analysis during enrichment — 2026-09-04

- Intent event: [`docs/intents/intent__backbeat-analysis-during-enrichment-2026-09-04-d4ec329b.md`](intents/intent__backbeat-analysis-during-enrichment-2026-09-04-d4ec329b.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `rust`

> # Backbeat analysis during enrichment — 2026-09-04
>
> ## Original request
>
> > oh btw, can we do this multiband percussion analysis, section local rhythm detection, and cue-preserving entrance timing when we do an "Analyze tracks", in http://127.0.0.1:8787/#mix with the button, or when? Finalized set
> > 36 tracks · 36 with BPM/key · BPM/key ready for plan build
> > 32/36 fully enriched · missing bpm/key 0, lyrics 4, chroma 0, phrases 0, beat_phase 0
> > ← Back to curate
> > Refresh list
> > Rescan titles/paths
> > Sync from Mixxx
> > Analyze & enrich missing
>
> > or when should we do all those implementation adds youj just did?
>
> ## Approved recommendation
>
> Analyze & enrich missing prepares reusable per-track multiband percussion
> and section-local rhythm evidence. Build reuses it and fills missing/stale
> analysis, then computes pair/section/cue-dependent entrances. Playback still
> verifies actual positions and rates before/during overlap. No analysis-only
> action may build/reorder a mix, move cues, or start playback. Distinguish
> cached analysis from confidence and blend readiness in the enrichment UI.
>
> ## Approval
>
> > Ok great, you implemented your recommendation already right? if not then go ahead
>
> Scope: existing enrichment workflow, shared rhythm cache, status/UI, tests
> and existing backbeat/finalized-set stories. No Rust DSP changes required.
<!-- pdd-intent-entry:backbeat-analysis-during-enrichment-2026-09-04-d4ec329b:end -->

<!-- pdd-intent-entry:implement-gradual-blend-recovery-63ec88bb:start -->
## Implement gradual blend recovery

- Intent event: [`docs/intents/intent__implement-gradual-blend-recovery-63ec88bb.md`](intents/intent__implement-gradual-blend-recovery-63ec88bb.md)
- Change kind: `correct`
- Supersedes: `ok-great-amend-the-user-story-please-also-just-r-34e4a77f`
- Scope: `existing_pdd_change`
- Technology: `not stated`

> # Implement gradual blend recovery
>
> ## Original approval
>
> So should we go ahead with the "next implementation" you mentioned?
>
> ## Approved context
>
> Ernest approves implementing the next step described after
> `request__gradual_seamless_crossfader_blends.md`: distinguish unavailable or
> inconclusive verification from confirmed misalignment while preserving smooth
> transitions. The independent story is
> `user_stories/story__when_i_blend_tracks_the_crossfader_moves_gradually_and_seamlessly.md`.
>
> ## Scoped implementation interpretation
>
> - Keep the planned musical blend duration under inconclusive/weak evidence;
>   report it as unverified, never as confirmed backbeat alignment.
> - Use repeated muted-entrance observations rather than a single threshold
>   sample. Preserve the last timed entrance instead of resetting it solely
>   because verification is inconclusive.
> - Distinguish sustained measurable mismatch and incompatible rhythm from
>   missing/weak observation. For confirmed mismatch use a gradual recovery of
>   at most eight beats, never lengthening an already shorter remaining fade.
> - Reserve faster emergency completion for actual remaining-audio/transport
>   constraints, with explicit reasons. Continue monitoring unverified blends.
> - Preserve cues, intentional tempo holds, requested DJ cuts and planned phrase
>   lengths. No blanket longer-duration override and no audible beat jumps.
> - Share policy between Build predictions and runtime, including old artifacts
>   with legacy fallback_beats=2. Report planned/effective/actual fade timing.
> - Add independent regressions and update the affected prompt/story/docs.
>   Do not control Mixxx, restart a running mix or rewrite the active plan.
<!-- pdd-intent-entry:implement-gradual-blend-recovery-63ec88bb:end -->

<!-- pdd-intent-entry:zero-automatic-short-handoffs-6e4a8cb8:start -->
## Zero automatic short handoffs

- Intent event: [`docs/intents/intent__zero-automatic-short-handoffs-6e4a8cb8.md`](intents/intent__zero-automatic-short-handoffs-6e4a8cb8.md)
- Change kind: `correct`
- Supersedes: `implement-gradual-blend-recovery-63ec88bb`
- Scope: `existing_pdd_change`
- Technology: `not stated`

> # Zero automatic short handoffs
>
> ## Ernest's correction (2026-09-04, verbatim)
>
> > or could we require that we get rid of almost all short handoffs? you almost never want to use it, as it breaks the energy and consistency of the beat, and only rarely, at most once if at all in a mix. We want to avoid as much as possible that's why I almost think we should require it to be not used at all or at most once in a mix
>
> > it was a really poor decision to make it like this with the short handoff for weak or inconsistent local snare/clap evidence, please don't do it again
>
> ## Scoped interpretation announced to Ernest
>
> Default to **zero automatic evidence-triggered short handoffs** in a mix,
> not a budget of one for the runner to spend. This supersedes even the
> eight-beat confirmed-mismatch recovery proposed in
> `request__implement_gradual_blend_recovery.md` earlier in this implementation.
> No automatic quota, opt-in setting, or UI feature is inferred from “at most
> once”; a rare deliberate short handoff would require an explicit request.
>
> - Keep the planned gradual fade for weak, missing, noisy or lost evidence
>   AND measured mismatch. Preserve best-effort cue-preserving alignment and
>   repeated verification; report mismatch honestly, without claiming success.
> - Do not blindly jump audible decks or invent tempo changes to hide errors.
>   Deliberately requested DJ cuts remain separate performance choices.
> - A corroborated stopped/exhausted outgoing track is a physical constraint,
>   not routine evidence recovery. Report it; do not promise a full overlap
>   after audio runs out. Preserve existing body reservation for transitions.
> - Build, previews and live execution share this policy. Older two-/eight-beat
>   recovery metadata must not reinstate the retired policy. Add whole-chain
>   regressions so the default is zero evidence-triggered short handoffs.
> - No live Mixxx controls, active-plan rewrites or automatic playback restart.
> - Update story, prompt, agent instructions and tests; independent review and
>   live listening are separate validation gates.
<!-- pdd-intent-entry:zero-automatic-short-handoffs-6e4a8cb8:end -->

<!-- pdd-intent-entry:song-playback-notes-and-skit-avoidance-2019cd0a:start -->
## Song playback notes and skit avoidance

- Intent event: [`docs/intents/intent__song-playback-notes-and-skit-avoidance-2019cd0a.md`](intents/intent__song-playback-notes-and-skit-avoidance-2019cd0a.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `not stated`

> # Song playback notes, skit avoidance, and listening feedback
>
> Received 2026-09-05. Add/clarify playback-note editing and extend the existing
> skit story; record audible backbeat regression separately. No live mix changes.
>
> ## Original request (verbatim)
>
> I wanted a feature that would at least let us add notes specifically for how a song is played. Specifically for this song, [11/110] play_body
>   riding The Notorious B.I.G. — Who Shot Ya for 312 live beats
>   hints: ['Optional: tweak [ChannelN] filterHighEq mid-phrase', 'Optional: beatjump_1_forward to skip to chorus', 'Optional: beatloop_4_toggle for a loop-roll fill']
>   trusted body: observed grid beat 43; keeping ride duration, resolving backbeat at live entrance
>  for this song, we want to either skip the skit starting at aroujnd 3:30 and ending at about 3:50 (you could try to load the same song on the other deck and then cross fade blend into 3:50 time on the same song, but on the other deck, from 3:30 on the former deck, or jujst start blending into the next song before the start of the skit. There should be a user story where we're trying to identify skits within or at the end of a song that we want to either skip if it's in the middle (one can try the method I described above) or start blending into the next song. Also the transitions are better, but for this one, it's off by one count, the beat parity or backbeat matching was off by 1 count: [10/110] transition
>   smooth_blend: Lloyd Banks — On Fire (Feat. 50 Cent) → The Notorious B.I.G. — Who Shot Ya
>   moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
>   notes: Near-identical tempo + friendly key — long crossfade with light EQ.
>   anchoring on [Channel2] beat (95.00 BPM)
>   backbeat: positions verified (-41 ms median); opening gradual blend
>   crossfade: planned 32 beats (20.2s); scheduled 32.0 beats (20.2s)
>   backbeat: local verification unavailable; keeping the gradual blend
>   bass swap (gradual)
>   backbeat: local verification unavailable; keeping the gradual blend
>   backbeat: local verification unavailable; keeping the gradual blend
>   crossfade landed -> deck 1: 32.0 beats / 20.2s executed (planned 32 beats)
>   rate settled to native tempo on deck 1
>   preload next into freed deck 2
> [load] deck 2: 06. WHO SHOT YA.mp3  (111s, 93.00 BPM, cue 0.44s verified at 0.44s)
>
> ## Bounded interpretation announced to Ernest
>
> - Expose the existing track-scoped plan-note API in Arrange with an editable
>   playback note, Save/Cancel and explicit return to the library default.
>   Link from Mix so notes are discoverable. Preserve revision checks,
>   exact recording identity, existing notes, other plans and library defaults.
> - Saving text records intent; it does not interpret arbitrary prose, rebuild
>   the artifact or change playback. Make that distinction explicit in the UI.
> - Extend the existing skit story to opening, middle and ending skits, including
>   source-time ranges, reviewed versus approximate timing, same-song two-deck
>   continuation, and finishing a normal next-song blend before the skit starts.
>   Do not silently treat a direct beatjump as the requested seamless splice.
> - Keep the gradual-v3 policy and current playback code/artifact untouched.
>   Investigate/report the logged one-count complaint; no blind parity flip.
> - Current rough 210–230-second range differs from historical 203.5–224.5;
>   exact bounds and a playable skip/early-exit plan remain to be validated.
>   No automatic DSP skit detector or two-deck splice is claimed implemented.
<!-- pdd-intent-entry:song-playback-notes-and-skit-avoidance-2019cd0a:end -->

<!-- pdd-intent-entry:retain-overlap-backbeat-parity-at-uncertain-entr-f2b17b74:start -->
## Retain overlap backbeat parity at uncertain entrances

- Intent event: [`docs/intents/intent__retain-overlap-backbeat-parity-at-uncertain-entr-f2b17b74.md`](intents/intent__retain-overlap-backbeat-parity-at-uncertain-entr-f2b17b74.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `rust`

> # Request: Put It On Me → Jealous is one count off
>
> Ernest, 2026-09-05, while listening to the existing run:
>
> ```text
> [61/110] transition
>   smooth_blend: Ja Rule — Put It On Me → Nick Jonas — Jealous
>   moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
>   anchoring on [Channel1] beat (93.19 BPM)
>   backbeat: unverified — weak or inconsistent local snare/clap evidence; keeping planned gradual blend
>   crossfade: planned 32 beats (20.6s); scheduled 32.0 beats (20.6s)
>   backbeat: sustained measured backbeat mismatch during overlap; keeping planned gradual blend (needs review)
>   crossfade landed -> deck 2: 32.0 beats / 20.6s executed (planned 32 beats)
> is still off by 1 count, match backbeat please i.e. beat parity
> ```
>
> Accepted implementation meaning: resolve the entrance using reliable local
> backbeat evidence within the intended overlap, even if the first section is
> uncertain. Preserve cue, full32-beat fade and current playing process. Build
> and test a separate Rust candidate, replay recorded positions, then offer an
> explicit next-run candidate. Do not replace the binary used by the current
> run. No blind jumps, cue shifts, confidence inflation, automatic short
> handoffs, or claims of audible success from numerical tests.
<!-- pdd-intent-entry:retain-overlap-backbeat-parity-at-uncertain-entr-f2b17b74:end -->
