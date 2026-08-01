"""Version-tolerant mix-plan provenance envelopes."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from brain import bunch_store
from brain.plan_revision import plan_rev
from brain.plan_types import PlanPaths


def decorate(plan: dict, slug: str, paths: PlanPaths) -> dict:
    result = deepcopy(plan)
    meta = json.loads(paths.plan_json.read_text())
    revs = plan_rev(paths).files
    activated = []
    order = [track.get("track_id") for track in result.get("tracks", [])]
    if paths.bunches.exists():
        data = json.loads(paths.bunches.read_text())
        for item in data.get("activated", []):
            if not item.get("enabled", True):
                continue
            try:
                bunch = bunch_store.get(item["bunch_id"])
            except KeyError:
                continue
            members = list(bunch.track_ids)
            honored = False
            if members and all(track_id in order for track_id in members):
                start = order.index(members[0])
                honored = order[start:start + len(members)] == members
            activated.append({"bunch_id": bunch.bunch_id, "label": bunch.label, "track_ids": members, "honored": honored})
    result["version"] = 3
    result["plan_id"] = meta["plan_id"]
    result["plan_slug"] = slug
    result["source_revs"] = revs
    result["bunches"] = activated
    return result


def read_tolerant(path: Path) -> dict:
    data = json.loads(path.read_text())
    version = data.get("version", 2)
    if version not in (2, 3):
        raise ValueError(f"unsupported mix plan version: {version}")
    return data
