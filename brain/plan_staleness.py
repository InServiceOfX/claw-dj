"""Read-only source-revision staleness reporting."""
from __future__ import annotations

from brain import plan_paths
from brain.plan_mix_envelope import read_tolerant
from brain.plan_revision import plan_rev


def is_stale(slug: str) -> dict:
    paths = plan_paths.resolve(slug)
    if not paths.mix_plan.exists():
        return {"stale": True, "changed_inputs": [], "reason": "missing_mix_plan"}
    plan = read_tolerant(paths.mix_plan)
    source = plan.get("source_revs")
    if not source:
        return {"stale": True, "changed_inputs": [], "reason": "no_source_revs"}
    current = plan_rev(paths).files
    changed = [name for name in current if source.get(name) != current[name]]
    return {"stale": bool(changed), "changed_inputs": changed, "reason": "inputs_changed" if changed else "current"}
