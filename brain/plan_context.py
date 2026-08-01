"""Stateless per-request plan resolution."""
from __future__ import annotations

from dataclasses import dataclass

from brain import plan_paths, plan_store
from brain.plan_revision import plan_rev
from brain.plan_types import PlanMeta, PlanPaths, Rev


@dataclass(frozen=True)
class PlanScope:
    meta: PlanMeta
    paths: PlanPaths
    rev: Rev


def for_request(query: dict, body: dict) -> PlanScope:
    body = body or {}
    query = query or {}
    slug = body.get("plan") or query.get("plan")
    if isinstance(slug, list):
        slug = slug[0] if slug else None
    paths = plan_paths.resolve(slug)
    meta = plan_store.get(paths.root.name)
    return PlanScope(meta, paths, plan_rev(paths))
