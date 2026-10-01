<!-- pdd-story-status: accepted-2026-09-30 (preserve: Ernest likes this as-is) -->
<!-- pdd-story-areas: playlist_editor, playlist.html, archive_mix_plan, plan_bunch_activation -->

# User Story: Search my music, add songs from Library to the Enabled set, clear a set safely, Finalize

## Story

As a DJ curating a set, I type in the search box to find songs in my
collection, click to move them from **Library** into the **Enabled set**,
preview any song right there, and when I want to start over I clear the set,
optionally archiving it first. When the set is right I press **Finalize for
Mixxx** to lock it in and go to Create the mix.

## Acceptance criteria (observable)

1. **Search.** Typing in the search field filters the Library by title,
   artist, album or path as I type; an artist filter narrows it further.
2. **Add with one click.** Each Library row has a control that enables the
   song; it appears in the Enabled set immediately with its BPM and key (or
   a visible "missing" marker). Unchecking removes it. The set count updates.
3. **Order of picking does not matter.** The Enabled set is a pool. The
   order I enabled songs in is not the playback order (see the Build mix plan
   story).
4. **Preview.** Every Library and Enabled-set row has a ▶ preview button
   that plays the song in the built-in player at the bottom of the page
   without loading Mixxx and without toggling the song on or off.
5. **Archive first + Clear set.** Next to the Enabled set there is an
   **Archive first** checkbox (on by default) and a **Clear set…** button.
   Clearing with Archive first on saves the current finalized playlist and
   mix plan before emptying the set; with it off, the set is emptied without
   an archive. Clear set always asks for confirmation.
6. **Finalize for Mixxx.** The Finalize for Mixxx button locks the current
   Enabled set as the finalized list for the active plan and opens 2 ·
   Create the mix showing exactly that list.

## Out of scope

- Ask the DJ brain (agent picks) on Curate; its engines are a separate story.

## Related

- Preview details: `story__when_i_curate_or_build_a_mix_i_can_preview_a_track_in_the_browser.md`
- Collection and scan: `story__when_i_mount_a_music_volume_i_can_index_it_and_curate_a_set_with_the_dj_brain.md`
- Request: `docs/intents/request__build_mix_plan_refactor_and_gui_preservation.md`
