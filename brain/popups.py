"""Pop-up cards for claw-dj: VH1 Pop-Up Video style facts and authors' commentary.

Two kinds of text pop up while a mix plays (on stream or in a video):
- agent-written music facts about the song/artist playing (no attribution mark);
- snippets of an author's own writing in `commentary/<author-slug>/`, always
  marked with the author's initials (Ernest: "EY"). Direct quotes are shown in
  quotation marks; distillations come only from the author's own
  `distilled.md` and are labeled "in brief", never shown as quotes.

No network, audio or Mixxx here: `hands/popup_overlay.py` serves the cards live
(OBS browser source) and video builders burn in `timeline()` /
`drawtext_filters()`. Story:
user_stories/story__while_the_mix_plays_pop_ups_show_music_facts_and_my_commentary.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import textwrap
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FACTS = ROOT / "brain" / "popup_facts.json"
DEFAULT_COMMENTARY = ROOT / "commentary"
CUE_FPS = 75


@dataclass(frozen=True)
class Card:
    id: str
    text: str
    kind: str                                   # "fact" | "quote" | "distilled"
    initials: str | None = None                 # author's initials; None for agent facts
    author: str | None = None
    source: str | None = None
    tags: tuple[str, ...] = ()
    part: tuple[int, int] | None = None         # (i, n) within a progression
    verified: bool = True

    @property
    def is_commentary(self) -> bool:
        return self.kind in ("quote", "distilled")

    def to_json(self) -> dict:
        return {"id": self.id, "text": self.text, "kind": self.kind, "initials": self.initials,
                "author": self.author, "source": self.source, "tags": list(self.tags),
                "part": list(self.part) if self.part else None}


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    artist: str
    title: str


# ------------------------------------------------------------------ loading
def load_facts(path: Path = DEFAULT_FACTS) -> list[Card]:
    """Agent-written facts. Every fact must say where it can be checked."""
    path = Path(path)
    if not path.exists():
        return []
    cards = []
    for raw in json.loads(path.read_text(encoding="utf-8")):
        if not str(raw.get("source") or "").strip():
            raise ValueError(f"fact {raw.get('id')!r} has no source")
        cards.append(Card(
            id=str(raw["id"]), text=str(raw["text"]).strip(), kind="fact",
            source=str(raw["source"]).strip(),
            tags=tuple(raw.get("artists") or ()) + tuple(f"title:{t}" for t in raw.get("titles") or ()),
            verified=bool(raw.get("verified", False)),
        ))
    return cards


def _initials(slug: str) -> str:
    return "".join(w[0].upper() for w in re.split(r"[-_\s]+", slug) if w)


def _front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    meta = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    tags = meta.get("tags", "").strip().strip("[]")
    meta["tags"] = tuple(t.strip().strip("'\"") for t in tags.split(",") if t.strip())
    return meta, text[end + 4:]


def _thread(texts: list[str], *, base_id: str, kind: str, initials: str, author: str, tags) -> list[Card]:
    parts = [s for t in texts for s in snippets(t)]
    n = len(parts)
    return [Card(id=f"{base_id}#{i}", text=p, kind=kind, initials=initials, author=author, tags=tuple(tags),
                 part=(i + 1, n) if n > 1 else None) for i, p in enumerate(parts)]


def load_commentary(root: Path = DEFAULT_COMMENTARY) -> list[list[Card]]:
    """Each author folder's writing as threads (one per pull quote / passage /
    distilled bullet), every card marked with the author's initials."""
    root = Path(root)
    threads: list[list[Card]] = []
    if not root.exists():
        return threads
    for adir in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        info = {}
        if (adir / "author.json").exists():
            info = json.loads((adir / "author.json").read_text(encoding="utf-8"))
        author = info.get("name") or adir.name.replace("-", " ").title()
        initials = info.get("initials") or _initials(adir.name)
        for f in sorted(adir.glob("*.md")):
            if f.name.startswith("_") or f.name.lower() == "readme.md":
                continue
            meta, body = _front_matter(f.read_text(encoding="utf-8"))
            tags = meta.get("tags", ())
            base = f"{adir.name}/{f.stem}"
            common = dict(initials=initials, author=author, tags=tags)
            if f.name == "distilled.md":
                for i, line in enumerate(l for l in body.splitlines() if l.strip().startswith("- ")):
                    threads.append(_thread([line.strip()[2:].strip()], base_id=f"{base}/{i}", kind="distilled", **common))
                continue
            lines = body.splitlines()
            quotes, cur = [], []
            for line in lines + [""]:
                if line.startswith(">"):
                    cur.append(line[1:].strip())
                elif cur:
                    quotes.append(" ".join(cur))
                    cur = []
            if quotes:
                passages = quotes
            else:
                passages, para = [], []
                for line in lines + [""]:
                    s = line.strip()
                    skip = s.startswith(("#", "- ", "* ", "```", "|")) or re.match(r"^\d+\.\s", s)
                    if s and not skip:
                        para.append(s)
                    elif para:
                        passages.append(" ".join(para))
                        para = []
            for i, p in enumerate(passages):
                threads.append(_thread([p], base_id=f"{base}/{i}", kind="quote", **common))
    return [t for t in threads if t]


