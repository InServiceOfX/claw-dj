"""Mix-compatibility graph for playlist ordering.

Scores transitions using cues a DJ can actually use in Mixxx:
  - BPM (rate adjust covers ~±8%; half/double-time treated as compatible)
  - musical key / Camelot neighbors (pitch-shift can fix near-misses)
  - known sample / cover lineage edges
  - shared lyric-ish tokens from titles (cheap stand-in until full lyrics)

Waveform cross-correlation is intentionally *not* in the hot path. Full-file
waveform similarity on thousands of tracks is minutes-to-hours of decode +
DSP even in Rust; Mixxx already owns beatgrids once tracks are analyzed.
Use Mixxx BPM/key for the large list; reserve waveform/chromagram work for a
small ordered set later if needed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from brain.library import Track
from brain.playlist import normalize

DEFAULT_LINEAGE = Path(__file__).parent / "playlist_seeds" / "mix_lineage.json"
DEFAULT_CHROMA = Path(__file__).parent / "data" / "chroma_similarity.json"

# Chromagram similarity above this counts as "the texture/beat aligns" — the
# evidence that lets a cross-genre transition off the hook. The current
# matrix (clawdj chroma, lineage set) clusters 0.95-0.99, so the bar is high.
CHROMA_MATCH = 0.975

# Open Key / Camelot notation without the A/B letter first — map common Mixxx
# key strings (e.g. "Am", "C#m", "F") onto Camelot numbers.
_NOTE_TO_CAMELOT_MAJOR = {
    "C": 8,
    "G": 9,
    "D": 10,
    "A": 11,
    "E": 12,
    "B": 1,
    "F#": 2,
    "GB": 2,
    "DB": 3,
    "C#": 3,
    "AB": 4,
    "G#": 4,
    "EB": 5,
    "D#": 5,
    "BB": 6,
    "A#": 6,
    "F": 7,
}
_NOTE_TO_CAMELOT_MINOR = {
    "A": 8,
    "E": 9,
    "B": 10,
    "F#": 11,
    "GB": 11,
    "C#": 12,
    "DB": 12,
    "G#": 1,
    "AB": 1,
    "D#": 2,
    "EB": 2,
    "A#": 3,
    "BB": 3,
    "F": 4,
    "C": 5,
    "G": 6,
    "D": 7,
}


@dataclass(frozen=True)
class MixEdge:
    from_id: str
    to_id: str
    score: float
    reasons: tuple[str, ...]


def parse_key(key: str | None) -> tuple[int, str] | None:
    """Return (camelot_number 1-12, 'A'|'B') or None."""
    if not key:
        return None
    raw = key.strip().replace(" ", "")
    if not raw:
        return None
    # Already Camelot-ish: 8A, 11B
    m = re.fullmatch(r"(\d{1,2})([ABab])", raw)
    if m:
        num = int(m.group(1))
        if 1 <= num <= 12:
            return num, m.group(2).upper()
    # Musical: Am, C#m, F, Bb
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(m|min|minor)?", raw, flags=re.I)
    if not m:
        return None
    note = (m.group(1) + (m.group(2) or "")).upper().replace("B", "B")
    # normalize flats: Bb -> BB handled via replace of single b after letter
    note = note[0] + note[1:].replace("B", "B")
    if len(note) > 1 and note[1] == "B":
        note = note[0] + "B"
    elif len(note) > 1 and note[1] == "#":
        note = note[0] + "#"
    minor = bool(m.group(3))
    table = _NOTE_TO_CAMELOT_MINOR if minor else _NOTE_TO_CAMELOT_MAJOR
    # enharmonic cleanup
    aliases = {"BB": "BB", "A#": "A#", "DB": "DB", "C#": "C#", "EB": "EB", "D#": "D#", "GB": "GB", "F#": "F#", "AB": "AB", "G#": "G#"}
    lookup = note
    if note.endswith("B") and len(note) == 2:
        lookup = note  # flat
    num = table.get(lookup)
    if num is None:
        return None
    return num, ("A" if minor else "B")


def bpm_compatibility(a: float | None, b: float | None) -> tuple[float, str | None]:
    """Score 0..1 for how easily two tempos can be beatmatched with rate."""
    if not a or not b or a <= 0 or b <= 0:
        return 0.35, "bpm unknown (assume workable after Mixxx analyze)"
    lo, hi = sorted((a, b))
    # half/double time
    for factor in (1.0, 2.0, 0.5):
        ratio = hi / (lo * factor) if factor else hi / lo
        if ratio < 1:
            ratio = 1 / ratio
        # ±8% is comfortable pitch/rate for most hip-hop/R&B
        if ratio <= 1.02:
            return 1.0, f"bpm nearly identical ({a:.1f}↔{b:.1f})"
        if ratio <= 1.08:
            return 0.9, f"bpm within ~8% rate adjust ({a:.1f}↔{b:.1f})"
        if ratio <= 1.15:
            return 0.65, f"bpm stretchy but possible ({a:.1f}↔{b:.1f})"
    return 0.15, f"bpm far ({a:.1f}↔{b:.1f})"


def tempo_step(a: float | None, b: float | None) -> float | None:
    """Effective tempo ratio incoming/outgoing after the closest half/double
    alignment. > 1 means the set speeds up at this transition."""
    if not a or not b or a <= 0 or b <= 0:
        return None
    best = None
    for factor in (1.0, 2.0, 0.5):
        ratio = (b * factor) / a
        if best is None or abs(ratio - 1.0) < abs(best - 1.0):
            best = ratio
    return best


def key_compatibility(a: str | None, b: str | None) -> tuple[float, str | None]:
    ka, kb = parse_key(a), parse_key(b)
    if not ka or not kb:
        return 0.4, "key unknown"
    na, ma = ka
    nb, mb = kb
    if na == nb and ma == mb:
        return 1.0, f"same key ({a})"
    # relative major/minor (same camelot number, A↔B)
    if na == nb and ma != mb:
        return 0.95, f"relative major/minor ({a}↔{b})"
    # adjacent camelot (energy change)
    diff = min((na - nb) % 12, (nb - na) % 12)
    if diff == 1 and ma == mb:
        return 0.85, f"camelot neighbor ({a}↔{b})"
    if diff == 1:
        return 0.55, f"near key ({a}↔{b})"
    if diff == 2 and ma == mb:
        return 0.4, f"two steps ({a}↔{b})"
    return 0.15, f"key clash ({a}↔{b}; pitch-shift may still fix)"


def load_lineage(path: Path = DEFAULT_LINEAGE) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def load_chroma_pairs(path: Path = DEFAULT_CHROMA) -> dict[tuple[str, str], float]:
    """Pairwise chromagram similarity keyed by sorted track_id pair.

    Produced by `clawdj chroma` on a small ordered set (never the full
    crate); coverage grows as more sets get enriched.
    """
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    paths = data.get("paths") or []
    similarity = data.get("similarity") or []
    pairs: dict[tuple[str, str], float] = {}
    for i, a in enumerate(paths):
        for j in range(i + 1, len(paths)):
            pairs[tuple(sorted((a, paths[j])))] = similarity[i][j]
    return pairs


def genre_of(track: Track) -> str | None:
    """Coarse genre: the library folder root is the reliable signal on this
    drive (HipHop/RnB); fall back to the ID3 genre tag's first token."""
    for root in ("HipHop", "RnB"):
        if f"/{root}/" in track.track_id:
            return root.lower()
    if track.genre:
        tokens = normalize(track.genre).split()
        return tokens[0] if tokens else None
    return None


