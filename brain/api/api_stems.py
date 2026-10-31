"""Stems page routes: vocals-only and instrumental-only tracks, and live layers.

GET  /api/stems                 both lists (?kind=vocals|instrumentals&q=&refresh=1)
POST /api/stems/kind            {track_id, kind}: hand override (auto clears it)
GET  /api/stems/beds            ?vocal_id=: instrumentals ranked for one vocal
GET  /api/stems/layer           live layer status (polled while playing)
POST /api/stems/layer           {vocal_id, bed_id, vocal_from_seconds?, count_shift_beats?,
                                 lead_bars?, dry_run?, take_over?}: plan, or play live in Mixxx
POST /api/stems/layer/stop      stop the layer (gentle 1.5 s fade, decks reset)

Starting a layer is only ever a button press; nothing here renders audio.
"""
from __future__ import annotations

from brain.api.common import ApiError


def _one(query: dict, key: str, default: str = "") -> str:
    return (query.get(key) or [default])[0]


def list_stems(app, params, method, body, query, headers=None):
    try:
        result = app.stem_list(kind=_one(query, "kind") or None, search=_one(query, "q"),
                               refresh=_one(query, "refresh") == "1")
    except ValueError as error:
        raise ApiError(400, "bad_kind", str(error)) from error
    return result, 200


def set_kind(app, params, method, body, query, headers=None):
    track_id, kind = str(body.get("track_id") or ""), str(body.get("kind") or "")
    if not track_id or not kind:
        raise ApiError(400, "missing_field", "track_id and kind are required")
    try:
        return app.set_stem_kind(track_id, kind), 200
    except KeyError as error:
        raise ApiError(404, "unknown_track", str(error)) from error


def beds(app, params, method, body, query, headers=None):
    vocal_id = _one(query, "vocal_id")
    if not vocal_id:
        raise ApiError(400, "missing_field", "vocal_id is required")
    return app.stem_beds(vocal_id, limit=min(50, int(_one(query, "limit", "12")))), 200


def layer(app, params, method, body, query, headers=None):
    if method == "GET":
        return app.stem_layer_status(), 200
    try:
        return app.start_stem_layer(body), 200
    except ValueError as error:
        raise ApiError(409, "layer_refused", str(error)) from error


def layer_stop(app, params, method, body, query, headers=None):
    return app.stop_stem_layer(), 200


ROUTES = (
    ("/api/stems", ("GET",), list_stems),
    ("/api/stems/kind", ("POST",), set_kind),
    ("/api/stems/beds", ("GET",), beds),
    ("/api/stems/layer", ("GET", "POST"), layer),
    ("/api/stems/layer/stop", ("POST",), layer_stop),
)
