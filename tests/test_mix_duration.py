"""Play-time estimates and the shell startup summary, using synthetic plans."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase

from hands.mix_duration import estimate_mix_seconds, mix_duration_label


def two_song_plan():
    return {
        "track_count": 2,
        "tracks": [{"track_id": "a", "bpm": 120}, {"track_id": "b", "bpm": 60}],
        "events": [
            {"op": "reset_instrument"},
            {"op": "load", "deck": 1, "track_id": "a"},
            {"op": "load", "deck": 2, "track_id": "b"},
            {"op": "start", "deck": 1},
            {"op": "play_body", "deck": 1, "beats": 120, "seconds": 999},
            {"op": "transition", "from_deck": 1, "to_deck": 2, "transition_beats": 16},
            {"op": "finale", "deck": 2, "beats": 60, "seconds": 999},
            {"op": "stop_all"},
        ],
    }


class MixDurationTests(TestCase):
    def test_sequential_excerpts_and_one_overlap_interval(self):
        # A minute of each song plus one eight-second blend = 2:08.
        plan = two_song_plan()
        before = copy.deepcopy(plan)
        self.assertEqual(estimate_mix_seconds(plan), 128)
        self.assertEqual(mix_duration_label(plan), "about 2 min")
        self.assertEqual(plan, before)

    def test_held_tempo_and_native_settle(self):
        plan = two_song_plan()
        plan["events"][3]["bpm_target"] = 60
        self.assertEqual(estimate_mix_seconds(plan), 196)
        plan["events"][5]["incoming_bpm_target"] = 120
        self.assertEqual(estimate_mix_seconds(plan), 166)

    def test_tempo_ramp_is_part_of_the_body(self):
        plan = two_song_plan()
        plan["events"][4].update(tempo_ramp_beats=60, exit_bpm_target=60)
        # 30s steady + ~40s ramp + 16s blend + 60s finale.
        self.assertEqual(estimate_mix_seconds(plan), 146)

    def test_play_to_end_uses_remainder_seconds(self):
        plan = two_song_plan()
        plan["events"][6].update(play_to_end=True, seconds=240)
        self.assertEqual(estimate_mix_seconds(plan), 308)

    def test_seconds_only_and_missing_bpm(self):
        plan = {"events": [{"op": "play_body", "seconds": 600},
                           {"op": "finale", "seconds": 1200}]}
        self.assertEqual(mix_duration_label(plan), "about 30 min")
        # Missing metadata still permits an estimate from the planned seconds.
        plan = two_song_plan()
        plan["tracks"] = []
        plan["events"][4]["seconds"] = 60
        plan["events"][6]["seconds"] = 60
        self.assertAlmostEqual(estimate_mix_seconds(plan), 129.6)

    def test_simultaneous_timeline_uses_last_end_not_sum_of_clips(self):
        plan = {
            "execution_mode": "live_source_tracks",
            "performance": {"clips": [
                {"start": 0, "length": 1800},
                {"start": 1500, "length": 1200},
                {"start": 0, "length": 2700},  # simultaneous supporting bed
            ]},
            "events": [{"op": "stop_clip", "at": 2700}],
        }
        self.assertEqual(estimate_mix_seconds(plan), 2700)
        self.assertEqual(mix_duration_label(plan), "about 45 min")

    def test_hours_short_and_empty_plans(self):
        for seconds, expected in [(3720, "about 1 hr 2 min"),
                                  (3600, "about 1 hr"), (10, "under 1 min")]:
            self.assertEqual(mix_duration_label({"events": [
                {"op": "finale", "seconds": seconds}]}), expected)
        self.assertEqual(estimate_mix_seconds({"events": []}), 0)

    def test_startup_estimate_and_argument_forwarding_without_live_playback(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            # Quoting in paths must not become executable Python/shell syntax.
            plan_path = folder / "mix 'quoted' $literal.json"
            plan_path.write_text(json.dumps(two_song_plan()))
            uv = folder / "uv"
            uv.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "assert sys.argv[1:3] == ['run', 'python']\n"
                "if sys.argv[3:5] == ['-m', 'hands.run_mix_plan']:\n"
                "    print('TEST_RUNNER_ARGS=' + json.dumps(sys.argv[5:]))\n"
                "else:\n"
                "    os.execv(sys.executable, [sys.executable, *sys.argv[3:]])\n"
            )
            uv.chmod(0o755)
            env = {**os.environ, "PATH": f"{folder}:{os.environ['PATH']}"}
            for dry_run in (False, True):
                with self.subTest(dry_run=dry_run):
                    flags = ["--dry-run"] if dry_run else []
                    result = subprocess.run(
                        ["bash", "scripts/run_mix.sh", "--plan", str(plan_path),
                         *flags, "--port", "9999", "--max-events", "1", "--record"],
                        cwd=root, env=env, capture_output=True, text=True, check=True,
                    )
                    self.assertIn("Estimated total mix length: about 2 min", result.stdout)
                    self.assertLess(result.stdout.index("Estimated total mix length"),
                                    result.stdout.index("TEST_RUNNER_ARGS="))
                    args_line = next(line for line in result.stdout.splitlines()
                                     if line.startswith("TEST_RUNNER_ARGS="))
                    forwarded = json.loads(args_line.split("=", 1)[1])
                    self.assertEqual(forwarded, ["--plan", str(plan_path), *flags,
                                                "--port", "9999", "--max-events", "1", "--record"])
