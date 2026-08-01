"""Sparse pair-keyed transition overrides.

Unlike RFC 7396, ``None`` means leave the derived value unchanged. Explicit
``clear={field: True}`` removes a field.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict

from brain import plan_journal, plan_paths
from brain.plan_revision import file_rev, write_checked
from brain.plan_types import Author, TransitionOverride


def _decode(item: dict) -> TransitionOverride:
    data = dict(item)
    if data.get("author") is not None:
        data["author"] = Author(data["author"])
    if "status" in data and "state" not in data:
        data["state"] = data.pop("status")
    return TransitionOverride(**{k: v for k, v in data.items() if k in TransitionOverride.__dataclass_fields__})


def _encode(item: TransitionOverride) -> dict:
    data = asdict(item)
    data["author"] = item.author.value if item.author else None
    data["status"] = data.pop("state")
    return data


def load(slug: str) -> list[TransitionOverride]:
    path = plan_paths.resolve(slug).transitions
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [_decode(item) for item in data.get("overrides", [])]


def upsert(slug, override: TransitionOverride, base_rev, *, author=None) -> str:
    if override.from_track_id == override.to_track_id:
        raise ValueError("transition pair must contain distinct tracks")
    chosen_author = Author(author) if author is not None else override.author
    override = TransitionOverride(**{**asdict(override), "author": chosen_author, "updated_at": time.time()})
    paths = plan_paths.resolve(slug)
    before = file_rev(paths.transitions)
    records = [item for item in load(slug) if (item.from_track_id, item.to_track_id) != (override.from_track_id, override.to_track_id)] + [override]
    after = write_checked(paths.transitions, {"version": 1, "overrides": [_encode(item) for item in records]}, base_rev)
    plan_journal.append(slug, "agent", "upsert_transition", {"from": override.from_track_id, "to": override.to_track_id}, before, after, author=chosen_author)
    return after


def clear(slug, from_id, to_id, base_rev) -> str:
    paths = plan_paths.resolve(slug)
    before = file_rev(paths.transitions)
    records = [item for item in load(slug) if (item.from_track_id, item.to_track_id) != (from_id, to_id)]
    after = write_checked(paths.transitions, {"version": 1, "overrides": [_encode(item) for item in records]}, base_rev)
    plan_journal.append(slug, "agent", "clear_transition", {"from": from_id, "to": to_id}, before, after)
    return after


def merge(segments: list[dict], overrides) -> list[dict]:
    table = {(item.from_track_id, item.to_track_id): item for item in overrides if item.state == "active"}
    result = []
    for source in segments:
        segment = dict(source)
        pair = (segment.get("from_track_id") or segment.get("from"), segment.get("to_track_id") or segment.get("to"))
        override = table.get(pair)
        fields = []
        if override:
            for field in ("technique", "beats", "showcase_move", "effects", "note"):
                value = getattr(override, field)
                if override.clear.get(field):
                    segment.pop(field, None)
                    fields.append(field)
                elif value is not None:
                    target = "transition_beats" if field == "beats" and "transition_beats" in segment else field
                    segment[target] = value
                    fields.append(field)
            segment["author"] = override.author.value if override.author else None
        segment["overridden"] = bool(fields)
        segment["override_fields"] = fields
        result.append(segment)
    return result


def reconcile(order: list[str], overrides) -> list[TransitionOverride]:
    adjacent = set(zip(order, order[1:]))
    result = []
    for item in overrides:
        state = "active" if (item.from_track_id, item.to_track_id) in adjacent else "orphaned"
        result.append(TransitionOverride(**{**asdict(item), "state": state}))
    return result
