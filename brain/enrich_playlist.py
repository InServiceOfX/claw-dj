"""Enrich the filtered/ordered playlist with lineage, lyrics, optional chroma.

Input: brain/data/playlist.json (the curated hit set).
Output:
  brain/data/playlist_enriched.json  — tracks + lyrics flags
  brain/data/lyric_pairs.json        — shared-phrase scores
  brain/data/chroma_similarity.json  — optional Rust chromagram matrix
  brain/data/mix_affinity.json       — combined transition affinities

Usage:
    uv run python -m brain.enrich_playlist
    uv run python -m brain.enrich_playlist --chroma --chroma-limit 12
    uv run python -m brain.enrich_playlist --skip-lyrics
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from brain.library import Track, load_crate
from brain.lyrics import enrich_tracks
from brain.mix_graph import (
    greedy_mix_order,
    lineage_pairs,
    load_lineage,
    pair_score,
    transition_report,
)
from brain.playlist import DEFAULT_PLAYLIST_JSON, DEFAULT_SELECTION, export_playlist, load_selection, save_selection

DATA_DIR = Path(__file__).parent / "data"
ENRICHED = DATA_DIR / "playlist_enriched.json"
LYRIC_PAIRS = DATA_DIR / "lyric_pairs.json"
CHROMA = DATA_DIR / "chroma_similarity.json"
AFFINITY = DATA_DIR / "mix_affinity.json"
REPO_ROOT = Path(__file__).resolve().parent.parent


def find_clawdj() -> Path | None:
    for profile in ("release", "debug"):
        candidate = REPO_ROOT / "core-rust" / "target" / profile / "clawdj"
        if candidate.exists():
            return candidate
    return None


def run_chroma(paths: list[str], out: Path) -> dict | None:
    binary = find_clawdj()
    if binary is None:
        # try build
        print("[chroma] building clawdj (first time may take a bit)...")
        subprocess.run(
            ["cargo", "build", "-p", "clawdj-cli"],
            cwd=REPO_ROOT / "core-rust",
            check=False,
        )
        binary = find_clawdj()
    if binary is None:
        print("[chroma] clawdj binary missing — skip chromagram")
        return None
    cmd = [str(binary), "chroma", "--out", str(out), "--"]
    cmd.extend(paths)
    print(f"[chroma] analyzing {len(paths)} tracks via Rust…")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-1500:] if result.stderr else result.stdout)
        print("[chroma] failed — continuing without waveform fingerprints")
        return None
    if out.exists():
        return json.loads(out.read_text())
    return None


def chroma_score(matrix: dict | None, path_a: str, path_b: str) -> float:
    if not matrix:
        return 0.0
    paths = matrix.get("paths") or []
    sims = matrix.get("similarity") or []
    try:
        i, j = paths.index(path_a), paths.index(path_b)
    except ValueError:
        return 0.0
    if i >= len(sims) or j >= len(sims[i]):
        return 0.0
    return float(sims[i][j])


def lyric_edge_map(pairs: list[dict]) -> dict[tuple[str, str], dict]:
    out = {}
    for pair in pairs:
        key = tuple(sorted((pair["a"], pair["b"])))
        out[key] = pair
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST_JSON)
    parser.add_argument("--skip-lyrics", action="store_true")
    parser.add_argument("--force-lyrics", action="store_true")
    parser.add_argument("--chroma", action="store_true", help="run Rust chromagram on a small prefix")
    parser.add_argument("--chroma-limit", type=int, default=12)
    parser.add_argument("--reorder", action="store_true", help="rewrite selection using enriched affinities")
    args = parser.parse_args()

    if not args.playlist.exists():
        raise SystemExit(f"missing {args.playlist} — curate a hits playlist first")
    tracks = json.loads(args.playlist.read_text())
    print(f"enriching {len(tracks)} filtered tracks")

    lyric_pairs: list[dict] = []
    if args.skip_lyrics:
        enriched = [dict(t, lyrics_found=False, lyrics=None) for t in tracks]
    else:
        enriched, lyric_pairs = enrich_tracks(tracks, force=args.force_lyrics)
        found = sum(1 for t in enriched if t.get("lyrics_found"))
        print(f"lyrics: {found}/{len(enriched)} found; {len(lyric_pairs)} non-zero pairs")

    chroma_matrix = None
    if args.chroma:
        paths = [t["track_id"] for t in enriched[: args.chroma_limit]]
        # only existing files
        paths = [p for p in paths if Path(p).exists()]
        chroma_matrix = run_chroma(paths, CHROMA)
        if chroma_matrix:
            print(f"chroma: {chroma_matrix.get('track_count')} fingerprints")

    # Build Track objects for mix_graph
    track_objs = [
        Track(
            track_id=t["track_id"],
            title=t["title"],
            artist=t["artist"],
            genre=t.get("genre"),
            album=t.get("album"),
            bpm=t.get("bpm"),
            key=t.get("key"),
        )
        for t in enriched
    ]
    lineage = lineage_pairs(track_objs, load_lineage())
    lyric_map = lyric_edge_map(lyric_pairs)
    print(f"lineage edges in set: {len(lineage)}")

    affinities = []
    by_id = {t.track_id: t for t in track_objs}
    for i, left in enumerate(track_objs):
        for right in track_objs[i + 1 :]:
            edge = pair_score(left, right, lineage=lineage)
            key = tuple(sorted((left.track_id, right.track_id)))
            lyric = lyric_map.get(key, {})
            chroma = chroma_score(chroma_matrix, left.track_id, right.track_id)
            score = edge.score
            reasons = list(edge.reasons)
            if lyric.get("score", 0) > 0.05:
                score = min(1.0, score + 0.12 * float(lyric["score"]))
                reasons.append(
                    f"lyric overlap {lyric['score']:.2f}"
                    + (f" ({', '.join(lyric.get('shared_bigrams', [])[:2])})" if lyric.get("shared_bigrams") else "")
                )
            if chroma > 0.55:
                score = min(1.0, score + 0.1 * chroma)
                reasons.append(f"chroma sim {chroma:.2f}")
            affinities.append(
                {
                    "a": left.track_id,
                    "b": right.track_id,
                    "a_title": f"{left.artist} — {left.title}",
                    "b_title": f"{right.artist} — {right.title}",
                    "score": round(score, 4),
                    "base_mix": round(edge.score, 4),
                    "lyric_score": lyric.get("score", 0.0),
                    "chroma_score": round(chroma, 4),
                    "reasons": reasons,
                }
            )
    affinities.sort(key=lambda row: -row["score"])

    # strip full lyrics from on-disk enriched export size; keep found flag
    slim = []
    for row in enriched:
        slim.append(
            {
                k: v
                for k, v in row.items()
                if k != "lyrics"
            }
            | {"lyrics_chars": len(row["lyrics"]) if row.get("lyrics") else 0}
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ENRICHED.write_text(json.dumps(slim, indent=2) + "\n")
    LYRIC_PAIRS.write_text(json.dumps(lyric_pairs[:200], indent=2) + "\n")
    AFFINITY.write_text(json.dumps({"pairs": affinities[:500], "lineage_edges": len(lineage)}, indent=2) + "\n")
    print(f"wrote {ENRICHED}")
    print(f"wrote {LYRIC_PAIRS}")
    print(f"wrote {AFFINITY}")
    if affinities:
        print("top affinities:")
        for row in affinities[:8]:
            print(f"  {row['score']:.2f}  {row['a_title']} ↔ {row['b_title']}")
            print(f"       {'; '.join(row['reasons'][:3])}")

    if args.reorder:
        # affinity-aware greedy: use enriched pair scores
        score_lookup = {
            tuple(sorted((row["a"], row["b"]))): row["score"] for row in affinities
        }

        def edge_score(a: Track, b: Track) -> float:
            return score_lookup.get(tuple(sorted((a.track_id, b.track_id))), 0.0)

        remaining = {t.track_id: t for t in track_objs}
        current = track_objs[0]
        order = [current]
        del remaining[current.track_id]
        while remaining:
            best = max(remaining.values(), key=lambda t: edge_score(current, t))
            order.append(best)
            del remaining[best.track_id]
            current = best
        crate = load_crate()
        ids = [t.track_id for t in order]
        save_selection(ids)
        export_playlist(crate, ids)
        report = transition_report(order, lineage=lineage)
        mean = sum(r["score"] for r in report) / len(report) if report else 0
        print(f"reordered selection ({len(order)} tracks, base mean transition {mean:.2f})")


if __name__ == "__main__":
    main()
