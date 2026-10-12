"""Live pop-up overlay for the claw-dj stream: an OBS browser source.

Serves a transparent page that pops up VH1-style bubbles: music facts about the
song claw-dj is playing, and snippets of authors' commentary marked with their
initials (EY for Ernest). It works out the playing song from Mixxx by itself
(the audible deck's exact duration matched against the active plan's tracks)
and never writes to Mixxx, so it can't disturb the mix.

    uv run python -m hands.popup_overlay              # then add the printed URL in OBS
    ... --interval 90 --show 12 --commentary-every 3 --verified-only
    ... --now-file now.json                            # {"artist": ..., "title": ...} without Mixxx

Story: user_stories/story__while_the_mix_plays_pop_ups_show_music_facts_and_my_commentary.md
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import subprocess
import socket
import threading
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from brain.popups import DEFAULT_COMMENTARY, DEFAULT_FACTS, Scheduler, load_commentary, load_facts
from hands.mixxx_control import DEFAULT_PORT, MixxxControl

ROOT = Path(__file__).resolve().parent.parent
PLANS = ROOT / "brain" / "data" / "plans"


# ------------------------------------------------------------- what's playing
def _xf_gain(deck: int, xf: float) -> float:
    """Linear crossfader: left decks (1, 3) full at -1, silent at +1; right decks (2, 4) mirrored."""
    left = deck in (1, 3)
    return max(0.0, min(1.0, (1.0 - xf) if left else (1.0 + xf)))


def audible_deck(mixxx, decks: tuple[int, ...] = (1, 2, 3, 4)) -> int | None:
    xf = mixxx.get("[Master]", "crossfader")
    best, level = None, 0.0
    for d in decks:
        g = f"[Channel{d}]"
        if mixxx.get(g, "play") < 0.5 or mixxx.get(g, "track_loaded") < 0.5:
            continue
        lv = mixxx.get(g, "volume") * _xf_gain(d, xf)
        if lv > level + 1e-9:
            best, level = d, lv
    return best


def _bpm_match(a: float, b: float) -> bool:
    """Same tempo, allowing half/double-time readings (80 vs 160)."""
    return any(abs(a * k - b) <= 0.02 * b for k in (0.5, 1.0, 2.0))


def identify_by_duration(duration_s: float, candidates: list[dict], tolerance_s: float = 0.6,
                         bpm: float | None = None) -> dict | None:
    """The unique candidate whose duration matches within its tolerance (`tol`
    per candidate when known exactly, else `tolerance_s`). When several match,
    the deck's analyzed BPM breaks the tie; still ambiguous gives None."""
    close = [c for c in candidates
             if c.get("duration") and abs(float(c["duration"]) - duration_s) <= float(c.get("tol", tolerance_s))]
    if len(close) > 1 and bpm and bpm > 0:
        close = [c for c in close if c.get("bpm") and _bpm_match(float(c["bpm"]), bpm)]
    return close[0] if len(close) == 1 else None


def _probe_duration(path: str) -> float | None:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True, timeout=15)
        return float(r.stdout.strip())
    except Exception:
        return None


def plan_candidates(index_path: Path | None = None, plans_dir: Path | None = None, *, probe: bool = True) -> list[dict]:
    """The active plan's tracks with durations and BPM ([] when the plan is missing).
    Durations are read exactly from the files when they can be (tight `tol`);
    otherwise the library's coarser duration is used."""
    plans_dir = Path(plans_dir or PLANS)
    try:
        slug = json.loads((plans_dir / "active.json").read_text())["active_slug"]
        tracks = json.loads((plans_dir / slug / "mix_plan.json").read_text())["tracks"]
    except Exception:
        return []
    lib = {}
    try:
        from brain import library_index
        path = index_path or library_index.current_index_path()
        with closing(library_index.connect(path)) as db:
            for t in tracks:
                row = db.execute("SELECT duration_seconds, bpm FROM tracks WHERE track_id = ?", (t["track_id"],)).fetchone()
                if row:
                    lib[t["track_id"]] = row
    except Exception:
        pass
    exact = {}
    if probe:
        paths = [t["track_id"] for t in tracks if Path(t["track_id"]).exists()]
        with cf.ThreadPoolExecutor(8) as ex:
            exact = dict(zip(paths, ex.map(_probe_duration, paths)))
    out = []
    for t in tracks:
        tid = t["track_id"]
        lib_dur, lib_bpm = (lib.get(tid) or (None, None))
        dur, tol = (exact.get(tid), 0.15) if exact.get(tid) else (lib_dur, 0.6)
        if dur:
            out.append({"artist": t.get("artist", ""), "title": t.get("title", ""), "duration": float(dur),
                        "tol": tol, "bpm": t.get("bpm") or lib_bpm})
    return out


