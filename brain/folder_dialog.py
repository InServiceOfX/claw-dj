"""Native folder chooser for the local claw-dj editor.

The browser cannot hand the page a real absolute path from
``<input type="file" webkitdirectory>`` (sandbox). This process *can* open a
system dialog and return a POSIX path, because the playlist editor is a
loopback-only local app.
"""

from __future__ import annotations

import platform
import shlex
import subprocess
import sys
from pathlib import Path


class FolderDialogCancelled(Exception):
    """User dismissed the native folder dialog."""


class FolderDialogUnavailable(Exception):
    """No native dialog backend is available on this platform/session."""


def choose_directory(
    *,
    prompt: str = "Choose a folder",
    initial: Path | str | None = None,
) -> Path:
    """Block until the user picks a directory; return its resolved path.

    Raises FolderDialogCancelled if the user cancels, FolderDialogUnavailable
    if this environment cannot show a dialog.
    """
    start = _initial_dir(initial)
    system = platform.system()
    if system == "Darwin":
        return _choose_macos(prompt=prompt, initial=start)
    if system == "Linux":
        return _choose_linux(prompt=prompt, initial=start)
    if system == "Windows":
        return _choose_tk(prompt=prompt, initial=start)
    raise FolderDialogUnavailable(f"no folder dialog backend for {system}")


def _initial_dir(initial: Path | str | None) -> Path | None:
    if initial is None or initial == "":
        return None
    candidate = Path(initial).expanduser()
    try:
        candidate = candidate.resolve()
    except OSError:
        return None
    if candidate.is_dir():
        return candidate
    parent = candidate.parent
    return parent if parent.is_dir() else None


def _choose_macos(*, prompt: str, initial: Path | None) -> Path:
    # AppleScript chooses a folder and returns a POSIX path. Quotes in the
    # prompt are escaped; the path is passed via a separate quoted form.
    safe_prompt = prompt.replace("\\", "\\\\").replace('"', '\\"')
    lines = [
        f'set thePrompt to "{safe_prompt}"',
    ]
    if initial is not None:
        lines.append(f"set theStart to POSIX file {shlex.quote(str(initial))}")
        lines.append(
            'set theFolder to choose folder with prompt thePrompt default location theStart'
        )
    else:
        lines.append("set theFolder to choose folder with prompt thePrompt")
    lines.append("return POSIX path of theFolder")
    script = "\n".join(lines)
    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError as error:
        raise FolderDialogUnavailable("osascript is not available") from error
    except subprocess.TimeoutExpired as error:
        raise FolderDialogUnavailable("folder dialog timed out") from error
    if completed.returncode != 0:
        # User cancel is typically status 1 with empty or -128-ish messaging.
        raise FolderDialogCancelled("folder dialog cancelled")
    path_text = (completed.stdout or "").strip()
    if not path_text:
        raise FolderDialogCancelled("folder dialog cancelled")
    return Path(path_text).expanduser().resolve()


def _choose_linux(*, prompt: str, initial: Path | None) -> Path:
    for argv in (
        _zenity_argv(prompt, initial),
        _kdialog_argv(prompt, initial),
    ):
        if argv is None:
            continue
        try:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired as error:
            raise FolderDialogUnavailable("folder dialog timed out") from error
        if completed.returncode != 0:
            raise FolderDialogCancelled("folder dialog cancelled")
        path_text = (completed.stdout or "").strip()
        if path_text:
            return Path(path_text).expanduser().resolve()
        raise FolderDialogCancelled("folder dialog cancelled")
    return _choose_tk(prompt=prompt, initial=initial)


def _zenity_argv(prompt: str, initial: Path | None) -> list[str] | None:
    argv = ["zenity", "--file-selection", "--directory", f"--title={prompt}"]
    if initial is not None:
        argv.append(f"--filename={initial}/")
    return argv


def _kdialog_argv(prompt: str, initial: Path | None) -> list[str] | None:
    start = str(initial) if initial is not None else str(Path.home())
    return ["kdialog", "--getexistingdirectory", start, "--title", prompt]


def _choose_tk(*, prompt: str, initial: Path | None) -> Path:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as error:  # pragma: no cover - depends on runtime
        raise FolderDialogUnavailable(f"tkinter folder dialog unavailable: {error}") from error
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    kwargs = {"title": prompt, "mustexist": True}
    if initial is not None:
        kwargs["initialdir"] = str(initial)
    try:
        chosen = filedialog.askdirectory(**kwargs)
    finally:
        root.destroy()
    if not chosen:
        raise FolderDialogCancelled("folder dialog cancelled")
    return Path(chosen).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    """CLI smoke helper: print one chosen path or exit 1 on cancel."""
    args = list(sys.argv[1:] if argv is None else argv)
    prompt = args[0] if args else "Choose a folder"
    initial = args[1] if len(args) > 1 else None
    try:
        print(choose_directory(prompt=prompt, initial=initial))
        return 0
    except FolderDialogCancelled:
        return 1
    except FolderDialogUnavailable as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
