"""Native OBS pop-ups for the claw-dj stream: no browser source, lowest footprint.

Drives OBS's own text sources through the authenticated OBS control
(hands/obs_control.py: scene-items, text-set, source-visible). OBS renders the
text natively, so there's no embedded Chromium. Auto mode follows the
scheduler; manual mode flips through cards (next / back / show / hide / pause /
resume) from the CLI or a tiny control page. `dry-run` prints the same cards
in the terminal, with no OBS at all.

One-time in OBS (the OBS control can't create or move sources): add to your
stream scene a Text source named "claw-dj pop-up" (the card), optionally a Text
source "claw-dj pop-up EY" (the initials badge) and a backdrop named
"claw-dj pop-up bubble" (Color or Image source). Style and place them, then:

    uv run python -m hands.popup_obs run --scene "Scene" --allow-write
    uv run python -m hands.popup_obs next | back | show | hide | pause | resume | status
    uv run python -m hands.popup_obs dry-run          # preview in the terminal

Story: user_stories/story__while_the_mix_plays_pop_ups_show_music_facts_and_my_commentary.md
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from brain.popups import DEFAULT_COMMENTARY, DEFAULT_FACTS, Card, Scheduler, card_lines, load_commentary, load_facts
from hands.obs_control import OBSControlError

TEXT_SOURCE, BADGE_SOURCE, BUBBLE_SOURCE = "claw-dj pop-up", "claw-dj pop-up EY", "claw-dj pop-up bubble"


def card_text(card: Card, *, wrap: int = 30, badge: bool = True) -> str:
    """The card's display text. With a badge source the initials live on the badge;
    without one they stay in the text, so commentary is never unattributed."""
    return "\n".join(card_lines(card, wrap, attribution=not badge))


class ObsDisplay:
    def __init__(self, control, *, scene: str, text_source: str = TEXT_SOURCE, badge_source: str | None = BADGE_SOURCE,
                 bubble_source: str | None = BUBBLE_SOURCE, wrap: int = 30):
        self.control, self.scene, self.wrap = control, scene, wrap
        self.names = {"text": text_source, "badge": badge_source, "bubble": bubble_source}
        self.text_id = self.badge_id = self.bubble_id = None
        self.err = sys.stderr
        self._down = False

    def resolve(self) -> None:
        items = self.control.execute("scene-items", {"sceneName": self.scene}).get("sceneItems", [])
        ids = {i.get("sourceName"): i.get("sceneItemId") for i in items}
        if self.names["text"] not in ids:
            raise ValueError(f"OBS scene {self.scene!r} has no source named {self.names['text']!r}: "
                             "add a Text source with that name (see docs/POPUPS.md)")
        self.text_id = ids[self.names["text"]]
        self.badge_id = ids.get(self.names["badge"]) if self.names["badge"] else None
        self.bubble_id = ids.get(self.names["bubble"]) if self.names["bubble"] else None

    def _write(self, action: str, data: dict) -> None:
        try:
            self.control.execute(action, data, allow_write=True)
            self._down = False
        except (OBSControlError, OSError, ValueError, PermissionError) as exc:
            if not self._down:                       # report once per outage; never break the stream
                print(f"pop-ups: OBS {action} failed ({exc}); will retry on the next card", file=self.err, flush=True)
            self._down = True

    def _visible(self, item_id, on: bool) -> None:
        if item_id is not None:
            self._write("source-visible", {"sceneName": self.scene, "sceneItemId": item_id, "sceneItemEnabled": on})

    def show(self, card: Card) -> None:
        has_badge = self.badge_id is not None
        self._write("text-set", {"inputName": self.names["text"], "text": card_text(card, wrap=self.wrap, badge=has_badge)})
        if has_badge:
            if card.is_commentary:
                self._write("text-set", {"inputName": self.names["badge"], "text": card.initials or ""})
            self._visible(self.badge_id, card.is_commentary)
        self._visible(self.bubble_id, True)
        self._visible(self.text_id, True)

    def hide(self) -> None:
        for item in (self.text_id, self.badge_id, self.bubble_id):
            self._visible(item, False)


class TerminalDisplay:
    """Dry-run: the cards as they'd pop up, printed in the terminal."""

    def __init__(self, out=None, *, wrap: int = 30):
        self.out, self.wrap = out or sys.stdout, wrap

    def show(self, card: Card) -> None:
        stamp = time.strftime("%H:%M:%S")
        body = "\n".join("   " + l for l in card_lines(card, self.wrap))
        src = f"   [{card.kind}{' · ' + card.source if card.source else ''}]"
        print(f"\n{stamp} POP-UP\n{body}\n{src}", file=self.out, flush=True)

    def hide(self) -> None:
        print(f"{time.strftime('%H:%M:%S')} (hidden)", file=self.out, flush=True)


