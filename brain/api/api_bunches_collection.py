"""Reusable library-bunch collection route."""
from __future__ import annotations

from brain import bunch_store, library_index
from brain.api.common import ApiError, finish

PATTERN = "/api/bunches"
METHODS = ("GET", "POST")


def _one(query, name):
    value = (query or {}).get(name)
    return value[0] if isinstance(value, list) and value else value


def hydrate(bunch):
    titles = {}
    if bunch.track_ids:
        try:
            marks = ",".join("?" for _ in bunch.track_ids)
            with library_index.connect(library_index.DEFAULT_INDEX) as db:
                titles = {row["track_id"]: dict(row) for row in db.execute(f"SELECT track_id,title,artist FROM tracks WHERE track_id IN ({marks})", list(bunch.track_ids))}
        except Exception:
            pass
    return {
        "bunch_id": bunch.bunch_id, "label": bunch.label, "ordered": bunch.ordered,
        "notes": bunch.notes, "archived": bunch.archived,
        "members": [{"track_id": track_id, "title": titles.get(track_id, {}).get("title", track_id), "artist": titles.get(track_id, {}).get("artist", ""), "position": index} for index, track_id in enumerate(bunch.track_ids)],
    }


def handle(app, params, method, body, query, headers=None):
    if method == "GET":
        track_id = _one(query, "track_id")
        bunches = bunch_store.list_for_track(track_id) if track_id else bunch_store.list()
        return finish({"bunches": [hydrate(item) for item in bunches]})
    body = body or {}
    try:
        bunch = bunch_store.create(body.get("label", ""), body.get("track_ids", []), bool(body.get("ordered", True)), "human", body.get("notes", ""))
    except ValueError as error:
        raise ApiError(400, "invalid_bunch", str(error), field="track_ids") from error
    return finish(hydrate(bunch), 201)
