"""Active-plan pointer route."""
from __future__ import annotations

from brain import plan_paths, plan_store
from brain.api.common import ApiError, finish, meta_dict, rev

PATTERN = "/api/plans/active"
METHODS = ("GET", "POST")


def _payload(meta):
    return {**meta_dict(meta), "rev": rev(meta.slug)}


def handle(app, params, method, body, query, headers=None):
    if method == "GET":
        meta = plan_store.get_active()
        if meta is None:
            raise ApiError(404, "active_plan_not_found", "no active plan")
        return finish(_payload(meta))
    if app.mix_state.get("running"):
        raise ApiError(409, "live_run_active", "cannot switch plans while a live run is active")
    slug = str((body or {}).get("slug", ""))
    try:
        meta = plan_store.set_active(slug)
    except (plan_paths.PlanNotFound, ValueError) as error:
        raise ApiError(404, "plan_not_found", f"plan not found: {slug}", slug=slug) from error
    persisted = app.load_plan_control_port(slug) if hasattr(app, "load_plan_control_port") else None
    if persisted is not None and not getattr(app, "explicit_control_port", False):
        app.control_port_override = persisted
        app.mix_state["mixxx_control_port"] = persisted
    if hasattr(app, "reload"):
        app.reload()
    return finish(_payload(meta))
