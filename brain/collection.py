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

from brain.library_index import DEFAULT_INDEX, configured_roots, connect

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser(
        "register", help="record where the collection is mounted on this machine"
    )
    register.add_argument(
        "mount_base",
        type=Path,
        nargs="?",
        help="collection root; derived from configured scan roots when omitted",
    )
    register.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=(
            "where claw-dj keeps its files on the drive; an existing clawdj/ "
            "directory at or above the collection is discovered automatically"
        ),
    )
    subparsers.add_parser("status", help="show the registered collection")
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

    collection = configured_collection(args.index)
    if collection is None:
        print("no collection registered on this machine yet")
        print("run: uv run python -m brain.collection register")
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