def snippets(text: str, max_chars: int = 180) -> list[str]:
    """Display-sized pieces: whole sentences joined while they fit; an overlong
    sentence is split at word boundaries. Order kept, nothing lost."""
    sentences = [s for s in re.split(r"(?<=[.!?…])\s+", " ".join(text.split())) if s]
    pieces: list[str] = []
    for s in sentences:
        if len(s) > max_chars:
            pieces.extend(textwrap.wrap(s, max_chars, break_long_words=True, break_on_hyphens=False))
        else:
            pieces.append(s)
    out: list[str] = []
    for p in pieces:
        if out and len(out[-1]) + 1 + len(p) <= max_chars:
            out[-1] = f"{out[-1]} {p}"
        else:
            out.append(p)
    return out


# ---------------------------------------------------------------- relevance
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"^\s*the\s+", "", s)
    return " ".join(s.split())


def _names(artist: str | None) -> list[str]:
    """'Joe Featuring Mariah Carey & Nas' -> ['joe', 'mariah carey', 'nas']."""
    if not artist:
        return []
    parts = re.split(r"\s*(?:;|,|&| and | x | feat\.?| featuring| ft\.?| f/| with)\s*", artist, flags=re.I)
    names = [_norm(p) for p in parts if _norm(p)]
    return names + [_norm(artist)]


def _matches(name: str, artist_names: list[str]) -> bool:
    n = _norm(name)
    if not n:
        return False
    for a in artist_names:
        if n == a or re.search(rf"(^| ){re.escape(n)}( |$)", a):
            return True
    return False


def is_relevant(card: Card, artist: str | None, title: str | None) -> bool:
    names = _names(artist)
    if not names:
        return False
    if card.kind == "fact":
        artists = [t for t in card.tags if not t.startswith("title:")]
        titles = [t[6:] for t in card.tags if t.startswith("title:")]
        if not artists or not any(_matches(a, names) for a in artists):
            return False
        return not titles or _norm(title or "") in {_norm(t) for t in titles}
    return any(_matches(t, names) for t in card.tags)


def _general(card: Card) -> bool:
    if card.kind == "fact":
        return not [t for t in card.tags if not t.startswith("title:")]
    return not card.tags


# ---------------------------------------------------------------- scheduler
class Scheduler:
    def __init__(self, facts: list[Card], threads: list[list[Card]], *, interval_s: float = 75.0,
                 show_s: float = 12.0, commentary_every: int = 3, verified_only: bool = False, seed: int = 0):
        if interval_s < show_s:
            raise ValueError(f"interval_s ({interval_s}) must be >= show_s ({show_s})")
        rng = random.Random(seed)
        self.facts = [f for f in facts if f.verified or not verified_only]
        rng.shuffle(self.facts)
        self.threads = [list(t) for t in threads if t]
        rng.shuffle(self.threads)
        self.interval_s, self.show_s = interval_s, show_s
        self.commentary_every = max(1, int(commentary_every))
        self._slot = 0
        self._shown_facts: set[str] = set()
        self._shown_threads: set[int] = set()
        self._thread: list[Card] = []           # remaining cards of the thread in progress
        self._last: float | None = None

    def _pick_fact(self, artist, title) -> Card | None:
        if not self.facts:
            return None
        for pool in ([f for f in self.facts if is_relevant(f, artist, title)],
                     [f for f in self.facts if _general(f)], self.facts):
            fresh = [f for f in pool if f.id not in self._shown_facts]
            if pool and not fresh and pool is self.facts:
                self._shown_facts.clear()
                fresh = list(pool)
            if fresh:
                self._shown_facts.add(fresh[0].id)
                return fresh[0]
        return None

    def _pick_commentary(self, artist, title) -> Card | None:
        if self._thread:
            return self._thread.pop(0)
        if not self.threads:
            return None
        idx = range(len(self.threads))
        for pool in ([i for i in idx if is_relevant(self.threads[i][0], artist, title)],
                     [i for i in idx if _general(self.threads[i][0])], list(idx)):
            fresh = [i for i in pool if i not in self._shown_threads]
            if pool and not fresh and len(pool) == len(self.threads):
                self._shown_threads.clear()
                fresh = list(pool)
            if fresh:
                self._shown_threads.add(fresh[0])
                self._thread = list(self.threads[fresh[0]])
                return self._thread.pop(0)
        return None

    def next_card(self, artist: str | None, title: str | None) -> Card | None:
        self._slot += 1
        want_commentary = self._slot % self.commentary_every == 0     # threads continue on commentary turns
        first, second = ((self._pick_commentary, self._pick_fact) if want_commentary
                         else (self._pick_fact, self._pick_commentary))
        return first(artist, title) or second(artist, title)

    def tick(self, now: float, artist: str | None, title: str | None) -> Card | None:
        if self._last is not None and now - self._last < self.interval_s:
            return None
        card = self.next_card(artist, title)
        if card is not None:
            self._last = now
        return card


