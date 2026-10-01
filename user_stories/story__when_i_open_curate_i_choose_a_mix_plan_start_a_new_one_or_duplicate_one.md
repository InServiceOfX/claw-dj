<!-- pdd-story-status: accepted-2026-09-30 (preserve: Ernest likes this as-is) -->
<!-- pdd-story-areas: plan_picker, plan_store, api_plans_collection, api_plan_duplicate, playlist.html -->
<!-- pdd-story-prompts: prompts/brain/plan_store_Python.prompt -->

# User Story: Open Curate, then pick a previous mix plan, start a new one, or duplicate one

## Story

As a DJ, when I open claw-dj at `http://127.0.0.1:8787/#curate`, the first
thing I see is a **Mix plan** dropdown. I can reopen a previous mix to keep
working on it, press **New** to start a fresh one, or press **Duplicate** to
branch a copy of the current mix, so that I never lose an earlier set while
I try something new.

## Acceptance criteria (observable)

1. **Curate is home.** Opening `#curate` (or the root page) lands on
   1 · Curate set with the Mix plan dropdown at the top of the page.
2. **Reopen a previous mix.** The dropdown lists my saved plans by name.
   Choosing one makes it the active plan: its enabled set, finalized list,
   notes and built mix plan are what Curate, Create the mix and Arrange
   show, and it is still active after a server restart.
3. **New.** Pressing New creates an empty plan with its own name and makes
   it active. The previous plan is unchanged and still in the dropdown.
4. **Duplicate.** Pressing Duplicate creates a copy of the active plan (its
   set, order constraints, notes and transitions) under a new name and
   makes the copy active. Editing the copy never changes the original.
5. Rename and Delete stay available next to New and Duplicate; Delete only
   moves the plan to the plan trash, after a confirmation that names it.
6. If the plan changed on disk (for example another agent edited it), the
   page says so and offers Refresh rather than overwriting it.

## Out of scope

- Sharing plans between machines.
- Merging two plans.

## Related

- `story__when_i_curate_i_search_the_library_and_add_songs_to_the_enabled_set.md`
- `story__when_i_finalize_a_set_i_enrich_build_a_mix_plan_and_start_mixxx.md`
- Request: `docs/intents/request__build_mix_plan_refactor_and_gui_preservation.md`