class NowPlaying:
    def __init__(self, *, mixxx_port: int | None = None, now_file: Path | None = None,
                 candidates: list[dict] | None = None, cache_s: float = 2.0):
        self.mixxx_port = mixxx_port if mixxx_port is not None else DEFAULT_PORT
        self.now_file = Path(now_file) if now_file else None
        self.candidates = candidates
        self.cache_s = cache_s
        self._cached: tuple[float, tuple[str | None, str | None]] | None = None

    def _read(self) -> tuple[str | None, str | None]:
        if self.now_file:
            d = json.loads(self.now_file.read_text(encoding="utf-8"))
            return d.get("artist") or None, d.get("title") or None
        if self.candidates is None:
            self.candidates = plan_candidates()
        with MixxxControl(port=self.mixxx_port, timeout_s=1.0) as m:
            deck = audible_deck(m)
            if deck is None:
                return None, None
            g = f"[Channel{deck}]"
            hit = identify_by_duration(m.get(g, "duration"), self.candidates, bpm=m.get(g, "file_bpm"))
        return (hit["artist"], hit["title"]) if hit else (None, None)

    def current(self) -> tuple[str | None, str | None]:
        now = time.monotonic()
        if self._cached and now - self._cached[0] < self.cache_s:
            return self._cached[1]
        try:
            value = self._read()
        except Exception:                    # the overlay must never disturb anything
            value = (None, None)
        self._cached = (now, value)
        return value


# --------------------------------------------------------------------- server
OVERLAY_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>claw-dj pop-ups</title>
<style>
  html, body { margin: 0; height: 100%; background: transparent; overflow: hidden; }
  body { font-family: "Avenir Next", "Helvetica Neue", Arial, sans-serif; }
  .bubble {
    position: absolute; max-width: 38vw; padding: 1.1em 1.4em 1.2em; border-radius: 1.4em;
    background: rgba(255, 252, 240, 0.96); color: #111; box-shadow: 0 0.5em 1.6em rgba(0,0,0,0.45);
    font-size: calc(2.15vw * var(--scale, 1)); line-height: 1.25; font-weight: 600;
    transform: scale(0); transform-origin: var(--origin, top left); opacity: 0;
  }
  .bubble.on  { animation: pop-in 0.42s cubic-bezier(.2,1.6,.4,1) forwards; }
  .bubble.off { animation: pop-out 0.32s ease-in forwards; }
  .bubble::after {                     /* the pop-up tail */
    content: ""; position: absolute; width: 1.2em; height: 1.2em; background: inherit;
    transform: rotate(45deg); left: var(--tail-x, 1.6em); top: var(--tail-y, auto); bottom: var(--tail-b, -0.5em);
  }
  .meta { margin-top: 0.55em; font-size: 0.48em; font-weight: 500; color: #555; letter-spacing: 0.04em; }
  .ey {
    position: absolute; right: -0.55em; top: -0.55em; width: 2.1em; height: 2.1em; border-radius: 50%;
    background: #111; color: #fffcf0; font-size: 0.42em; font-weight: 700; display: grid; place-items: center;
    letter-spacing: 0.02em; box-shadow: 0 0.2em 0.5em rgba(0,0,0,0.35);
  }
  .ey[hidden], .meta[hidden] { display: none; }   /* agent facts must show no mark at all */
  @keyframes pop-in  { 0% { transform: scale(0); opacity: 0 } 100% { transform: scale(1); opacity: 1 } }
  @keyframes pop-out { 0% { transform: scale(1); opacity: 1 } 100% { transform: scale(0); opacity: 0 } }
</style></head>
<body>
<div id="b" class="bubble"><div id="t"></div><div id="m" class="meta"></div><div id="ey" class="ey" hidden></div></div>
<script>
  const q = new URLSearchParams(location.search);
  document.documentElement.style.setProperty("--scale", q.get("scale") || "1");
  const spots = [  // safe positions: [left, top, origin, tail]
    ["5vw", "8vh", "top left", "top"], ["57vw", "8vh", "top right", "top"],
    ["5vw", "52vh", "bottom left", "bottom"], ["57vw", "52vh", "bottom right", "bottom"]];
  let serial = -1, hideTimer = null, spot = 0;
  const b = document.getElementById("b"), t = document.getElementById("t"),
        m = document.getElementById("m"), ey = document.getElementById("ey");
  function show(card, showS) {
    const quote = card.kind === "quote";
    t.textContent = quote ? "“" + card.text + "”" : card.text;
    const bits = [];
    if (card.kind === "distilled") bits.push("in brief");
    if (card.part) bits.push(card.part[0] + "/" + card.part[1]);
    m.textContent = bits.join("  ·  ");
    m.hidden = bits.length === 0;
    ey.hidden = !card.initials;            // agent facts carry no mark
    ey.textContent = card.initials || "";
    const s = spots[spot++ % spots.length];
    b.style.left = s[0]; b.style.top = s[1]; b.style.setProperty("--origin", s[2]);
    b.style.setProperty("--tail-b", s[3] === "bottom" ? "-0.5em" : "auto");
    b.style.setProperty("--tail-y", s[3] === "top" ? "-0.5em" : "auto");
    b.className = "bubble"; void b.offsetWidth; b.className = "bubble on";
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => { b.className = "bubble off"; }, Math.max(1, showS) * 1000);
  }
  async function poll() {
    try {
      const r = await fetch("/card", {cache: "no-store"});
      const d = await r.json();
      if (d.card && d.serial !== serial) { serial = d.serial; show(d.card, d.show_s); }
    } catch (e) {}
    setTimeout(poll, 1000);
  }
  poll();
