"""Order constraints from a mix brief — agent JSON parse + deterministic apply."""
from __future__ import annotations

import json
from unittest import TestCase
from unittest.mock import patch

from brain.mix_order_brief import (
    apply_constraints,
    core_title,
    force_adjacent,
    mashup_payoff_pairs,
    order_from_brief,
    parse_constraints,
    place_block_in_region,
    short_ids,
)


def _rows(n: int = 8) -> list[dict]:
    return [
        {
            "track_id": f"/music/{i}.mp3",
            "artist": f"Artist{i}",
            "title": f"Title{i}",
            "bpm": 90.0 + i,
            "key": "Am",
        }
        for i in range(n)
    ]


class MixOrderBriefTest(TestCase):
    def test_blank_direction_reviews_every_provider_including_two_song_sets(self) -> None:
        from brain.llm_providers import PROVIDERS

        for provider in PROVIDERS:
            for size in (2, 3):
                with self.subTest(provider=provider, size=size):
                    prompts = []
                    def ask(prompt):
                        prompts.append(prompt)
                        return json.dumps({"order": [f"t{i:03d}" for i in range(size)]})
                    ordered, notes, _ = order_from_brief(
                        _rows(size), "  \n", engine=provider, ask=ask,
                        mix_context={"name": "mix-to-listen", "ride_most_of_song": True},
                    )
                    self.assertEqual(len(prompts), 1)
                    self.assertIn("reviewing a continuous mix order", prompts[0])
                    self.assertIn('"ride_most_of_song": true', prompts[0])
                    self.assertIn("User brief (may be empty): (none)", prompts[0])
                    self.assertCountEqual([r["track_id"] for r in ordered], [r["track_id"] for r in _rows(size)])
                    self.assertTrue(any("kept the optimized order" in n for n in notes))

    def test_blank_direction_provider_failure_keeps_two_song_optimizer_result(self) -> None:
        from unittest.mock import Mock
        expected, _, _ = order_from_brief(_rows(2), "", engine="none")
        ask = Mock(side_effect=RuntimeError("synthetic unavailable provider"))
        actual, notes, _ = order_from_brief(_rows(2), "", engine="llama-server", ask=ask)
        self.assertEqual(actual, expected)
        ask.assert_called_once()
        self.assertTrue(any("review skipped" in note for note in notes))

    def test_first_pass_model_receives_notes_after_long_comment(self) -> None:
        from unittest.mock import Mock
        rows = _rows(2)
        rows[0]["dj_notes"] = "comment " * 80 + "; mandatory_end_seconds=92"
        ask = Mock(return_value='{"order": ["t000", "t001"]}')
        order_from_brief(rows, "", engine="claude-cli", ask=ask)
        self.assertIn("mandatory_end_seconds=92", ask.call_args.args[0])

    def test_compose_blank_direction_passes_each_effective_feel_and_keeps_song_set(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from brain.build_mix_plan import compose_mix_plan
        from brain.mix_profiles import PROFILES

        with TemporaryDirectory() as directory:
            root = Path(directory)
            playlist = root / "playlist.json"
            playlist.write_text(json.dumps(_rows(3)))
            for name in PROFILES:
                with self.subTest(profile=name):
                    prompts = []
                    def ask(prompt):
                        prompts.append(prompt)
                        return '{"order": ["t000", "t001", "t002"]}'
                    plan = compose_mix_plan(playlist=playlist, profile_name=name,
                                            mix_brief="", order_engine="claude-cli",
                                            out=root / "mix.json", dj_notes_lookup={}, ask=ask)
                    reviews = [p for p in prompts if "reviewing a continuous mix order" in p]
                    self.assertEqual(len(reviews), 1)
                    self.assertIn('"name": "' + name + '"', reviews[0])
                    self.assertCountEqual([r['track_id'] for r in plan['tracks']], [r['track_id'] for r in _rows(3)])
                    if name != "dj-showcase":
                        self.assertEqual(len(prompts), 1)

    def test_no_model_and_empty_brief_still_reorder_exactly_once(self) -> None:
        rows = [
            {"track_id": "/b.mp3", "artist": "B", "title": "B", "bpm": 140.0, "key": "F#"},
            {"track_id": "/a.mp3", "artist": "A", "title": "A", "bpm": 90.0, "key": "Am"},
            {"track_id": "/c.mp3", "artist": "C", "title": "C", "bpm": 92.0, "key": "C"},
        ]
        ordered, notes, _ = order_from_brief(rows, "", engine="none")
        self.assertNotEqual([r["track_id"] for r in ordered], [r["track_id"] for r in rows])
        self.assertCountEqual([r["track_id"] for r in ordered], [r["track_id"] for r in rows])
        self.assertEqual(len({r["track_id"] for r in ordered}), len(rows))
        self.assertTrue(any("deterministic" in note for note in notes))

    def test_invalid_model_ids_raise_for_caller_fallback(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown track ids"):
            order_from_brief(
                _rows(3),
                "put the unknown song first",
                engine="claude-cli",
                ask=lambda _prompt: json.dumps({"opener_id": "t999"}),
            )

    def test_h_models_api_is_a_text_provider_for_ordering(self) -> None:
        with patch("brain.llm_providers.ask", return_value='{}') as ask:
            ordered, notes, _ = order_from_brief(_rows(3), "smooth", engine="hcompany-api")
        self.assertEqual(len(ordered), 3)
        self.assertTrue(ask.called)
        self.assertTrue(all(call.args[0] == "hcompany-api" for call in ask.call_args_list))

    def test_force_adjacent_and_region(self) -> None:
        order = [f"t{i:03d}" for i in range(10)]
        order = force_adjacent(order, "t008", "t001", ordered=False)
        self.assertEqual(abs(order.index("t008") - order.index("t001")), 1)
        order = place_block_in_region(order, ["t008", "t001"], "first_half")
        mid = (order.index("t008") + order.index("t001")) / 2
        self.assertLess(mid, len(order) * 0.55)

    def test_parse_constraints_rejects_unknown_ids(self) -> None:
        allowed = {"t000", "t001", "t002"}
        text = json.dumps(
            {
                "use_only": None,
                "adjacent": [["t000", "t002"], ["t999", "t001"]],
                "adjacent_ordered": True,
                "regions": [{"ids": ["t000", "t002"], "where": "first_half"}],
                "notes": ["pair opener with closer"],
            }
        )
        with self.assertRaisesRegex(ValueError, "unknown track ids"):
            parse_constraints(text, allowed)

    def test_compose_falls_back_when_model_fails(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from brain.build_mix_plan import compose_mix_plan

        rows = _rows(4)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            playlist = root / "playlist.json"
            out = root / "mix_plan.json"
            playlist.write_text(json.dumps(rows))
            plan = compose_mix_plan(
                playlist=playlist,
                mix_brief="put an unknown track first",
                order_engine="claude-cli",
                tracks=None,
                out=out,
                ask=lambda _prompt: json.dumps({"opener_id": "t999"}),
            )
        self.assertCountEqual(
            [track["track_id"] for track in plan["tracks"]],
            [row["track_id"] for row in rows],
        )
        self.assertTrue(
            any("failed; used local ordering" in note for note in plan["profile"]["order_notes"])
        )

    def test_apply_constraints_subset_and_adjacent(self) -> None:
        rows = _rows(6)
        ids = short_ids(rows)
        # Map known short ids for Title1 and Title4
        a = next(sid for sid, row in ids.items() if row["title"] == "Title1")
        b = next(sid for sid, row in ids.items() if row["title"] == "Title4")
        ordered, notes = apply_constraints(
            rows,
            {
                "use_only": [a, b, "t000"],
                "opener_id": "t000",
                "adjacent": [(a, b)],
                "adjacent_ordered": False,
                "regions": [{"ids": [a, b], "where": "middle"}],
                "notes": ["test"],
            },
        )
        self.assertEqual(len(ordered), 3)
        titles = [row["title"] for row in ordered]
        self.assertEqual(abs(titles.index("Title1") - titles.index("Title4")), 1)
        self.assertTrue(any("adjacent" in n for n in notes))

    def test_mashup_payoff_pairs_tease_not_same_song_version(self) -> None:
        rows = [
            {
                "track_id": "/music/break.mp3",
                "artist": "Holla Boyz",
                "title": "Show Me Love In Da Club (Hollaboyz Remix)",
                "bpm": 92.0,
                "key": "C#m",
            },
            {
                "track_id": "/music/club.mp3",
                "artist": "50 Cent",
                "title": "In Da Club",
                "bpm": 90.0,
                "key": "C#m",
            },
            {
                "track_id": "/music/pimp.mp3",
                "artist": "50 Cent",
                "title": "P.I.M.P.",
                "bpm": 85.0,
                "key": "Ebm",
            },
            {
                "track_id": "/music/pimp-remix.mp3",
                "artist": "50 Cent",
                "title": "P.I.M.P. Remix (Explicit)",
                "bpm": 85.0,
                "key": "Ebm",
            },
            {
                "track_id": "/music/club-inst.mp3",
                "artist": "50 Cent",
                "title": "In Da Club (Instrumental)",
                "bpm": 90.0,
                "key": "C#m",
            },
        ]
        self.assertEqual(core_title("P.I.M.P. Remix (Explicit)"), core_title("P.I.M.P."))
        self.assertEqual(
            mashup_payoff_pairs(rows),
            [("/music/break.mp3", "/music/club.mp3")],
        )

    def test_apply_constraints_puts_original_after_party_break(self) -> None:
        rows = [
            {
                "track_id": "/music/a.mp3",
                "artist": "A",
                "title": "Filler One",
                "bpm": 90.0,
                "key": "Am",
            },
            {
                "track_id": "/music/club.mp3",
                "artist": "50 Cent",
                "title": "In Da Club",
                "bpm": 90.0,
                "key": "C#m",
            },
            {
                "track_id": "/music/break.mp3",
                "artist": "Holla Boyz",
                "title": "Show Me Love In Da Club (Hollaboyz Remix)",
                "bpm": 92.0,
                "key": "C#m",
            },
            {
                "track_id": "/music/z.mp3",
                "artist": "Z",
                "title": "Filler Two",
                "bpm": 91.0,
                "key": "Am",
            },
        ]
        ids = short_ids(rows)
        remix_sid = next(
            sid for sid, row in ids.items() if "Hollaboyz" in row["title"]
        )
        ordered, notes = apply_constraints(
            rows,
            {
                "use_only": None,
                "opener_id": remix_sid,
                "adjacent": [],
                "adjacent_ordered": False,
                "regions": [],
                "notes": [],
            },
        )
        titles = [row["title"] for row in ordered]
        self.assertEqual(
            titles.index("Show Me Love In Da Club (Hollaboyz Remix)") + 1,
            titles.index("In Da Club"),
        )
        self.assertTrue(any("mashup payoff" in note for note in notes))

    def test_order_from_brief_with_injected_ask(self) -> None:
        rows = _rows(6)
        ids = short_ids(rows)
        a = next(sid for sid, row in ids.items() if "Title2" in row["title"])
        b = next(sid for sid, row in ids.items() if "Title5" in row["title"])

        def fake_ask(_prompt: str) -> str:
            return json.dumps(
                {
                    "use_only": None,
                    "adjacent": [[a, b]],
                    "adjacent_ordered": False,
                    "regions": [{"ids": [a, b], "where": "first_half"}],
                    "notes": ["forced Title2 next to Title5 early"],
                }
            )

        ordered, notes, constraints = order_from_brief(
            rows,
            "put Title2 next to Title5 in the first half",
            engine="claude-cli",
            ask=fake_ask,
        )
        self.assertEqual(len(ordered), 6)
        titles = [row["title"] for row in ordered]
        self.assertEqual(abs(titles.index("Title2") - titles.index("Title5")), 1)
        mid = (titles.index("Title2") + titles.index("Title5")) / 2
        self.assertLess(mid, len(titles) * 0.55)
        self.assertTrue(constraints["adjacent"])
        self.assertTrue(notes)

    def test_compose_mix_plan_honors_injected_order(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from brain.build_mix_plan import compose_mix_plan, plan_summary

        rows = _rows(5)
        # Put distinctive titles like the real brief
        rows[1]["title"] = "Parce Que Tu Crois"
        rows[1]["artist"] = "Charles Aznavour"
        rows[3]["title"] = "What's The Difference (Feat. Eminem & Xzibit)"
        rows[3]["artist"] = "Dr. Dre"
        ids = short_ids(rows)
        a = next(sid for sid, row in ids.items() if "Parce" in row["title"])
        b = next(sid for sid, row in ids.items() if "Difference" in row["title"])

        def fake_ask(_prompt: str) -> str:
            return json.dumps(
                {
                    "adjacent": [[a, b]],
                    "regions": [{"ids": [a, b], "where": "first_half"}],
                    "notes": ["Aznavour next to What's The Difference in first half"],
                }
            )

        with TemporaryDirectory() as directory:
            root = Path(directory)
            playlist = root / "playlist.json"
            out = root / "mix_plan.json"
            playlist.write_text(json.dumps(rows))
            plan = compose_mix_plan(
                playlist=playlist,
                profile_name="dj-showcase",
                mix_brief="mix Parce Que tu Crois next to What's the difference in the first half",
                order_engine="claude-cli",
                tracks=None,
                out=out,
                ask=fake_ask,
            )
            titles = [t["title"] for t in plan["tracks"]]
            self.assertEqual(
                abs(titles.index("Parce Que Tu Crois") - titles.index("What's The Difference (Feat. Eminem & Xzibit)")),
                1,
            )
            summary = plan_summary(plan)
            self.assertTrue(summary["order_notes"])
            self.assertEqual(summary["order_engine"], "claude-cli")
