"""Canonical path resolution for legacy and directory-per-plan storage."""
from __future__ import annotations

import json
from pathlib import Path

from brain.plan_types import PlanPaths, validate_slug

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_PLANS_DIR = DATA_DIR / "plans"


class PlanNotFound(FileNotFoundError):
    def __init__(self, slug: str | None):
        self.slug = slug
        super().__init__(f"plan not found: {slug or '<active>'}")


def _paths(root: Path) -> PlanPaths:
    return PlanPaths(root, root / "plan.json", root / "selection.json", root / "exclusions.json", root / "playlist.json", root / "mix_plan.json", root / "notes.json", root / "bunches.json", root / "transitions.json", root / "journal.jsonl")


def legacy_paths() -> PlanPaths:
    root = DEFAULT_PLANS_DIR.parent
    return PlanPaths(root, root / "plan.json", root / "playlist_selection.json", root / "playlist_exclusions.json", root / "playlist.json", root / "mix_plan.json", root / "notes.json", root / "bunches.json", root / "transitions.json", root / "journal.jsonl")


def resolve(slug: str | None = None) -> PlanPaths:
    plans = DEFAULT_PLANS_DIR.resolve()
    if slug is None:
        pointer = DEFAULT_PLANS_DIR / "active.json"
        if not pointer.exists():
            if not DEFAULT_PLANS_DIR.exists():
                return legacy_paths()
            raise PlanNotFound(None)
        slug = json.loads(pointer.read_text()).get("active_slug")
        if slug is None:
            raise PlanNotFound(None)
    validate_slug(slug)
    target = (DEFAULT_PLANS_DIR / slug).resolve()
    try:
        target.relative_to(plans)
    except ValueError:
        raise ValueError(f"plan path escapes plans directory: {slug!r}") from None
    paths = _paths(target)
    if not paths.plan_json.exists():
        raise PlanNotFound(slug)
    return paths


def list_slugs() -> list[str]:
    if not DEFAULT_PLANS_DIR.exists():
        return []
    return sorted(p.parent.name for p in DEFAULT_PLANS_DIR.glob("*/plan.json") if not p.parent.name.startswith("."))
