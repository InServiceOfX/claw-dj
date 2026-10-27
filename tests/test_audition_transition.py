"""Live transition audition: placement math, shared runner path, refusals.

Never talks to a real Mixxx: every control connection is a fake.
"""
from __future__ import annotations

import copy
import io
import itertools
import json
import shutil
import subprocess
import threading
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch

from hands import audition_transition as audition
from hands.audition_transition import (
    AuditionError,
    AuditionRefused,
    AuditionSession,
    find_transition,
    list_transitions,
    plan_audition,
    run_audition,
    running_mix_processes,
)

ANCHOR_1 = {
    "grid_bpm": 120.0,
    "first_beat_seconds": 2.0,
    "planned_anchor_beat_index": 80,
    "target_beat_mod4": 0,
    "target_beat_parity": 0,
}
ANCHOR_2 = {
    "grid_bpm": 100.0,
    "first_beat_seconds": 0.5,
    "planned_anchor_beat_index": 133,
    "target_beat_mod4": 1,
    "target_beat_parity": 1,
}


def make_plan() -> dict:
    """A -> B -> C -> D on decks 1/2/1/2, shaped like a real built artifact."""
    def load(op, deck, name, cue, beat):
        return {"op": op, "deck": deck, "track_id": f"/music/{name}.mp3", "artist": "Artist",
                "title": name, "cue_seconds": cue, "cue_beat_index": beat}

    return {
        "version": 1,
        "tracks": [
            {"track_id": "/music/A.mp3", "bpm": 120.0},
            {"track_id": "/music/B.mp3", "bpm": 100.0},
            {"track_id": "/music/C.mp3", "bpm": 95.0},
            {"track_id": "/music/D.mp3", "bpm": 90.0},
        ],
        "runtime": {"mixxx_control_port": 9995},
        "events": [
            {"op": "reset_instrument"},
            load("load", 1, "A", 10.0, 16),
            load("load", 2, "B", 1.0, 0),
            {"op": "start", "deck": 1},
            {"op": "play_body", "deck": 1, "beats": 63, "track": "Artist — A",
             "track_id": "/music/A.mp3", "phase_anchor": dict(ANCHOR_1)},
            load("preload_after_transition", 1, "C", 5.0, 8),
            {"op": "transition", "from_deck": 1, "to_deck": 2, "from_track": "Artist — A",
             "to_track": "Artist — B", "technique": "smooth_blend", "transition_beats": 32,
             "moves": ["sync", "snare_align", "eq_dip_out_mid", "crossfade", "eq_restore"],
             "incoming_bpm_target": 101.0},
            {"op": "play_body", "deck": 2, "beats": 100, "track": "Artist — B",
             "track_id": "/music/B.mp3", "phase_anchor": dict(ANCHOR_2)},
            load("preload_after_transition", 2, "D", 0.2, 0),
            {"op": "transition", "from_deck": 2, "to_deck": 1, "from_track": "Artist — B",
             "to_track": "Artist — C", "technique": "smooth_blend", "transition_beats": 32,
             "moves": ["sync", "crossfade"]},
            {"op": "play_body", "deck": 1, "beats": 64, "track": "Artist — C",
             "track_id": "/music/C.mp3",
             "phase_anchor": {"grid_bpm": 95.0, "first_beat_seconds": 0.1,
                              "planned_anchor_beat_index": 105, "target_beat_mod4": 1,
                              "target_beat_parity": 1}},
            {"op": "transition", "from_deck": 1, "to_deck": 2, "from_track": "Artist — C",
             "to_track": "Artist — D", "technique": "smooth_blend", "transition_beats": 32,
             "moves": ["sync", "crossfade"]},
            {"op": "finale", "deck": 2, "beats": 64},
            {"op": "stop_all"},
        ],
    }


class FakeMixxx:
    def __init__(self, values=None) -> None:
        self.values = dict(values or {})
        self.writes: list[tuple[str, str, float]] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def get(self, group: str, key: str) -> float:
        return float(self.values.get((group, key), 0.0))

    def set(self, group: str, key: str, value: float) -> None:
        self.values[(group, key)] = value
        self.writes.append((group, key, value))


