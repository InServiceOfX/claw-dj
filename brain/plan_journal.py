"""Append-only per-plan audit journal."""
from __future__ import annotations

import json
import os
import time

from brain import plan_paths
from brain.plan_types import Actor, Author


def append(slug, actor, action, detail, rev_before, rev_after, author=None) -> None:
    actor_value = Actor(actor).value
    author_value = Author(author).value if author is not None else None
    path = plan_paths.resolve(slug).journal
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"at": time.time(), "actor": actor_value, "author": author_value, "action": str(action), "detail": detail or {}, "rev_before": rev_before, "rev_after": rev_after}
    payload = (json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


def read(slug, limit=50, *, actor=None, author=None) -> list[dict]:
    path = plan_paths.resolve(slug).journal
    if not path.exists():
        return []
    if actor is not None:
        actor = Actor(actor).value
    if author is not None:
        author = Author(author).value
    records = []
    for line in path.read_bytes().splitlines():
        try:
            item = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        item.setdefault("author", None)
        if (actor is None or item.get("actor") == actor) and (author is None or item.get("author") == author):
            records.append(item)
    return list(reversed(records))[:limit]
