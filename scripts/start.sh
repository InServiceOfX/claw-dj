#!/usr/bin/env bash
# One command to get claw-dj running: launches the patched Mixxx with the
# control API, waits for it to come up, then opens the playlist editor.
#
# Usage: scripts/start.sh
#
# Prereqs (one-time, see docs/BUILD_MIXXX.md and PROGRESS.md):
#   - the patched Mixxx fork built and installed as /Applications/Mixxx.app
#   - uv sync already run in this repo
set -euo pipefail
cd "$(dirname "$0")/.."

MIXXX_PORT=9995
EDITOR_PORT=8787
EDITOR_URL="http://127.0.0.1:${EDITOR_PORT}"

if ! nc -z 127.0.0.1 "$MIXXX_PORT" 2>/dev/null; then
  # `open -a Mixxx --args ...` SILENTLY DROPS the args when Mixxx is already
  # running: macOS just focuses the existing instance. So a Mixxx that was
  # launched from the Dock (or that crashed its API and got relaunched) can
  # never gain the control API this way, and the old failure message blamed
  # the wrong thing entirely. Detect it and say what actually needs doing.
  if pgrep -f "Mixxx.app/Contents/MacOS/Mixxx" >/dev/null 2>&1; then
    echo "Mixxx is already running, but WITHOUT the control API on port ${MIXXX_PORT}." >&2
    echo "macOS ignores --args for an app that is already open, so this script" >&2
    echo "cannot add the API to that instance." >&2
    echo "Quit Mixxx completely (Cmd+Q) and re-run this script." >&2
    exit 1
  fi
  echo "Starting Mixxx with the control API on port ${MIXXX_PORT}..."
  open -a Mixxx --args --control-api-port "$MIXXX_PORT"
  n=0
  until nc -z 127.0.0.1 "$MIXXX_PORT" 2>/dev/null || [ "$n" -ge 40 ]; do
    sleep 3
    n=$((n + 1))
  done
  if ! nc -z 127.0.0.1 "$MIXXX_PORT" 2>/dev/null; then
    echo "Mixxx didn't open the control API within 2 minutes." >&2
    echo "Check: is /Applications/Mixxx.app the patched fork build, not stock Mixxx?" >&2
    echo "See docs/BUILD_MIXXX.md." >&2
    exit 1
  fi
  echo "Mixxx control API is up."
else
  echo "Mixxx control API already running on port $MIXXX_PORT — reusing it."
fi

echo "Opening the playlist editor..."
editor_page="$(curl -fsS --max-time 2 "$EDITOR_URL/" 2>/dev/null || true)"
case "$editor_page" in
  *"<title>claw-dj playlist</title>"*)
    echo "Playlist editor already running on port $EDITOR_PORT — reusing it."
    open "$EDITOR_URL"
    ;;
  *)
    if nc -z 127.0.0.1 "$EDITOR_PORT" 2>/dev/null; then
      echo "Port $EDITOR_PORT is already used by something other than the claw-dj playlist editor." >&2
      echo "Inspect it with: lsof -nP -iTCP:$EDITOR_PORT -sTCP:LISTEN" >&2
      exit 1
    fi
    uv run python -m brain.playlist_editor --host 127.0.0.1 --port "$EDITOR_PORT" --open
    ;;
esac