class FakeControlFactory:
    def __init__(self, values=None) -> None:
        self.values = values or {}
        self.connections: list[FakeMixxx] = []

    def __call__(self, *, port: int, timeout_s: float = 5.0) -> FakeMixxx:
        connection = FakeMixxx(self.values)
        self.connections.append(connection)
        return connection


def refusing_factory(*args, **kwargs):
    raise AssertionError("must not connect to Mixxx")


def identity_prepare(plan, **kwargs):
    return plan


class PlanAuditionTests(TestCase):
    def test_lead_in_seek_comes_from_the_phase_anchor_grid(self) -> None:
        spec = plan_audition(make_plan(), 1, lead_bars=8, tail_bars=16)
        out = spec["outgoing"]
        self.assertEqual((out["deck"], out["anchor_beat_index"], out["lead_in_beat_index"]), (1, 80, 48))
        # first_beat + (48 - half-beat pre-roll) * 60/120
        self.assertAlmostEqual(out["lead_in_seconds"], 2.0 + 47.5 * 0.5)
        self.assertAlmostEqual(out["anchor_seconds"], 2.0 + 80 * 0.5)
        self.assertEqual(spec["setup"][1]["cue_seconds"], round(2.0 + 47.5 * 0.5, 4))
        body = spec["events"][1]
        self.assertEqual((body["op"], body["deck"], body["beats"]), ("play_body", 1, 32))

    def test_incoming_cue_is_taken_from_the_plan(self) -> None:
        first = plan_audition(make_plan(), 1)
        self.assertEqual(first["setup"][2]["cue_seconds"], 1.0)
        self.assertEqual(first["incoming"]["source_op"], "load")
        second = plan_audition(make_plan(), 2)
        # C was preloaded onto deck 1 and lands there after transition 1.
        self.assertEqual(second["setup"][2]["track_id"], "/music/C.mp3")
        self.assertEqual(second["setup"][2]["deck"], 1)
        self.assertEqual(second["setup"][2]["cue_seconds"], 5.0)
        self.assertEqual(second["incoming"]["cue_beat_index"], 8)

    def test_snare_align_and_phase_anchor_pass_through_unchanged(self) -> None:
        plan = make_plan()
        spec = plan_audition(plan, 1)
        self.assertTrue(spec["snare_align"])
        self.assertEqual(spec["events"][2], plan["events"][6])
        self.assertEqual(spec["events"][1]["phase_anchor"], ANCHOR_1)

    def test_outgoing_keeps_the_previous_play_bpm_hold(self) -> None:
        spec = plan_audition(make_plan(), 2)
        self.assertEqual(spec["outgoing"]["bpm_target"], 101.0)
        self.assertEqual(spec["events"][0], {"op": "start", "deck": 2, "detail": "audition lead-in", "bpm_target": 101.0})
        self.assertAlmostEqual(spec["outgoing"]["lead_in_seconds"], 0.5 + (133 - 32 - 0.5) * 0.6, places=3)
        # A settled entry plays at native tempo: no bpm_target at all.
        self.assertNotIn("bpm_target", plan_audition(make_plan(), 3)["events"][0])

    def test_lead_in_never_starts_before_the_outgoing_entry(self) -> None:
        spec = plan_audition(make_plan(), 1, lead_bars=40)
        out = spec["outgoing"]
        self.assertEqual(out["lead_in_beat_index"], 16)
        self.assertEqual(out["preroll_beats"], 0.0)
        self.assertAlmostEqual(out["lead_in_seconds"], 10.0)
        self.assertEqual(spec["events"][1]["beats"], 80 - 16 - 1)
        self.assertTrue(any("shortened" in note for note in spec["notes"]))

    def test_lead_in_does_not_cross_a_planned_skip(self) -> None:
        plan = make_plan()
        plan["events"][4].update(skip_after_beats=40, skip_beats=16)
        spec = plan_audition(plan, 1, lead_bars=8)
        # The count excludes jumped beats; the source position does not.
        self.assertEqual(spec["outgoing"]["anchor_beat_index"], 96)
        self.assertEqual(spec["outgoing"]["lead_in_beat_index"], 96 - (63 - 40) - 1)
        self.assertEqual(spec["events"][1]["phase_anchor"]["target_beat_mod4"], 0)

    def test_transition_after_a_vocal_layer_counts_the_layer(self) -> None:
        plan = make_plan()
        vocal = {"op": "transition", "from_deck": 2, "to_deck": 1, "technique": "vocal_over_bed",
                 "transition_beats": 64, "moves": ["sync", "vocal_over_bed"], "keep_outgoing_live": True}
        events = plan["events"]
        # B's ride -> vocal layer on deck 1 -> straight into B -> C, no ride between.
        events[9:9] = [vocal, {"op": "load", "deck": 1, "track_id": "/music/C.mp3", "cue_seconds": 5.0, "cue_beat_index": 8}]
        spec = plan_audition(plan, 3)
        self.assertEqual(spec["outgoing"]["anchor_beat_index"], 133 + 64 + 1)
        self.assertTrue(spec["events"][1]["phase_anchor"]["synthesized_for_audition"])
        self.assertTrue(any("vocal-over-bed" in note for note in spec["notes"]))

    def test_bounds_and_lookup_by_track_pair(self) -> None:
        plan = make_plan()
        transitions = list_transitions(plan)
        self.assertEqual([item["number"] for item in transitions], [1, 2, 3])
        self.assertEqual(find_transition(transitions, "/music/B.mp3", "/music/C.mp3"), 2)
        with self.assertRaises(AuditionError):
            find_transition(transitions, "/music/A.mp3", "/music/D.mp3")
        for number in (0, 4):
            with self.assertRaises(AuditionError) as ctx:
                plan_audition(plan, number)
            self.assertIn("this mix has 3", str(ctx.exception))

    def test_tail_bars_zero_stops_at_the_landing(self) -> None:
        ops = [event["op"] for event in plan_audition(make_plan(), 1, tail_bars=0)["events"]]
        self.assertEqual(ops, ["start", "play_body", "transition", "stop_all"])
        tail = plan_audition(make_plan(), 1, tail_bars=4)["events"][3]
        self.assertEqual((tail["op"], tail["deck"], tail["beats"]), ("finale", 2, 16))

    def test_performance_plans_are_refused(self) -> None:
        plan = make_plan()
        plan["execution_mode"] = "live_source_tracks"
        with self.assertRaises(AuditionError):
            plan_audition(plan, 1)


