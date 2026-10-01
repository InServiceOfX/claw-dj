"""Every Mix feel and Build mix plan follow the DJ's per-song notes."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from brain.build_mix_plan import compose_mix_plan
from brain.mix_order_brief import order_from_brief

PROFILES = ("dj-showcase", "club-set", "mix-to-listen")


def _rows(n: int = 6) -> list[dict]:
    return [
        {
            "track_id": f"/music/{i}.mp3",
            "artist": f"Artist{i}",
            "title": f"Title{i}",
            "bpm": 92.0 + i * 0.5,
            "key": "Am",
            "duration_seconds": 240.0,
        }
        for i in range(n)
    ]


class DjNotesRespectedTest(TestCase):
    def setUp(self) -> None:
        patcher = patch("brain.mix_order_brief._snare_confidence", return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _build(self, profile: str, notes: dict[str, str]) -> dict:
        rows = _rows()
        with TemporaryDirectory() as directory:
            playlist = Path(directory) / "playlist.json"
            playlist.write_text(json.dumps(rows))
            return compose_mix_plan(
                playlist=playlist,
                profile_name=profile,
                order_engine="none",
                out=Path(directory) / "mix_plan.json",
                dj_notes_lookup=notes,
            )

    def test_ride_and_cue_notes_win_in_every_profile(self) -> None:
        notes = {"/music/3.mp3": "cue_seconds=12.5; ride_beats=40; trust_ride_beats"}
        for profile in PROFILES:
            with self.subTest(profile=profile):
                plan = self._build(profile, notes)
                bodies = [e for e in plan["events"] if e["op"] == "play_body" and e.get("track_id") == "/music/3.mp3"]
                track = next(t for t in plan["tracks"] if t["track_id"] == "/music/3.mp3")
                self.assertAlmostEqual(float(track["cue_seconds"]), 12.5, delta=0.6)
                if bodies:  # not the closing song
                    self.assertEqual(bodies[0]["beats"], 40)
                    self.assertTrue(bodies[0].get("trust_ride_beats"))

    def test_opener_and_full_track_notes_pin_the_ends(self) -> None:
        rows = _rows()
        rows[4]["dj_notes"] = "opener_style=juggle_intro"
        rows[1]["dj_notes"] = "full_track"
        ordered, notes, _ = order_from_brief(rows, "", engine="none")
        self.assertEqual(ordered[0]["track_id"], "/music/4.mp3")
        self.assertEqual(ordered[-1]["track_id"], "/music/1.mp3")
        self.assertTrue(any("opener_style" in n for n in notes))

    def test_model_review_cannot_move_a_pinned_closer(self) -> None:
        rows = _rows()
        rows[1]["dj_notes"] = "full_track"

        def ask(prompt: str) -> str:
            # Ids follow the optimized order, so t005 is the pinned closer;
            # the model tries to open with it.
            return json.dumps({"order": ["t005", "t000", "t001", "t002", "t003", "t004"], "notes": []})

        ordered, notes, _ = order_from_brief(rows, "", engine="claude-cli", ask=ask)
        self.assertEqual(ordered[-1]["track_id"], "/music/1.mp3")
        self.assertTrue(any("rejected" in n for n in notes))

    def test_listen_ride_accounts_for_a_skip_note(self) -> None:
        notes = {"/music/2.mp3": "skip_from_seconds=100; skip_to_seconds=160"}
        plain = self._build("mix-to-listen", {})
        skipped = self._build("mix-to-listen", notes)

        def beats(plan):
            return next(e["beats"] for e in plan["events"] if e["op"] == "play_body" and e.get("track_id") == "/music/2.mp3")

        # 60 s skipped at ~93 BPM ≈ 93 fewer live beats.
        self.assertLess(beats(skipped), beats(plain) - 60)
