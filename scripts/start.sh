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

PORT=9995

if ! nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
  echo "Starting Mixxx with the control API on port ${PORT}..."
  open -a Mixxx --args --control-api-port "$PORT"
  n=0
  until nc -z 127.0.0.1 "$PORT" 2>/dev/null || [ "$n" -ge 40 ]; do
    sleep 3
    n=$((n + 1))
  done
  if ! nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
    echo "Mixxx didn't open the control API within 2 minutes." >&2
    echo "Check: is /Applications/Mixxx.app the patched fork build, not stock Mixxx?" >&2
    echo "See docs/BUILD_MIXXX.md." >&2
    exit 1
  fi
  echo "Mixxx control API is up."
else
  echo "Mixxx control API already running on port $PORT — reusing it."
fi

echo "Opening the playlist editor..."
uv run python -m brain.playlist_editor --open