@patch("hands.source_cutoffs.prepare_plan", side_effect=identity_prepare)
class RunAuditionTests(TestCase):
    def test_dry_run_prints_the_plan_and_never_connects(self, _prepare) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            spec = run_audition(make_plan(), 1, port=9995, dry_run=True, control_factory=refusing_factory)
        text = output.getvalue()
        self.assertEqual(spec["number"], 1)
        self.assertIn("transition 1 of 3", text)
        self.assertIn("snare_align", text)
        self.assertIn("32-beat lead-in from grid beat 48", text)
        self.assertIn("cued 1.000s (beat 0)", text)
        self.assertIn("dry-run: no Mixxx connection", text)

    def test_refuses_while_a_mix_run_is_playing(self, _prepare) -> None:
        ps = "  999 1 /repo/.venv/bin/python -m hands.run_mix_plan --plan nastribute\n"
        with self.assertRaises(AuditionRefused) as ctx, redirect_stdout(io.StringIO()):
            run_audition(make_plan(), 1, port=9995, control_factory=refusing_factory, ps_output=ps)
        self.assertEqual(ctx.exception.code, "mix_running")

    def test_refuses_to_take_over_playing_decks(self, _prepare) -> None:
        factory = FakeControlFactory({("[Channel1]", "play"): 1.0})
        with self.assertRaises(AuditionRefused) as ctx, redirect_stdout(io.StringIO()):
            run_audition(make_plan(), 1, port=9995, control_factory=factory, ps_output="")
        self.assertEqual(ctx.exception.code, "decks_playing")
        self.assertEqual([c.writes for c in factory.connections], [[]])

    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.wait_for_beats")
    @patch("hands.run_mix_plan.time.sleep")
    @patch("hands.run_mix_plan.time.monotonic", side_effect=itertools.count(0.0, 0.5))
    @patch("hands.audition_transition.load_deck")
    @patch("hands.audition_transition.reset_instrument")
    def test_runs_the_full_runner_transition_path(
        self, reset, load, _monotonic, _sleep, wait_beats, _next_beat, _prepare
    ) -> None:
        values = {("[Channel1]", "bpm"): 120.0, ("[Channel2]", "bpm"): 100.0}
        factory = FakeControlFactory(values)
        with redirect_stdout(io.StringIO()):
            spec = run_audition(make_plan(), 1, port=9995, tail_bars=4, control_factory=factory, ps_output="")
        reset.assert_called_once()
        self.assertEqual(
            [call.args[1:5] for call in load.call_args_list],
            [(1, "/music/A.mp3", 0.1, spec["outgoing"]["lead_in_seconds"]), (2, "/music/B.mp3", 0.1, 1.0)],
        )
        # Lead-in body carries the plan's phase_anchor into the runtime guard.
        wait_beats.assert_any_call(9995, "[Channel1]", 32, timeout_s=90.0,
                                   phase_anchor=ANCHOR_1, trust_ride_beats=False)
        wait_beats.assert_any_call(9995, "[Channel2]", 16, timeout_s=90.0)
        writes = factory.connections[0].writes
        # The play_bpm hold on this transition means phase-only sync, then
        # the snare_align jump -- exactly the full runner's order.
        self.assertIn(("[Channel2]", "rateRange", 0.08), writes)
        sync_at = writes.index(("[Channel2]", "beatsync_phase", 1))
        jump_at = writes.index(("[Channel2]", "beatjump_1_forward", 1))
        self.assertGreater(jump_at, sync_at)
        self.assertIn(("[Master]", "crossfader", -1.0), writes)
        self.assertIn(("[Channel1]", "play", 1), writes)
        # stop_all, then a fresh connection silences both decks.
        self.assertIn(("[Channel2]", "play", 0), writes)
        self.assertIn(("[Channel1]", "play", 0), factory.connections[-1].writes)

    @patch("hands.audition_transition._run_events", side_effect=KeyboardInterrupt)
    @patch("hands.audition_transition.load_deck")
    @patch("hands.audition_transition.reset_instrument")
    def test_stop_silences_both_decks(self, _reset, _load, _run, _prepare) -> None:
        factory = FakeControlFactory()
        with redirect_stdout(io.StringIO()):
            spec = run_audition(make_plan(), 1, port=9995, control_factory=factory, ps_output="")
        self.assertTrue(spec["stopped"])
        last = factory.connections[-1].writes
        self.assertIn(("[Channel1]", "play", 0), last)
        self.assertIn(("[Channel2]", "play", 0), last)

    def test_cli_dry_run_with_a_plan_file(self, _prepare) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "mix_plan.json"
            path.write_text(json.dumps(make_plan()))
            output = io.StringIO()
            with redirect_stdout(output):
                code = audition.main(["--plan", str(path), "--transition", "2", "--dry-run"])
                listed = audition.main(["--plan", str(path), "--list"])
            with redirect_stdout(io.StringIO()):
                bad = audition.main(["--plan", str(path), "--transition", "9", "--dry-run"])
        self.assertEqual((code, listed, bad), (0, 0, audition.EXIT_REFUSED))
        self.assertIn("transition 2 of 3", output.getvalue())
        self.assertIn("held at 101.00 BPM", output.getvalue())

    def test_cli_nudge_override_reaches_the_run_but_not_the_plan_file(self, _prepare) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "mix_plan.json"
            path.write_text(json.dumps(make_plan()))
            before = path.read_text()
            output = io.StringIO()
            with redirect_stdout(output), patch("hands.audition_transition.run_audition", return_value={}) as run:
                code = audition.main(["--plan", str(path), "--transition", "2", "--nudge-ms", "-120", "--dry-run"])
            ran_plan = run.call_args.args[0]
            transitions = [e for e in ran_plan["events"] if e["op"] == "transition"]
            self.assertEqual(code, 0)
            self.assertEqual(transitions[1]["incoming_nudge_ms"], -120.0)
            self.assertEqual(path.read_text(), before)
            self.assertIn("nudge for this run: -120 ms", output.getvalue())


