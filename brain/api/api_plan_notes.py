"""Track-scoped plan note override route."""
from __future__ import annotations

from dataclasses import asdict

from brain import plan_notes, plan_revision
from brain.api.common import ApiError, finish, require_base, rev
from brain.plan_types import Author

PATTERN = "/api/plans/<slug>/notes"
METHODS = ("POST",)


def handle(app, params, method, body, query, headers=None):
    slug, body = params["slug"], body or {}
    paths = require_base(slug, body.get("base_rev"))
    track_id = str(body.get("track_id", ""))
    try:
        if body.get("clear"):
            effective = plan_notes.clear_override(slug, track_id, plan_revision.file_rev(paths.notes))
        else:
            author = Author(body.get("author", "human"))
            plan_notes.set_override(slug, track_id, body.get("note", ""), author, plan_revision.file_rev(paths.notes))
            effective = plan_notes.get_effective(slug, [track_id])[0]
    except ValueError as error:
        raise ApiError(400, "invalid_author", str(error), legal_values=[item.value for item in Author]) from error
    return finish({"rev": rev(slug), "effective": asdict(effective)})
