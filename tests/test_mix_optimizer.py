"""Whole-set mix order: selection order must not matter; backbeat-aware."""
import json
import random
from unittest import TestCase
from unittest.mock import patch

from brain.library import Track
from brain.mix_graph import greedy_mix_order
from brain.mix_optimizer import MixGraph, optimize_order, order_summary
from brain.onset_analysis import agree_on_parity


def _track(i: int, bpm: float, key: str, artist: str = "A") -> Track:
    return Track(f"/m/{i:02d}.mp3", f"Song {i}", f"{artist}{i % 3}", bpm=bpm, key=key)


def _set(n: int = 14) -> list[Track]:
    rng = random.Random(7)
    keys = ["Am", "Em", "Bm", "F#m", "C", "G", "D", "Dm"]
    return [_track(i, round(rng.uniform(86, 104), 1), rng.choice(keys)) for i in range(n)]


class OptimizerTest(TestCase):
    def test_selection_order_does_not_change_the_result(self) -> None:
        tracks = _set()
        first = optimize_order(MixGraph(tracks), time_budget_s=2)
        shuffled = tracks[:]
        random.Random(3).shuffle(shuffled)
        second = optimize_order(MixGraph(shuffled), time_budget_s=2)
        reversed_ = optimize_order(MixGraph(tracks[::-1]), time_budget_s=2)
        self.assertEqual(first, second)
        self.assertEqual(first, reversed_)

    def test_every_song_exactly_once(self) -> None:
        tracks = _set()
        order = optimize_order(MixGraph(tracks), time_budget_s=2)
        self.assertCountEqual(order, [t.track_id for t in tracks])

    def test_not_worse_than_greedy_tour(self) -> None:
        tracks = _set(18)
        graph = MixGraph(tracks)
        greedy = [t.track_id for t in greedy_mix_order(tracks, chroma={})]
        best = optimize_order(graph, time_budget_s=3)
        self.assertGreaterEqual(
            graph.objective([graph.index[i] for i in best]) + 1e-9,
            graph.objective([graph.index[i] for i in greedy]),
        )

    def test_opener_is_respected(self) -> None:
        tracks = _set()
        opener = tracks[5].track_id
        self.assertEqual(optimize_order(MixGraph(tracks), opener_id=opener, time_budget_s=2)[0], opener)

    def test_weak_snare_reads_are_kept_apart(self) -> None:
        # Identical tempo/key everywhere: only backbeat verifiability differs.
        tracks = [_track(i, 95.0, "Am") for i in range(8)]
        conf = {t.track_id: 0.6 for t in tracks}
        for weak in (tracks[0], tracks[1], tracks[2]):
            conf[weak.track_id] = 0.02
        graph = MixGraph(tracks, snare_confidence=conf, gate=0.15)
        order = optimize_order(graph, time_budget_s=2)
        summary = order_summary(graph, order)
        self.assertEqual(summary["backbeat_blind"], 0)
        self.assertEqual(len(graph.report(order)), 7)

    def test_report_labels_backbeat(self) -> None:
        tracks = [_track(i, 95.0, "Am") for i in range(3)]
        conf = {tracks[0].track_id: 0.5, tracks[1].track_id: 0.01, tracks[2].track_id: 0.5}
        graph = MixGraph(tracks, snare_confidence=conf)
        labels = [e.backbeat for e in graph.report([t.track_id for t in tracks])]
        self.assertEqual(labels, ["one_side_unverified", "one_side_unverified"])


