# Local OBS control for any agent harness

## Scope

OBS owns the Twitch login and stream service. This adapter only uses OBS's
native WebSocket v5 API. It never reads Twitch tokens, stream keys, OBS stream
service settings, or arbitrary source settings. There is no MCP dependency.
Hermes, Codex, Claude Code and other local agents can invoke the same JSON CLI
or import the same Python client. This is macOS/Linux tooling; the private-file
helper uses POSIX ownership, mode and no-follow checks.

Original intent and approval: `docs/intents/intent__harness-neutral-local-obs-control-for-claw-dj-a8742751.md`.
The accepted choice is Python library + JSON CLI with explicit write/output
permission gates. Live Mixxx performances are distinct from VOD playback;
this integration does not make Twitch policy or music-rights decisions.

## Installation

From the checkout:

```sh
uv sync --extra obs
.venv/bin/python -m hands.obs_cli capabilities
```

After installation, `.venv/bin/claw-obs` is the equivalent executable. It can
be called by absolute path from any working directory; no harness-specific
plugin or active shell virtualenv is required.

The optional `obs` extra installs websocket-client, not another OBS plugin.
OBS 28+ includes obs-websocket. OBS must already be running. The tool does not
launch OBS or alter its preferences automatically. It defaults to
`127.0.0.1:4455`; `--port` selects another configured port. Only literal
loopback addresses and localhost are accepted. Do not expose the server on
an untrusted network. OBS may listen on all interfaces: client-side loopback
restriction does not change server binding. Keep authentication enabled and
use firewall restrictions if needed.

## One-time local authentication

In OBS: Tools -> WebSocket Server Settings. Enable the server, retain
Enable Authentication, and Apply. Do not disable authentication to avoid
password setup. A firewall/OS permission prompt requires the user's decision.

Run this directly in your own terminal, not through an agent tool that captures
stdin or a chat message:

```sh
.venv/bin/python -m hands.obs_cli setup-password
```

Paste only the OBS WebSocket password into the hidden prompt. The helper creates
`~/.config/claw-dj/obs-websocket-password` with mode 0600 and refuses overwrite.
It does not read OBS's saved password or Twitch credentials. To use another
private secret file, pass `--password-file /absolute/path`. The process
variable `OBS_WEBSOCKET_PASSWORD` is an alternative for a secret manager;
never put its literal value in shell commands/history. Explicit files override
the environment. Password files must be regular, owned by the current user,
private to that user and not symlinks. Setup rejects paths inside the source
checkout and requires an interactive terminal. Never commit this file.

## Read-only checks

```sh
.venv/bin/python -m hands.obs_cli version
.venv/bin/python -m hands.obs_cli status
.venv/bin/python -m hands.obs_cli scenes
.venv/bin/python -m hands.obs_cli inputs
.venv/bin/python -m hands.obs_cli scene-items --data '{"sceneName":"Scene"}'
.venv/bin/python -m hands.obs_cli audio --data '{"inputName":"Mixxx"}'
.venv/bin/python -m hands.obs_cli screenshot --data '{"sourceName":"Scene"}' --save /tmp/claw-dj-obs-preview.png
```

Screenshot defaults are 640x360. Optional `width` and `height` control the
request. PNGs are written only to a new, explicitly chosen file with an
existing parent directory. No overwrites. Keep production images outside
Git; the CLI rejects screenshot destinations inside the source checkout.
The CLI returns the screenshot path, not a base64 dump. An OBS screenshot
shows its scene content, not necessarily the app's chrome.

Every normal command prints one JSON object:
`{"ok":true,"action":"...","data":{...}}` or
`{"ok":false,"action":"...","error":"..."}`.
Exit codes: 0 success; 2 invalid/gated input or local secret/file error;
1 operation/connection/protocol failure. `--help` is human-readable.
Failures never print raw transport exceptions, OBS comments or credentials.
No automatic retries of mutations.

## Mutation contract

Writes require both an explicit human instruction and `--allow-write`.
The flag declares authorization; it does not prove a human gave it. Agents
must obtain authorization before using it, particularly while outputs are active.

Actions and JSON fields:

- `scene-create`, `scene-switch`, `scene-preview`: `sceneName`.
- `source-visible`: `sceneName`, `sceneItemId`, `sceneItemEnabled` (boolean).
- `input-mute`: `inputName`, `inputMuted` (boolean).
- `input-volume`: `inputName`, `inputVolumeDb` (-100 to 0 dB, finite).
- `text-set`: `inputName`, `text`; only existing OBS text-source kinds.
- `color-create`: `sceneName`, `inputName`, `color`, `width`, `height`;
  color is an unsigned 32-bit OBS ABGR integer, not a CSS color string.
- `studio-mode`: `studioModeEnabled` (boolean).

Example, only after authorization:

```sh
.venv/bin/python -m hands.obs_cli scene-switch --allow-write --data '{"sceneName":"Live"}'
```

`stream-start`, `stream-stop`, `record-start`, `record-stop` additionally require
`--allow-output`. Their data object is empty. Enabling output flags does not
bypass Twitch policies, a rights decision or the need for a specific human
instruction. Do not run these commands to test the connection. There are no
output toggle commands, raw RPC calls, script execution, deletion, arbitrary
input creation, or stream service configuration. Source deletion and arbitrary
browser/media/capture source creation are deliberately not part of v1.

Scene/source names must come from actual OBS inventory, not guesses. Source
visibility uses the scene item ID, not the input ID. Request data is schema
validated and unexpected fields are rejected. Keep all beat-critical Mixxx
work in existing hands/Rust code; OBS is a separate presentation surface.

## Python interface

Import `OBSControl` and `validate_action` from `hands.obs_control`.
Construct with `host`, `port`, `password`, `timeout_s`; use a context manager.
Call `execute(action, data, allow_write=False, allow_output=False)`.
The connection is lazy: construction and validation do not start outputs or
connect until a permitted execute. The client validates actions even when
called directly, without the CLI. `close()` releases the connection.

The client supports authenticated Hello/Identify/Identified, request IDs and
response status, bounded deadlines and interleaved OBS events. It has no
Twitch API access. OBS's own Twitch authorization does not grant this CLI
Twitch chat/moderation API access. MCP can later wrap these same functions,
without duplicating transport or permission policy.

## Verification

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_obs_*.py' -v
```

Tests use synthetic data and protocol fixtures. They must not read personal
OBS secrets, start outputs, alter personal scenes or operate Mixxx. Separately
verify version/status/scenes/inputs against real OBS after local authentication.
A synthetic protocol test is not evidence of real streaming, recording,
audio routing or performance quality. A live read-only failure is a blocker,
not permission to disable OBS authentication.

References:
- https://obsproject.com/kb/remote-control-guide
- https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
