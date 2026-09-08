<!-- pdd-story-status: implemented-awaiting-browser-acceptance-2026-09-05 -->
<!-- pdd-story-areas: plan_notes, arrange, playback_intent -->
<!-- pdd-story-prompts: prompts/brain/web/arrange_JavaScript.prompt, prompts/brain/plan_notes_Python.prompt -->
<!-- pdd-story-dev-units: arrange_JavaScript.prompt, plan_notes_Python.prompt -->

# User Story: Save how I want a particular song to be played

As a DJ/listener, I want to add and review a note on a particular recording
about how it should be played, so instructions such as avoiding a skit are
not lost between listening, planning and the next mix.

## Acceptance criteria

1. Find playback-note editing from Mix/Arrange on the song, distinct from the
   transition note between two songs. Edit multiple lines and see the current
   note before changing it; do not lose older instructions just by opening it.
2. Identify the exact recording and note scope. A save for this plan must not
   rewrite library defaults or change the song's note in another plan. Show
   whether the note is inherited or overridden; restore the library default
   only as an explicit, confirmed action.
3. Cancel without writing. Keep ordinary failed saves editable and explain
   stale revisions rather than silently overwriting/retrying. A plan switch
   must not redirect an in-flight save or its completion to the new plan.
4. Saving records the request, not proof of playback enforcement. Explain
   which directives are supported, that free-text intent may need review,
   and that a build is required to produce new playback events. Never alter
   the current live mix merely because a note was saved.
5. Who Shot Ya: preserve the musical opening and gradual blends while noting
   that the spoken scene should not be played. Approximate 3:30–3:50 is not
   a certified region; the [skit story](story__when_a_track_opens_with_a_skit_i_skip_it.md)
   specifies the later reviewed skip/early-exit behavior.
6. Notes remain inspectable by humans and agents. Unavailable audio is not
   grounds to discard the note; text editing must not move/reorder the track.
7. Saving one song or refreshing Arrange must not discard another song's
   unsaved draft. Retain drafts by original plan and recording across in-app
   plan switches, and warn before browser reload/navigation discards them.
   An old visible form must reject Save/Clear after switching plans; a late
   response must not repaint an old plan under a new plan's identity.
8. Note editing works on plans with active bunches, including the current
   three-bunch heavy-rotation plan; the rendering path must not fail before
   the song editors become reachable.

Source: [Ernest's request](../docs/intents/request__song_playback_notes_and_skit_avoidance.md).
