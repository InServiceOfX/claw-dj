"""Machine-local registry for per-volume music collections.

The active pointer belongs on this machine, not inside any removable
collection.  A missing registry deliberately means "use the legacy local
index"; an unavailable registered collection is an error, never a reason to
silently select a different database.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path


DEFAULT_REGISTRY = Path(__file__).parent / "data" / "collections.json"
REGISTRY_VERSION = 1
REQUIRED_FIELDS = (
    "collection_id",
    "display_name",
    "mount_base",
    "data_dir",
    "index_path",
    "volume_label",
    "last_used_at",
)


class RegistryFormatError(RuntimeError):
    """The machine-local registry is malformed or internally conflicting."""


class CollectionUnavailable(RuntimeError):
    """A known collection's mount or SQLite database is not available."""


def _empty() -> dict:
    return {"version": REGISTRY_VERSION, "active_collection_id": None, "collections": []}


def _normalized_record(record: dict) -> dict:
    if not isinstance(record, dict):
        raise RegistryFormatError("collection record must be an object")
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise RegistryFormatError(f"collection record is missing: {', '.join(missing)}")
    result = {field: record[field] for field in REQUIRED_FIELDS}
    for field in REQUIRED_FIELDS[:-1]:
        if not isinstance(result[field], str) or not result[field].strip():
            raise RegistryFormatError(f"collection {field} must be a non-empty string")
    if result["last_used_at"] is not None and not isinstance(result["last_used_at"], (int, float)):
        raise RegistryFormatError("collection last_used_at must be a number or null")
    for field in ("mount_base", "data_dir", "index_path"):
        path = Path(result[field]).expanduser()
        if not path.is_absolute():
            raise RegistryFormatError(f"collection {field} must be an absolute path")
        result[field] = str(path)
    return result


def _validate(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise RegistryFormatError("collection registry must be a JSON object")
    if payload.get("version") != REGISTRY_VERSION:
        raise RegistryFormatError(
            f"unsupported collection registry version: {payload.get('version')!r}"
        )
    active = payload.get("active_collection_id")
    if active is not None and (not isinstance(active, str) or not active):
        raise RegistryFormatError("active_collection_id must be a string or null")
    raw_records = payload.get("collections")
    if not isinstance(raw_records, list):
        raise RegistryFormatError("collections must be a list")
    records = [_normalized_record(record) for record in raw_records]
    by_id: dict[str, dict] = {}
    by_index: dict[str, str] = {}
    for record in records:
        collection_id = record["collection_id"]
        if collection_id in by_id:
            raise RegistryFormatError(f"duplicate collection identity: {collection_id}")
        index_path = record["index_path"]
        if index_path in by_index:
            raise RegistryFormatError(
                f"collection database {index_path} is claimed by both "
                f"{by_index[index_path]} and {collection_id}"
            )
        by_id[collection_id] = record
        by_index[index_path] = collection_id
    if active is not None and active not in by_id:
        raise RegistryFormatError(f"active collection is not registered: {active}")
    return {"version": REGISTRY_VERSION, "active_collection_id": active, "collections": records}


def _load(registry_path: Path) -> dict:
    if not registry_path.exists():
        return _empty()
    try:
        payload = json.loads(registry_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RegistryFormatError(f"could not read collection registry {registry_path}: {error}") from error
    return _validate(payload)


def _write(payload: dict, registry_path: Path) -> None:
    checked = _validate(payload)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{registry_path.name}.", suffix=".tmp", dir=registry_path.parent
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w") as handle:
            json.dump(checked, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, registry_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _available(record: dict) -> bool:
    return Path(record["mount_base"]).is_dir() and Path(record["index_path"]).is_file()


def _require_available(record: dict) -> None:
    mount = Path(record["mount_base"])
    index = Path(record["index_path"])
    if not mount.is_dir():
        raise CollectionUnavailable(
            f"collection {record['display_name']!r} is not mounted at {mount}"
        )
    if not index.is_file():
        raise CollectionUnavailable(
            f"collection database is unavailable at {index}; reconnect the volume and retry"
        )


def list_collections(*, registry_path: Path = DEFAULT_REGISTRY) -> list[dict]:
    """Return validated records in stable registration order."""
    return [dict(record) for record in _load(Path(registry_path))["collections"]]


def active_collection(*, registry_path: Path = DEFAULT_REGISTRY) -> dict | None:
    payload = _load(Path(registry_path))
    active = payload["active_collection_id"]
    if active is None:
        return None
    return dict(next(record for record in payload["collections"] if record["collection_id"] == active))


def active_index_path(*, registry_path: Path = DEFAULT_REGISTRY, fallback: Path) -> Path:
    registry_path = Path(registry_path)
    if not registry_path.exists():
        return Path(fallback)
    record = active_collection(registry_path=registry_path)
    if record is None:
        raise RegistryFormatError("collection registry exists but has no active collection")
    _require_available(record)
    return Path(record["index_path"])


def register(
    record: dict, *, activate: bool = True, registry_path: Path = DEFAULT_REGISTRY
) -> dict:
    """Register one collection, preserving every other record atomically."""
    registry_path = Path(registry_path)
    candidate = _normalized_record(record)
    payload = _load(registry_path)
    records = payload["collections"]
    existing = next(
        (item for item in records if item["collection_id"] == candidate["collection_id"]),
        None,
    )
    same_index = next(
        (item for item in records if item["index_path"] == candidate["index_path"]),
        None,
    )
    if same_index is not None and same_index["collection_id"] != candidate["collection_id"]:
        raise ValueError(
            f"database already belongs to collection {same_index['collection_id']}: "
            f"{candidate['index_path']}"
        )
    if existing is not None:
        moved = any(
            existing[field] != candidate[field]
            for field in ("mount_base", "data_dir", "index_path")
        )
        if moved and _available(existing):
            raise ValueError(
                f"collection identity {candidate['collection_id']} conflicts with its "
                "existing available paths"
            )
        if existing["last_used_at"] is not None and candidate["last_used_at"] is None:
            candidate["last_used_at"] = existing["last_used_at"]
        records[records.index(existing)] = candidate
    else:
        records.append(candidate)
    if activate:
        _require_available(candidate)
        candidate["last_used_at"] = time.time()
        payload["active_collection_id"] = candidate["collection_id"]
    _write(payload, registry_path)
    return dict(candidate)


def activate(
    collection_id: str, *, registry_path: Path = DEFAULT_REGISTRY
) -> dict:
    registry_path = Path(registry_path)
    payload = _load(registry_path)
    record = next(
        (item for item in payload["collections"] if item["collection_id"] == collection_id),
        None,
    )
    if record is None:
        raise KeyError(collection_id)
    _require_available(record)
    record["last_used_at"] = time.time()
    payload["active_collection_id"] = collection_id
    _write(payload, registry_path)
    return dict(record)