class PopupController:
    def __init__(self, scheduler: Scheduler, display, now_playing, *, clock=time.monotonic):
        self.scheduler, self.display, self.now_playing, self.clock = scheduler, display, now_playing, clock
        self.history: list[Card] = []
        self.pos = -1                                # index of the current card in history
        self.paused = False
        self.visible_since: float | None = None
        self.song = (None, None)
        self.lock = threading.RLock()

    def _show(self, card: Card | None) -> Card | None:
        if card is not None:
            self.display.show(card)
            self.visible_since = self.clock()
        return card

    def step(self) -> None:
        with self.lock:
            now = self.clock()
            if self.visible_since is not None and not self.paused and now - self.visible_since >= self.scheduler.show_s:
                self.display.hide()
                self.visible_since = None
            if self.paused:
                return
            self.song = self.now_playing.current()
            card = self.scheduler.tick(now, *self.song)
            if card is not None:
                self.history.append(card)
                self.pos = len(self.history) - 1
                self._show(card)

    def next(self) -> Card | None:
        with self.lock:
            if self.pos < len(self.history) - 1:
                self.pos += 1
                return self._show(self.history[self.pos])
            card = self.scheduler.next_card(*self.now_playing.current())
            if card is not None:
                self.history.append(card)
                self.pos = len(self.history) - 1
                self.scheduler._last = self.clock()  # the auto clock restarts from a manual card
            return self._show(card)

    def back(self) -> Card | None:
        with self.lock:
            if self.pos > 0:
                self.pos -= 1
            return self._show(self.history[self.pos]) if self.history else None

    def show_again(self) -> Card | None:
        with self.lock:
            return self._show(self.history[self.pos]) if self.history else None

    def hide(self) -> None:
        with self.lock:
            self.display.hide()
            self.visible_since = None

    def pause(self) -> None:
        with self.lock:
            self.paused = True

    def resume(self) -> None:
        with self.lock:
            self.paused = False

    def status(self) -> dict:
        with self.lock:
            cur = self.history[self.pos] if self.history else None
            return {"mode": "paused" if self.paused else "auto", "visible": self.visible_since is not None,
                    "card": cur.to_json() if cur else None,
                    "position": [self.pos + 1, len(self.history)],
                    "now_playing": {"artist": self.song[0], "title": self.song[1]}}


