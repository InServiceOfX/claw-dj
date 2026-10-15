<!-- pdd-story-status: drafted-2026-10-14 -->
<!-- pdd-story-areas: audition_transition, run_mix_plan, transition, playlist_editor, arrange, plan_client, preview_transitions -->
<!-- pdd-story-prompts: prompts/hands/audition_transition_Python.prompt, prompts/brain/web/arrange_JavaScript.prompt, prompts/brain/web/plan_client_JavaScript.prompt -->
<!-- pdd-story-dev-units: audition_transition_Python.prompt, arrange_JavaScript.prompt, plan_client_JavaScript.prompt -->

# User Story: When I audit a mix, I audition one transition live in Mixxx and step between them

## Story

As a DJ auditing a built mix, I pick one transition and hear **Mixxx itself**
play it: a few bars of the outgoing song from exactly where the full mix
would be, the real transition, and a short stretch of the incoming song.
Then I step to the previous or next transition, replay the same one, or
stop. I audit and edit transitions one at a time instead of listening to a
whole multi-hour mix, and without a rendered audio file standing in for the
live mix.

## Acceptance criteria (observable)

1. **Same starting point as the full mix.** The outgoing song starts a
   configurable lead-in (default 8 bars) before the planned fade start on its
   own beatgrid — the plan's `phase_anchor.planned_anchor_beat_index`, which
   already counts the previous blend, skips and backbeat nudges. The
   transition lands on the same beat of the bar as in the full mix.
2. **Same incoming cue.** The incoming song is cued exactly as the plan's
   load or preload event cues it.
3. **Same deck state.** The outgoing deck is at the tempo and pitch the full
   run would be holding (play_bpm hold, keep-blend tempo, settle target),
   with keylock and quantize on, EQ and filter open, and the crossfader on the
   outgoing side.
4. **Same transition code.** The blend is performed by the full mix runner's
   own transition path — sync or phase-only sync, the `snare_align` one-beat
   jump, EQ and fader curves, the runtime bar guard — not a second
   implementation.
5. **Step, replay, stop.** I can go to the previous or next transition by
   number, replay the current one, and stop at any time; stop silences both
   decks and resets their EQ and filter. The page shows which transition is
   playing (number of total) and whether it is in the lead-in, the
   transition or the tail.
6. **I start it.** Playback starts only when I press a button (GUI) or run
   the command without `--dry-run` (CLI). A dry run prints what would happen
   and never connects to Mixxx.
7. **Never hijack.** If a full mix run is playing, or a Mixxx deck is
   already playing, the audition refuses with a clear message instead of
   taking the decks. Taking over playing decks is a separate, explicit
   choice.
8. **Edit, rebuild, re-audition.** Every audition reads the current built
   plan file, so after I edit a transition and rebuild, Replay plays the new
   version. The page tells me when the plan has edits that are not built yet.
9. **Honest about approximations.** Where the plan cannot fix the starting
   point exactly (right after a vocal-over-bed layer, after a same-song
   handoff, or an older plan without `phase_anchor`), the audition says so.

## Must not

- Do not render audio to audition a transition.
- Do not start playback without an explicit button press or command.
- Do not take over the decks of a running mix.
- Do not modify the plan, its notes or its built artifact while auditioning.

## Example

A 15-hour R&B mix has 256 transitions. Ernest opens Arrange, presses
"Audition in Mixxx" under transition 51 (Aaliyah — Rock The Boat into Trey
Songz — Slow Motion, a `snare_align` blend). Mixxx plays 32 beats of Rock The
Boat ending on the planned fade start, the synced blend with the one-beat
snare jump, then 16 bars of Slow Motion, and stops. He presses Next to hear
transition 52, Previous to go back, edits 51's beats, rebuilds, and presses
Replay to hear the edit.

## Source

Ernest, 2026-10-14:

> I'd rather have Live in Mixxx and see about "sunsetting" the render method
> ... work on that live in Mixxx being able to skip forward or backward
> transitions so we could edit and audit for me the user.

The ffmpeg render (`brain/preview_transitions.py`) is deprecated by this
story: it starts the fade at cue + ride and ignores the previous blend,
skips, the next-beat anchor, `snare_align` and grid alignment. It is removed
after Ernest confirms the live audition.

Related: `story__live_mini_experiments_on_a_section_of_a_mix.md` (live, no
rendered audio), `story__when_i_blend_i_match_the_snare_not_just_the_beat.md`
(`snare_align`).
