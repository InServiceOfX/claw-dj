#!/usr/bin/env bash
# See usage() below (also: scripts/run_mix.sh --help).
set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
  cat <<'EOF'
Run a mix plan against Mixxx (same plan the playlist editor "Build mix plan"
writes and "Start mix" reads).

Default plan (important)
  Uses the *active named plan* from the GUI
  (brain/data/plans/active.json → brain/data/plans/<slug>/mix_plan.json).

  It does NOT default to the old legacy file brain/data/mix_plan.json unless
  that is still the only plan layout (no plans/ directory). That legacy file
  is often a stale USB-era plan and will fail with "no such file" after you
  switch collections to Elements.

Usage:
  scripts/run_mix.sh                  # LIVE — drive Mixxx with the active plan
  scripts/run_mix.sh --dry-run        # rehearse only (no Mixxx needed)
  scripts/run_mix.sh --plan PATH      # explicit mix_plan.json
  scripts/run_mix.sh --port 9995      # explicit Mixxx control API port
  scripts/run_mix.sh --max-events 10  # only first N events
  scripts/run_mix.sh --record         # record via Mixxx recorder around the plan
  scripts/run_mix.sh --help

Examples:
  # After Build mix plan in the editor for the active plan:
  scripts/run_mix.sh --dry-run
  scripts/run_mix.sh

  # Named plan directory:
  scripts/run_mix.sh --plan brain/data/plans/imported-working-mix/mix_plan.json

  # Full underlying CLI:
  uv run python -m hands.run_mix_plan --help

Options (passed through to hands.run_mix_plan):
  --plan PATH         mix-plan JSON (default: active GUI plan)
  --port PORT         Mixxx control API port override
  --dry-run           do not talk to Mixxx
  --max-events N      execute only the first N events
  --record            start/stop Mixxx recorder around the set
  -h, --help          this help

Build a plan first if none exists:
  • Playlist editor → Create the mix → Build mix plan
  • or: uv run python -m brain.build_mix_plan --help
EOF
}

PLAN=""
DRY_RUN=0
EXTRA_ARGS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --plan)
      if [ "$#" -lt 2 ]; then
        echo "run_mix.sh: --plan requires a path" >&2
        exit 2
      fi
      PLAN="$2"
      shift 2
      ;;
    --plan=*)
      PLAN="${1#--plan=}"
      shift
      ;;
    --port|--max-events)
      if [ "$#" -lt 2 ]; then
        echo "run_mix.sh: $1 requires a value" >&2
        exit 2
      fi
      EXTRA_ARGS+=("$1" "$2")
      shift 2
      ;;
    --port=*|--max-events=*)
      EXTRA_ARGS+=("$1")
      shift
      ;;
    --record)
      EXTRA_ARGS+=("$1")
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

# Resolve default plan the same way hands.run_mix_plan / the GUI do.
if [ -z "$PLAN" ]; then
  PLAN="$(
    uv run python - <<'PY'
from pathlib import Path
from brain import plan_paths

try:
    paths = plan_paths.resolve(None)
    print(paths.mix_plan)
except plan_paths.PlanNotFound:
    legacy = plan_paths.legacy_paths().mix_plan
    if legacy.is_file():
        print(legacy)
    else:
        raise SystemExit(1)
PY
  )" || {
    echo "No active mix plan found." >&2
    echo "Build one in the playlist editor (Create the mix → Build mix plan)," >&2
    echo "or pass --plan path/to/mix_plan.json" >&2
    echo "Legacy fallback brain/data/mix_plan.json is missing or plans/ has no active slug." >&2
    exit 1
  }
fi

if [ ! -f "$PLAN" ]; then
  echo "No mix plan at $PLAN yet." >&2
  echo "Build one first in the playlist editor, or:" >&2
  echo "  uv run python -m brain.build_mix_plan --help" >&2
  exit 1
fi

echo "Plan: $PLAN"
uv run python -c "
import json
from pathlib import Path
from brain.build_mix_plan import plan_summary
plan_path = Path(r'''$PLAN''')
plan = json.loads(plan_path.read_text())
s = plan_summary(plan, plan_path=str(plan_path))
profile = s.get('profile') or {}
dj_format = s.get('dj_format') or {}
print(f\"  {s['track_count']} tracks, {s['event_count']} events, {s['segment_count']} transitions\")
print(f\"  profile: {profile.get('name')}   dj_format: {dj_format.get('name', 'none')}\")
if s.get('format_compliance'):
    print(f\"  format compliance: {s['format_compliance']}\")
# Warn if plan still points at an unmounted volume (common after collection switch).
ids = []
for track in plan.get('tracks') or []:
    if isinstance(track, dict) and track.get('track_id'):
        ids.append(track['track_id'])
    elif isinstance(track, str):
        ids.append(track)
missing = [p for p in ids if not Path(p).is_file()]
if missing:
    print(f\"  WARNING: {len(missing)}/{len(ids)} track path(s) missing on disk (first: {missing[0]})\")
    print('  This plan may be from another volume — rebuild after Finalize on the active collection.')
"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "Dry run (no Mixxx moves):"
  uv run python -m hands.run_mix_plan --plan "$PLAN" --dry-run ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
else
  echo "Running LIVE — this will drive Mixxx using an explicit --port, plan metadata, or validated Mixxx discovery."
  uv run python -m hands.run_mix_plan --plan "$PLAN" ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
fi
