"""Resolve and stream a library track for in-browser preview.

Preview is a Curate/Mix listen, not a Mixxx performance. Only indexed
track_ids (absolute library paths) may be opened.
"""
from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from brain.library import Track

_RANGE = re.compile(r"bytes=(\d*)-(\d*)$", re.IGNORECASE)

MIME = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".wav": "audio/wav",
    ".wave": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
}


class PreviewError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def content_type(path: Path) -> str:
    return MIME.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def parse_byte_range(header: str | None, size: int) -> tuple[int, int, bool]:
    """Return inclusive start, end, and whether this was a Range request."""
    if not header or not header.strip():
        return 0, size - 1, False
    match = _RANGE.match(header.strip())
    if not match:
        raise PreviewError(416, "invalid_range", "invalid Range header")
    start_s, end_s = match.group(1), match.group(2)
    if start_s == "" and end_s == "":
        raise PreviewError(416, "invalid_range", "invalid Range header")
    if start_s == "":
        suffix = int(end_s)
        if suffix <= 0:
            raise PreviewError(416, "invalid_range", "invalid Range header")
        start = max(0, size - suffix)
        end = size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else size - 1
    if start >= size or end < start:
        raise PreviewError(416, "invalid_range", "Range not satisfiable")
    return start, min(end, size - 1), True


def resolve_preview_path(by_id: dict[str, Track], track_id: str) -> Path:
    if not track_id or track_id not in by_id:
        raise PreviewError(404, "unknown_track", "track is not in the loaded library")
    raw = Path(track_id)
    if not raw.is_absolute() or ".." in raw.parts:
        raise PreviewError(404, "unknown_track", "track is not in the loaded library")
    try:
        requested = raw.expanduser().resolve()
        indexed = Path(by_id[track_id].track_id).expanduser().resolve()
    except OSError as error:
        raise PreviewError(404, "unavailable", "audio file is not available") from error
    if requested != indexed:
        raise PreviewError(404, "unknown_track", "track is not in the loaded library")
    if not requested.is_file():
        raise PreviewError(404, "unavailable", "audio file is not available")
    return requested
