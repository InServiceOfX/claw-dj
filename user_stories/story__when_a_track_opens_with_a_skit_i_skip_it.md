<!-- pdd-story-status: drafted-2026-08-28 -->
<!-- pdd-story-areas: verse, mix_directives, build_mix_plan, lyric_timeline -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Skip spoken skits — mix the song, not the dialogue

## Story

As a DJ I **almost never want to play a skit**. Album skits (phone calls,
window-shooting scenes, skit tracks, spoken intros before the beat) are
not the record. Cue past them. Blend into the first hook or the first
real verse.

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
   this song. Enforcement is the library `tracks.dj_notes` row
   (`skip_from_seconds=203.5; skip_to_seconds=224.5` onto “As we
   proceed”), including Born Again / Greatest Hits copies of the same
   cut. A plan overlay may add ride/cue notes; it must not drop those
   skip tokens. A shorter ride that never reaches 3:24 is also legal.

## Must not

- Do not treat “start from 0:00 is iconic” as a blanket rule when the
  opening is a skit.
- Do not auto-skip every long first verse — many songs rap from bar 1
  with no skit. This is a skit/dialogue skip, not “skip the first verse.”
- Do not let a plan overlay drop library `skip_from_seconds` /
  `skip_to_seconds`. Those crate notes are the any-mix enforcement.
- Do not start Mixxx to prove the cue.

## Source

Ernest, 2026-08-28, after 50centgunitera mixed G.O.D. Pt. III from 0:00:

> we DO NOT want to play any of the first beginning part where it's
> just a skit. We almost never want to play any skits part. And we're
> cutting off Prodigy's first verse in the middle.
