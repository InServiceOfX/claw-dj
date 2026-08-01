"""Revision-guarded full ordering and bunch movement route."""
from __future__ import annotations

import json

from brain import order_constraints, plan_journal, plan_revision, transition_overrides
from brain.api.common import ApiError, finish, hydrated_activations, read_ids, require_base, rev

PATTERN = "/api/plans/<slug>/order"
METHODS = ("POST",)


def _persist_reconciled(paths, order):
    records = transition_overrides.reconcile(order, transition_overrides.load(paths.root.name))
    payload = {"version": 1, "overrides": [transition_overrides._encode(item) for item in records]}
    plan_revision.write_checked(paths.transitions, payload, plan_revision.file_rev(paths.transitions))
    return [f"{item.from_track_id}->{item.to_track_id}" for item in records if item.state == "orphaned"]


def handle(app, params, method, body, query, headers=None):
    slug, body = params["slug"], body or {}
    if app.mix_state.get("running"):
        raise ApiError(409, "live_run_active", "cannot reorder while a live run is active")
    paths = require_base(slug, body.get("base_rev"))
    current = read_ids(paths.selection)
    if "move_bunch" in body:
        bunch_id = str(body["move_bunch"])
        activation = next((item for item in hydrated_activations(slug, current) if str(item["bunch_id"]) == bunch_id), None)
        if activation is None:
            raise ApiError(404, "bunch_not_active", "active bunch not found", bunch_id=bunch_id)
        members = activation["track_ids"]
        remaining = [item for item in current if item not in members]
        index = max(0, min(int(body.get("to_index", 0)), len(remaining)))
        order = remaining[:index] + members + remaining[index:]
    else:
        order = list(body.get("track_ids") or [])
    if len(order) != len(current) or set(order) != set(current):
        raise ApiError(400, "not_a_permutation", "track_ids must be a permutation of the current selection")
    groups = [item["track_ids"] for item in hydrated_activations(slug, current)]
    try:
        order_constraints.assert_intact(order, groups)
    except order_constraints.ConstraintViolation as error:
        broken = next((item for item in hydrated_activations(slug, current) if _broken(order, item["track_ids"])), None)
        raise ApiError(422, "bunch_constraint", str(error), bunch_id=(broken or {}).get("bunch_id")) from error
    before = rev(slug)
    plan_revision.write_checked(paths.selection, {"version": 1, "track_ids": order}, plan_revision.file_rev(paths.selection))
    rows = json.loads(paths.playlist.read_text()) if paths.playlist.exists() else []
    by_id = {row.get("track_id"): row for row in rows}
    plan_revision.write_checked(paths.playlist, [by_id.get(item, {"track_id": item}) for item in order], plan_revision.file_rev(paths.playlist))
    orphaned = _persist_reconciled(paths, order)
    after = rev(slug)
    plan_journal.append(slug, "gui", "reorder", {"track_ids": order, "orphaned_transitions": orphaned}, before, after)
    return finish({"rev": after, "order": order, "orphaned_transitions": orphaned})


def _broken(order, members):
    present = [item for item in members if item in order]
    return len(present) > 1 and order[order.index(present[0]):order.index(present[0]) + len(present)] != present