class RunningProcessTests(TestCase):
    def test_finds_live_runners_but_not_dry_runs_or_own_launcher(self) -> None:
        ps = "\n".join([
            "  40 1 uv run python -m hands.audition_transition --plan x --transition 3",
            "  50 40 /venv/bin/python -m hands.audition_transition --plan x --transition 3",
            "  60 1 /venv/bin/python -m hands.run_mix_plan --plan x --dry-run",
            "  70 1 nvim hands/run_mix_plan.py",
            "  80 1 /venv/bin/python ./hands/run_mix_plan.py --plan x",
        ])
        found = running_mix_processes(ps_output=ps, own_pid=50)
        self.assertEqual(len(found), 1)
        self.assertIn("pid 80", found[0])


class FakeProcess:
    def __init__(self, lines, *, returncode=0, hang=False) -> None:
        self.stdout = iter(lines)
        self.returncode = None
        self._final = returncode
        self._hang = hang
        self.signals: list[int] = []
        self.killed = False
        self._done = threading.Event()
        if not hang:
            self._done.set()

    def poll(self):
        return self.returncode if self._done.is_set() and self.returncode is not None else None

    def wait(self, timeout=None):
        if not self._done.wait(timeout if timeout is not None else 5.0):
            raise subprocess.TimeoutExpired("audition", timeout)
        self.returncode = self._final
        return self.returncode

    def send_signal(self, signum) -> None:
        self.signals.append(signum)

    def kill(self) -> None:
        self.killed = True
        self._final = -9
        self._done.set()


