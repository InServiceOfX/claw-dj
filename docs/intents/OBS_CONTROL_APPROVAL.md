# Accepted OBS control interpretation

## Source and approval

Original request is preserved by PDD in
`intent__harness-neutral-local-obs-control-for-claw-dj-a8742751.md`.
The user selected: "Approve Python library + JSON CLI; keep public/output actions explicitly gated."
The user then instructed: "Also keep working on our OBS integration please until success".

The user clarified that the channel's intended operation is a live Mixxx
performance and not music-bearing VOD playback. Policy discussion is separate
from implementing the local OBS tools; this document makes no Twitch eligibility
or music-rights determination.

## Current intended behavior

Python is the accepted implementation language. The original intake inferred
Rust from the open-ended original request; that inference is not the accepted
technology choice. OBS presentation control is a separate unit, not a change
to brain.plan_cli or hands.live_kit. Use native obs-websocket v5 behind one Python
client and JSON CLI. MCP is deferred, with the client reusable as its backend.

- Read version, scene/input inventories, scene items, audio mute/volume and
  output/statistics state; export an explicitly requested preview PNG.
- Explicitly gated scene create/switch/preview, visibility, mute, volume,
  existing text-source updates, synthetic color-source creation and studio mode.
- Explicit start/stop streaming/recording functions exist but require separate
  output and write permissions. Never invoke outputs for connection testing.
- Localhost-only client; authenticated WebSocket handshake when OBS requires it.
- Preserve existing mixes, Mixxx timing, original songs and personal scenes.
- No arbitrary RPC, stream service settings, Twitch tokens, stream keys,
  source deletion, arbitrary capture/browser/media source creation or hidden
  recording/streaming.
- Credentials are supplied by local hidden-input setup or secret manager;
  no secret text in chat, arguments, outputs, Git, prompts or evidence.

## Proof

Use unittest RED/GREEN tests, synthetic protocol fixtures and CLI failure/gate
checks. Test the actual OBS connection separately with version/status/scenes
and no mutations or outputs. A disabled server or missing locally authorized
password is a blocker, not a successful real-OBS verification.

## PDD evidence boundary

`pdd intent plan` ran using the exact request. Approved `intent apply --no-sync
--no-story` persisted the request/current-intent entry, then made no visible
progress through its model-backed architecture step for more than six minutes.
The agent terminated that process before allowing the wrong inferred Rust
scope to generate unrelated changes. OBS prompts, implementation and scoped
manifest entries are maintained directly and tested; automatic generation
and semantic certification are not claimed. The immutable original request
and its intake metadata remain available, with this accepted interpretation
resolving the technology/target inference.

The attempted reviewed-byte PDD baseline was rejected because base/head do not
contain `.pdd/repository-id`. No repository-wide PDD bootstrap was performed to
bypass that prerequisite. This does not invalidate the executable tests, but no
PDD fingerprint baseline or canonical certification is claimed.
