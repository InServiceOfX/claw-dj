"""Non-destructive lifecycle operations for plan directories."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import asdict

from brain import plan_journal, plan_paths
from brain.plan_revision import file_rev, write_checked
from brain.plan_types import PlanMeta, PlanStatus, slugify


def _decode(data: dict) -> PlanMeta:
    data = dict(data)
    data.pop("version", None)
    data["status"] = PlanStatus(data["status"])
    return PlanMeta(**data)


def _encode(meta: PlanMeta) -> dict:
    data = asdict(meta)
    data["version"] = 1
    data["status"] = meta.status.value
    return data


def _available_slug(display_name: str) -> str:
    base = slugify(display_name)
    candidate, suffix = base, 2
    while candidate in {"active", "trash"} or (plan_paths.DEFAULT_PLANS_DIR / candidate).exists():
        trim = 64 - len(f"-{suffix}")
        candidate = f"{base[:trim].rstrip('-')}-{suffix}"
        suffix += 1
    return candidate


def create(display_name: str, *, collection_id: str | None = None, origin: str = "created", origin_ref: str | None = None) -> PlanMeta:
    if not str(display_name).strip():
        raise ValueError("display_name must not be empty")
    now = time.time()
    slug = _available_slug(display_name)
    root = plan_paths.DEFAULT_PLANS_DIR / slug
    root.mkdir(parents=True, exist_ok=False)
    meta = PlanMeta(str(uuid.uuid4()), slug, display_name, PlanStatus.WIP, origin, origin_ref, collection_id, now, now)
    try:
        write_checked(root / "plan.json", _encode(meta), "")
        for name, payload in (("selection.json", {"version": 1, "track_ids": []}), ("exclusions.json", {"version": 1, "track_ids": []}), ("playlist.json", []), ("notes.json", {"version": 1, "overrides": []}), ("bunches.json", {"version": 1, "activated": []}), ("transitions.json", {"version": 1, "overrides": []})):
            write_checked(root / name, payload, "")
    except BaseException:
        shutil.rmtree(root)
        raise
    return meta


def list(*, status: PlanStatus | None = None) -> list[PlanMeta]:
    result = [get(slug) for slug in plan_paths.list_slugs()]
    if status is not None:
        wanted = PlanStatus(status)
        result = [meta for meta in result if meta.status == wanted]
    return sorted(result, key=lambda meta: (meta.updated_at, meta.slug), reverse=True)


def get(slug: str) -> PlanMeta:
    return _decode(json.loads(plan_paths.resolve(slug).plan_json.read_text()))


def _replace_meta(slug: str, changes: dict, base_rev: str | None, action: str) -> PlanMeta:
    paths = plan_paths.resolve(slug)
    old = get(slug)
    data = _encode(old)
    data.update(changes, updated_at=time.time())
    new = _decode(data)
    before = file_rev(paths.plan_json)
    after = write_checked(paths.plan_json, _encode(new), base_rev)
    plan_journal.append(slug, "agent", action, changes, before, after)
    return new


def rename(slug: str, display_name: str, base_rev: str | None = None) -> PlanMeta:
    return _replace_meta(slug, {"display_name": display_name}, base_rev, "rename")


def set_status(slug: str, status: PlanStatus, base_rev: str) -> PlanMeta:
    return _replace_meta(slug, {"status": PlanStatus(status).value}, base_rev, "set_status")


def duplicate(slug: str, display_name: str) -> PlanMeta:
    source = plan_paths.resolve(slug).root
    target_slug = _available_slug(display_name)
    target = plan_paths.DEFAULT_PLANS_DIR / target_slug
    shutil.copytree(source, target)
    old = get(slug)
    now = time.time()
    meta = PlanMeta(str(uuid.uuid4()), target_slug, display_name, PlanStatus.WIP, "duplicated", slug, old.collection_id, now, now, description=old.description)
    write_checked(target / "plan.json", _encode(meta), file_rev(target / "plan.json"))
    (target / "journal.jsonl").unlink(missing_ok=True)
    return meta


def delete(slug: str) -> None:
    paths = plan_paths.resolve(slug)
    trash = plan_paths.DEFAULT_PLANS_DIR / ".trash"
    trash.mkdir(parents=True, exist_ok=True)
    target = trash / slug
    if target.exists():
        target = trash / f"{slug}-{int(time.time())}"
    os.replace(paths.root, target)
    write_checked(target / "tombstone.json", {"version": 1, "slug": slug, "deleted_at": time.time()}, "")
    pointer = plan_paths.DEFAULT_PLANS_DIR / "active.json"
    if pointer.exists() and json.loads(pointer.read_text()).get("active_slug") == slug:
        write_checked(pointer, {"version": 1, "active_slug": None, "updated_at": time.time()}, file_rev(pointer))


def get_active() -> PlanMeta | None:
    # plan_paths.resolve() deliberately falls back to the legacy singleton
    # data directory when no plan workspace exists.  That directory is not
    # an active plan, so require the pointer before interpreting its basename
    # as a slug.
    if not (plan_paths.DEFAULT_PLANS_DIR / "active.json").exists():
        return None
    try:
        return get(plan_paths.resolve().root.name)
    except plan_paths.PlanNotFound:
        return None


def set_active(slug: str) -> PlanMeta:
    paths = plan_paths.resolve(slug)
    meta = _replace_meta(slug, {"last_opened_at": time.time()}, file_rev(paths.plan_json), "open_plan")
    pointer = plan_paths.DEFAULT_PLANS_DIR / "active.json"
    write_checked(pointer, {"version": 1, "active_slug": slug, "updated_at": time.time()}, file_rev(pointer))
    return meta
