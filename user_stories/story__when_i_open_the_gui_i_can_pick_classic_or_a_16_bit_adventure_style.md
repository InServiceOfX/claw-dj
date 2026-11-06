<!-- pdd-story-status: drafted-2026-10-31 -->
<!-- pdd-story-areas: playlist.html, theme_adventure.css, api_static_assets -->

# User Story: Pick the Classic look or a 16-bit adventure look for the GUI

## Story

As a DJ using the local claw-dj GUI, I keep today's look as **Classic**: a
utilitarian, text-first browser app with dark terminal-style, neon-green logs
that show progress. I can also switch to a **16-bit** look with the warmth of a
cozy SNES-era adventure or farming game: wooden signs, parchment panels, chunky
pixel borders, and text boxes for logs.

The 16-bit look is a skin, not a different app. I can see as many tracks and
track listings as in Classic, with type slightly bigger, and every control
does exactly what it does in Classic, or better.

## Acceptance criteria (observable)

1. **Classic is the default and unchanged.**
   - A first visit, a private window, or a browser that blocks site storage
     shows Classic.
   - Classic's layout, colours, fonts and density are what they were before.
     The only addition is the small style switch in the header.
   - Every 16-bit rule is scoped under `html[data-ui-theme="adventure"]`, so
     none of it can leak into Classic.
2. **One switch, remembered per browser.**
   - The header has a two-button switch labelled **Classic** and **16-bit**.
     The pressed button shows the current style (`aria-pressed`).
   - The choice is saved in this browser's `localStorage` (`clawdj.uiTheme`).
     Every storage read and write is wrapped in try/catch; on failure the page
     stays on Classic and keeps working.
   - The saved style is applied before first paint, so the page does not flash
     Classic and then change.
3. **Same functionality in both styles.**
   - Curate, Create the mix and Arrange work the same: search, filters, track
     checkboxes, the preview dock and its ▶ buttons, Ask the DJ brain,
     Finalize, Analyze & enrich, Build, Start mix (still confirmation-gated),
     Arrange drag/keyboard reordering, bunches, transition cards, the
     transition editor, Audition, Refresh and the journal.
   - Switching style changes no page logic, plan data, selection or playback.
     It never starts Mixxx.
4. **Track lists stay dense and legible.**
   - Library, enabled set, finalized set, candidate order and Arrange rows keep
     Classic's row heights and columns. Body and row text is about 1–2px
     bigger than Classic.
   - Body text uses a readable rounded system font. The pixel-style monospace
     treatment is for headings, labels, BPM/key and logs only.
5. **Logs stay readable.**
   - The progress console keeps its bright green text, restyled as a framed
     in-game text box on a dark blue ground with strong contrast.
6. **Accessible and responsive.**
   - Keyboard focus is clearly visible: a thick dashed outline.
   - The existing phone and tablet layouts still work, and press animations
     respect `prefers-reduced-motion`.
7. **Original, offline art only.**
   - All art is built from CSS gradients and box-shadows, with no images and
     no network-loaded fonts, so the GUI works offline.
   - The style uses no game sprites, logos, fonts or character names, and no
     trademarked game names appear in the UI.

## Out of scope

- No new pages, controls or workflow changes. Improvements to function belong
  in their own stories and apply to both styles.
- No dark-mode variant of either style.

## Source

Ernest, 2026-10-31:

> as a user, I want to preserve the UX design language we have currently
> which is a very utilitarian, text based, functional, web application,
> browser based web application with some terminal, neon green log like parts
> to it to show progress. As a user I want to preserve that as "classic" while
> also having a UX that is Stardew Valley-like, Super Mario World or Legend of
> Zelda for the SNES, but adapted appropriate enough that we can see all the
> tracks and track listings etc. just as much as classic view (I'm talking
> about the font sizes, etc., though make them slightly bigger). But
> nevertheless it has the same functionality or better as a UX as what I call
> now the classic view please.
