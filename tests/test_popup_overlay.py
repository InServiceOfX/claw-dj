"""hands.popup_overlay: live OBS browser-source overlay for pop-up cards."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from brain.popups import Card, Scheduler
from hands.popup_overlay import NowPlaying, audible_deck, identify_by_duration, make_server


class FakeMixxx:
    def __init__(self, values):
        self.values = values
        self.writes = []

    def get(self, group, key):
        return self.values.get((group, key), 0.0)

    def set(self, group, key, value):          # the overlay must never write
        self.writes.append((group, key, value))


def deck(values, n, *, play=1.0, vol=1.0, loaded=1.0, duration=200.0):
    g = f"[Channel{n}]"
    values.update({(g, "play"): play, (g, "volume"): vol, (g, "track_loaded"): loaded, (g, "duration"): duration})


class AudibleDeckTests(unittest.TestCase):
    def test_crossfader_and_volume_pick_the_audible_deck(self) -> None:
        v = {("[Master]", "crossfader"): -1.0}
        deck(v, 1)
        deck(v, 2)
        m = FakeMixxx(v)
        self.assertEqual(audible_deck(m), 1)                 # crossfader hard left
        v[("[Master]", "crossfader")] = 1.0
        self.assertEqual(audible_deck(m), 2)
        v[("[Master]", "crossfader")] = 0.0
        v[("[Channel2]", "volume")] = 0.3
        self.assertEqual(audible_deck(m), 1)                 # centered: louder channel fader wins
        self.assertEqual(m.writes, [])

    def test_nothing_audible(self) -> None:
        v = {("[Master]", "crossfader"): 0.0}
        deck(v, 1, play=0.0)
        deck(v, 2, vol=0.0)
        self.assertIsNone(audible_deck(FakeMixxx(v)))


class IdentifyTests(unittest.TestCase):
    CANDS = [{"artist": "Tyrese", "title": "Lately", "duration": 266.5},
             {"artist": "Joe", "title": "Sweeter Than Sugar", "duration": 238.0},
             {"artist": "Joe", "title": "Twin A", "duration": 300.0},
             {"artist": "Joe", "title": "Twin B", "duration": 300.2}]

    def test_unique_nearest_within_tolerance(self) -> None:
        self.assertEqual(identify_by_duration(266.533, self.CANDS)["title"], "Lately")
        self.assertIsNone(identify_by_duration(250.0, self.CANDS))

    def test_ambiguous_durations_do_not_guess(self) -> None:
        self.assertIsNone(identify_by_duration(300.1, self.CANDS))

    def test_bpm_breaks_ties_including_half_time(self) -> None:
        cands = [{"artist": "A", "title": "Slow", "duration": 240.0, "bpm": 80.0},
                 {"artist": "B", "title": "Fast", "duration": 240.2, "bpm": 100.0}]
        self.assertEqual(identify_by_duration(240.1, cands, bpm=160.0)["title"], "Slow")   # double-time reading
        self.assertEqual(identify_by_duration(240.1, cands, bpm=100.5)["title"], "Fast")
        self.assertIsNone(identify_by_duration(240.1, cands, bpm=120.0))

    def test_exact_durations_use_their_tight_tolerance(self) -> None:
        cands = [{"artist": "A", "title": "One", "duration": 200.00, "tol": 0.15},
                 {"artist": "B", "title": "Two", "duration": 200.40, "tol": 0.15}]
        self.assertEqual(identify_by_duration(200.05, cands)["title"], "One")


class NowPlayingTests(unittest.TestCase):
    def test_now_file_mode(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "now.json"
            p.write_text(json.dumps({"artist": "Joe", "title": "Stutter"}))
            self.assertEqual(NowPlaying(now_file=p, cache_s=0).current(), ("Joe", "Stutter"))

    def test_mixxx_mode_identifies_the_audible_deck(self) -> None:
        v = {("[Master]", "crossfader"): 1.0}
        deck(v, 2, duration=266.533)

        class Ctx(FakeMixxx):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with patch("hands.popup_overlay.MixxxControl", lambda **k: Ctx(v)):
            np = NowPlaying(mixxx_port=1, candidates=IdentifyTests.CANDS, cache_s=0)
            self.assertEqual(np.current(), ("Tyrese", "Lately"))

    def test_errors_never_raise(self) -> None:
        def boom(**k):
            raise ConnectionRefusedError("no mixxx")
        with patch("hands.popup_overlay.MixxxControl", boom):
            self.assertEqual(NowPlaying(mixxx_port=1, candidates=[], cache_s=0).current(), (None, None))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "now.json"
            p.write_text("not json")
            self.assertEqual(NowPlaying(now_file=p, cache_s=0).current(), (None, None))


class StaticNow:
    def __init__(self, artist, title):
        self.value = (artist, title)

    def current(self):
        return self.value


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        facts = [Card("joe-1", "Joe is from Columbus, Georgia.", "fact", source="Wikipedia: Joe (singer)", tags=("Joe",))]
        threads = [[Card("ey/x#0", "Sampling is a conversation.", "quote", initials="EY", author="Ernest Yeung")]]
        self.sched = Scheduler(facts, threads, interval_s=0.0, show_s=0.0, commentary_every=2)
        self.server = make_server(self.sched, StaticNow("Joe", "x"), host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read().decode("utf-8")

    def test_card_json_marks_commentary_and_not_facts(self) -> None:
        self.sched.show_s = 30.0
        status, ctype, body = self.get("/card")
        first = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("json", ctype)
        self.assertEqual(first["card"]["kind"], "fact")
        self.assertIsNone(first["card"]["initials"])
        self.sched._last = None                              # force the next card now
        second = json.loads(self.get("/card")[2])
        self.assertEqual(second["card"]["initials"], "EY")
        self.assertGreater(second["serial"], first["serial"])

    def test_overlay_health_and_404(self) -> None:
        status, ctype, body = self.get("/overlay")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("transparent", body)
        # the EY badge must truly disappear for facts (CSS display would otherwise override [hidden])
        self.assertIn(".ey[hidden]", body)
        self.assertEqual(json.loads(self.get("/health")[2]), {"ok": True})
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get("/nope")
        self.assertEqual(e.exception.code, 404)
        e.exception.close()


if __name__ == "__main__":
    unittest.main()
