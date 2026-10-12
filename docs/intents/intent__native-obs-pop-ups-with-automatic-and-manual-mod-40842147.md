# Intent: Native OBS pop-ups with automatic and manual modes

<!-- pdd-intent-id: native-obs-pop-ups-with-automatic-and-manual-mod-40842147 -->
<!-- pdd-intent-sha256: 408421471e4687254e0d68e5c4c95c252f4a502ef8842354af510db70ee9f593 -->

## Record

- Intent ID: `native-obs-pop-ups-with-automatic-and-manual-mod-40842147`
- Kind: `add`
- Supersedes: none
- Approval ID: `native-obs-pop-ups-with-automatic-and-manual-mod-40842147`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `408421471e4687254e0d68e5c4c95c252f4a502ef8842354af510db70ee9f593`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> Build the native OBS version of the pop-ups for the lowest memory footprint on the stream machine: drive OBS's own text sources through the existing authenticated OBS control instead of a browser source, sized to my actual (smaller than 1920x1080) canvas because I want to spend less bandwidth on video and more on audio. Give it an automatic mode for unattended streams and a manual mode where I can flip forward, go back, show, hide, pause and resume cards. Let me preview the text without OBS.

## Must Stay Unchanged

- Let me preview the text without OBS.

## Examples

- None stated.

## Candidate Product Areas

- Transparent OBS browser-source overlay serving brain.popups cards over HTTP (/overlay, /card, /health); knows the playing song from Mixxx...
- Harness-neutral OBS WebSocket v5 client with strict action schemas, loopback-only endpoints, sanitized errors, deadlines and explicit...
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Pop-up card content and choice: agent-written sourced facts (brain/popup_facts.json, no attribution mark) and authors' commentary from...
