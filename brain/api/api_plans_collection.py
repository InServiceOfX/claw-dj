"""Plan collection list/create route."""
from __future__ import annotations

import json

from brain import plan_paths, plan_staleness, plan_store
from brain.api.common import ApiError, finish, meta_dict, read_ids
from brain.plan_types import PlanStatus

PATTERN = "/api/plans"
METHODS = ("GET", "POST")


def handle(app, params, method, body, query, headers=None):
    if method == "POST":
        name = str((body or {}).get("display_name", ""))
        if not name.strip():
            raise ApiError(400, "invalid_field", "display_name must not be empty", field="display_name")
        meta = plan_store.create(name)
        return finish({"slug": meta.slug, "display_name": meta.display_name, "status": meta.status.value}, 201)
    raw_status = (query or {}).get("status")
    if isinstance(raw_status, list):
        raw_status = raw_status[0] if raw_status else None
    try:
        status = PlanStatus(raw_status) if raw_status else None
    except ValueError as error:
        raise ApiError(400, "invalid_status", "unknown status", legal_values=[item.value for item in PlanStatus]) from error
    metas = plan_store.list(status=status)
    if status is None:
        metas = [meta for meta in metas if meta.status != PlanStatus.ARCHIVED]
    plans = []
    for meta in metas:
        paths = plan_paths.resolve(meta.slug)
        plans.append({**meta_dict(meta), "track_count": len(read_ids(paths.selection)), "stale": plan_staleness.is_stale(meta.slug)["stale"]})
    plans.sort(key=lambda item: (item.get("last_opened_at") or 0, item.get("updated_at") or 0), reverse=True)
    return finish({"plans": plans})
