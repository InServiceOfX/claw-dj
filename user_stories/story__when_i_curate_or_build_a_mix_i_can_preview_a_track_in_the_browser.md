<!-- pdd-story-status: drafted-2026-08-18 -->
<!-- pdd-story-areas: playlist_editor, playlist.html, arrange.js -->

# User Story: Preview a library track from the browser GUI

## Story

As a DJ using the local playlist GUI (`#curate` or `#mix`, and Arrange), I can
press Preview on a track and hear it immediately in the same browser tab, so I
can decide whether it belongs in the set without loading Mixxx or installing a
browser plugin.

## Why not Mixxx for this

Mixxx is the performance instrument (Analyze & enrich, Start mix). Using it to
audition a Curate row would steal a deck, interrupt a live set, require Mixxx
to be running, and trip extra macOS file-permission prompts. Quick listen is a
different job.

## Acceptance criteria (observable)

1. **Curate**
   - Every library row and enabled-set row has a Preview control that does
     not toggle enable/disable.
   - Preview starts playback of that file in the page.

2. **Create the mix**
   - Each finalized-set row has the same Preview control.

3. **Arrange**
   - Each arranged track has Preview.

4. **Player**
   - One native HTML5 `<audio>` player (no extra browser install, no JS
     audio framework).
   - Starting a new preview stops the previous one.
   - The player shows which track is playing and can pause/seek/stop.

5. **Server**
   - `GET /api/preview?track_id=…` streams only a track that is already in
     the loaded library index (`track_id` is the absolute path).
   - A path that exists on disk but is **not** an indexed track is rejected
     (404). Relative paths and `..` are rejected.
   - A missing/unmounted indexed file is 404, not a hang.
   - Byte `Range` requests are honored so seeking does not load the whole
     file into RAM.
   - Mixxx is not started, loaded, or spoken to.

## Out of scope

- Previewing a transition (EQ/crossfade). That remains Mixxx / transition
  preview tooling.
- Transcoding formats the browser cannot decode (some AIFF/FLAC).
- Remote or multi-user access. This stays loopback-only like the rest of
  `:8787`.

## Related

- Finalize / Start mix: Mixxx stays the live path.
  `story__when_i_finalize_a_set_i_enrich_build_a_mix_plan_and_start_mixxx.md`
