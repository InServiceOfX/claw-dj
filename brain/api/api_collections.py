"""Loopback API for listing, estimating, registering, and activating collections."""
from __future__ import annotations

from pathlib import Path

from brain import collection, collection_registry, folder_dialog
from brain.api.common import ApiError, finish


PATTERN = "/api/collections"
METHODS = ("GET", "POST")


def _registry_path(app) -> Path:
    return Path(getattr(app, "registry_path", collection_registry.DEFAULT_REGISTRY))


def _alive(thread) -> bool:
    return bool(thread is not None and thread.is_alive())


def _busy_reasons(app) -> list[str]:
    reasons: list[str] = []
    if _alive(getattr(app, "scan_thread", None)):
        reasons.append("scan")
    state = getattr(app, "mix_state", {}) or {}
    if _alive(getattr(app, "enrich_thread", None)) or state.get("enriching"):
        reasons.append("enrichment")
    if _alive(getattr(app, "mix_thread", None)) or state.get("building"):
        reasons.append("build")
    if _alive(getattr(app, "mix_run_thread", None)) or state.get("running"):
        reasons.append("live_playback")
    return reasons


def _listed(app) -> dict:
    registry_path = _registry_path(app)
    active = collection_registry.active_collection(registry_path=registry_path)
    active_id = active["collection_id"] if active else None
    collections = []
    for record in collection_registry.list_collections(registry_path=registry_path):
        mount = Path(record["mount_base"])
        index = Path(record["index_path"])
        collections.append(
            {
                **record,
                "mounted": mount.is_dir() and index.is_file(),
                "active": record["collection_id"] == active_id,
            }
        )
    reasons = _busy_reasons(app)
    return {
        "active_collection_id": active_id,
        "collections": collections,
        "busy": bool(reasons),
        "busy_reasons": reasons,
    }


def _reject_unknown(body: dict, allowed: set[str]) -> None:
    unexpected = sorted(set(body) - allowed)
    if unexpected:
        raise ApiError(
            400,
            "invalid_field",
            f"unexpected field(s): {', '.join(unexpected)}",
            fields=unexpected,
        )


def _path(value, field: str) -> Path:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ApiError(400, "invalid_field", f"{field} must be a directory path", field=field)
    return Path(value).expanduser()


def _roots(body: dict, mount: Path) -> list[Path]:
    raw = body.get("roots")
    if raw is None:
        return [mount]
    if not isinstance(raw, list) or not raw:
        raise ApiError(400, "invalid_field", "roots must be a non-empty list", field="roots")
    return [_path(value, "roots") for value in raw]


def _require_idle(app) -> None:
    reasons = _busy_reasons(app)
    if reasons:
        raise ApiError(
            409,
            "collection_busy",
            "cannot switch collections while work is running",
            busy_reasons=reasons,
        )


def handle(app, params, method, body, query, headers=None):
    registry_path = _registry_path(app)
    if method == "GET":
        return finish(_listed(app))

    body = body or {}
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_body", "request body must be an object")
    action = body.get("action")
    if action == "browse":
        # Native OS folder dialog. The browser cannot return real absolute
        # paths from <input type=file webkitdirectory>; this local process can.
        _reject_unknown(body, {"action", "prompt", "initial"})
        prompt = body.get("prompt") or "Choose a folder"
        if not isinstance(prompt, str) or not prompt.strip():
            raise ApiError(400, "invalid_field", "prompt must be a non-empty string", field="prompt")
        initial_raw = body.get("initial")
        initial: Path | None = None
        if initial_raw is not None:
            if not isinstance(initial_raw, str):
                raise ApiError(400, "invalid_field", "initial must be a path string", field="initial")
            initial = Path(initial_raw).expanduser() if initial_raw.strip() else None
        try:
            chosen = folder_dialog.choose_directory(prompt=prompt.strip(), initial=initial)
        except folder_dialog.FolderDialogCancelled:
            return finish({"cancelled": True, "path": None})
        except folder_dialog.FolderDialogUnavailable as error:
            raise ApiError(503, "folder_dialog_unavailable", str(error)) from error
        except OSError as error:
            raise ApiError(500, "folder_dialog_failed", str(error)) from error
        return finish({"cancelled": False, "path": str(chosen)})

    if action == "estimate":
        _reject_unknown(body, {"action", "mount_base", "roots"})
        mount = _path(body.get("mount_base"), "mount_base").resolve()
        roots = _roots(body, mount)
        try:
            normalized = collection._validated_roots(mount, roots)
            return finish(collection.estimate_scan(normalized))
        except (collection.CollectionNotConfiguredError, OSError) as error:
            raise ApiError(400, "invalid_path", str(error)) from error

    if action == "register":
        _reject_unknown(
            body,
            {"action", "mount_base", "roots", "display_name", "scan"},
        )
        _require_idle(app)
        mount = _path(body.get("mount_base"), "mount_base")
        roots = _roots(body, mount)
        display_name = body.get("display_name")
        if display_name is not None and (not isinstance(display_name, str) or not display_name.strip()):
            raise ApiError(
                400, "invalid_field", "display_name must not be empty", field="display_name"
            )
        scan_requested = body.get("scan", False)
        if not isinstance(scan_requested, bool):
            raise ApiError(400, "invalid_field", "scan must be true or false", field="scan")
        try:
            result = collection.create_collection(
                mount,
                roots=roots,
                display_name=display_name,
                registry_path=registry_path,
            )
        except collection_registry.CollectionUnavailable as error:
            raise ApiError(503, "collection_unavailable", str(error)) from error
        except (collection.CollectionNotConfiguredError, ValueError, OSError) as error:
            raise ApiError(400, "invalid_collection", str(error)) from error
        app.reload()
        response = {**result, "scan_started": False}
        if scan_requested:
            app.start_scan()
            response["scan_started"] = True
        return finish(response, 201)

    if action == "activate":
        _reject_unknown(body, {"action", "collection_id"})
        _require_idle(app)
        collection_id = body.get("collection_id")
        if not isinstance(collection_id, str) or not collection_id:
            raise ApiError(
                400, "invalid_field", "collection_id is required", field="collection_id"
            )
        try:
            result = collection.activate_collection(
                collection_id, registry_path=registry_path
            )
        except KeyError as error:
            raise ApiError(
                404,
                "collection_not_found",
                f"unknown collection: {collection_id}",
                collection_id=collection_id,
            ) from error
        except collection_registry.CollectionUnavailable as error:
            raise ApiError(503, "collection_unavailable", str(error)) from error
        app.reload()
        return finish({**result, "active": True})

    raise ApiError(
        400,
        "invalid_action",
        "action must be browse, estimate, register, or activate",
        legal_values=["browse", "estimate", "register", "activate"],
    )
