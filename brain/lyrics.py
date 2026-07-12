"""Fetch and score lyrics for a small hit pool (not the full crate).

Uses the free LRCLIB API (https://lrclib.net) with an on-disk cache under
`brain/data/lyrics/`. Designed for ~50–80 tracks — never 14k.

Shared-phrase scoring is intentionally simple: normalize tokens, drop stop
words, score Jaccard overlap + multi-word n-gram hits for wordplay/hooks.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from brain.playlist import normalize

DATA_DIR = Path(__file__).parent / "data"
LYRICS_DIR = DATA_DIR / "lyrics"
CACHE_INDEX = LYRICS_DIR / "index.json"
LRCLIB_SEARCH = "https://lrclib.net/api/search"
USER_AGENT = "claw-dj/0.1 (hackathon playlist enrichment; local-only cache)"

STOP = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "is",
    "it", "you", "i", "me", "my", "we", "our", "your", "that", "this", "with",
    "from", "at", "be", "was", "are", "am", "do", "don", "t", "s", "m", "re",
    "ve", "ll", "just", "like", "know", "got", "get", "gotta", "yeah", "oh",
    "uh", "la", "na", "hey", "baby", "girl", "man", "come", "make", "let",
    "want", "wanna", "gonna", "ain", "not", "no", "yes", "all", "up", "down",
    "out", "so", "if", "when", "what", "who", "how", "why", "can", "could",
    "would", "should", "will", "now", "then", "there", "here", "love", "feel",
}


def cache_key(artist: str, title: str) -> str:
    base = f"{normalize(artist)}__{normalize(title)}"
    return re.sub(r"[^a-z0-9_]+", "_", base)[:120]


def _load_index() -> dict:
    if CACHE_INDEX.exists():
        return json.loads(CACHE_INDEX.read_text())
    return {}


def _save_index(index: dict) -> None:
    LYRICS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_INDEX.write_text(json.dumps(index, indent=2) + "\n")


def _http_get_json(url: str, timeout_s: float = 12.0) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return json.loads(response.read().decode())


def fetch_lyrics(artist: str, title: str, *, force: bool = False) -> dict:
    """Return {artist, title, lyrics, source, found} from cache or LRCLIB."""
    LYRICS_DIR.mkdir(parents=True, exist_ok=True)
    key = cache_key(artist, title)
    path = LYRICS_DIR / f"{key}.json"
    index = _load_index()

    if path.exists() and not force:
        return json.loads(path.read_text())

    # Prefer plain title without featuring clauses for search hit-rate.
    clean_title = re.sub(r"\s*[\(\[].*?[\)\]]", "", title).strip()
    clean_title = re.split(r"\s+feat\.?\s+", clean_title, flags=re.I)[0].strip()
    query = urllib.parse.urlencode({"q": f"{artist} {clean_title}"})
    record = {
        "artist": artist,
        "title": title,
        "lyrics": None,
        "source": None,
        "found": False,
        "error": None,
    }
    try:
        results = _http_get_json(f"{LRCLIB_SEARCH}?{query}")
        if isinstance(results, list) and results:
            best = results[0]
            text = best.get("plainLyrics") or best.get("syncedLyrics")
            if text:
                # strip simple timestamps if synced
                text = re.sub(r"\[\d+:\d+[^\]]*\]", "", text)
                record.update(
                    {
                        "lyrics": text.strip(),
                        "source": f"lrclib:{best.get('id')}",
                        "found": True,
                        "matched_artist": best.get("artistName"),
                        "matched_title": best.get("trackName"),
                    }
                )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        record["error"] = str(error)

    path.write_text(json.dumps(record, indent=2) + "\n")
    index[key] = {
        "artist": artist,
        "title": title,
        "found": record["found"],
        "path": str(path.name),
    }
    _save_index(index)
    return record


def tokens(lyrics: str | None) -> set[str]:
    if not lyrics:
        return set()
    words = normalize(lyrics).split()
    return {w for w in words if len(w) > 2 and w not in STOP}


def bigrams(lyrics: str | None) -> set[str]:
    if not lyrics:
        return set()
    words = [w for w in normalize(lyrics).split() if len(w) > 2 and w not in STOP]
    return {f"{a} {b}" for a, b in zip(words, words[1:])}


def lyric_overlap(a: str | None, b: str | None) -> dict:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return {"score": 0.0, "shared_tokens": [], "shared_bigrams": []}
    shared = sorted(ta & tb)
    ba, bb = bigrams(a), bigrams(b)
    shared_bi = sorted(ba & bb)
    jaccard = len(shared) / max(1, len(ta | tb))
    # Boost multi-word phrase hits (hooks / wordplay candidates).
    score = min(1.0, jaccard * 4.0 + 0.15 * len(shared_bi))
    return {
        "score": round(score, 4),
        "shared_tokens": shared[:24],
        "shared_bigrams": shared_bi[:12],
    }


def enrich_tracks(tracks: list[dict], *, force: bool = False) -> list[dict]:
    """Attach lyrics + pairwise lyric scores for a small ordered playlist."""
    enriched = []
    for track in tracks:
        record = fetch_lyrics(track["artist"], track["title"], force=force)
        row = dict(track)
        row["lyrics_found"] = record["found"]
        row["lyrics_source"] = record.get("source")
        row["lyrics"] = record.get("lyrics")
        enriched.append(row)

    pairs = []
    for i, left in enumerate(enriched):
        for right in enriched[i + 1 :]:
            overlap = lyric_overlap(left.get("lyrics"), right.get("lyrics"))
            if overlap["score"] <= 0:
                continue
            pairs.append(
                {
                    "a": left["track_id"],
                    "b": right["track_id"],
                    "a_title": f"{left['artist']} — {left['title']}",
                    "b_title": f"{right['artist']} — {right['title']}",
                    **overlap,
                }
            )
    pairs.sort(key=lambda row: -row["score"])
    return enriched, pairs
