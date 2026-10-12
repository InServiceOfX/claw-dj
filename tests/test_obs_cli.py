"""Harness-neutral OBS command-line contract, without a live OBS dependency."""
from __future__ import annotations

import contextlib
import base64
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class OBSCLITests(unittest.TestCase):
    def setUp(self):
        # Never inherit a personal secret-manager value in synthetic tests.
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch('hands.obs_cli.default_password_path',
                               side_effect=AssertionError('personal default path forbidden')))

    def run_cli(self, argv, **kwargs):
        from hands import obs_cli
        # control_factory alone does not bypass CLI credential loading.
        with patch.object(obs_cli, 'load_password', return_value='synthetic-cli-password'):
            return obs_cli.main(argv, **kwargs)

    def test_synthetic_cli_cannot_read_default_private_password(self):
        from hands import obs_cli
        class Control:
            def __init__(self, **kwargs):
                self.password = kwargs['password']
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def execute(self, *args, **kwargs):
                return {}
        # Guard before invocation: even the RED run cannot open a real file.
        with patch('hands.obs_cli.os.open', side_effect=AssertionError('private file forbidden')) as opened, \
                patch('hands.obs_cli.default_password_path', side_effect=AssertionError('default path forbidden')) as default, \
                contextlib.redirect_stdout(io.StringIO()):
            code = self.run_cli(['version'], control_factory=Control)
        self.assertEqual(code, 0)
        default.assert_not_called()
        opened.assert_not_called()

    def test_secret_setup_refuses_the_source_checkout(self):
        from hands import obs_cli
        path = Path(obs_cli.__file__).resolve().parents[1] / 'obs-test-secret-must-not-exist'
        with patch('sys.stdin.isatty', return_value=True), patch('getpass.getpass', return_value='fixture-only'):
            try:
                with self.assertRaises(obs_cli.CLIError):
                    obs_cli.setup_password(path)
            finally:
                if path.exists():
                    path.unlink()  # Clean up only this synthetic test-owned file.

    def test_capabilities_work_without_obs_connection(self):
        from hands import obs_cli
        def forbidden(**kwargs):
            self.fail('capabilities must not instantiate OBS')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.run_cli(['capabilities'], control_factory=forbidden)
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())['data']
        self.assertIn('status', data['read'])
        self.assertIn('scene-switch', data['write'])
        self.assertIn('stream-start', data['output'])
        self.assertNotIn('GetStreamServiceSettings', str(data))

    def test_screenshot_is_saved_not_dumped_to_agent_context(self):
        from hands import obs_cli
        image = b'\x89PNG\r\n\x1a\nsynthetic-test-fixture'
        class Control:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def execute(self, *args, **kwargs):
                return {'imageData': 'data:image/png;base64,' + base64.b64encode(image).decode()}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'preview.png'
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = self.run_cli(['screenshot', '--data', '{"sourceName":"Scene"}',
                                     '--save', str(path)], control_factory=Control)
            self.assertEqual(code, 0)
            self.assertEqual(path.read_bytes(), image)
            self.assertNotIn('imageData', out.getvalue())
            self.assertEqual(json.loads(out.getvalue())['data']['path'], str(path))
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.run_cli(['screenshot', '--data', '{"sourceName":"Scene"}',
                                     '--save', str(path)], control_factory=Control)
            self.assertEqual(code, 2)
            self.assertEqual(path.read_bytes(), image)

    def test_password_file_is_private_and_not_echoed(self):
        from hands import obs_cli
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'password'
            path.write_text('test-fixture-password')
            path.chmod(0o600)
            self.assertEqual(obs_cli.load_password(path), 'test-fixture-password')
            path.chmod(0o644)
            with self.assertRaises(obs_cli.CLIError):
                obs_cli.load_password(path)
            link = Path(directory) / 'link'
            link.symlink_to(path)
            with self.assertRaises(obs_cli.CLIError):
                obs_cli.load_password(link)

    def test_setup_password_refuses_overwrite(self):
        from hands import obs_cli
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'password'
            with patch('getpass.getpass', return_value='test-only-password'), patch('sys.stdin.isatty', return_value=True):
                obs_cli.setup_password(path)
                with self.assertRaises(obs_cli.CLIError):
                    obs_cli.setup_password(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.read_text(), 'test-only-password')

    def test_secret_setup_requires_interactive_terminal(self):
        from hands import obs_cli
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'password'
            with patch('sys.stdin.isatty', return_value=False), patch('getpass.getpass', return_value='fixture-password') as prompt:
                with self.assertRaises(obs_cli.CLIError):
                    obs_cli.setup_password(path)
                prompt.assert_not_called()
            self.assertFalse(path.exists())

    def test_unexpected_transport_exception_never_echoes_password(self):
        from hands import obs_cli
        class Control:
            def __init__(self, **kwargs):
                raise RuntimeError('fixture-secret-value')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.run_cli(['version'], control_factory=Control)
        self.assertEqual(code, 1)
        self.assertNotIn('fixture-secret-value', out.getvalue())
        self.assertFalse(json.loads(out.getvalue())['ok'])

    def test_mutation_is_denied_before_control_construction(self):
        from hands import obs_cli
        calls = []
        class Control:
            def __init__(self, **kwargs):
                calls.append(kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def execute(self, *args, **kwargs):
                return {}
        for action in ('scene-switch', 'stream-start', 'record-stop',
                       'GetStreamServiceSettings'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = self.run_cli([action], control_factory=Control)
            self.assertEqual(code, 2)
            self.assertFalse(json.loads(out.getvalue())['ok'])
        self.assertEqual(calls, [])

    def test_output_requires_separate_permission(self):
        from hands import obs_cli
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.run_cli(['stream-start', '--allow-write'])
        self.assertEqual(code, 2)
        self.assertIn('allow-output', json.loads(out.getvalue())['error'])

    def test_malformed_data_returns_json_not_traceback(self):
        from hands import obs_cli
        for data in ('{', '[]', 'null'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = self.run_cli(['version', '--data', data])
            self.assertEqual(code, 2)
            self.assertFalse(json.loads(out.getvalue())['ok'])

    def test_read_command_emits_one_json_document(self):
        self.assertIsNotNone(importlib.util.find_spec('hands.obs_cli'),
                             'OBS JSON CLI must exist')
        cli = importlib.import_module('hands.obs_cli')

        class Control:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def execute(self, action, data, **kwargs):
                self_action = action
                if self_action != 'version':
                    raise AssertionError('Unexpected action')
                return {'obsVersion': 'test-fixture'}

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.run_cli(['version'], control_factory=Control)
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload, {'ok': True, 'action': 'version',
                                   'data': {'obsVersion': 'test-fixture'}})


if __name__ == '__main__':
    unittest.main()