class AuditionSessionTests(TestCase):
    def follow(self, session: AuditionSession, proc: FakeProcess) -> None:
        session._follow(proc)

    def test_status_tracks_runner_phases_and_finish(self) -> None:
        proc = FakeProcess(["[audition] phase: loading\n", "\n", "[1/5] start\n", "[2/5] play_body\n",
                            "[3/5] transition\n", "\n", "[4/5] finale\n"])
        launched = []
        session = AuditionSession(popen=lambda cmd, **kw: launched.append(cmd) or proc, python="py")
        with patch.object(threading.Thread, "start", lambda self: None):
            status = session.start(plan_path="/p/mix_plan.json", number=7, port=9995,
                                   info={"count": 12, "from_label": "A", "to_label": "B"})
        self.assertTrue(status["playing"])
        self.assertEqual(launched[0][:4], ["py", "-u", "-m", "hands.audition_transition"])
        self.assertIn("7", launched[0])
        self.follow(session, proc)
        status = session.status()
        self.assertEqual((status["playing"], status["phase"], status["count"]), (False, "finished", 12))

    def test_refusal_is_reported_with_its_code(self) -> None:
        proc = FakeProcess(["[audition] refused (decks_playing): Mixxx deck 1 is playing\n"],
                           returncode=audition.EXIT_REFUSED)
        session = AuditionSession(popen=lambda cmd, **kw: proc, python="py")
        with patch.object(threading.Thread, "start", lambda self: None):
            session.start(plan_path="p", number=1, port=9995)
        self.follow(session, proc)
        status = session.status()
        self.assertEqual((status["phase"], status["refused"]), ("refused", "decks_playing"))
        self.assertIn("deck 1", status["error"])

    def test_stepping_stops_the_previous_audition_first(self) -> None:
        first = FakeProcess([], hang=True)
        second = FakeProcess([])
        procs = iter([first, second])
        commands = []
        session = AuditionSession(popen=lambda cmd, **kw: commands.append(cmd) or next(procs), python="py")
        with patch.object(threading.Thread, "start", lambda self: None):
            session.start(plan_path="p", number=3, port=9995)
            first.send_signal = lambda signum: (first.signals.append(signum), first._done.set())
            session.start(plan_path="p", number=4, port=9995)
        self.assertEqual(len(first.signals), 1)
        self.assertEqual(session.status()["transition"], 4)

    def test_stop_kills_a_stuck_child_and_silences_the_decks(self) -> None:
        proc = FakeProcess([], hang=True)
        silenced = []
        session = AuditionSession(popen=lambda cmd, **kw: proc, python="py", silence=silenced.append)
        with patch.object(threading.Thread, "start", lambda self: None):
            session.start(plan_path="p", number=1, port=9123)
        status = session.stop(timeout_s=0.01)
        self.assertTrue(proc.killed)
        self.assertEqual(silenced, [9123])
        self.assertEqual((status["playing"], status["phase"]), (False, "stopped by user"))


