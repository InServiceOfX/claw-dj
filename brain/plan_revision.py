"""Content revision tokens and atomic optimistic-concurrency writes."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from brain.plan_types import PlanPaths, Rev

SOURCE_NAMES = ("selection", "playlist", "notes", "bunches", "transitions")


def file_rev(path: Path) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plan_rev(paths: PlanPaths) -> Rev:
    files = {name: file_rev(getattr(paths, name)) for name in SOURCE_NAMES}
    digest = hashlib.sha256()
    for name in SOURCE_NAMES:
        digest.update(name.encode() + b"\0" + files[name].encode() + b"\0")
    return Rev(digest.hexdigest(), files)


def read_with_rev(path: Path) -> tuple[Any, str]:
    if not path.exists():
        return {}, ""
    return json.loads(path.read_text()), file_rev(path)


class StalePlanError(RuntimeError):
    def __init__(self, current_rev: str, *, changed_files: list[str] | None = None):
        self.current_rev = current_rev
        self.changed_files = changed_files or []
        super().__init__("stale plan write refused")

    def payload(self) -> dict:
        return {"current_rev": self.current_rev, "changed_files": self.changed_files, "summary": "Plan changed on disk; refresh and retry."}


def write_checked(path: Path, data: Any, base_rev: str | None) -> str:
    current = file_rev(path)
    if base_rev is not None and base_rev != current:
        raise StalePlanError(current, changed_files=[path.name])
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise
    return file_rev(path)
