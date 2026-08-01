"""Read-only plan journal route."""
from __future__ import annotations

from brain import plan_journal
from brain.api.common import ApiError, finish, require_plan

PATTERN = "/api/plans/<slug>/journal"
METHODS = ("GET",)


def _one(query, name):
    value = (query or {}).get(name)
    return value[0] if isinstance(value, list) and value else value


def handle(app, params, method, body, query, headers=None):
    slug = params["slug"]
    require_plan(slug)
    try:
        limit = min(500, max(0, int(_one(query, "limit") or 50)))
        entries = plan_journal.read(slug, limit, actor=_one(query, "actor"), author=_one(query, "author"))
    except (ValueError, TypeError) as error:
        raise ApiError(400, "invalid_query", str(error)) from error
    return finish({"entries": entries})
