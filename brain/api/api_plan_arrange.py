"""One-shot disk-truth Arrange snapshot route."""
from __future__ import annotations

from brain.api.common import finish, snapshot

PATTERN = "/api/plans/<slug>/arrange"
METHODS = ("GET",)


def handle(app, params, method, body, query, headers=None):
    payload = snapshot(params["slug"])
    return finish(payload, headers={"ETag": f'"{payload["rev"]}"'})