CONTROL_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>claw-dj pop-ups</title>
<style>body{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:16px;background:#111;color:#eee}
button{font-size:20px;padding:14px 18px;margin:6px;border-radius:12px;border:0;background:#f4efe1;color:#111}
#s{margin-top:14px;white-space:pre-wrap;font-size:16px;color:#ccc}</style></head><body>
<h2>claw-dj pop-ups</h2>
<button onclick="go('back')">&#9664; Back</button><button onclick="go('next')">Next &#9654;</button><br>
<button onclick="go('show')">Show</button><button onclick="go('hide')">Hide</button><br>
<button onclick="go('pause')">Pause auto</button><button onclick="go('resume')">Resume auto</button>
<div id="s"></div>
<script>
async function go(a){const r=await fetch('/'+a,{method:'POST'});draw(await r.json());}
function draw(d){const c=d.card;document.getElementById('s').textContent=
 d.mode+(d.visible?' · showing':'')+' · '+d.position[0]+'/'+d.position[1]+'\\n'+
 (d.now_playing.artist?('now: '+d.now_playing.artist+' - '+d.now_playing.title+'\\n'):'')+
 (c?('\\n'+c.text+(c.initials?'  — '+c.initials:'')):'');}
setInterval(async()=>draw(await (await fetch('/status')).json()),2000);go('status');
</script></body></html>"""


def make_control_server(controller: PopupController, *, host: str = "127.0.0.1", port: int = 8766) -> ThreadingHTTPServer:
    actions = {"/next": controller.next, "/back": controller.back, "/show": controller.show_again,
               "/hide": controller.hide, "/pause": controller.pause, "/resume": controller.resume,
               "/status": lambda: None}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle(self):
            path = self.path.split("?", 1)[0]
            if path == "/":
                return self._send(200, CONTROL_HTML.encode(), "text/html; charset=utf-8")
            if path in actions:
                actions[path]()
                return self._send(200, json.dumps(controller.status()).encode(), "application/json")
            return self._send(404, b'{"error": "not found"}', "application/json")

        do_GET = do_POST = _handle

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer((host, port), Handler)


def _card_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--interval", type=float, default=75.0, help="seconds between automatic pop-ups")
    p.add_argument("--show", type=float, default=12.0, help="seconds each pop-up stays up")
    p.add_argument("--commentary-every", type=int, default=3)
    p.add_argument("--verified-only", action="store_true")
    p.add_argument("--wrap", type=int, default=30, help="characters per line")
    p.add_argument("--now-file", type=Path, default=None, help='JSON {"artist","title"} instead of Mixxx')
    p.add_argument("--mixxx-port", type=int, default=None)
    p.add_argument("--facts", type=Path, default=DEFAULT_FACTS)
    p.add_argument("--commentary", type=Path, default=DEFAULT_COMMENTARY)
    p.add_argument("--control-host", default="127.0.0.1", help="0.0.0.0 to use the control page from a phone")
    p.add_argument("--control-port", type=int, default=8766)


def _serve(a, display) -> None:
    from hands.popup_overlay import NowPlaying
    facts, threads = load_facts(a.facts), load_commentary(a.commentary)
    sched = Scheduler(facts, threads, interval_s=a.interval, show_s=a.show, commentary_every=a.commentary_every,
                      verified_only=a.verified_only, seed=int(time.time()))
    ctl = PopupController(sched, display, NowPlaying(mixxx_port=a.mixxx_port, now_file=a.now_file))
    srv = make_control_server(ctl, host=a.control_host, port=a.control_port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"pop-ups: {len(sched.facts)} facts, {len(threads)} commentary threads; auto every {a.interval:g}s "
          f"for {a.show:g}s. Control: http://{a.control_host}:{a.control_port}/  (or: python -m hands.popup_obs next)",
          flush=True)
    try:
        while True:
            ctl.step()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        ctl.hide()
        srv.shutdown()
        srv.server_close()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="claw-dj native OBS pop-ups (auto + manual)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="drive OBS text sources (needs --allow-write)")
    run.add_argument("--scene", required=True, help="the OBS scene holding the pop-up sources")
    run.add_argument("--allow-write", action="store_true", help="required: lets this process change OBS text/visibility")
    run.add_argument("--text-source", default=TEXT_SOURCE)
    run.add_argument("--badge-source", default=BADGE_SOURCE)
    run.add_argument("--bubble-source", default=BUBBLE_SOURCE)
    run.add_argument("--obs-port", type=int, default=4455)
    run.add_argument("--password-file", default=None)
    _card_args(run)
    dry = sub.add_parser("dry-run", help="preview the cards in the terminal, no OBS")
    _card_args(dry)
    for name in ("next", "back", "show", "hide", "pause", "resume", "status"):
        c = sub.add_parser(name, help=f"{name} on a running pop-up process")
        c.add_argument("--control-port", type=int, default=8766)
        c.add_argument("--control-host", default="127.0.0.1")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        if not a.allow_write:
            ap.error("run changes OBS text and visibility: pass --allow-write to confirm")
        from hands.obs_cli import load_password
        from hands.obs_control import OBSControl
        control = OBSControl(port=a.obs_port, password=load_password(a.password_file), timeout_s=3.0)
        disp = ObsDisplay(control, scene=a.scene, text_source=a.text_source, badge_source=a.badge_source or None,
                          bubble_source=a.bubble_source or None, wrap=a.wrap)
        disp.resolve()
        disp.hide()
        _serve(a, disp)
    elif a.cmd == "dry-run":
        _serve(a, TerminalDisplay(wrap=a.wrap))
    else:
        host = "127.0.0.1" if a.control_host == "0.0.0.0" else a.control_host
        path = {"show": "show"}.get(a.cmd, a.cmd)
        with urllib.request.urlopen(urllib.request.Request(f"http://{host}:{a.control_port}/{path}", method="POST"),
                                    timeout=5) as r:
            print(r.read().decode())


if __name__ == "__main__":
    main()
