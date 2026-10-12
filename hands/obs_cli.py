"""Harness-neutral JSON entry point for local OBS control."""
from __future__ import annotations

import argparse
import base64
import json
import getpass
import os
from pathlib import Path
import stat
import sys

from hands.obs_control import READ_ACTIONS, WRITE_ACTIONS, OUTPUT_ACTIONS, validate_action


class CLIError(ValueError):
    pass


class JSONParser(argparse.ArgumentParser):
    def error(self, message):
        raise CLIError('Invalid command arguments; use --help for usage')


def default_password_path() -> Path:
    return Path.home() / '.config' / 'claw-dj' / 'obs-websocket-password'


def outside_checkout(path: Path) -> None:
    if path.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise CLIError('Secrets and generated screenshots must stay outside the source checkout')


def load_password(path=None) -> str | None:
    if path is None and os.environ.get('OBS_WEBSOCKET_PASSWORD'):
        return os.environ['OBS_WEBSOCKET_PASSWORD']
    explicit = path is not None
    path = Path(path) if explicit else default_password_path()
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'r') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
                raise CLIError('Password file must be an owned regular file with mode 0600')
            password = handle.read(4097)
            if not password or len(password) > 4096 or '\n' in password or '\r' in password:
                raise CLIError('Password file contains an invalid password')
            return password
    except FileNotFoundError:
        if not explicit:
            return None
        raise CLIError('Password file not found') from None
    except (OSError, UnicodeError):
        raise CLIError('Cannot read private password file; symlinks are not accepted') from None


def setup_password(path=None) -> None:
    if not sys.stdin.isatty():
        raise CLIError('Run setup-password directly in your own interactive terminal')
    path = Path(path) if path is not None else default_password_path()
    outside_checkout(path)
    password = getpass.getpass('OBS WebSocket password (hidden; not Twitch password): ')
    if not password or len(password) > 4096 or '\n' in password or '\r' in password:
        raise CLIError('Empty or invalid password')
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(password)
    except OSError:
        raise CLIError('Cannot create password file; existing files are never overwritten') from None


def main(argv=None, *, control_factory=None) -> int:
    parser = JSONParser(description=__doc__)
    parser.add_argument('action')
    parser.add_argument('--data', default='{}', help='JSON object of action parameters')
    parser.add_argument('--allow-write', action='store_true')
    parser.add_argument('--allow-output', action='store_true')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=4455, type=int)
    parser.add_argument('--timeout', default=5.0, type=float)
    parser.add_argument('--password-file', type=Path)
    parser.add_argument('--save', type=Path, help='New file path for screenshot PNG; never overwrites')
    action = None
    try:
        args = parser.parse_args(argv)
        action = args.action
        if action == 'capabilities':
            print(json.dumps({'ok': True, 'action': action, 'data': {
                'read': sorted(READ_ACTIONS), 'write': sorted(WRITE_ACTIONS),
                'output': sorted(OUTPUT_ACTIONS), 'transport': 'OBS WebSocket v5',
                'host': 'loopback only', 'default_port': 4455}}))
            return 0
        if action == 'setup-password':
            setup_password(args.password_file)
            print(json.dumps({'ok': True, 'action': action, 'data': {'saved': True}}))
            return 0
        if action not in READ_ACTIONS | WRITE_ACTIONS | OUTPUT_ACTIONS:
            raise CLIError('Unknown or forbidden action')
        if action in WRITE_ACTIONS | OUTPUT_ACTIONS and not args.allow_write:
            raise CLIError('Mutation requires --allow-write and explicit human authorization')
        if action in OUTPUT_ACTIONS and not args.allow_output:
            raise CLIError('Output control requires --allow-output and explicit human authorization')
        try:
            data = json.loads(args.data)
        except ValueError:
            raise CLIError('--data must be a valid JSON object') from None
        if not isinstance(data, dict):
            raise CLIError('--data must be a JSON object')
        if action == 'screenshot':
            data.setdefault('width', 640)
            data.setdefault('height', 360)
        try:
            validate_action(action, data, allow_write=args.allow_write,
                            allow_output=args.allow_output)
        except (ValueError, PermissionError):
            raise CLIError('Invalid action parameters; see docs/OBS_AGENT_CONTROL.md') from None
        if action == 'screenshot' and args.save is None:
            raise CLIError('Screenshot requires --save with a new PNG path')
        if args.save is not None and action != 'screenshot':
            raise CLIError('--save is only valid for screenshot')
        if args.save is not None and (args.save.exists() or args.save.is_symlink()):
            raise CLIError('Screenshot destination already exists')
        if args.save is not None:
            outside_checkout(args.save)
        if control_factory is None:
            from hands.obs_control import OBSControl
            control_factory = OBSControl
        password = load_password(args.password_file)
        with control_factory(host=args.host, port=args.port, password=password,
                             timeout_s=args.timeout) as obs:
            result = obs.execute(action, data, allow_write=args.allow_write,
                                 allow_output=args.allow_output)
        if action == 'screenshot':
            assert args.save is not None
            uri = result.get('imageData', '')
            prefix = 'data:image/png;base64,'
            if not isinstance(uri, str) or not uri.startswith(prefix):
                raise CLIError('OBS did not return a PNG screenshot')
            try:
                image = base64.b64decode(uri[len(prefix):], validate=True)
            except ValueError:
                raise CLIError('OBS returned invalid screenshot encoding') from None
            if not image.startswith(b'\x89PNG\r\n\x1a\n') or len(image) > 32 * 1024 * 1024:
                raise CLIError('OBS returned invalid or oversized screenshot')
            try:
                fd = os.open(args.save, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as handle:
                    handle.write(image)
            except OSError:
                raise CLIError('Cannot create screenshot; parent directory must exist and file must be new') from None
            result = {'path': str(args.save.absolute()), 'bytes': len(image)}
        print(json.dumps({'ok': True, 'action': action, 'data': result}, allow_nan=False))
        return 0
    except CLIError as exc:
        print(json.dumps({'ok': False, 'action': action, 'error': str(exc)}))
        return 2
    except Exception:
        print(json.dumps({'ok': False, 'action': action,
                          'error': 'OBS operation failed; check server, authentication, parameters, and dependency installation'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