</script></body></html>
"""


def make_server(scheduler: Scheduler, now_playing, *, host: str = "0.0.0.0", port: int = 8765) -> ThreadingHTTPServer:
    state = {"serial": 0, "card": None, "at": 0.0}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:                       # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in ("/", "/overlay"):
                return self._send(200, OVERLAY_HTML.encode("utf-8"), "text/html; charset=utf-8")
            if path == "/health":
                return self._send(200, b'{"ok": true}', "application/json")
            if path == "/card":
                now = time.monotonic()
                with lock:
                    artist, title = now_playing.current()
                    card = scheduler.tick(now, artist, title)
                    if card is not None:
                        state.update(serial=state["serial"] + 1, card=card, at=now)
                    active = state["card"] if state["card"] and now - state["at"] < scheduler.show_s else None
                    body = {"serial": state["serial"], "card": active.to_json() if active else None,
                            "show_s": scheduler.show_s, "now_playing": {"artist": artist, "title": title}}
                return self._send(200, json.dumps(body).encode("utf-8"), "application/json")
            return self._send(404, b'{"error": "not found"}', "application/json")

        def log_message(self, *args) -> None:           # quiet
            pass

    return ThreadingHTTPServer((host, port), Handler)


def _lan_ip() -> str:
    try:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
            s.connect(("192.0.2.1", 9))                 # no packets sent; picks the LAN interface
            return s.getsockname()[0]
    except OSError:
        return "localhost"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--mixxx-port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--interval", type=float, default=75.0, help="seconds between pop-ups")
    ap.add_argument("--show", type=float, default=12.0, help="seconds each pop-up stays up")
    ap.add_argument("--commentary-every", type=int, default=3, help="every Nth pop-up is commentary (when any exists)")
    ap.add_argument("--verified-only", action="store_true", help="only facts a human has checked")
    ap.add_argument("--now-file", type=Path, default=None, help='JSON {"artist","title"} instead of Mixxx')
    ap.add_argument("--facts", type=Path, default=DEFAULT_FACTS)
    ap.add_argument("--commentary", type=Path, default=DEFAULT_COMMENTARY)
    a = ap.parse_args(argv)
    facts, threads = load_facts(a.facts), load_commentary(a.commentary)
    sched = Scheduler(facts, threads, interval_s=a.interval, show_s=a.show,
                      commentary_every=a.commentary_every, verified_only=a.verified_only, seed=int(time.time()))
    now = NowPlaying(mixxx_port=a.mixxx_port, now_file=a.now_file)
    server = make_server(sched, now, host=a.host, port=a.port)
    print(f"pop-ups: {len(sched.facts)} facts, {sum(len(t) for t in threads)} commentary snippets "
          f"({len(threads)} threads); every {a.interval:g}s for {a.show:g}s", flush=True)
    print(f"OBS Browser Source URL: http://{_lan_ip()}:{a.port}/overlay  (1920x1080; or http://localhost:{a.port}/overlay "
          "on this machine)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
