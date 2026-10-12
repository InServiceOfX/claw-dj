"""hands.popup_obs: native OBS text-source pop-ups, auto and manual, plus a terminal dry-run."""
import io
import json
import threading
import unittest
import urllib.error
import urllib.request

from brain.popups import Card, Scheduler
from hands.obs_control import OBSControlError
from hands.popup_obs import ObsDisplay, PopupController, TerminalDisplay, card_text, main, make_control_server

FACT = Card("joe-1", "Joe is from Columbus, Georgia.", "fact", source="Wikipedia: Joe (singer)", tags=("Joe",))
QUOTE = Card("ey/a#0", "Sampling is a conversation across decades.", "quote", initials="EY", author="Ernest Yeung")


class FakeOBS:
    def __init__(self, items=None, fail=False):
        self.items = items if items is not None else [
            {"sourceName": "claw-dj pop-up", "sceneItemId": 11},
            {"sourceName": "claw-dj pop-up EY", "sceneItemId": 12},
            {"sourceName": "claw-dj pop-up bubble", "sceneItemId": 13},
            {"sourceName": "Mixxx", "sceneItemId": 1}]
        self.calls = []
        self.fail = fail

    def execute(self, action, data=None, *, allow_write=False, allow_output=False):
        self.calls.append((action, data, allow_write))
        if self.fail and action != "scene-items":
            raise OBSControlError("OBS communication failed")
        if action == "scene-items":
            return {"sceneItems": self.items}
        return {}

    def writes(self):
        return [(a, d) for a, d, w in self.calls if a != "scene-items"]


def display(obs, **kw):
    d = ObsDisplay(obs, scene="Live", text_source="claw-dj pop-up", badge_source=kw.get("badge", "claw-dj pop-up EY"),
                   bubble_source=kw.get("bubble", "claw-dj pop-up bubble"))
    d.resolve()
    return d


class ObsDisplayTests(unittest.TestCase):
    def test_resolve_by_name_and_missing_text_source_is_an_error(self) -> None:
        d = display(FakeOBS())
        self.assertEqual((d.text_id, d.badge_id, d.bubble_id), (11, 12, 13))
        with self.assertRaises(ValueError) as e:
            display(FakeOBS(items=[{"sourceName": "Mixxx", "sceneItemId": 1}]))
        self.assertIn("claw-dj pop-up", str(e.exception))
        d2 = display(FakeOBS(items=[{"sourceName": "claw-dj pop-up", "sceneItemId": 11}]))
        self.assertEqual((d2.badge_id, d2.bubble_id), (None, None))      # optional sources simply unused

    def test_fact_shows_text_and_no_badge(self) -> None:
        obs = FakeOBS()
        display(obs).show(FACT)
        w = obs.writes()
        self.assertIn(("text-set", {"inputName": "claw-dj pop-up", "text": card_text(FACT)}), w)
        self.assertIn(("source-visible", {"sceneName": "Live", "sceneItemId": 12, "sceneItemEnabled": False}), w)
        self.assertIn(("source-visible", {"sceneName": "Live", "sceneItemId": 11, "sceneItemEnabled": True}), w)
        self.assertTrue(all(allow for a, d, allow in obs.calls if a != "scene-items"))   # every write is allow_write
        self.assertNotIn("EY", card_text(FACT))

    def test_commentary_shows_the_initials_badge(self) -> None:
        obs = FakeOBS()
        display(obs).show(QUOTE)
        w = obs.writes()
        self.assertIn(("text-set", {"inputName": "claw-dj pop-up EY", "text": "EY"}), w)
        self.assertIn(("source-visible", {"sceneName": "Live", "sceneItemId": 12, "sceneItemEnabled": True}), w)
        text = next(d["text"] for a, d in w if a == "text-set" and d["inputName"] == "claw-dj pop-up")
        self.assertNotIn("— EY", text)                                     # the badge carries it

    def test_without_a_badge_source_the_initials_stay_in_the_text(self) -> None:
        obs = FakeOBS(items=[{"sourceName": "claw-dj pop-up", "sceneItemId": 11}])
        display(obs, badge=None, bubble=None).show(QUOTE)
        text = next(d["text"] for a, d in obs.writes() if a == "text-set")
        self.assertIn("— EY", text)

    def test_hide_and_obs_errors_never_raise(self) -> None:
        obs = FakeOBS()
        d = display(obs)
        d.hide()
        self.assertEqual({d_["sceneItemId"] for a, d_ in obs.writes() if a == "source-visible"}, {11, 12, 13})
        broken = FakeOBS(fail=True)
        bd = display(broken)
        err = io.StringIO()
        bd.err = err
        bd.show(FACT)
        bd.show(QUOTE)
        bd.hide()
        self.assertEqual(len(err.getvalue().strip().splitlines()), 1)      # reported once per outage


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Now:
    def current(self):
        return ("Joe", "x")


