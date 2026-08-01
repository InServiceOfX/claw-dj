#!/usr/bin/env bash
# See usage() below (also: scripts/run_mix.sh --help).
set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
  cat <<'EOF'
Run the last mix plan built by `brain.build_mix_plan` (the same file the
playlist editor's "Build mix plan" writes and "Start mix" reads) — so you
don't have to remember `python -m hands.run_mix_plan --plan
brain/data/mix_plan.json`.

Defaults to LIVE — this drives Mixxx. Pass --dry-run to only rehearse.

Usage:
  scripts/run_mix.sh                # live — drives Mixxx (needs scripts/start.sh running)
  scripts/run_mix.sh --dry-run      # rehearse only, no Mixxx connection needed
  scripts/run_mix.sh --record
  scripts/run_mix.sh --max-events 10
  scripts/run_mix.sh --help
EOF
}

PLAN="brain/data/mix_plan.json"
DRY_RUN=0
EXTRA_ARGS=()

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --dry-run) DRY_RUN=1 ;;
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

if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry run (no Mixxx moves):"
  uv run python -m hands.run_mix_plan --plan "$PLAN" --dry-run ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
else
  echo "Running LIVE — this will drive Mixxx using an explicit --port, plan metadata, or validated Mixxx discovery."
  uv run python -m hands.run_mix_plan --plan "$PLAN" ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
fi
