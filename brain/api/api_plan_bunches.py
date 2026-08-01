"""Plan-local reusable-bunch activation route."""
from __future__ import annotations

from brain import plan_bunch_activation, plan_revision
from brain.api.common import ApiError, finish, hydrated_activations, require_base, rev

PATTERN = "/api/plans/<slug>/bunches"
METHODS = ("GET", "POST")


def handle(app, params, method, body, query, headers=None):
    slug = params["slug"]
    if method == "GET":
        from brain.api.common import require_plan
        require_plan(slug)
        return finish({"activations": hydrated_activations(slug)})
    body = body or {}
    paths = require_base(slug, body.get("base_rev"))
    bunch_id = str(body.get("bunch_id", ""))
    try:
        if bool(body.get("enabled")):
            activation = plan_bunch_activation.activate(slug, bunch_id, region=body.get("region"), base_rev=plan_revision.file_rev(paths.bunches))
        else:
            activation = plan_bunch_activation.deactivate(slug, bunch_id, base_rev=plan_revision.file_rev(paths.bunches))
    except plan_bunch_activation.OverlapConflict as error:
        conflict = error.conflict
        raise ApiError(409, "bunch_overlap", str(error), conflicting_bunch_id=conflict.conflicting_bunch_id, shared_track_ids=list(conflict.shared_track_ids)) from error
    except KeyError as error:
        raise ApiError(404, "bunch_not_found", f"bunch not found: {bunch_id}", bunch_id=bunch_id) from error
    return finish({"rev": rev(slug), "activation": activation})
