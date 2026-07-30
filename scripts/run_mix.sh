#!/usr/bin/env bash
# One command to run the last mix plan built by `brain.build_mix_plan` (the
# same file the playlist editor's "Build mix plan" writes and "Start mix"
# reads) — so you don't have to remember `python -m hands.run_mix_plan
# --plan brain/data/mix_plan.json --port 9995`.
#
# Usage:
#   scripts/run_mix.sh              # dry run (default — no Mixxx moves)
#   scripts/run_mix.sh --live       # actually drives Mixxx
#   scripts/run_mix.sh --live --record
#   scripts/run_mix.sh --live --max-events 10
#
# Requires Mixxx running with the control API (scripts/start.sh) for --live;
# --dry-run never needs it.
set -euo pipefail
cd "$(dirname "$0")/.."

PLAN="brain/data/mix_plan.json"
PORT=9995
LIVE=0
EXTRA_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --live) LIVE=1 ;;
    *) EXTRA_ARGS+=("$arg") ;;
  esac
done

if [ ! -f "$PLAN" ]; then
  echo "No mix plan at $PLAN yet." >&2
  echo "Build one first: uv run python -m brain.build_mix_plan --profile <name> --dj-format <name>" >&2
  echo "or use 'Build mix plan' in the playlist editor." >&2
  exit 1
fi

echo "Plan: $PLAN"
uv run python -c "
import json
from brain.build_mix_plan import plan_summary
plan = json.loads(open('$PLAN').read())
s = plan_summary(plan, plan_path='$PLAN')
profile = s.get('profile') or {}
dj_format = s.get('dj_format') or {}
print(f\"  {s['track_count']} tracks, {s['event_count']} events, {s['segment_count']} transitions\")
print(f\"  profile: {profile.get('name')}   dj_format: {dj_format.get('name', 'none')}\")
if s.get('format_compliance'):
    print(f\"  format compliance: {s['format_compliance']}\")
"

if [ "$LIVE" -eq 1 ]; then
  if ! nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
    echo "Mixxx control API is not up on port $PORT — run scripts/start.sh first." >&2
    exit 1
  fi
  echo "Running LIVE — this will drive Mixxx."
  uv run python -m hands.run_mix_plan --plan "$PLAN" --port "$PORT" ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
else
  echo "Dry run (pass --live to actually drive Mixxx):"
  uv run python -m hands.run_mix_plan --plan "$PLAN" --dry-run ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
fi
