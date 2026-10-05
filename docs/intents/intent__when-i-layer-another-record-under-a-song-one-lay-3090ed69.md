# Intent: When I layer another record under a song, one layer at a time, lined up by harmony

<!-- pdd-intent-id: when-i-layer-another-record-under-a-song-one-lay-3090ed69 -->
<!-- pdd-intent-sha256: 3090ed69bc8d6a08d23695355fab9adccf6d6bdc106de0482961e4e992267414 -->

## Record

- Intent ID: `when-i-layer-another-record-under-a-song-one-lay-3090ed69`
- Kind: `add`
- Supersedes: none
- Approval ID: `when-i-layer-another-record-under-a-song-one-lay-3090ed69`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `3090ed69bc8d6a08d23695355fab9adccf6d6bdc106de0482961e4e992267414`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> As a DJ, when I layer another record (an instrumental, a sample source) under a different song, claw-dj keeps it unmuddled and lines it up by harmony, section by section.
> 1. At most one supporting layer at a time under the song; never two instrumentals at once.
> 2. Under a section that already carries its own bass (e.g. a chorus), the layer does not add a second bass: use its riff or hook part with its bass cut, a little under full (channel fader about 0.85).
> 3. Each layered section is lined up by measured harmony (beat-synced chroma), separately: a short odd-length break in the song (Ariana Grande's 4-beat break at 1:07) shifts it against the layer's 4-bar harmony loop, so one fixed offset for the whole song is wrong after it.
> 4. Which part of the layer plays is chosen by measurement (its bass-only part, chorus bars, the bar with a sampled hook), not guessed.
> 5. Layers come in and go out on short EQ ramps over a running bed; a deck only jumps to a new section while silent. Filters are brief 1-2 beat accents, never held.
> 6. A same-beat lineage over its own instrumental may keep a continuous bed (existing full-mix layering story); a different song gets selective layers.
> Example: Mo Money Mo Problems instrumental under Ariana Grande's Break Your Heart Right Back, 2026-10-04: two instrumentals and the instrumental's bass under her second chorus were "too much" and "muddled"; one layer with the bass cut at fader 0.85 under the chorus, and per-section offsets (instrumental beat = her beat + 8 mod 16 before the break, + 4 after), were accepted.

## Must Stay Unchanged

- At most one supporting layer at a time under the song; never two instrumentals at once.
- Filters are brief 1-2 beat accents, never held.

## Examples

- As a DJ, when I layer another record (an instrumental, a sample source) under a different song, claw-dj keeps it unmuddled and lines it up by harmony, section by section.
- Under a section that already carries its own bass (e.g.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
