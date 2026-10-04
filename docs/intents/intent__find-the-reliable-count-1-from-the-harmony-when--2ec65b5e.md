# Intent: Find the reliable count 1 from the harmony when the drums are too syncopated to count

<!-- pdd-intent-id: find-the-reliable-count-1-from-the-harmony-when--2ec65b5e -->
<!-- pdd-intent-sha256: 2ec65b5e63cf7dc596e8de98c3985df988c207503e2491cfc2ded611b7b90614 -->

## Record

- Intent ID: `find-the-reliable-count-1-from-the-harmony-when--2ec65b5e`
- Kind: `add`
- Supersedes: none
- Approval ID: `find-the-reliable-count-1-from-the-harmony-when--2ec65b5e`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `2ec65b5e63cf7dc596e8de98c3985df988c207503e2491cfc2ded611b7b90614`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> As a DJ, when records are heavily syncopated or live-drummed, I want claw-dj to stop trusting drum onsets and the grid to find count 1, and instead find the reliable count 1, and the matching bar between two songs, from the harmony.
> 1. Count 1 within a song: from chroma (which notes sound, drums mostly ignored), find where the song's harmonic loop or phrase restarts and its real local tempo; use that as the bar and phrase grid for cueing and blending instead of a constant Mixxx grid that drifts on live drums.
> 2. Matching bar between songs: when two songs share harmonic material (a sample, interpolation, remix or cover), cross-correlate their chroma at several speed ratios to find which bar of one plays the same music as which bar of the other, and how much one was slowed.
> 3. Blend on it: start the incoming song exactly on that matched count 1 at the outgoing song's live tempo, one deck tuned so the shared material agrees in pitch, no quantize snap on that start, and the outgoing deck fading slowly in unison.
> 4. Human anchor: a count 1 the DJ names by ear (for example a sung word) is cross-checked against the measurement; disagreement is reported, never silently overridden.
> 5. Remembered: verified count-1 positions, matched bars, live tempos and pitch offsets are written to both songs' DJ notes so any agent harness reuses them.
> 6. Analysis only: the measurement decodes audio for numbers, never renders audio to play.
> Example: I'm Coming Out into Mo Money Mo Problems. Count-based blends kept failing; chroma showed Mo Money's 0:00 is her 2:55.6 reprise slowed from her live ~110.7 BPM to 104.4, phrase every 4 bars; starting Mo Money's count 1 on that bar in unison with a 40-count fade was verified great on 2026-10-03.

## Must Stay Unchanged

- Human anchor: a count 1 the DJ names by ear (for example a sung word) is cross-checked against the measurement; disagreement is reported, never silently overridden.
- Analysis only: the measurement decodes audio for numbers, never renders audio to play.

## Examples

- As a DJ, when records are heavily syncopated or live-drummed, I want claw-dj to stop trusting drum onsets and the grid to find count 1, and instead find the reliable count 1, and the matching bar between two songs, from the harmony.
- Matching bar between songs: when two songs share harmonic material (a sample, interpolation, remix or cover), cross-correlate their chroma at several speed ratios to find which bar of one plays the same music as which bar of the other, and how much one was slowed.
- Human anchor: a count 1 the DJ names by ear (for example a sung word) is cross-checked against the measurement; disagreement is reported, never silently overridden.

## Candidate Product Areas

- Reusable live Mixxx moves for live mini-experiments and hand-built live mixes: library lookup by artist/title (folder hint for duplicate...
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
