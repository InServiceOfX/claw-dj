"""Wrapper lifecycle regression, with a fake runner and no Mixxx connection."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RunMixScriptTests(unittest.TestCase):
    def test_edit_during_playback_cannot_break_shell_after_runner_completes(self):
        source = Path(__file__).resolve().parents[1] / 'scripts/run_mix.sh'
        subprocess.run(['bash', '-n', str(source)], check=True)
        for args in ([], ['--dry-run']):
            with self.subTest(args=args), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'scripts').mkdir()
                (root / 'bin').mkdir()
                script = root / 'scripts/run_mix.sh'
                script.write_text(source.read_text())
                plan = root / 'plan.json'
                plan.write_text('{}')
                uv = root / 'bin/uv'
                uv.write_text(f'#!{sys.executable}\n'
                              'import sys\n'
                              'if "-m" in sys.argv:\n'
                              '    print("FAKE_RUNNER_STARTED", flush=True)\n'
                              '    sys.stdin.readline()\n'
                              '    print("mix plan complete", flush=True)\n')
                uv.chmod(0o755)
                env = {**os.environ, 'PATH': str(root / 'bin') + os.pathsep + os.environ['PATH']}
                with subprocess.Popen(['bash', str(script), '--plan', str(plan), *args],
                                      env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True) as process:
                    try:
                        for line in process.stdout:
                            if line.strip() == 'FAKE_RUNNER_STARTED':
                                break
                        else:
                            self.fail('fake runner did not start')
                        # Simulate an in-place edit while playback is waiting.
                        # This deliberately invalid file must never be reread.
                        script.write_text('"' * 32769)
                        output, errors = process.communicate('\n', timeout=5)
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                    self.assertEqual(process.returncode, 0, errors)
                    self.assertIn('mix plan complete', output)
                    self.assertNotIn('unexpected EOF', errors)