def lineage_pairs(tracks: list[Track], lineage: list[dict] | None = None) -> set[tuple[str, str]]:
    """Undirected edges between track_ids that share a researched sample link."""
    lineage = lineage if lineage is not None else load_lineage()
    by_norm: dict[tuple[str, str], Track] = {}
    for track in tracks:
        by_norm[(normalize(track.artist), normalize(track.title))] = track

    def find(artist: str, title: str) -> Track | None:
        wa, wt = normalize(artist), normalize(title)
        for (aa, tt), track in by_norm.items():
            if (wa in aa or aa in wa) and (wt == tt or wt in tt or tt in wt):
                return track
        return None

    edges: set[tuple[str, str]] = set()
    for item in lineage:
        a = find(item["artist"], item["title"])
        b = find(item["sample_artist"], item["sample_title"])
        if a and b and a.track_id != b.track_id:
            pair = tuple(sorted((a.track_id, b.track_id)))
            edges.add(pair)  # type: ignore[arg-type]
    return edges


def title_token_overlap(a: Track, b: Track) -> tuple[float, str | None]:
    stop = {
        "the",
        "a",
        "an",
        "and",
        "feat",
        "ft",
        "with",
        "remix",
        "mix",
        "radio",
        "edit",
        "version",
        "album",
        "single",
    }
    ta = {t for t in normalize(a.title).split() if len(t) > 2 and t not in stop}
    tb = {t for t in normalize(b.title).split() if len(t) > 2 and t not in stop}
    if not ta or not tb:
        return 0.0, None
    shared = ta & tb
    if not shared:
        return 0.0, None
    score = min(1.0, 0.25 * len(shared))
    return score, f"shared title tokens {sorted(shared)[:4]}"


