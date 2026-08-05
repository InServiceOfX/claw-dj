#!/usr/bin/env bash
# One command to get claw-dj running: launches the patched Mixxx with the
# control API, waits for it to come up, then opens the playlist editor.
#
# Usage: scripts/start.sh [--mixxx-port PORT]
#
# Prereqs (one-time, see docs/BUILD_MIXXX.md and PROGRESS.md):
#   - the patched Mixxx fork built and installed as /Applications/Mixxx.app
#   - uv sync already run in this repo
set -euo pipefail
cd "$(dirname "$0")/.."

PREFERRED_MIXXX_PORT=9995
EXPLICIT_MIXXX_PORT=""
EDITOR_PORT=8787
EDITOR_URL="http://127.0.0.1:${EDITOR_PORT}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mixxx-port)
      [ "$#" -ge 2 ] || { echo "--mixxx-port needs a value" >&2; exit 2; }
      EXPLICIT_MIXXX_PORT="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: scripts/start.sh [--mixxx-port PORT]"
      exit 0
      ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

DISCOVER_ARGS=(discover --preferred "$PREFERRED_MIXXX_PORT")
if [ -n "$EXPLICIT_MIXXX_PORT" ]; then
  DISCOVER_ARGS+=(--explicit "$EXPLICIT_MIXXX_PORT")
fi

if MIXXX_PORT=$(uv run python -m hands.mixxx_control "${DISCOVER_ARGS[@]}" 2>/tmp/clawdj-mixxx-discovery.err); then
  echo "Mixxx control API already running on port $MIXXX_PORT — reusing it."
else
  DISCOVERY_STATUS=$?
  if [ "$DISCOVERY_STATUS" -eq 3 ]; then
    echo "Mixxx is running, but no reachable control API matched the allowed candidates." >&2
    sed -n '1,3p' /tmp/clawdj-mixxx-discovery.err >&2
    echo "No second Mixxx instance was started." >&2
    exit 1
  fi
  if [ "$DISCOVERY_STATUS" -ne 4 ]; then
    sed -n '1,5p' /tmp/clawdj-mixxx-discovery.err >&2
    exit "$DISCOVERY_STATUS"
  fi
  MIXXX_PORT="${EXPLICIT_MIXXX_PORT:-$PREFERRED_MIXXX_PORT}"
  echo "Starting Mixxx with the control API on port ${MIXXX_PORT}..."
  open -a Mixxx --args --control-api-port "$MIXXX_PORT"
  n=0
  until uv run python -m hands.mixxx_control probe "$MIXXX_PORT" || [ "$n" -ge 40 ]; do
    sleep 3
    n=$((n + 1))
  done
  if ! uv run python -m hands.mixxx_control probe "$MIXXX_PORT"; then
    echo "Mixxx didn't open the control API within 2 minutes." >&2
    echo "Check: is /Applications/Mixxx.app the patched fork build, not stock Mixxx?" >&2
    echo "See docs/BUILD_MIXXX.md." >&2
    exit 1
  fi
  echo "Mixxx control API is up."
fi

echo "Opening the playlist editor..."
editor_page="$(curl -fsS --max-time 2 "$EDITOR_URL/" 2>/dev/null || true)"
case "$editor_page" in
  *"<title>claw-dj playlist</title>"*)
    echo "Playlist editor already running on port $EDITOR_PORT — reusing it."
    # Multi-plan UI loads /web/*.js and /api/plans. An old editor process can
    # still serve the HTML shell while those routes 404 — force a restart then.
    if ! curl -fsS --max-time 2 -o /dev/null "$EDITOR_URL/web/plan_picker.js" 2>/dev/null \
      || ! curl -fsS --max-time 2 -o /dev/null "$EDITOR_URL/api/plans" 2>/dev/null; then
      echo "That editor looks stale (missing multi-plan routes)." >&2
      echo "Stop it, then start again:" >&2
      echo "  scripts/stop.sh" >&2
      echo "  scripts/start.sh" >&2
      exit 1
    fi
    if ! curl -fsS --max-time 2 -X POST \
      -H 'Content-Type: application/json' \
      -d "{\"port\":${MIXXX_PORT}}" \
      "$EDITOR_URL/api/mix/control-port" >/dev/null; then
      echo "Could not push Mixxx control port $MIXXX_PORT to the running editor." >&2
      echo "Stop and restart the editor:" >&2
      echo "  scripts/stop.sh && scripts/start.sh" >&2
      exit 1
    fi
    open "$EDITOR_URL"
    ;;
  *)
    if nc -z 127.0.0.1 "$EDITOR_PORT" 2>/dev/null; then
      echo "Port $EDITOR_PORT is already used by something other than the claw-dj playlist editor." >&2
      echo "Inspect it with: lsof -nP -iTCP:$EDITOR_PORT -sTCP:LISTEN" >&2
      echo "If it is a leftover editor, stop it with: scripts/stop.sh" >&2
      exit 1
    fi
    uv run python -m brain.playlist_editor --host 127.0.0.1 --port "$EDITOR_PORT" \
      --mixxx-control-port "$MIXXX_PORT" --open
    ;;
esac
