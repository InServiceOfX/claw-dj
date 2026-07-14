"""Archive a known-good mix plan and the files needed to reproduce it."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = REPO_ROOT / "brain" / "data" / "mix_plan.json"
DEFAULT_PLAYLIST = REPO_ROOT / "brain" / "data" / "playlist.json"
DEFAULT_ARCHIVES = REPO_ROOT / "brain" / "data" / "archives"
RUNTIME_SOURCES = (
    REPO_ROOT / "brain" / "build_mix_plan.py",
    REPO_ROOT / "brain" / "mix_profiles.py",
    REPO_ROOT / "hands" / "run_mix_plan.py",
    REPO_ROOT / "hands" / "transition.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str | None:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def archive_mix_plan(
    *,
    plan: Path = DEFAULT_PLAN,
    playlist: Path = DEFAULT_PLAYLIST,
    archive_root: Path = DEFAULT_ARCHIVES,
    label: str = "known-good",
) -> Path:
    if not plan.exists():
        raise FileNotFoundError(f"mix plan not found: {plan}")
    if not playlist.exists():
        raise FileNotFoundError(f"playlist not found: {playlist}")

    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H%M%S_%z")
    slug = re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-") or "known-good"
    destination = archive_root / f"{stamp}_{slug}"
    suffix = 2
    while destination.exists():
        destination = archive_root / f"{stamp}_{slug}-{suffix}"
        suffix += 1
    runtime_dir = destination / "runtime"
    runtime_dir.mkdir(parents=True)

    archived: list[dict[str, str]] = []
    for source, relative in (
        (plan, Path("mix_plan.json")),
        (playlist, Path("playlist.json")),
        *((source, Path("runtime") / source.relative_to(REPO_ROOT)) for source in RUNTIME_SOURCES),
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        archived.append({"path": str(relative), "sha256": sha256(target)})

    plan_payload = json.loads(plan.read_text())
    manifest = {
        "version": 1,
        "archived_at": datetime.now().astimezone().isoformat(),
        "label": label,
        "successful_full_playback": True,
        "track_count": plan_payload.get("track_count"),
        "event_count": len(plan_payload.get("events") or []),
        "git_branch": git_value("branch", "--show-current"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": bool(git_value("status", "--porcelain")),
        "files": archived,
        "run": (
            "uv run python -m hands.run_mix_plan "
            "--plan brain/data/mix_plan.json --port 9995"
        ),
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (destination / "RUN.md").write_text(
        "# Known-good claw-dj mix\n\n"
        "This snapshot completed a full audible playback before archival.\n\n"
        "From the repository root, restore `mix_plan.json` and `playlist.json` "
        "to `brain/data/`, then run:\n\n"
        "```bash\n"
        "uv run python -m hands.run_mix_plan \\\n"
        "  --plan brain/data/mix_plan.json \\\n"
        "  --port 9995\n"
        "```\n"
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVES)
    parser.add_argument("--label", default="known-good")
    args = parser.parse_args()
    destination = archive_mix_plan(
        plan=args.plan,
        playlist=args.playlist,
        archive_root=args.archive_root,
        label=args.label,
    )
    print(f"archived mix plan: {destination}")


if __name__ == "__main__":
    main()
