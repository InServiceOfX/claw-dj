"""Reusable library-bunch item update/archive route."""
from __future__ import annotations

import json
import time

from brain import bunch_store, plan_bunch_activation, plan_journal, plan_paths, plan_revision
from brain.api.api_bunches_collection import hydrate
from brain.api.common import ApiError, finish, rev

PATTERN = "/api/bunches/<bunch_id>"
METHODS = ("GET", "POST")


def _get(bunch_id):
    try:
        return bunch_store.get(bunch_id)
    except KeyError as error:
        raise ApiError(404, "bunch_not_found", f"bunch not found: {bunch_id}", bunch_id=bunch_id) from error


def handle(app, params, method, body, query, headers=None):
    bunch_id = params["bunch_id"]
    if method == "GET":
        return finish(hydrate(_get(bunch_id)))
    _get(bunch_id)
    affected = plan_bunch_activation.plans_activating(bunch_id)
    before = {slug: rev(slug) for slug in affected}
    body = body or {}
    if body.get("action") == "archive":
        result = bunch_store.archive(bunch_id)
    else:
        result = bunch_store.update(
            bunch_id,
            label=body.get("label"), notes=body.get("notes"), ordered=body.get("ordered"),
            track_ids=body.get("track_ids") if "track_ids" in body else None,
        )
    for slug in affected:
        paths = plan_paths.resolve(slug)
        data = json.loads(paths.bunches.read_text()) if paths.bunches.exists() else {"version": 1, "activated": []}
        for activation in data.get("activated", []):
            if str(activation.get("bunch_id")) != str(bunch_id):
                continue
            activation["library_updated_at"] = time.time()
            activation["warning"] = "archived" if result.bunch.archived else activation.get("warning")
            if "track_ids" in body and body.get("action") != "archive":
                removed = set(activation.get("removed_track_ids", []))
                activation["track_ids"] = [item for item in result.bunch.track_ids if item not in removed]
                if len(activation["track_ids"]) < 2:
                    activation["enabled"] = False
                    activation["warning"] = "fewer_than_two_members"
        plan_revision.write_checked(paths.bunches, data, plan_revision.file_rev(paths.bunches))
        plan_journal.append(slug, "gui", "library_bunch_changed", {"bunch_id": bunch_id, "archived": result.bunch.archived}, before[slug], rev(slug))
    return finish({**hydrate(result.bunch), "auto_archived": result.auto_archived, "affected_slugs": affected})
