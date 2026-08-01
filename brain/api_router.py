"""Small deterministic router for the local stdlib HTTP server."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from brain.plan_revision import StalePlanError


class NotFound(LookupError):
    pass


class MethodNotAllowed(LookupError):
    def __init__(self, methods):
        self.methods = tuple(sorted(methods))
        self.headers = {"Allow": ", ".join(self.methods)}
        super().__init__(f"method not allowed; use {self.headers['Allow']}")


@dataclass(frozen=True)
class _Route:
    pattern: str
    segments: tuple[str, ...]
    methods: tuple[str, ...]
    handler: object


_ROUTES: list[_Route] = []


def clear() -> None:
    _ROUTES.clear()


def register(pattern: str, methods: tuple[str, ...], handler) -> None:
    segments = tuple(part for part in pattern.strip("/").split("/") if part)
    if any(item.pattern == pattern for item in _ROUTES):
        raise ValueError(f"route already registered: {pattern}")
    _ROUTES.append(_Route(pattern, segments, tuple(m.upper() for m in methods), handler))


def _match(registered: _Route, segments: tuple[str, ...]):
    if len(registered.segments) != len(segments):
        return None
    params, score = {}, []
    for pattern, actual in zip(registered.segments, segments):
        if pattern.startswith("<") and pattern.endswith(">"):
            params[pattern[1:-1]] = actual
            score.append(0)
        elif pattern == actual:
            score.append(1)
        else:
            return None
    return tuple(score), params


def route(method: str, path: str):
    clean = urlparse(path).path
    segments = tuple(part for part in clean.strip("/").split("/") if part)
    matches = []
    for registered in _ROUTES:
        matched = _match(registered, segments)
        if matched is not None:
            score, params = matched
            matches.append((score, registered, params))
    if not matches:
        raise NotFound(clean)
    _, selected, params = max(matches, key=lambda item: item[0])
    if method.upper() not in selected.methods:
        raise MethodNotAllowed(selected.methods)
    return selected.handler, params


def invoke(handler, *args, **kwargs):
    """Invoke a route and translate the shared stale-write error at one point."""
    try:
        return handler(*args, **kwargs)
    except StalePlanError as error:
        return ({"error": "stale_plan", **error.payload()}, 409)
