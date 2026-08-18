# Intent: Preview a track quickly from the browser GUI

<!-- pdd-intent-id: through-the-browser-gui-http-127-0-0-1-8787-cura-88023c99 -->
<!-- pdd-intent-sha256: 88023c999421f9bb2cf4cd084310877b4ded6e27bf34d5b7959b260e3f48ef09 -->

## Record

- Intent ID: `through-the-browser-gui-http-127-0-0-1-8787-cura-88023c99`
- Kind: `add`
- Approval: user asked for a PDD user story and then implementation
- Source: inline chat 2026-08-18
- Request SHA-256: `88023c999421f9bb2cf4cd084310877b4ded6e27bf34d5b7959b260e3f48ef09`
- Planner note: keyword match suggested plan_types / plan_mix_build; those
  are the wrong product areas. This belongs to the playlist GUI.

## Original Request

> Through the browser GUI, http://127.0.0.1:8787/#curate or
> http://127.0.0.1:8787/#mix could the user preview a track quickly? We
> could use mixxx since it's expected to be available and already to go
> or, and only if it's lightweight, very low memory footprint, in the
> browser, some kind of audio player to preview the track, that doesn't
> require the user to install something else for the browser. Maybe this
> could be a user story in the context of PDD for claw-dj project. And
> once that user story is written, please implement

## Meaning (accepted)

- Quick audition from Curate and Mix (and Arrange, same GUI).
- Prefer a native in-tab player over Mixxx so decks stay free.
- No extra browser software.
- Then implement.

## Must stay unchanged

- Start mix / Analyze & enrich still use Mixxx.
- Enabling a track is still the checkbox, not Preview.
- Arbitrary disk files must not be streamable.