# ------------------------------------------------------------------- videos
def parse_cue_sheet(path: Path, duration_s: float | None = None) -> list[Segment]:
    tracks, cur = [], {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith("TRACK"):
            if cur:
                tracks.append(cur)
            cur = {}
        elif s.startswith("TITLE") and line.startswith(" "):          # track-level (indented) titles only
            cur["title"] = s.split(" ", 1)[1].strip().strip('"')
        elif s.startswith("PERFORMER") and line.startswith(" "):
            cur["artist"] = s.split(" ", 1)[1].strip().strip('"')
        elif s.startswith("INDEX 01"):
            m, sec, fr = (int(x) for x in s.split()[-1].split(":"))
            cur["start"] = m * 60 + sec + fr / CUE_FPS
    if cur:
        tracks.append(cur)
    tracks = [t for t in tracks if "start" in t]
    segs = []
    for i, t in enumerate(tracks):
        end = tracks[i + 1]["start"] if i + 1 < len(tracks) else (duration_s if duration_s else t["start"] + 600.0)
        segs.append(Segment(round(t["start"], 3), round(end, 3), t.get("artist", ""), t.get("title", "")))
    return segs


def timeline(segments: list[Segment], scheduler: Scheduler, *, first_offset_s: float = 10.0) -> list[dict]:
    items, free = [], 0.0
    for seg in segments:
        t = max(seg.start + first_offset_s, free)
        while t + scheduler.show_s <= seg.end - 1.0:
            card = scheduler.next_card(seg.artist, seg.title)
            if card is None:
                break
            items.append({"start": round(t, 3), "end": round(t + scheduler.show_s, 3),
                          "artist": seg.artist, "title": seg.title, "card": card})
            free = t + scheduler.show_s
            t += scheduler.interval_s
    return items


def card_lines(card: Card, width: int = 30, *, attribution: bool = True) -> list[str]:
    """Display lines. With attribution=False the "— <initials>" line is left out,
    only for displays that show the initials as a separate badge."""
    text = f"“{card.text}”" if card.kind == "quote" else card.text
    lines = textwrap.wrap(text, width) or [text]
    if card.kind == "distilled":
        lines.append("in brief")
    if card.part:
        lines.append(f"{card.part[0]}/{card.part[1]}")
    if card.is_commentary and attribution:
        lines.append(f"— {card.initials}")
    return lines


def drawtext_filters(items: list[dict], out_dir: Path, fontfile: str, *, fontsize: int = 46,
                     x: str = "60", y: str = "60") -> str:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chain = []
    for i, it in enumerate(items):
        p = out_dir / f"popup_{i:03d}.txt"
        p.write_text("\n".join(card_lines(it["card"])), encoding="utf-8")
        tf = str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        chain.append(f"drawtext=fontfile='{fontfile}':textfile='{tf}':fontsize={fontsize}:fontcolor=white:"
                     f"line_spacing=10:box=1:boxcolor=black@0.62:boxborderw=26:x={x}:y={y}:"
                     f"enable='between(t,{it['start']:.3f},{it['end']:.3f})'")
    return ",".join(chain)


# ---------------------------------------------------------------------- CLI
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="claw-dj pop-up cards (facts + commentary)")
    ap.add_argument("--facts", type=Path, default=DEFAULT_FACTS)
    ap.add_argument("--commentary", type=Path, default=DEFAULT_COMMENTARY)
    ap.add_argument("--verified-only", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("preview", help="print the next cards for a song")
    pv.add_argument("--artist", default=None)
    pv.add_argument("--title", default=None)
    pv.add_argument("--count", type=int, default=6)
    tl = sub.add_parser("timeline", help="cards for a recorded mix, from its Mixxx cue sheet")
    tl.add_argument("--cue", type=Path, required=True)
    tl.add_argument("--duration", type=float, default=None)
    tl.add_argument("--interval", type=float, default=45.0)
    tl.add_argument("--show", type=float, default=10.0)
    tl.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    facts, threads = load_facts(a.facts), load_commentary(a.commentary)
    if a.cmd == "preview":
        s = Scheduler(facts, threads, interval_s=0, show_s=0, verified_only=a.verified_only)
        for _ in range(a.count):
            c = s.next_card(a.artist, a.title)
            if c is None:
                print("(no cards)")
                break
            print("\n".join(card_lines(c)) + f"\n   [{c.kind}{' · ' + c.source if c.source else ''}]\n")
        return
    s = Scheduler(facts, threads, interval_s=a.interval, show_s=a.show, verified_only=a.verified_only)
    items = timeline(parse_cue_sheet(a.cue, a.duration), s)
    data = [dict(it, card=it["card"].to_json()) for it in items]
    text = json.dumps(data, indent=1, ensure_ascii=False)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
        print(f"wrote {len(data)} cards to {a.out}")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
