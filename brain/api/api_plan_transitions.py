"""Sparse transition patch route; null leaves a derived field unchanged."""
from __future__ import annotations

from dataclasses import asdict

from brain import plan_revision, transition_overrides
from brain.api.common import ApiError, finish, require_base, rev
from brain.plan_types import Author, TransitionOverride

PATTERN = "/api/plans/<slug>/transitions"
METHODS = ("POST",)
FIELDS = ("technique", "beats", "showcase_move", "effects", "note")


def _segment(slug, from_id, to_id):
    item = next((item for item in transition_overrides.load(slug) if (item.from_track_id, item.to_track_id) == (from_id, to_id)), None)
    if item is None:
        return {"from_track_id": from_id, "to_track_id": to_id, "overridden": False, "override_fields": [], "state": "derived", "author": None}
    value = asdict(item)
    value["author"] = item.author.value if item.author else None
    value.update(overridden=True, override_fields=[field for field in FIELDS if getattr(item, field) is not None or item.clear.get(field)])
    return value


def handle(app, params, method, body, query, headers=None):
    slug, body = params["slug"], body or {}
    paths = require_base(slug, body.get("base_rev"))
    from_id, to_id = str(body.get("from_track_id", "")), str(body.get("to_track_id", ""))
    if not from_id or not to_id:
        raise ApiError(400, "invalid_pair", "from_track_id and to_track_id are required")
    try:
        if body.get("clear"):
            transition_overrides.clear(slug, from_id, to_id, plan_revision.file_rev(paths.transitions))
        else:
            author = Author(body.get("author", "human"))
            current = next((item for item in transition_overrides.load(slug) if (item.from_track_id, item.to_track_id) == (from_id, to_id)), None)
            values = {field: getattr(current, field) if current else None for field in FIELDS}
            for field in FIELDS:
                if field in body and body[field] is not None:
                    values[field] = body[field]
            order = json_order(paths)
            state = "active" if (from_id, to_id) in set(zip(order, order[1:])) else "orphaned"
            override = TransitionOverride(from_id, to_id, author=author, state=state, **values)
            transition_overrides.upsert(slug, override, plan_revision.file_rev(paths.transitions), author=author)
    except ValueError as error:
        raise ApiError(400, "invalid_author", str(error), legal_values=[item.value for item in Author]) from error
    return finish({"rev": rev(slug), "segment": _segment(slug, from_id, to_id)})


def json_order(paths):
    import json
    data = json.loads(paths.selection.read_text()) if paths.selection.exists() else {"track_ids": []}
    return list(data.get("track_ids", data))
