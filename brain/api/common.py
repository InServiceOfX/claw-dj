"""Shared response, revision, hydration, and snapshot helpers for plan routes."""
from __future__ import annotations

import json
import hashlib
from dataclasses import asdict
from http import HTTPStatus

from brain import bunch_store, library_index, plan_bunch_activation, plan_notes, plan_paths, plan_revision, plan_staleness, plan_store, transition_overrides
from brain.plan_mix_envelope import read_tolerant


class ApiError(RuntimeError):
    def __init__(self, status, code, message, **details):
        self.status = int(status)
        self.payload = {"error": code, "message": message, **details}
        super().__init__(message)


def require_plan(slug):
    try:
        return plan_paths.resolve(slug)
    except plan_paths.PlanNotFound as error:
        raise ApiError(404, "plan_not_found", str(error), slug=slug) from error


def require_base(slug, base_rev):
    if base_rev is None:
        raise ApiError(400, "base_rev_required", "base_rev is required", field="base_rev")
    paths = require_plan(slug)
    token, files = workspace_rev(paths)
    if base_rev != token:
        raise plan_revision.StalePlanError(token, changed_files=list(files))
    return paths


def rev(slug):
    return workspace_rev(require_plan(slug))[0]


def workspace_rev(paths):
    source = plan_revision.plan_rev(paths).files
    files = {"plan_json": plan_revision.file_rev(paths.plan_json), "exclusions": plan_revision.file_rev(paths.exclusions), **source}
    digest = hashlib.sha256()
    for name, value in files.items():
        digest.update(name.encode() + b"\0" + value.encode() + b"\0")
    return digest.hexdigest(), files


def meta_dict(meta):
    value = asdict(meta)
    value["status"] = meta.status.value
    return value


def read_ids(path):
    if not path.exists():
        return []
    value = json.loads(path.read_text())
    return list(value.get("track_ids", value) if isinstance(value, dict) else value)


def track_rows(track_ids):
    if not track_ids:
        return []
    found = {}
    try:
        marks = ",".join("?" for _ in track_ids)
        with library_index.connect() as db:
            for row in db.execute(f"SELECT * FROM tracks WHERE track_id IN ({marks})", track_ids):
                found[row["track_id"]] = dict(row)
    except Exception:
        pass
    return [found.get(track_id, {"track_id": track_id, "title": track_id, "artist": ""}) for track_id in track_ids]


def _span(order, members):
    positions = [order.index(item) for item in members if item in order]
    if not positions:
        return None
    return {"start": min(positions), "end": max(positions)}


def hydrated_activations(slug, order=None):
    order = order or read_ids(require_plan(slug).selection)
    result = []
    for activation in plan_bunch_activation.list_active(slug):
        try:
            bunch = bunch_store.get(activation["bunch_id"])
        except KeyError:
            continue
        members = list(activation.get("track_ids") or bunch.track_ids)
        result.append({
            **activation,
            "label": bunch.label,
            "track_ids": members,
            "ordered": bunch.ordered,
            "archived": bunch.archived,
            "span": _span(order, members),
        })
    return result


def snapshot(slug):
    """Build one disk-truth arrange snapshot without consulting GUI buffers."""
    for _ in range(3):
        payload = _snapshot_once(slug)
        if payload["rev"] == workspace_rev(require_plan(slug))[0]:
            return payload
    current, files = workspace_rev(require_plan(slug))
    raise plan_revision.StalePlanError(current, changed_files=list(files))


def _snapshot_once(slug):
    paths = require_plan(slug)
    token, files = workspace_rev(paths)
    artifact = read_tolerant(paths.mix_plan) if paths.mix_plan.exists() else None
    fallback_rows = json.loads(paths.playlist.read_text()) if paths.playlist.exists() else track_rows(read_ids(paths.selection))
    stale = plan_staleness.is_stale(slug)
    tracks = list(((artifact or {}).get("tracks") if not stale["stale"] else None) or fallback_rows)
    order = [row.get("track_id") for row in tracks if row.get("track_id")]
    notes = [asdict(item) for item in plan_notes.get_effective(slug, order)]
    order_changed = bool({"selection", "playlist"}.intersection(stale.get("changed_inputs", [])))
    derived = [] if order_changed else list((artifact or {}).get("segments") or [])
    overrides = transition_overrides.reconcile(order, transition_overrides.load(slug))
    segments = transition_overrides.merge(derived, overrides)
    override_table = {(item.from_track_id, item.to_track_id): item for item in overrides}
    for segment in segments:
        pair = (segment.get("from_track_id") or segment.get("from"), segment.get("to_track_id") or segment.get("to"))
        matched = override_table.get(pair)
        segment.setdefault("state", matched.state if matched else "derived")
    return {
        "slug": slug,
        "tracks": tracks,
        "notes": notes,
        "segments": segments,
        "bunches": hydrated_activations(slug, order),
        "revs": files,
        "rev": token,
        "stale": stale["stale"],
        "staleness": stale,
        "artifact": artifact,
    }


def finish(payload, status=HTTPStatus.OK, headers=None):
    return payload, int(status), (headers or {})
