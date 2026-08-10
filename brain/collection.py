"""Where the music collection is, recorded as data instead of as a constant.

The collection is normally one external drive holding every genre root. Two
facts about it need to be known, and neither belongs in source code:

  * `collection_id` -- a stable UUID identifying the drive itself. It lives in
    a marker file ON the collection (`<mount_base>/clawdj/collection.json`), so
    plugging the same drive into another machine yields the same id there. It
    is deliberately NOT the volume label: labels are renameable, and a label
    baked into code is exactly what this module exists to remove.
  * `mount_base` -- where that collection is mounted on THIS machine, which
    legitimately differs per machine (`/Volumes/<label>` on macOS,
    `/media/<user>/<label>` on Linux). Stored per machine in the local index.

Track identity is still the absolute file path (see
tests/test_music_collection_identity.py for why that is deliberate and what
would have to change together to move off it). So the volume label remains
part of the collection contract for now: a replacement drive must be named
identically or every track_id, and every human dj_notes annotation keyed to
one, orphans. Recording the mount base here is what makes that contract
inspectable, and is the groundwork for eventually not needing it.

Usage:

    uv run python -m brain.collection status
    uv run python -m brain.collection register            # derive from roots
    uv run python -m brain.collection register /Volumes/MyDrive/Music
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from contextlib import closing
from pathlib import Path

from brain import collection_registry
from brain.collection_registry import DEFAULT_REGISTRY
from brain.library_index import DEFAULT_INDEX, configured_roots, connect
from brain.scan_library import AUDIO_EXTENSIONS

# claw-dj's own files on the drive (portable database, archives, the identity
# marker) live together in one directory, kept out of the music tree.
COLLECTION_DIR_NAME = "clawdj"
MARKER_NAME = "collection.json"
PORTABLE_DB_NAME = "library.sqlite3"
# How far above the collection to look for an existing clawdj/ directory. The
# established layout puts it at the drive root while the music sits in a
# subdirectory (`<drive>/clawdj/` beside `<drive>/Music/`), so the data
# directory is NOT simply `<mount_base>/clawdj` and must not be assumed --
# guessing wrong would strand an existing portable database.
DATA_DIR_SEARCH_PARENTS = 3


class CollectionNotConfiguredError(RuntimeError):
    """No collection has been registered on this machine yet."""


def find_data_dir(mount_base: Path) -> Path:
    """Locate claw-dj's directory on the drive, preferring one that exists.

    Searches the collection and its nearest parents so an established layout
    keeps its current portable database and archives. Falls back to creating
    the directory inside the collection for a fresh drive.
    """
    candidate = mount_base
    for _ in range(DATA_DIR_SEARCH_PARENTS + 1):
        existing = candidate / COLLECTION_DIR_NAME
        if existing.is_dir():
            return existing
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return mount_base / COLLECTION_DIR_NAME


def marker_path(data_dir: Path) -> Path:
    return data_dir / MARKER_NAME


def portable_db_path(data_dir: Path) -> Path:
    return data_dir / PORTABLE_DB_NAME


def derive_mount_base(roots: list[str] | None = None, *, index_path: Path = DEFAULT_INDEX) -> Path:
    """Infer the collection root from the already-configured scan roots.

    The genre roots share a parent (the six under `<drive>/Music`, say), so the
    common ancestor is the collection. Deriving it means an existing setup --
    and a second machine that mounts the same drive at the same place -- needs
    no manual configuration.
    """
    paths = [Path(root) for root in (roots if roots is not None else configured_roots(index_path))]
    if not paths:
        raise CollectionNotConfiguredError(
            "no scan roots configured yet, so the collection cannot be derived; "
            "add a music folder first or pass an explicit mount base"
        )
    common = Path(os.path.commonpath([str(path) for path in paths]))
    # commonpath of a single root returns that root; its parent is the
    # collection, since a root is a genre directory inside it.
    return common.parent if len(paths) == 1 else common


def read_or_create_marker(
    data_dir: Path, *, preferred_id: str | None = None
) -> tuple[str, bool]:
    """Return (collection_id, created). Reuses an existing marker if present.

    `preferred_id` adopts an id this machine already recorded for the same
    collection when the drive has no marker yet — otherwise re-registering an
    index that predates the marker would mint a second identity and orphan
    everything associated with the first.
    """
    marker = marker_path(data_dir)
    if marker.exists():
        try:
            payload = json.loads(marker.read_text())
            existing = str(payload["collection_id"])
        except (OSError, json.JSONDecodeError, KeyError) as error:
            raise RuntimeError(
                f"{marker} exists but is not readable as a collection marker: {error}. "
                "Move it aside to re-register this collection."
            ) from error
        return existing, False

    collection_id = preferred_id or str(uuid.uuid4())
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {"collection_id": collection_id, "created_at": time.time()}, indent=2
        )
        + "\n"
    )
    return collection_id, True


def register_collection(
    mount_base: Path | None = None,
    *,
    index_path: Path = DEFAULT_INDEX,
    data_dir: Path | None = None,
) -> dict:
    """Record where the collection is mounted on this machine.

    Writes a marker file into claw-dj's directory on the drive if it has none,
    so the identity travels with the drive rather than living only in this
    machine's index. `data_dir` overrides the discovered location.
    """
    base = (
        Path(mount_base).expanduser().resolve()
        if mount_base is not None
        else derive_mount_base(index_path=index_path)
    )
    if not base.is_dir():
        raise CollectionNotConfiguredError(f"not a directory: {base}")

    resolved_data_dir = (
        Path(data_dir).expanduser().resolve()
        if data_dir is not None
        else find_data_dir(base)
    )
    # An id this machine already recorded for the same collection takes
    # precedence over minting a new one, so an index that predates the on-drive
    # marker keeps its identity instead of orphaning it.
    with closing(connect(index_path)) as db:
        previous = db.execute(
            "SELECT collection_id FROM collections WHERE mount_base=?", (str(base),)
        ).fetchone()
    collection_id, created = read_or_create_marker(
        resolved_data_dir,
        preferred_id=previous["collection_id"] if previous else None,
    )
    now = time.time()
    with closing(connect(index_path)) as db:
        db.execute(
            """INSERT INTO collections(collection_id, mount_base, data_dir,
                                       volume_label, created_at, last_seen_at)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(collection_id) DO UPDATE SET
                   mount_base=excluded.mount_base,
                   data_dir=excluded.data_dir,
                   volume_label=excluded.volume_label,
                   last_seen_at=excluded.last_seen_at""",
            (collection_id, str(base), str(resolved_data_dir), base.name, now, now),
        )
        db.commit()
    return {
        "collection_id": collection_id,
        "mount_base": str(base),
        "data_dir": str(resolved_data_dir),
        "volume_label": base.name,
        "marker_created": created,
        "portable_db": str(portable_db_path(resolved_data_dir)),
    }


def configured_collection(index_path: Path = DEFAULT_INDEX) -> dict | None:
    with closing(connect(index_path)) as db:
        row = db.execute(
            "SELECT * FROM collections ORDER BY last_seen_at DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def resolve_portable_db(index_path: Path = DEFAULT_INDEX) -> Path:
    """Where the portable copy of the library database lives on the collection.

    Replaces a hardcoded `/Volumes/<label>/...` default. Raises rather than
    guessing, so a wrong drive is never written to silently.
    """
    collection = configured_collection(index_path)
    if collection is None:
        raise CollectionNotConfiguredError(
            "no music collection registered on this machine — run "
            "`uv run python -m brain.collection register` (it can derive the "
            "location from your configured scan roots), or pass an explicit "
            "path with --usb-db"
        )
    if not collection["data_dir"]:
        # Migrated from an index that recorded no data directory. Guessing
        # here could point at an empty sibling of the real database.
        raise CollectionNotConfiguredError(
            "the registered collection has no recorded data directory (its "
            "index predates that field) — re-run "
            "`uv run python -m brain.collection register` to fill it in, or "
            "pass an explicit path with --usb-db"
        )
    return portable_db_path(Path(collection["data_dir"]))


def _validated_roots(mount_base: Path, roots: list[Path] | None) -> list[Path]:
    selected = list(roots) if roots is not None else [mount_base]
    if not selected:
        raise CollectionNotConfiguredError("at least one scan root is required")
    normalized: list[Path] = []
    for root in selected:
        candidate = Path(root).expanduser().resolve()
        if not candidate.is_dir():
            raise CollectionNotConfiguredError(f"not a directory: {candidate}")
        try:
            candidate.relative_to(mount_base)
        except ValueError as error:
            raise CollectionNotConfiguredError(
                f"scan root is outside the chosen collection {mount_base}: {candidate}"
            ) from error
        if candidate not in normalized:
            normalized.append(candidate)
    return normalized


def ensure_legacy_collection(
    *,
    legacy_index: Path = DEFAULT_INDEX,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict | None:
    """Record the pre-existing local index without moving or rewriting it."""
    legacy_index = Path(legacy_index).expanduser().resolve()
    if not legacy_index.is_file():
        return None
    for record in collection_registry.list_collections(registry_path=registry_path):
        if Path(record["index_path"]) == legacy_index:
            if collection_registry.active_collection(registry_path=registry_path) is None:
                return collection_registry.activate(
                    record["collection_id"], registry_path=registry_path
                )
            return record
    legacy_id = "legacy-local-" + uuid.uuid5(
        uuid.NAMESPACE_URL, f"claw-dj:{legacy_index}"
    ).hex
    record = {
        "collection_id": legacy_id,
        "display_name": "Legacy local library",
        "mount_base": str(legacy_index.parent),
        "data_dir": str(legacy_index.parent),
        "index_path": str(legacy_index),
        "volume_label": legacy_index.parent.name,
        "last_used_at": None,
    }
    return collection_registry.register(
        record,
        activate=collection_registry.active_collection(registry_path=registry_path) is None,
        registry_path=registry_path,
    )


def create_collection(
    mount_base: Path,
    *,
    roots: list[Path] | None = None,
    display_name: str | None = None,
    data_dir: Path | None = None,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict:
    """Create or reuse one per-volume marker/database, then activate it.

    This performs schema and configured-root initialization only.  It never
    scans tags or starts any analysis/enrichment work.
    """
    base = Path(mount_base).expanduser().resolve()
    if not base.is_dir():
        raise CollectionNotConfiguredError(f"not a directory: {base}")
    normalized_roots = _validated_roots(base, roots)
    resolved_data_dir = (
        Path(data_dir).expanduser().resolve()
        if data_dir is not None
        else find_data_dir(base).resolve()
    )
    resolved_data_dir.mkdir(parents=True, exist_ok=True)
    collection_id, marker_created = read_or_create_marker(resolved_data_dir)
    index_path = portable_db_path(resolved_data_dir).resolve()

    # Explicit create/switch is the migration boundary. Startup never calls
    # this and therefore remains silent and non-mutating.
    ensure_legacy_collection(
        legacy_index=DEFAULT_INDEX,
        registry_path=registry_path,
    )
    with closing(connect(index_path)) as db:
        added_at = time.time()
        for root in normalized_roots:
            db.execute(
                "INSERT INTO roots(path, added_at) VALUES (?, ?) "
                "ON CONFLICT(path) DO NOTHING",
                (str(root), added_at),
            )
        db.commit()

    record = {
        "collection_id": collection_id,
        "display_name": (display_name or base.name or collection_id).strip(),
        "mount_base": str(base),
        "data_dir": str(resolved_data_dir),
        "index_path": str(index_path),
        "volume_label": base.name,
        "last_used_at": None,
    }
    registered = collection_registry.register(
        record, activate=True, registry_path=registry_path
    )
    return {**registered, "marker_created": marker_created, "roots": [str(root) for root in normalized_roots]}


def activate_collection(
    collection_id: str, *, registry_path: Path = DEFAULT_REGISTRY
) -> dict:
    ensure_legacy_collection(
        legacy_index=DEFAULT_INDEX,
        registry_path=registry_path,
    )
    return collection_registry.activate(collection_id, registry_path=registry_path)


def estimate_scan(roots: list[Path]) -> dict:
    """Count candidate paths only; do not open tags or call external services."""
    normalized: list[Path] = []
    paths: set[str] = set()
    for root in roots:
        candidate = Path(root).expanduser().resolve()
        if not candidate.is_dir():
            raise CollectionNotConfiguredError(f"not a directory: {candidate}")
        normalized.append(candidate)
        paths.update(
            str(path.resolve())
            for path in candidate.rglob("*")
            if path.suffix.lower() in AUDIO_EXTENSIONS and not path.name.startswith("._")
        )
    # Existing scans range widely with storage contention. This is presented
    # as an estimate, not a deadline; 20 path/tag records per second is a
    # deliberately conservative local-only baseline.
    count = len(paths)
    estimated_seconds = round(count / 20, 1)
    return {
        "roots": [str(root) for root in normalized],
        "audio_file_count": count,
        "estimated_seconds": estimated_seconds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_parser = subparsers.add_parser(
        "register", help="record where the collection is mounted on this machine"
    )
    register_parser.add_argument(
        "mount_base",
        type=Path,
        nargs="?",
        help="collection root; derived from configured scan roots when omitted",
    )
    register_parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=(
            "where claw-dj keeps its files on the drive; an existing clawdj/ "
            "directory at or above the collection is discovered automatically"
        ),
    )
    subparsers.add_parser("list", help="list known per-volume collections")
    subparsers.add_parser("status", help="show the registered collection")
    create_parser = subparsers.add_parser("new", help="create or reuse a per-volume collection")
    create_parser.add_argument("mount_base", type=Path)
    create_parser.add_argument("--root", action="append", type=Path, dest="roots")
    create_parser.add_argument("--name", dest="display_name")
    create_parser.add_argument(
        "--scan",
        action="store_true",
        help="explicitly run the incremental metadata scan after creation",
    )
    use_parser = subparsers.add_parser("use", help="activate a known collection")
    use_parser.add_argument("collection_id")
    args = parser.parse_args()

    if args.command == "register":
        try:
            result = register_collection(
                args.mount_base, index_path=args.index, data_dir=args.data_dir
            )
        except (CollectionNotConfiguredError, RuntimeError) as error:
            raise SystemExit(f"could not register the collection: {error}") from None
        print(f"collection id : {result['collection_id']}")
        print(f"mount base    : {result['mount_base']}")
        print(f"data dir      : {result['data_dir']}")
        print(f"volume label  : {result['volume_label']}")
        print(f"portable db   : {result['portable_db']}")
        if result["marker_created"]:
            print(f"wrote a new marker to {marker_path(Path(result['data_dir']))}")
        else:
            print("reused the marker already on the drive")
        return

    if args.command == "list":
        active = collection_registry.active_collection(registry_path=args.registry)
        active_id = active["collection_id"] if active else None
        for item in collection_registry.list_collections(registry_path=args.registry):
            marker = "*" if item["collection_id"] == active_id else " "
            print(f"{marker} {item['collection_id']}  {item['display_name']}  {item['mount_base']}")
        return

    if args.command == "new":
        requested_roots = args.roots or [args.mount_base]
        estimate = estimate_scan(requested_roots)
        print(
            f"estimated {estimate['audio_file_count']} audio files "
            f"(~{estimate['estimated_seconds']:.1f}s metadata scan)"
        )
        result = create_collection(
            args.mount_base,
            roots=requested_roots,
            display_name=args.display_name,
            registry_path=args.registry,
        )
        print(f"active collection: {result['display_name']} ({result['collection_id']})")
        print(f"database: {result['index_path']}")
        if args.scan:
            from brain.library import DEFAULT_CRATE_CACHE
            from brain.library_index import export_records
            from brain.scan_library import incremental_scan

            summary = incremental_scan(
                [Path(root) for root in result["roots"]],
                index_path=Path(result["index_path"]),
            )
            DEFAULT_CRATE_CACHE.write_text(json.dumps(export_records(Path(result["index_path"])), indent=2))
            print(
                f"scan complete: {summary['new']} new, {summary['changed']} changed, "
                f"{summary['unchanged']} unchanged"
            )
        return

    if args.command == "use":
        try:
            result = activate_collection(args.collection_id, registry_path=args.registry)
        except (KeyError, collection_registry.CollectionUnavailable) as error:
            raise SystemExit(f"could not activate collection: {error}") from None
        print(f"active collection: {result['display_name']} ({result['collection_id']})")
        print(f"database: {result['index_path']}")
        return

    active = collection_registry.active_collection(registry_path=args.registry)
    if active is not None:
        print(f"collection id : {active['collection_id']}")
        print(f"display name  : {active['display_name']}")
        print(f"mount base    : {active['mount_base']}")
        print(f"data dir      : {active['data_dir']}")
        print(f"volume label  : {active['volume_label']}")
        print(f"mounted now   : {'yes' if Path(active['mount_base']).is_dir() else 'NO'}")
        print(f"database      : {active['index_path']}")
        return

    collection = configured_collection(args.index)
    if collection is None:
        print("no collection registered on this machine yet")
        print("run: uv run python -m brain.collection new MOUNT --root ROOT")
        return
    mount_base = Path(collection["mount_base"])
    portable_db = portable_db_path(Path(collection["data_dir"]))
    print(f"collection id : {collection['collection_id']}")
    print(f"mount base    : {mount_base}")
    print(f"data dir      : {collection['data_dir']}")
    print(f"volume label  : {collection['volume_label']}")
    print(f"mounted now   : {'yes' if mount_base.is_dir() else 'NO'}")
    print(f"portable db   : {portable_db}"
          f"{'' if portable_db.exists() else '  (not exported yet)'}")


if __name__ == "__main__":
    main()
