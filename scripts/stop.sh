#!/usr/bin/env bash
# Stop the claw-dj playlist editor. Does not quit Mixxx — close Mixxx from
# the dock / Cmd-Q yourself when you want that.
#
# Usage:
#   scripts/stop.sh              # stop editor on the default port 8787
#   scripts/stop.sh --port 8788  # stop editor on another port
#   scripts/stop.sh --force      # SIGKILL if a polite stop does not free the port
#
# After stopping, start a fresh editor with:
#   scripts/start.sh
set -euo pipefail
cd "$(dirname "$0")/.."

EDITOR_PORT=8787
FORCE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --port)
      [ "$#" -ge 2 ] || { echo "--port needs a value" >&2; exit 2; }
      EDITOR_PORT="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Stop the claw-dj playlist editor. Does not quit Mixxx.

Usage:
  scripts/stop.sh              # stop editor on port 8787
  scripts/stop.sh --port PORT  # stop editor on another port
  scripts/stop.sh --force      # SIGKILL if polite stop fails

After stopping, start a fresh editor with:
  scripts/start.sh
EOF
      exit 0
      ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if ! [[ "$EDITOR_PORT" =~ ^[0-9]+$ ]] || [ "$EDITOR_PORT" -lt 1 ] || [ "$EDITOR_PORT" -gt 65535 ]; then
  echo "invalid port: $EDITOR_PORT" >&2
  exit 2
fi

# Collect listener PIDs on the editor port, then expand to matching parent/child
# process trees that actually look like playlist_editor (never kill by port alone
# if the command line is unrelated).
listener_pids() {
  lsof -nP -iTCP:"$EDITOR_PORT" -sTCP:LISTEN -t 2>/dev/null | sort -u || true
}

looks_like_editor() {
  local pid="$1" cmd
  cmd="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  case "$cmd" in
    *brain.playlist_editor*|*playlist_editor*) return 0 ;;
    *) return 1 ;;
  esac
}

expand_related() {
  local pid related parent cmd
  for pid in "$@"; do
    [ -n "$pid" ] || continue
    printf '%s\n' "$pid"
    parent="$(ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ' || true)"
    if [ -n "$parent" ] && [ "$parent" != "1" ] && looks_like_editor "$parent"; then
      printf '%s\n' "$parent"
    fi
    # uv run often parents the real Python process; also catch siblings/children
    # that share the playlist_editor command line.
    while read -r related; do
      [ -n "$related" ] || continue
      cmd="$(ps -p "$related" -o args= 2>/dev/null || true)"
      case "$cmd" in
        *brain.playlist_editor*|*playlist_editor*) printf '%s\n' "$related" ;;
      esac
    done < <(pgrep -P "$pid" 2>/dev/null || true)
  done | sort -u
}

PIDS=()
while read -r pid; do
  [ -n "$pid" ] || continue
  if looks_like_editor "$pid"; then
    PIDS+=("$pid")
  else
    cmd="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    echo "Port $EDITOR_PORT is held by pid $pid, but it does not look like playlist_editor:" >&2
    echo "  $cmd" >&2
    echo "Refusing to kill it. Inspect with: lsof -nP -iTCP:$EDITOR_PORT -sTCP:LISTEN" >&2
    exit 1
  fi
done < <(listener_pids)

if [ "${#PIDS[@]}" -eq 0 ]; then
  # No listener — still try to reap orphaned uv/python editor processes that
  # may not be bound (crashed mid-start) so the next start is clean.
  orphans=()
  while read -r pid; do
    [ -n "$pid" ] || continue
    orphans+=("$pid")
  done < <(pgrep -f 'python -m brain.playlist_editor' 2>/dev/null || true)

  if [ "${#orphans[@]}" -eq 0 ]; then
    echo "Playlist editor is not running on port $EDITOR_PORT."
    exit 0
  fi

  echo "No listener on port $EDITOR_PORT, but found orphaned playlist_editor process(es): ${orphans[*]}"
  PIDS=("${orphans[@]}")
else
  related=()
  while read -r pid; do
    [ -n "$pid" ] || continue
    related+=("$pid")
  done < <(expand_related "${PIDS[@]}")
  PIDS=("${related[@]}")
fi

echo "Stopping playlist editor (port $EDITOR_PORT): ${PIDS[*]}"
for pid in "${PIDS[@]}"; do
  cmd="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  [ -n "$cmd" ] && echo "  pid $pid  $cmd"
done

kill -TERM "${PIDS[@]}" 2>/dev/null || true

# Wait up to ~5s for the port to free.
n=0
while [ "$n" -lt 25 ]; do
  still=()
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      still+=("$pid")
    fi
  done
  if [ "${#still[@]}" -eq 0 ] && ! lsof -nP -iTCP:"$EDITOR_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Playlist editor stopped. Mixxx was left running."
    echo "Restart with: scripts/start.sh"
    exit 0
  fi
  sleep 0.2
  n=$((n + 1))
done

if [ "$FORCE" -eq 1 ]; then
  echo "Still running after SIGTERM — sending SIGKILL..."
  kill -KILL "${PIDS[@]}" 2>/dev/null || true
  sleep 0.3
  if lsof -nP -iTCP:"$EDITOR_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Port $EDITOR_PORT is still in use after --force." >&2
    lsof -nP -iTCP:"$EDITOR_PORT" -sTCP:LISTEN >&2 || true
    exit 1
  fi
  echo "Playlist editor force-stopped. Mixxx was left running."
  echo "Restart with: scripts/start.sh"
  exit 0
fi

echo "Playlist editor did not exit cleanly. Re-run with --force, or inspect:" >&2
echo "  lsof -nP -iTCP:$EDITOR_PORT -sTCP:LISTEN" >&2
exit 1