class EditorAuditionTests(TestCase):
    def setUp(self) -> None:
        from brain import plan_paths

        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        patcher = patch.object(plan_paths, "DEFAULT_PLANS_DIR", Path(self.directory.name) / "plans")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.plan_path = Path(self.directory.name) / "mix_plan.json"
        self.plan_path.write_text(json.dumps(make_plan()))

    def app(self):
        from brain.playlist_editor import PlaylistApp

        app = PlaylistApp(control_port=9555)
        app._mix_plan_path = lambda slug=None: self.plan_path

        class FakeSession:
            calls: list[dict] = []
            playing = False

            def start(self, **kwargs):
                self.calls.append(kwargs)
                return {"playing": True, **kwargs}

            def is_playing(self):
                return self.playing

        app.audition = FakeSession()
        return app

    def test_resolves_an_arrange_pair_to_the_built_transition(self) -> None:
        app = self.app()
        app.start_audition(slug="demo", from_track_id="/music/B.mp3", to_track_id="/music/C.mp3")
        call = app.audition.calls[-1]
        self.assertEqual((call["number"], call["port"], call["plan_path"]), (2, 9555, self.plan_path))
        self.assertEqual(call["info"]["count"], 3)
        with self.assertRaises(ValueError):
            app.start_audition(slug="demo", transition=4)

    def test_refuses_while_a_full_mix_is_running(self) -> None:
        app = self.app()
        release = threading.Event()
        self.addCleanup(release.set)
        app.mix_run_thread = threading.Thread(target=release.wait, args=(5,), daemon=True)
        app.mix_run_thread.start()
        with self.assertRaises(ValueError) as ctx:
            app.start_audition(slug="demo", transition=1)
        self.assertIn("full mix is playing", str(ctx.exception))
        self.assertEqual(app.audition.calls, [])

    def test_full_mix_refuses_while_an_audition_plays(self) -> None:
        app = self.app()
        app.audition.playing = True
        with self.assertRaises(ValueError) as ctx:
            app.start_mix(confirm=True)
        self.assertIn("audition", str(ctx.exception))


class EditorAuditionRoutesTest(TestCase):
    def test_routes_map_button_presses_to_the_app(self) -> None:
        import urllib.request
        from http.server import ThreadingHTTPServer
        from types import SimpleNamespace

        from brain.playlist_editor import make_handler

        calls = []
        app = SimpleNamespace(
            mix_state={"running": 0},
            audition_status=lambda: {"playing": False, "phase": "idle", "transition": None},
            start_audition=lambda **kwargs: calls.append(kwargs) or {"playing": True, **kwargs},
            stop_audition=lambda: calls.append("stop") or {"playing": False},
        )
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        except PermissionError:
            self.skipTest("execution sandbox does not permit a loopback listener")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = "http://%s:%s" % server.server_address

        def post(path, body):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read())

        with urllib.request.urlopen(base + "/api/audition", timeout=2) as response:
            self.assertEqual(json.loads(response.read())["phase"], "idle")
        status, _ = post("/api/audition/start", {"plan": "demo", "transition": "3", "take_over": True})
        self.assertEqual(status, 202)
        self.assertEqual(calls[0], {"slug": "demo", "transition": 3, "from_track_id": None, "to_track_id": None,
                                    "lead_bars": None, "tail_bars": None, "take_over": True})
        post("/api/audition/start", {"plan": "demo", "from_track_id": "a", "to_track_id": "b", "lead_bars": 4})
        self.assertEqual((calls[1]["from_track_id"], calls[1]["lead_bars"], calls[1]["transition"]), ("a", 4, None))
        self.assertEqual(post("/api/audition/stop", {})[0], 200)
        self.assertEqual(calls[-1], "stop")


