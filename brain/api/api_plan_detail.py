"""Plan metadata, lifecycle, and soft-delete route."""
from __future__ import annotations

from brain import plan_paths, plan_revision, plan_staleness, plan_store
from brain.api.common import ApiError, finish, meta_dict, require_base, require_plan, rev
from brain.plan_types import PlanStatus, header_safe

PATTERN = "/api/plans/<slug>"
METHODS = ("GET", "POST")


def handle(app, params, method, body, query, headers=None):
    slug = params["slug"]
    paths = require_plan(slug)
    if method == "GET":
        token = rev(slug)
        return finish({"meta": meta_dict(plan_store.get(slug)), "rev": token, **plan_staleness.is_stale(slug)}, headers={"ETag": f'"{header_safe(slug)}:{token}"'})
    body = body or {}
    require_base(slug, body.get("base_rev"))
    if body.get("action") == "delete":
        if app.mix_state.get("running"):
            raise ApiError(409, "live_run_active", "cannot delete a plan while a live run is active")
        plan_store.delete(slug)
        return finish({"slug": slug, "deleted": True})
    if "status" in body:
        try:
            status = PlanStatus(body["status"])
        except ValueError as error:
            raise ApiError(400, "invalid_status", "unknown status", legal_values=[item.value for item in PlanStatus]) from error
        meta = plan_store.set_status(slug, status, plan_revision.file_rev(paths.plan_json))
    elif "display_name" in body:
        if not str(body["display_name"]).strip():
            raise ApiError(400, "invalid_field", "display_name must not be empty", field="display_name")
        meta = plan_store.rename(slug, str(body["display_name"]), plan_revision.file_rev(paths.plan_json))
    else:
        raise ApiError(400, "invalid_request", "expected display_name, status, or action=delete")
    return finish({**meta_dict(meta), "rev": rev(slug)})
