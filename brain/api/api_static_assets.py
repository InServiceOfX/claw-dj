"""Serve same-origin browser modules with deterministic MIME types."""
from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from brain.api.common import ApiError, finish

PATTERN = "/web/<file>"
METHODS = ("GET",)
WEB_ROOT = Path(__file__).parents[1] / "web"
MIME = {".js": "text/javascript", ".css": "text/css"}


def handle(app, params, method, body, query, headers=None):
    name = params["file"]
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise ApiError(404, "asset_not_found", "asset not found")
    root = WEB_ROOT.resolve()
    path = (root / name).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ApiError(404, "asset_not_found", "asset not found") from error
    if not path.is_file():
        raise ApiError(404, "asset_not_found", "asset not found")
    data = path.read_bytes()
    etag = f'"{hashlib.sha256(data).hexdigest()}"'
    response_headers = {"ETag": etag, "Content-Type": MIME.get(path.suffix, mimetypes.guess_type(path.name)[0] or "application/octet-stream")}
    supplied = (headers or {}).get("If-None-Match", "")
    if supplied.removeprefix("W/") == etag:
        return finish(b"", 304, response_headers)
    return finish(data, 200, response_headers)