class RecordingDisplay:
    def __init__(self):
        self.shown, self.hidden = [], 0

    def show(self, card):
        self.shown.append(card.id)

    def hide(self):
        self.hidden += 1


def controller(**kw):
    sched = Scheduler([FACT, Card("gen", "General.", "fact", source="s")], [[QUOTE]],
                      interval_s=kw.get("interval", 30.0), show_s=kw.get("show", 10.0), commentary_every=3)
    disp, clock = RecordingDisplay(), Clock()
    return PopupController(sched, disp, Now(), clock=clock), disp, clock


class ControllerTests(unittest.TestCase):
    def test_auto_shows_then_hides_after_show_s(self) -> None:
        c, d, clock = controller()
        c.step()
        self.assertEqual(d.shown, ["joe-1"])
        clock.t = 5.0
        c.step()
        self.assertEqual(d.hidden, 0)
        clock.t = 10.5
        c.step()
        self.assertEqual(d.hidden, 1)
        clock.t = 31.0
        c.step()
        self.assertEqual(len(d.shown), 2)

    def test_next_back_history(self) -> None:
        c, d, clock = controller()
        a = c.next().id
        b = c.next().id
        self.assertNotEqual(a, b)
        self.assertEqual(c.back().id, a)
        self.assertEqual(c.next().id, b)             # forward through history, not a new card
        self.assertEqual(c.status()["position"], [2, 2])

    def test_pause_stops_auto_but_not_manual(self) -> None:
        c, d, clock = controller()
        c.pause()
        c.step()
        self.assertEqual(d.shown, [])
        c.next()
        clock.t = 50.0
        c.step()
        self.assertEqual(d.hidden, 0)                # paused manual card stays up
        c.resume()
        c.step()
        self.assertEqual(c.status()["mode"], "auto")


class ControlServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c, self.d, _ = controller()
        self.srv = make_control_server(self.c, host="127.0.0.1", port=0)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.shutdown)
        self.addCleanup(self.srv.server_close)

    def get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return r.status, r.read().decode()

    def test_endpoints(self) -> None:
        s = json.loads(self.get("/next")[1])
        self.assertEqual(s["card"]["id"], "joe-1")
        self.assertEqual(json.loads(self.get("/pause")[1])["mode"], "paused")
        self.assertEqual(json.loads(self.get("/resume")[1])["mode"], "auto")
        self.assertIn("next", self.get("/")[1].lower())
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get("/nope")
        self.assertEqual(e.exception.code, 404)
        e.exception.close()


class CliTests(unittest.TestCase):
    def test_run_refuses_without_allow_write(self) -> None:
        with self.assertRaises(SystemExit) as e:
            main(["run", "--scene", "Live"])
        self.assertNotEqual(e.exception.code, 0)

    def test_terminal_display_prints_cards(self) -> None:
        out = io.StringIO()
        t = TerminalDisplay(out)
        t.show(QUOTE)
        t.show(FACT)
        t.hide()
        text = out.getvalue()
        self.assertIn("— EY", text)
        self.assertIn("Columbus", text)


if __name__ == "__main__":
    unittest.main()
