# Control local OBS from any AI harness without surrendering Twitch credentials

As the operator of claw-dj, I want my local OBS to be inspectable and controllable
through a Python library and JSON command-line tools, so that Hermes or another
agent can help present my live Mixxx performance without needing a Twitch
password or stream key.

Source: original request in
`docs/intents/intent__harness-neutral-local-obs-control-for-claw-dj-a8742751.md`;
accepted Python/CLI interpretation in `docs/intents/OBS_CONTROL_APPROVAL.md`.

## Acceptance

- From any local harness, I can discover supported actions and read OBS's
  real scene/input/output state once I have enabled authenticated local control.
- I can explicitly ask for scene/source/audio changes through the same tools;
  the tools reject writes without a separate write-permission declaration.
- Stream and recording start/stop require an additional output declaration.
  Building, discovery, connection tests and inspection never start them.
- OBS keeps my Twitch login. The tools do not extract Twitch tokens, stream
  keys or arbitrary service/source settings, and never print the WebSocket
  password or raw failures that might contain secrets.
- I can keep the WebSocket password in private local storage, entered through
  my own hidden terminal prompt, rather than chat or source control.
- Existing Mixxx behavior, music and personal plans remain unchanged.
- If the WebSocket server is disabled or authentication is not supplied, I
  receive an honest failure instead of a claimed live integration success.

## Evidence boundaries

Deterministic synthetic protocol/CLI tests prove transport and permission
contracts. Real OBS inspection must be reported separately. No synthetic
fixture proves real audio routing, a successful Twitch broadcast or subjective
mix quality. Public actions remain human-gated.

<!-- pdd-story-prompts: prompts/hands/obs_control_Python.prompt, prompts/hands/obs_cli_Python.prompt -->
