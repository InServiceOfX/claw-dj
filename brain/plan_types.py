"""Shared, I/O-free types for plan workspaces."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class PlanStatus(StrEnum):
    wip = "wip"
    ready = "ready"
    archived = "archived"
    WIP = wip
    READY = ready
    ARCHIVED = archived


class Author(StrEnum):
    human = "human"
    agent = "agent"
    llm = "llm"
    HUMAN = human
    AGENT = agent
    LLM = llm


class Actor(StrEnum):
    gui = "gui"
    cli = "cli"
    agent = "agent"
    GUI = gui
    CLI = cli
    AGENT = agent


@dataclass(frozen=True)
class PlanMeta:
    plan_id: str
    slug: str
    display_name: str
    status: PlanStatus
    origin: str
    origin_ref: str | None
    collection_id: str | None
    created_at: float
    updated_at: float
    last_opened_at: float | None = None
    description: str = ""


@dataclass(frozen=True)
class PlanPaths:
    root: Path
    plan_json: Path
    selection: Path
    exclusions: Path
    playlist: Path
    mix_plan: Path
    notes: Path
    bunches: Path
    transitions: Path
    journal: Path


@dataclass(frozen=True)
class Rev:
    token: str
    files: dict[str, str]


@dataclass(frozen=True)
class Bunch:
    bunch_id: str
    label: str
    track_ids: tuple[str, ...]
    ordered: bool = True
    source: str = "human"
    notes: str = ""
    archived: bool = False


@dataclass(frozen=True)
class OrderConstraints:
    use_only: tuple[str, ...] | None = None
    opener_id: str | None = None
    adjacent: tuple[tuple[str, str], ...] = ()
    adjacent_ordered: bool = False
    regions: tuple[dict[str, Any], ...] = ()
    notes: tuple[str, ...] = ()
    groups: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class TransitionOverride:
    from_track_id: str
    to_track_id: str
    technique: str | None = None
    beats: int | None = None
    showcase_move: str | None = None
    effects: list[dict] | None = None
    note: str | None = None
    author: Author | None = None
    state: str = "active"
    updated_at: float | None = None
    clear: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class EffectiveNote:
    track_id: str
    note: str
    layer: str
    diverged: bool
    available: bool


RESERVED_SLUGS = frozenset({"active", "trash"})
_SLUG_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def slugify(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:64].rstrip("-")
    value = value or "plan"
    return f"{value}-2" if value in RESERVED_SLUGS else value


def validate_slug(slug: str) -> None:
    if not isinstance(slug, str) or slug in RESERVED_SLUGS or slug.startswith(".") or not _SLUG_RE.fullmatch(slug):
        raise ValueError(f"invalid or reserved plan slug: {slug!r}")


def header_safe(value: str) -> str:
    return str(value).replace("\r", "").replace("\n", "")