def pair_score(
    a: Track,
    b: Track,
    *,
    lineage: set[tuple[str, str]] | None = None,
    chroma: dict[tuple[str, str], float] | None = None,
) -> MixEdge:
    reasons: list[str] = []
    bpm_s, bpm_r = bpm_compatibility(a.bpm, b.bpm)
    key_s, key_r = key_compatibility(a.key, b.key)
    if bpm_r:
        reasons.append(bpm_r)
    if key_r:
        reasons.append(key_r)
    pair = tuple(sorted((a.track_id, b.track_id)))
    lineage_s = 0.0
    if lineage and pair in lineage:
        lineage_s = 1.0
        reasons.append("sample/cover lineage")
    tok_s, tok_r = title_token_overlap(a, b)
    if tok_r:
        reasons.append(tok_r)
    # Weighted: BPM and key dominate; lineage is a strong story boost.
    score = 0.45 * bpm_s + 0.35 * key_s + 0.15 * lineage_s + 0.05 * tok_s

    # Continuity guideline (Ernest, 2026-07-12): dramatic genre switches are
    # a statement to use sparingly — same artist / same genre reads as a
    # coherent journey. A cross-genre move is "earned" when sample lineage
    # or chromagram texture backs it; otherwise it pays a toll here and a
    # streak penalty in greedy_mix_order.
    chroma_sim = chroma.get(pair) if chroma else None
    texture_match = chroma_sim is not None and chroma_sim >= CHROMA_MATCH
    if normalize(a.artist) == normalize(b.artist):
        score += 0.10
        reasons.append("same artist")
    ga, gb = genre_of(a), genre_of(b)
    if ga and gb:
        if ga == gb:
            score += 0.05
        elif texture_match:
            score += 0.03
            reasons.append(f"cross-genre but texture aligns (chroma {chroma_sim:.2f})")
        elif not lineage_s:
            score -= 0.12
            reasons.append(f"genre jump ({ga}→{gb}, unbacked)")

    # Sample lineage is the foundation of the showcase: mixing the original
    # with the song that samples it (often a very different genre) is the
    # story, so it nearly overrides everything else.
    if lineage_s:
        score = max(score, 0.92)
    return MixEdge(a.track_id, b.track_id, min(1.0, score), tuple(reasons))


def greedy_mix_order(
    tracks: list[Track],
    *,
    start: Track | None = None,
    lineage: set[tuple[str, str]] | None = None,
    chroma: dict[tuple[str, str], float] | None = None,
    max_consecutive_slowdowns: int = 2,
    genre_jump_cooldown: int = 4,
) -> list[Track]:
    """Nearest-neighbor tour maximizing successive mix scores.

    Keeps dancefloor energy up: transitions into an equal-or-slightly-faster
    tempo get a bonus, slowing down is tolerated at most
    `max_consecutive_slowdowns` transitions in a row (DJ note from Ernest:
    one or two successive slow-downs is fine, more kills the room).

    Keeps genre switches rare: an *unbacked* genre jump (no lineage, no
    chroma texture match) starts a cooldown of `genre_jump_cooldown` picks
    during which further unbacked jumps are heavily discouraged — dramatic
    switches are a statement, not a habit. Lineage/chroma-backed crossings
    are exempt: those are the showcase.
    """
    if not tracks:
        return []
    if chroma is None:
        chroma = load_chroma_pairs()

    def unbacked_jump(a: Track, b: Track) -> bool:
        ga, gb = genre_of(a), genre_of(b)
        if not ga or not gb or ga == gb:
            return False
        pair = tuple(sorted((a.track_id, b.track_id)))
        if lineage and pair in lineage:
            return False
        sim = chroma.get(pair)
        return not (sim is not None and sim >= CHROMA_MATCH)

    remaining = {track.track_id: track for track in tracks}
    current = start if start and start.track_id in remaining else tracks[0]
    order = [current]
    del remaining[current.track_id]
    slowdown_streak = 0
    jump_cooldown = 0
    while remaining:
        best: Track | None = None
        best_score = -1e9
        best_slow = False
        best_jump = False
        for candidate in remaining.values():
            edge = pair_score(current, candidate, lineage=lineage, chroma=chroma)
            step = tempo_step(current.bpm, candidate.bpm)
            adjusted = edge.score
            slow = step is not None and step < 0.98
            if step is not None:
                if 1.0 <= step <= 1.06:
                    adjusted += 0.05  # energy up: ideal
                elif slow:
                    adjusted -= 0.03
                    if slowdown_streak >= max_consecutive_slowdowns:
                        adjusted -= 0.35  # only if nothing better exists
            jump = unbacked_jump(current, candidate)
            if jump and jump_cooldown > 0:
                adjusted -= 0.30  # a second dramatic switch too soon
            if adjusted > best_score:
                best_score = adjusted
                best = candidate
                best_slow = slow
                best_jump = jump
        assert best is not None
        order.append(best)
        del remaining[best.track_id]
        current = best
        slowdown_streak = slowdown_streak + 1 if best_slow else 0
        jump_cooldown = genre_jump_cooldown if best_jump else max(0, jump_cooldown - 1)
    return order


def transition_report(
    tracks: list[Track],
    *,
    lineage: set[tuple[str, str]] | None = None,
    chroma: dict[tuple[str, str], float] | None = None,
) -> list[dict]:
    if chroma is None:
        chroma = load_chroma_pairs()
    report = []
    for left, right in zip(tracks, tracks[1:]):
        edge = pair_score(left, right, lineage=lineage, chroma=chroma)
        report.append(
            {
                "from": f"{left.artist} — {left.title}",
                "to": f"{right.artist} — {right.title}",
                "score": round(edge.score, 3),
                "reasons": list(edge.reasons),
                "bpm": [left.bpm, right.bpm],
                "key": [left.key, right.key],
            }
        )
    return report
