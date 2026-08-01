"""Plan-local activation and disjointness for reusable bunches."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

from brain import bunch_store, plan_journal, plan_paths
from brain.mix_order_brief import REGION_SLICES
from brain.plan_revision import file_rev, write_checked


@dataclass(frozen=True)
class Conflict:
    conflicting_bunch_id: str
    shared_track_ids: tuple[str, ...]


class OverlapConflict(ValueError):
    def __init__(self, conflict: Conflict):
        self.conflict = conflict
        super().__init__(f"bunch overlaps {conflict.conflicting_bunch_id}: {list(conflict.shared_track_ids)}")


def _records(slug: str) -> list[dict]:
    path = plan_paths.resolve(slug).bunches
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return list(data.get("activated", data if isinstance(data, list) else []))


def list_active(slug: str) -> list[dict]:
    return [dict(item) for item in _records(slug) if item.get("enabled", True)]


def check_disjoint(slug: str, bunch_id) -> Conflict | None:
    wanted = set(bunch_store.get(bunch_id).track_ids)
    for item in list_active(slug):
        if str(item["bunch_id"]) == str(bunch_id):
            continue
        try:
            existing = item.get("track_ids") or bunch_store.get(item["bunch_id"]).track_ids
            shared = wanted.intersection(existing)
        except KeyError:
            continue
        if shared:
            return Conflict(str(item["bunch_id"]), tuple(sorted(shared)))
    return None


def activate(slug, bunch_id, *, region=None, base_rev) -> dict:
    if region is not None and region not in REGION_SLICES:
        raise ValueError(f"invalid bunch region: {region}")
    bunch = bunch_store.get(bunch_id)
    conflict = check_disjoint(slug, bunch_id)
    if conflict:
        raise OverlapConflict(conflict)
    paths = plan_paths.resolve(slug)
    before = file_rev(paths.bunches)
    records = _records(slug)
    record = next((x for x in records if str(x["bunch_id"]) == str(bunch_id)), None)
    values = {"bunch_id": str(bunch_id), "track_ids": list(bunch.track_ids), "removed_track_ids": [], "enabled": True, "region": region, "pinned_position": None, "activated_at": time.time(), "warning": "archived" if bunch.archived else None}
    if record is None:
        records.append(values)
        record = values
    else:
        record.update(values)
    after = write_checked(paths.bunches, {"version": 1, "activated": records}, base_rev)
    plan_journal.append(slug, "agent", "activate_bunch", {"bunch_id": str(bunch_id)}, before, after)
    return dict(record)


def deactivate(slug, bunch_id, *, base_rev) -> dict:
    paths = plan_paths.resolve(slug)
    before = file_rev(paths.bunches)
    records = _records(slug)
    record = next((x for x in records if str(x["bunch_id"]) == str(bunch_id)), None)
    if record is None:
        record = {"bunch_id": str(bunch_id), "enabled": False, "activated_at": time.time()}
        records.append(record)
    else:
        record["enabled"] = False
    after = write_checked(paths.bunches, {"version": 1, "activated": records}, base_rev)
    plan_journal.append(slug, "agent", "deactivate_bunch", {"bunch_id": str(bunch_id)}, before, after)
    return dict(record)


def plans_activating(bunch_id) -> list[str]:
    result = []
    for slug in plan_paths.list_slugs():
        if any(str(item.get("bunch_id")) == str(bunch_id) for item in list_active(slug)):
            result.append(slug)
    return result
