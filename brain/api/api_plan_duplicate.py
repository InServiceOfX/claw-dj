"""Full on-disk plan duplication route."""
from __future__ import annotations

from brain import plan_paths, plan_store
from brain.api.common import ApiError, finish, meta_dict, require_plan

PATTERN = "/api/plans/<slug>/duplicate"
METHODS = ("POST",)


def handle(app, params, method, body, query, headers=None):
    slug = params["slug"]
    require_plan(slug)
    source = plan_store.get(slug)
    name = str((body or {}).get("display_name") or f"{source.display_name} copy")
    try:
        meta = plan_store.duplicate(slug, name)
    except FileExistsError as error:
        raise ApiError(409, "slug_collision", str(error)) from error
    return finish(meta_dict(meta), 201)