class SnareAgreementTest(TestCase):
    def test_agreeing_windows_take_the_weakest_confidence(self) -> None:
        reads = [
            {"snare_parity": 1, "confidence": 0.40},
            {"snare_parity": 1, "confidence": 0.20},
            {"snare_parity": 0, "confidence": 0.05},
        ]
        result = agree_on_parity(reads, gate=0.15)
        self.assertEqual(result["snare_parity"], 1)
        self.assertAlmostEqual(result["confidence"], 0.20)

    def test_disagreeing_windows_do_not_replace_the_read(self) -> None:
        reads = [{"snare_parity": 1, "confidence": 0.7}, {"snare_parity": 0, "confidence": 0.3}]
        self.assertIsNone(agree_on_parity(reads, gate=0.15))

    def test_one_strong_window_is_not_enough(self) -> None:
        reads = [{"snare_parity": 1, "confidence": 0.9}, {"snare_parity": 1, "confidence": 0.1}]
        self.assertIsNone(agree_on_parity(reads, gate=0.15))


def _rows(n: int) -> list[dict]:
    return [
        {"track_id": t.track_id, "title": t.title, "artist": t.artist, "bpm": t.bpm, "key": t.key}
        for t in _set(n)
    ]


class RefineTest(TestCase):
    """The model reviews the optimized order; hard rules decide."""

    def setUp(self) -> None:
        patcher = patch("brain.mix_order_brief._snare_confidence", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, reply_for_refine, brief: str = "", constraints_reply: dict | None = None):
        from brain.mix_order_brief import order_from_brief

        def ask(prompt: str) -> str:
            if "reviewing a continuous mix order" in prompt:
                return reply_for_refine(prompt)
            return json.dumps(constraints_reply or {})

        return order_from_brief(_rows(8), brief, engine="claude-cli", ask=ask)

    def test_model_failure_keeps_optimized_order(self) -> None:
        def boom(_prompt):
            raise RuntimeError("not signed in")

        ordered, notes, _ = self._run(boom)
        self.assertEqual(len(ordered), 8)
        self.assertTrue(any("review skipped" in n for n in notes))

    def test_wrong_song_set_is_rejected(self) -> None:
        ordered, notes, _ = self._run(lambda _p: json.dumps({"order": ["t000", "t001"], "notes": []}))
        self.assertEqual(len(ordered), 8)
        self.assertTrue(any("review skipped" in n for n in notes))

    def test_small_story_swap_is_accepted(self) -> None:
        from brain.mix_order_brief import order_from_brief

        baseline, _, _ = order_from_brief(_rows(8), "", engine="none")
        ids = [f"t{i:03d}" for i in range(8)]
        # Swap the last two songs of the optimized order (cheap change).
        by_path = {row["track_id"]: f"t{i:03d}" for i, row in enumerate(baseline)}
        proposal = [by_path[row["track_id"]] for row in baseline]
        proposal[-1], proposal[-2] = proposal[-2], proposal[-1]
        self.assertCountEqual(proposal, ids)
        ordered, notes, _ = self._run(lambda _p: json.dumps({"order": proposal, "notes": ["better closer"]}))
        self.assertEqual(ordered[-1]["track_id"], baseline[-2]["track_id"])
        self.assertTrue(any("review accepted" in n for n in notes))

    def test_breaking_a_requested_pair_is_rejected(self) -> None:
        constraints = {"adjacent": [["t001", "t006"]], "adjacent_ordered": True, "notes": ["pair"]}
        ordered, notes, _ = self._run(
            lambda _p: json.dumps({"order": [f"t{i:03d}" for i in range(8)], "notes": []}),
            brief="put song 1 into song 6",
            constraints_reply=constraints,
        )
        ids = [row["track_id"] for row in ordered]
        a, b = "/m/01.mp3", "/m/06.mp3"
        self.assertEqual(ids.index(b) - ids.index(a), 1)
        self.assertTrue(any("rejected" in n or "kept" in n for n in notes))

    def test_retired_engine_falls_back_to_optimizer(self) -> None:
        from brain.mix_order_brief import order_from_brief

        ordered, notes, _ = order_from_brief(_rows(5), "anything", engine="nemoclaw")
        self.assertEqual(len(ordered), 5)
        self.assertTrue(any("retired" in n for n in notes))
