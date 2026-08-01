"""Revision-guarded plan membership mutation route."""
from __future__ import annotations

import json

from brain import bunch_store, plan_journal, plan_revision, transition_overrides
from brain.api.common import ApiError, finish, read_ids, require_base, rev, track_rows

PATTERN = "/api/plans/<slug>/tracks"
METHODS = ("POST",)


def handle(app, params, method, body, query, headers=None):
    slug, body = params["slug"], body or {}
    if app.mix_state.get("running"):
        raise ApiError(409, "live_run_active", "cannot change tracks while a live run is active")
    paths = require_base(slug, body.get("base_rev"))
    add = list(dict.fromkeys(str(item) for item in body.get("add", [])))
    remove = list(dict.fromkeys(str(item) for item in body.get("remove", [])))
    shared = sorted(set(add).intersection(remove))
    if shared:
        raise ApiError(400, "ambiguous_membership", "a track cannot be added and removed together", track_ids=shared)
    before = rev(slug)
    current = read_ids(paths.selection)
    order = [item for item in current if item not in set(remove)]
    order.extend(item for item in add if item not in order)
    exclusions = [item for item in read_ids(paths.exclusions) if item not in add]
    exclusions.extend(item for item in remove if item not in exclusions)
    plan_revision.write_checked(paths.selection, {"version": 1, "track_ids": order}, plan_revision.file_rev(paths.selection))
    plan_revision.write_checked(paths.exclusions, {"version": 1, "track_ids": exclusions}, plan_revision.file_rev(paths.exclusions))
    existing = json.loads(paths.playlist.read_text()) if paths.playlist.exists() else []
    by_id = {row.get("track_id"): row for row in existing}
    for row in track_rows([item for item in add if item not in by_id]):
        by_id[row["track_id"]] = row
    plan_revision.write_checked(paths.playlist, [by_id.get(item, {"track_id": item}) for item in order], plan_revision.file_rev(paths.playlist))
    activations = json.loads(paths.bunches.read_text()).get("activated", []) if paths.bunches.exists() else []
    deactivated = []
    for activation in activations:
        if not activation.get("enabled", True):
            continue
        try:
            original_members = activation.get("track_ids") or list(bunch_store.get(activation["bunch_id"]).track_ids)
        except KeyError:
            original_members = activation.get("track_ids", [])
        removed_members = set(activation.get("removed_track_ids", [])).union(set(remove).intersection(original_members))
        members = [item for item in original_members if item not in removed_members]
        activation["track_ids"] = members
        activation["removed_track_ids"] = sorted(removed_members)
        if len(members) < 2:
            activation["enabled"] = False
            deactivated.append({"bunch_id": activation["bunch_id"], "reason": "fewer_than_two_members"})
    plan_revision.write_checked(paths.bunches, {"version": 1, "activated": activations}, plan_revision.file_rev(paths.bunches))
    records = transition_overrides.reconcile(order, transition_overrides.load(slug))
    plan_revision.write_checked(paths.transitions, {"version": 1, "overrides": [transition_overrides._encode(item) for item in records]}, plan_revision.file_rev(paths.transitions))
    orphaned = [f"{item.from_track_id}->{item.to_track_id}" for item in records if item.state == "orphaned"]
    after = rev(slug)
    detail = {"add": add, "remove": remove, "deactivated_bunches": deactivated, "orphaned_transitions": orphaned}
    plan_journal.append(slug, "gui", "change_tracks", detail, before, after)
    return finish({"rev": after, "track_ids": order, "deactivated_bunches": deactivated, "orphaned_transitions": orphaned})
