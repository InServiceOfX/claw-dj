"""DJ showcase: the model choreographs moves; the rules decide."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from brain.build_mix_plan import compose_mix_plan
from brain.showcase_moves import build_prompt, validate


def _t(n: int, **extra) -> list[dict]:
    return [{"i": i, **extra} for i in range(n)]


class ValidateTest(TestCase):
    def test_unknown_moves_are_dropped(self) -> None:
        plan, _ = validate([{"i": 3, "flourish": "laser_show", "exit": "teleport"}], _t(8), smooth_opening=0)
        self.assertNotIn(3, plan)

    def test_model_never_gets_an_abrupt_exit(self) -> None:
        # Ernest, 2026-10-17: "I hate the sharp cut off ... DO NOT DO THAT."
        moves = [{"i": i, "flourish": "loop_roll", "exit": "echo_out"} for i in range(8)]
        plan, notes = validate(moves, _t(8), smooth_opening=0)
        self.assertEqual([i for i, p in plan.items() if p["exit"] != "none"], [])
        self.assertTrue(any("declined (no abrupt cut-offs)" in n for n in notes))
        self.assertNotIn("echo_out", build_prompt(_t(2), ""))

    def test_notes_and_lineage_and_opening_win(self) -> None:
        transitions = _t(8)
        transitions[4]["noted_style"] = True
        transitions[5]["lineage"] = True
        transitions[6]["no_flourish"] = True
        moves = [{"i": i, "flourish": "stutter_fill", "exit": "filter_drop"} for i in (0, 4, 5, 6)]
        plan, _ = validate(moves, transitions, smooth_opening=1)
        self.assertNotIn(0, plan)
        self.assertEqual(plan[4]["exit"], "none")
        self.assertEqual(plan[5]["exit"], "none")
        self.assertIsNone(plan.get(6, {}).get("flourish"))


def _rows(n: int = 6) -> list[dict]:
    return [
        {"track_id": f"/music/{i}.mp3", "artist": f"A{i}", "title": f"T{i}",
         "bpm": 92.0 + i * 0.5, "key": "Am", "duration_seconds": 240.0}
        for i in range(n)
    ]


class ComposeShowcaseTest(TestCase):
    def setUp(self) -> None:
        patcher = patch("brain.mix_order_brief._snare_confidence", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _build(self, profile: str, ask, notes=None) -> dict:
        with TemporaryDirectory() as directory:
            playlist = Path(directory) / "playlist.json"
            playlist.write_text(json.dumps(_rows()))
            return compose_mix_plan(
                playlist=playlist, profile_name=profile, order_engine="claude-cli",
                out=Path(directory) / "mix_plan.json", ask=ask, dj_notes_lookup=notes or {},
            )

    @staticmethod
    def _ask(prompt: str) -> str:
        if "choreographing a DJ SHOWCASE" in prompt:
            return json.dumps({"moves": [
                {"i": i, "flourish": "transformer_cut", "exit": "echo_out" if i == 3 else "none", "why": "peak"}
                for i in range(5)
            ]})
        return json.dumps({"order": [], "notes": []})  # review: invalid -> skipped

    def test_showcase_uses_model_moves(self) -> None:
        plan = self._build("dj-showcase", self._ask)
        sources = [s.get("showcase_source") for s in plan["segments"]]
        self.assertIn("model", sources)
        self.assertTrue(any(s["showcase_move"] == "transformer_cut" for s in plan["segments"]))
        # Ernest, 2026-10-17: no abrupt cut-offs; the model's echo-out is dropped
        self.assertFalse(any(s["technique"] == "echo_out_exit" for s in plan["segments"]))

    def test_other_mix_feels_ignore_choreography(self) -> None:
        plan = self._build("mix-to-listen", self._ask)
        self.assertFalse(any(s.get("showcase_source") for s in plan["segments"]))

    def test_dj_note_exit_wins_over_model(self) -> None:
        notes = {}
        plan_probe = self._build("dj-showcase", self._ask)
        outgoing = plan_probe["tracks"][3]["track_id"]
        notes[outgoing] = 'exit_style=filter_drop abrupt_reason="highlight the drop"'
        plan = self._build("dj-showcase", self._ask, notes)
        index = [t["track_id"] for t in plan["tracks"]].index(outgoing)
        self.assertEqual(plan["segments"][index]["technique"], "filter_drop_exit")
        transition = [e for e in plan["events"] if e["op"] == "transition"][index]
        self.assertEqual(transition["abrupt_exit"]["reason"], "highlight the drop")

    def test_dj_note_exit_without_ernests_reason_is_ignored(self) -> None:
        plan_probe = self._build("dj-showcase", self._ask)
        outgoing = plan_probe["tracks"][3]["track_id"]
        plan = self._build("dj-showcase", self._ask, {outgoing: "exit_style=echo_out"})
        index = [t["track_id"] for t in plan["tracks"]].index(outgoing)
        self.assertNotIn(plan["segments"][index]["technique"], ("echo_out_exit", "filter_drop_exit"))

    def test_model_failure_keeps_rotation(self) -> None:
        def boom(prompt):
            raise RuntimeError("down")
        plan = self._build("dj-showcase", boom)
        self.assertFalse(any(s.get("showcase_source") for s in plan["segments"]))
        self.assertTrue(any("choreography skipped" in n for n in plan["profile"]["order_notes"]))
