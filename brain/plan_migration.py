"""Idempotent, non-destructive promotion of legacy singleton plan files."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
from contextlib import closing
from pathlib import Path

from brain import library_index, plan_paths
from brain.plan_revision import file_rev, write_checked
from brain.plan_types import slugify

MIGRATION_VERSION = 1
DEFAULT_NAME = "Imported working mix"


class MigrationAborted(RuntimeError):
    pass


def _legacy_files():
    legacy = plan_paths.legacy_paths()
    return {"selection": legacy.selection, "exclusions": legacy.exclusions, "playlist": legacy.playlist, "mix_plan": legacy.mix_plan}


def migrate(*, dry_run: bool = False) -> dict:
    files = _legacy_files()
    existing = {name: path for name, path in files.items() if path.exists()}
    report = {"status": "planned" if dry_run else "migrated", "files": sorted(existing), "slug": slugify(DEFAULT_NAME)}
    version = 0
    if library_index.DEFAULT_INDEX.exists():
        with closing(sqlite3.connect(library_index.DEFAULT_INDEX)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            version = db.execute("PRAGMA user_version").fetchone()[0]
    if version >= MIGRATION_VERSION:
        return {"status": "already_migrated", "files": [], "slug": None}
    if dry_run:
        return report
    if not existing:
        return {"status": "nothing_to_migrate", "files": [], "slug": None}
    plans = plan_paths.DEFAULT_PLANS_DIR
    plans.mkdir(parents=True, exist_ok=True)
    slug = report["slug"]
    target = plans / slug
    if target.exists():
        raise MigrationAborted(f"migration target already exists while user_version is 0: {target}")
    stage = Path(tempfile.mkdtemp(prefix=".migration-", dir=plans))
    promoted = False
    pointer = plans / "active.json"
    pointer_before = pointer.read_bytes() if pointer.exists() else None
    now = time.time()
    try:
        meta = {"version": 1, "plan_id": str(uuid.uuid4()), "slug": slug, "display_name": DEFAULT_NAME, "description": "", "status": "wip", "created_at": now, "updated_at": now, "last_opened_at": None, "collection_id": None, "origin": "migrated", "origin_ref": str(plan_paths.legacy_paths().root)}
        write_checked(stage / "plan.json", meta, "")
        mapping = {"selection": "selection.json", "exclusions": "exclusions.json", "playlist": "playlist.json", "mix_plan": "mix_plan.json"}
        for name, path in existing.items():
            shutil.copy2(path, stage / mapping[name])
        defaults = {"notes.json": {"version": 1, "overrides": []}, "bunches.json": {"version": 1, "activated": []}, "transitions.json": {"version": 1, "overrides": []}}
        for filename, payload in defaults.items():
            write_checked(stage / filename, payload, "")
        os.replace(stage, target)
        promoted = True
        write_checked(pointer, {"version": 1, "active_slug": slug, "updated_at": time.time()}, file_rev(pointer))
        library_index.DEFAULT_INDEX.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(library_index.DEFAULT_INDEX)) as db:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("BEGIN IMMEDIATE")
            db.execute(f"PRAGMA user_version = {MIGRATION_VERSION}")
            db.commit()
    except BaseException as error:
        if stage.exists():
            shutil.rmtree(stage)
        if promoted and target.exists():
            shutil.rmtree(target)
        if pointer_before is None:
            pointer.unlink(missing_ok=True)
        else:
            fd, restore_name = tempfile.mkstemp(prefix=".active-restore-", dir=plans)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(pointer_before)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(restore_name, pointer)
            finally:
                Path(restore_name).unlink(missing_ok=True)
        raise MigrationAborted(str(error)) from error
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(migrate(dry_run=args.dry_run), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
