<!-- pdd-story-status: expanded-2026-09-05-awaiting-region-and-playback-validation -->
<!-- pdd-story-areas: verse, mix_directives, build_mix_plan, lyric_timeline -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Avoid opening, middle and ending skits without breaking the mix

## Story

As a DJ I **almost never want to play a skit**. Album skits (phone calls,
window-shooting scenes, skit tracks, spoken intros before the beat) are
not the record. Identify them at the start, middle or end of a recording.
Cue past an opening scene, continue smoothly after a middle scene, or blend
into the next song before the scene can be heard. Keep the musical intro,
verses and gradual beat/backbeat-matched transfer; avoiding a skit must not
reintroduce automatic short handoffs.

`cue_seconds=0` is legal for an **iconic musical intro** (Disco Inferno
count-in, On Fire “We on fire”). It is **not** legal for a spoken scene
that happens to sit at 0:00.

The lyric detector makes this worse: skit lines do not repeat, so they
are labeled **verse**. `verse_guard` then treats the dialogue as a verse
to protect — `intro_top` rewrites to 0:00, and `respect_verse_exit`
**extends the ride through the whole skit**. The blend then hits the
actual rapper mid-verse (or right as they start).

Until a reliable skit detector exists, human notes win: skip to the
hook / first verse (`entry_style=verse_landing` or `trust_cue_seconds`
past the dialogue). Do not invent timestamps without synced lyrics.

## Acceptance criteria (observable)

1. **Do not cue a spoken skit.** If the opening is dialogue / a scene
   before the beat or hook, the mix-in is the first musical hook or
   bar 1 of the first real verse — not 0:00.
2. **Do not protect a skit as a verse.** A detector-labeled “verse”
   that is only the opening scene must not force `intro_top` or an
   extended ride through the dialogue.
3. **Finish the real verse.** Skipping the skit is not an excuse to
   clip the rapper who follows.
4. **Human locks win.** `trust_cue_seconds` / `verse_landing` past the
   skit are not rewritten back to 0.
5. **Example (50centgunitera).** Mobb Deep *G.O.D. Pt. III*: window
   skit 0:03–1:06. Opening hook “QBC, sip lime Bacardi” 1:06. Prodigy
   verse 1 1:28 “Awright, now pay attention…”. Old cue 0 + ~102-beat
   ride played the whole skit; the 32-beat blend cut Prodigy. Now
   32-beat `verse_landing` onto Prodigy (pre-roll is the hook, not the
   skit); ride through Havoc; fade on the last hook.
6. **Example (already locked).** Biggie *My Downfall*: skip the phone
   skit, cue 66.65.
7. **Example (Who Shot Ya album, any mix, 2026-08-31).** Ready to Die
   remaster: last verse ends ~3:20 (“Hammer cock, in the fire
   position”). Then the gun-in-mouth / victim-squeal scene
   (~3:24–3:44, “Can't talk with a gun in your mouth”). That is a
   skit, not a verse, and it is demoralizing — skip it, cut it, or
   start the outgoing blend **before** it in **every** mix that uses
   this song. Historical requested bounds were 203.5–224.5 seconds onto
   “As we proceed.” On September 5 Ernest estimated about 3:30–3:50 instead.
   Review these competing bounds on the exact recording; equivalent releases
   need their own verified source offsets. A plan overlay must not drop an
   established library skip. Do not claim library enforcement merely because
   a document says it exists. A complete next-song fade before the scene is
   also legal.
8. **Notes identify a region and treatment.** Record the exact recording,
   approximate/reviewed source-file start/end, why it is a skit, and whether
   to continue this song or leave it. Show whether the request is merely
   recorded or implemented in built events. Vague notes are not certified
   detector results.
9. **Middle skit: seamless continuation when feasible.** Load the same
   recording on the other deck at clean post-skit material, align beats and
   backbeats, and blend gradually. Start early enough that the outgoing skit
   never becomes audible. The incoming source position advances throughout
   the overlap; if a specific phrase must land at completion, account for
   overlap without pre-rolling into the skit. Reserve the second deck without
   overwriting a live bed or upcoming track, then preload the next song on
   the freed deck. This is an internal operation, not a duplicate playlist
   entry. Do not substitute the different 50 Cent Who Shot Ya recording.
10. **Ending skit or infeasible continuation: exit in advance.** Finish the
    full next-song blend before the forbidden region starts. Merely starting
    the fade at 3:30 with the scene still audible is insufficient. Reserve
    source-time headroom for loading, incoming overlap, body and outgoing
    fade; verify the deadline live without turning uncertainty into a cut.
11. **Detect candidates; review uncertainty.** Use available audio and
    transcript/section evidence to suggest skits. Spoken delivery, sparse
    drums, unique lyrics or an automatic “verse” label are not sufficient
    individually. Reviewed regions override contradictory labels. Never
    auto-skip rap verses or iconic musical callouts because a classifier is
    unsure.
12. **Verify the chain.** Audition before/after windows, the complete skip or
    early-exit blend, and the following transition. Confirm no forbidden
    dialogue was audible, intended music survives, deck ownership/preload
    works and the fade remains gradual. Keep planned, observed and listener
    evidence separate.

## Must not

- Do not treat “start from 0:00 is iconic” as a blanket rule when the
  opening is a skit.
- Do not auto-skip every long first verse — many songs rap from bar 1
  with no skit. This is a skit/dialogue skip, not “skip the first verse.”
- Do not let a plan overlay drop library `skip_from_seconds` /
  `skip_to_seconds`. Those crate notes are the any-mix enforcement.
- Do not start Mixxx to prove the cue.
- Do not silently replace a requested two-deck smooth continuation with an
  audible beatjump: that is a different technique.
- Do not change a running mix, truncate audio files, or call a saved sentence
  an implemented skip.

## Source

Ernest, 2026-08-28, after 50centgunitera mixed G.O.D. Pt. III from 0:00:

> we DO NOT want to play any of the first beginning part where it's
> just a skit. We almost never want to play any skits part. And we're
> cutting off Prodigy's first verse in the middle.

Expanded from [Ernest's September 5 request](../docs/intents/request__song_playback_notes_and_skit_avoidance.md).
Implementation status is kept separately in
[the evidence report](../docs/WHO_SHOT_YA_LISTENING_REVIEW_2026-09-05.md).