ARRANGE_JS = Path(__file__).parents[1] / "brain" / "web" / "arrange.js"


class ArrangeAuditionControlsTest(TestCase):
    @skipUnless(shutil.which("node"), "node is not installed")
    def test_audition_starts_only_on_press_and_steps_by_number(self) -> None:
        script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    innerHTML: '', textContent: '', listeners: {}, disabled: false, dataset: {},
    addEventListener(event, callback) { this.listeners[event] = callback; },
    querySelectorAll() { return []; },
  });
  return elements.get(id);
}
const auditionButton = element('audition-button');
auditionButton.dataset = {auditionIndex: '1'};
const nextButton = element('next-button');
nextButton.dataset = {auditionStep: 'next'};
element('arrange-root').querySelectorAll = selector =>
  selector === '[data-audition-index]' ? [auditionButton] : [];
element('audition-bar').querySelectorAll = selector =>
  selector === '[data-audition-step]' ? [nextButton] : [];
const snapshot = {
  tracks: ['a', 'b', 'c'].map(track_id => ({track_id, title: `Song ${track_id}`})),
  bunches: [], notes: [], segments: [], rev: 'r1', revs: {}, stale: true, artifact: {version: 1},
};
const started = [];
const playing = number => ({playing: true, phase: 'loading', transition: number, count: 3,
  from_label: 'Song b', to_label: 'Song c', from_track_id: 'b', to_track_id: 'c'});
const context = vm.createContext({
  document: {getElementById: element, addEventListener() {}},
  setTimeout() { return 1; }, clearTimeout() {},
  client: {
    async refreshPlan() { return snapshot; },
    async auditionStatus() { return {playing: false, phase: 'idle', transition: null}; },
    async startAudition(choice) { started.push(choice); return playing(choice.transition ?? 2); },
  },
  mountPlanPicker: () => ({refresh: async () => ({slug: 'saved-plan'}), setSnapshotState() {}}),
  createTransitionEditor: () => ({close() {}}),
});
const source = fs.readFileSync(process.argv[1], 'utf8').replace(/^import .*;\n/gm, '');
vm.runInContext(source, context);
const tick = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  await tick(); await tick(); await tick();
  const root = element('arrange-root');
  assert.equal((root.innerHTML.match(/data-audition-index=/g) || []).length, 2);
  assert.match(root.innerHTML, /Audition in Mixxx/);
  assert.match(element('audition-bar').innerHTML, /Nothing plays until you press it/);
  assert.match(element('audition-bar').innerHTML, /unbuilt edits/);
  assert.equal(started.length, 0, 'nothing may play before a button press');
  auditionButton.listeners.click();
  await tick(); await tick();
  assert.deepEqual(JSON.parse(JSON.stringify(started)), [{plan: 'saved-plan', from_track_id: 'b', to_track_id: 'c'}]);
  const bar = element('audition-bar').innerHTML;
  assert.match(bar, /Playing transition 2 of 3/);
  assert.match(bar, /data-audition-step="prev" >Previous/);
  assert.match(bar, /data-audition-step="stop" class="danger" >Stop/);
  nextButton.listeners.click();
  await tick(); await tick();
  assert.deepEqual(JSON.parse(JSON.stringify(started[1])), {plan: 'saved-plan', transition: 3});
  assert.match(element('audition-bar').innerHTML, /data-audition-step="next" disabled>Next/);
})().catch(error => { console.error(error); process.exit(1); });
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", script, str(ARRANGE_JS)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    import unittest

    unittest.main()
