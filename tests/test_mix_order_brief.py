"""Order constraints from a mix brief — agent JSON parse + deterministic apply."""
from __future__ import annotations

import json
from unittest import TestCase

from brain.mix_order_brief import (
    apply_constraints,
    force_adjacent,
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
    def test_force_adjacent_and_region(self) -> None:
        order = [f"t{i:03d}" for i in range(10)]
        order = force_adjacent(order, "t008", "t001", ordered=False)
        self.assertEqual(abs(order.index("t008") - order.index("t001")), 1)
        order = place_block_in_region(order, ["t008", "t001"], "first_half")
        mid = (order.index("t008") + order.index("t001")) / 2
        self.assertLess(mid, len(order) * 0.55)

    def test_parse_constraints_filters_unknown_ids(self) -> None:
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
        constraints = parse_constraints(text, allowed)
        self.assertEqual(constraints["adjacent"], [("t000", "t002")])
        self.assertTrue(constraints["adjacent_ordered"])
        self.assertEqual(constraints["regions"][0]["where"], "first_half")

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
            engine="nemoclaw",
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
                order_engine="nemoclaw",
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
            self.assertEqual(summary["order_engine"], "nemoclaw")
