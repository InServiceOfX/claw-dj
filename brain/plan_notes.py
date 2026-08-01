"""Sparse plan note overlays over global library DJ notes."""
from __future__ import annotations

import json
import time
from contextlib import closing

from brain import library_index, plan_journal, plan_paths
from brain.plan_revision import file_rev, write_checked
from brain.plan_types import Author, EffectiveNote

DEFAULT_INDEX = library_index.DEFAULT_INDEX


def _overrides(slug) -> list[dict]:
    path = plan_paths.resolve(slug).notes
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return list(data.get("overrides", []))


def _global(track_ids: list[str]) -> dict[str, tuple[str, bool]]:
    if not track_ids:
        return {}
    marks = ",".join("?" for _ in track_ids)
    with closing(library_index.connect(DEFAULT_INDEX)) as db:
        rows = db.execute(f"SELECT track_id,dj_notes,available FROM tracks WHERE track_id IN ({marks})", track_ids)
        return {r["track_id"]: (r["dj_notes"] or "", bool(r["available"])) for r in rows}


def get_effective(slug: str, track_ids: list[str]) -> list[EffectiveNote]:
    global_notes = _global(track_ids)
    overrides = {item["track_id"]: item for item in _overrides(slug)}
    result = []
    for track_id in track_ids:
        global_note, available = global_notes.get(track_id, ("", False))
        override = overrides.get(track_id)
        if override is None:
            result.append(EffectiveNote(track_id, global_note, "global", False, available))
        else:
            baseline = override.get("global_note_at_override")
            result.append(EffectiveNote(track_id, override.get("note", ""), "plan", baseline is not None and baseline != global_note, available))
    return result


def set_override(slug, track_id, note, author, base_rev) -> str:
    author = Author(author)
    paths = plan_paths.resolve(slug)
    before = file_rev(paths.notes)
    records = _overrides(slug)
    global_note = _global([track_id]).get(track_id, ("", False))[0]
    record = {"track_id": track_id, "note": str(note), "updated_at": time.time(), "author": author.value, "global_note_at_override": global_note}
    records = [item for item in records if item.get("track_id") != track_id] + [record]
    after = write_checked(paths.notes, {"version": 1, "overrides": records}, base_rev)
    plan_journal.append(slug, "agent", "set_note_override", {"track_id": track_id}, before, after, author=author)
    return after


def clear_override(slug, track_id, base_rev) -> EffectiveNote:
    paths = plan_paths.resolve(slug)
    before = file_rev(paths.notes)
    records = [item for item in _overrides(slug) if item.get("track_id") != track_id]
    after = write_checked(paths.notes, {"version": 1, "overrides": records}, base_rev)
    plan_journal.append(slug, "agent", "clear_note_override", {"track_id": track_id}, before, after)
    return get_effective(slug, [track_id])[0]
