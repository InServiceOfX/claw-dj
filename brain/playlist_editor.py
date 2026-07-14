"""Local playlist picker backed by the crate and Mixxx analysis snapshot.

Usage: uv run python -m brain.playlist_editor --open
"""
from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from brain.library import Track, load_crate
from brain.library_index import configured_roots, scan_status
from brain.playlist import (
    DATA_DIR,
    export_playlist,
    load_exclusions,
    load_seed,
    load_selection,
    match_seed,
    save_exclusions,
    save_selection,
    track_record,
)

BRAIN_CACHE = {engine: DATA_DIR / f"brain_picks_{engine}.json" for engine in ("nemoclaw", "h-agent")}
MIX_PLAN_PATH = DATA_DIR / "mix_plan.json"
DEFAULT_PLAYLIST_JSON = DATA_DIR / "playlist.json"

WEB_ROOT = Path(__file__).parent / "web"


class PlaylistApp:
    def __init__(self) -> None:
        self.scan_thread: threading.Thread | None = None
        self.scan_error: str | None = None
        self.brain_thread: threading.Thread | None = None
        self.brain_state: dict = {"running": 0, "error": None, "picks": None,
                                  "brief": None, "engine": None}
        self.mix_thread: threading.Thread | None = None
        self.mix_run_thread: threading.Thread | None = None
        self.enrich_thread: threading.Thread | None = None
        self.mix_state: dict = {
            "building": 0,
            "running": 0,
            "enriching": 0,
            "error": None,
            "profile": None,
            "mix_brief": None,
            "order_engine": None,
            "summary": None,
            "live_error": None,
            "live_message": None,
            "enrich_message": None,
            "enrich_error": None,
            "enrich_report": None,
            "enrich_log": [],
        }
        self.reload()

    def reload(self) -> None:
        self.tracks = load_crate()
        self.by_id = {track.track_id: track for track in self.tracks}
        self.selection = [track_id for track_id in load_selection() if track_id in self.by_id]
        self.selected = set(self.selection)
        self.excluded = set(load_exclusions())

    def ingest_status(self) -> dict:
        status = scan_status()
        if self.scan_error:
            status["error"] = self.scan_error
        return status

    def start_scan(self) -> dict:
        if self.scan_thread and self.scan_thread.is_alive():
            return self.ingest_status()
        roots = [Path(path) for path in configured_roots()]
        if not roots:
            raise ValueError(
                "No music folders configured. Run brain.scan_library with your RnB and HipHop folders once."
            )

        def work() -> None:
            self.scan_error = None
            try:
                from brain.catalog import write_catalog
                from brain.library_index import export_records
                from brain.scan_library import incremental_scan

                summary = incremental_scan(roots)
                records = export_records()
                from brain.library import DEFAULT_CRATE_CACHE
                DEFAULT_CRATE_CACHE.write_text(json.dumps(records, indent=2))
                write_catalog(records, roots=[str(root) for root in roots])
                if summary.get("new"):
                    self._refresh_new_music_view()
                self.reload()
            except Exception as error:  # surfaced in the local UI
                self.scan_error = str(error)

        self.scan_thread = threading.Thread(target=work, daemon=True)
        self.scan_thread.start()
        return {**self.ingest_status(), "running": 1}

    def _refresh_new_music_view(self) -> None:
        """Rebuild the agent-facing new-music view from the newest scan batch,
        so 'Ask the DJ brain' always reasons over what the last scan found."""
        from contextlib import closing

        from brain.library_index import connect

        with closing(connect()) as db:
            started = db.execute("SELECT started_at FROM scan_state WHERE id=1").fetchone()[0]
            rows = [dict(r) for r in db.execute(
                "SELECT track_id, artist, title, album, genre, duration_seconds "
                "FROM tracks WHERE available=1 AND first_seen_at >= ? "
                "ORDER BY artist, title", (started,),
            )]
        if not rows:
            return
        view = {
            "note": "Newest scan batch (metadata only; no bpm/key yet). "
                    "Pick playlist candidates from these ids only.",
            "track_count": len(rows),
            "tracks": [
                {"id": f"n{i:04d}", "artist": r["artist"], "title": r["title"],
                 "album": r["album"], "genre": r["genre"],
                 "duration_seconds": r["duration_seconds"]}
                for i, r in enumerate(rows)
            ],
        }
        (DATA_DIR / "new_music_agent.json").write_text(json.dumps(view, indent=1) + "\n")
        (DATA_DIR / "new_music_ids.json").write_text(
            json.dumps({r["track_id"]: f"n{i:04d}" for i, r in enumerate(rows)}, indent=1) + "\n"
        )

    def _annotate(self, picks: list[dict]) -> list[dict]:
        return [
            {**pick, "in_library": pick["track_id"] in self.by_id,
             "enabled": pick["track_id"] in self.selected,
             "excluded": pick["track_id"] in self.excluded}
            for pick in picks
        ]

    def brain_status(self) -> dict:
        status = dict(self.brain_state)
        results = dict(status.get("results") or {})
        # Fall back to each engine's last cached run so results survive
        # editor restarts and show even when nothing ran this session.
        for engine, cache in BRAIN_CACHE.items():
            if engine not in results and cache.exists():
                results[engine] = json.loads(cache.read_text())
        status["results"] = {
            engine: {**data, "picks": self._annotate(data.get("picks") or [])}
            for engine, data in results.items()
        }
        return status

    def ask_brain(self, brief: str, engine: str, count: int) -> dict:
        """Run agent candidate-picking (one engine or both) in the background."""
        engines = ("nemoclaw", "h-agent") if engine == "both" else (engine,)
        for name in engines:
            if name not in BRAIN_CACHE:
                raise ValueError(f"unknown engine {name!r}")
        if not brief.strip():
            raise ValueError("brief is empty — say what kind of set you want")
        if self.brain_thread and self.brain_thread.is_alive():
            return self.brain_status()
        self.brain_state = {"running": 1, "error": None, "results": {},
                            "brief": brief, "engine": engine}

        def work() -> None:
            errors = []
            for name in engines:
                try:
                    from brain.pick_candidates import run_pick

                    picks = run_pick(engine=name, brief=brief, count=count)
                    result = {"brief": brief, "engine": name, "picks": picks}
                    self.brain_state["results"][name] = result
                    BRAIN_CACHE[name].write_text(json.dumps(result, indent=1) + "\n")
                except Exception as error:  # surfaced in the local UI
                    errors.append(f"{name}: {error}")
            self.brain_state.update(running=0, error="; ".join(errors) or None)

        self.brain_thread = threading.Thread(target=work, daemon=True)
        self.brain_thread.start()
        return self.brain_status()

    def suggest_blends(self, limit: int = 20) -> dict:
        """Deterministic mix-graph picks that blend with the CURRENT edited set.

        Only Mixxx-analyzed tracks can be scored honestly, so candidates are
        analyzed, unselected, non-excluded library tracks ranked by their best
        transition score against any track in the set.

        Always returns a human-readable `message` so the UI can explain empty
        results, weak set links, or "set already blends well" cases.
        """
        from brain.mix_graph import (
            lineage_pairs,
            load_chroma_pairs,
            load_lineage,
            pair_score,
            transition_report,
        )

        set_tracks = [self.by_id[i] for i in self.selection if i in self.by_id]
        if not set_tracks:
            raise ValueError("enabled set is empty — nothing to blend against")

        unanalyzed = [
            {"artist": t.artist, "title": t.title, "track_id": t.track_id}
            for t in set_tracks
            if not t.bpm
        ]
        analyzed_in_set = [t for t in set_tracks if t.bpm]
        internal_mean = None
        weak_internal: list[dict] = []
        if len(analyzed_in_set) >= 2:
            report = transition_report(analyzed_in_set)
            if report:
                internal_mean = round(sum(row["score"] for row in report) / len(report), 3)
                weak_internal = [
                    {
                        "from": row.get("from") or row.get("a"),
                        "to": row.get("to") or row.get("b"),
                        "score": row["score"],
                    }
                    for row in report
                    if row["score"] < 0.45
                ][:5]

        candidates = [
            track for track in self.tracks
            if track.bpm and track.track_id not in self.selected
            and track.track_id not in self.excluded
        ]
        lineage = lineage_pairs(set_tracks + candidates, load_lineage())
        chroma = load_chroma_pairs()
        scored = []
        anchors = analyzed_in_set or set_tracks
        for candidate in candidates:
            edge, anchor = max(
                ((pair_score(anchor, candidate, lineage=lineage, chroma=chroma), anchor)
                 for anchor in anchors),
                key=lambda row: row[0].score,
            )
            scored.append((edge.score, candidate, anchor, edge.reasons))
        scored.sort(key=lambda row: -row[0])
        # Only surface reasonably strong external blends by default.
        strong = [(s, c, a, r) for s, c, a, r in scored if s >= 0.55]
        shown = strong[:limit] if strong else scored[: min(5, limit)]
        picks = [
            {
                "id": f"s{i:03d}",
                "artist": candidate.artist,
                "title": candidate.title,
                "track_id": candidate.track_id,
                "score": round(score, 2),
                "blends_with": f"{anchor.artist} — {anchor.title}",
                "why": list(reasons)[:2],
            }
            for i, (score, candidate, anchor, reasons) in enumerate(shown)
        ]

        parts: list[str] = []
        if unanalyzed:
            titles = ", ".join(f"{u['artist']} — {u['title']}" for u in unanalyzed[:3])
            extra = f" (+{len(unanalyzed) - 3} more)" if len(unanalyzed) > 3 else ""
            parts.append(
                f"{len(unanalyzed)} track(s) in the set lack BPM/key (e.g. {titles}{extra}) — "
                "analyze them in Mixxx before trusting blend scores for those slots."
            )
        if internal_mean is not None:
            if internal_mean >= 0.7 and not weak_internal:
                parts.append(
                    f"Your current set already blends well (mean consecutive score {internal_mean}). "
                    "No urgent adds — optional library blends below if you want more options."
                )
            elif weak_internal:
                parts.append(
                    f"Set mean consecutive score {internal_mean}; {len(weak_internal)} weak link(s) "
                    "inside the set. Library blends below may shore those up."
                )
            else:
                parts.append(f"Set mean consecutive score {internal_mean}.")
        if not candidates:
            parts.append(
                "No analyzed library tracks left outside the set (and not excluded) to suggest."
            )
        elif not picks:
            parts.append("No external blend candidates scored usefully against this set.")
        elif strong:
            parts.append(
                f"Found {len(strong)} solid library blend(s) (score ≥ 0.55) from "
                f"{len(candidates)} analyzed candidates — check ones you want, then Add."
            )
        else:
            parts.append(
                f"No strong external blends (best scores < 0.55). Showing top {len(picks)} weak options; "
                "the set may already be self-sufficient."
            )

        return {
            "engine": "mix-graph",
            "brief": "analyzed tracks that blend with the current set",
            "candidates_considered": len(candidates),
            "internal_mean_score": internal_mean,
            "unanalyzed_in_set": unanalyzed,
            "weak_internal": weak_internal,
            "message": " ".join(parts),
            "picks": self._annotate(picks),
        }

    def apply_picks(self, track_ids: list[str]) -> dict:
        added = 0
        unknown = 0
        for track_id in track_ids:
            if track_id not in self.by_id:
                unknown += 1
                continue
            if track_id not in self.selected:
                self.selection.append(track_id)
                self.selected.add(track_id)
                added += 1
            self.excluded.discard(track_id)
        save_selection(self.selection)
        save_exclusions(sorted(self.excluded))
        return {"added": added, "unknown": unknown, "selected_count": len(self.selection)}

    def metadata(self) -> dict:
        return {
            "track_count": len(self.tracks),
            "analyzed_count": sum(track.bpm is not None for track in self.tracks),
            "selected_count": len(self.selection),
            "selected_analyzed_count": sum(self.by_id[track_id].bpm is not None for track_id in self.selection),
            "artists": sorted({track.artist for track in self.tracks}, key=str.casefold),
        }

    def search(self, params: dict[str, list[str]]) -> dict:
        query = params.get("q", [""])[0].casefold().strip()
        artist = params.get("artist", [""])[0]
        analysis = params.get("analysis", ["all"])[0]
        selected_only = params.get("selected", ["0"])[0] == "1"
        limit = min(int(params.get("limit", ["400"])[0]), 1000)

        tracks = self.tracks
        if selected_only:
            tracks = [self.by_id[track_id] for track_id in self.selection]
        else:
            tracks = sorted(tracks, key=lambda track: (track.artist.casefold(), track.title.casefold()))
        if query:
            tracks = [
                track for track in tracks
                if query in f"{track.artist} {track.title} {track.track_id}".casefold()
            ]
        if artist:
            tracks = [track for track in tracks if track.artist == artist]
        if analysis == "analyzed":
            tracks = [track for track in tracks if track.bpm is not None]
        elif analysis == "missing":
            tracks = [track for track in tracks if track.bpm is None]

        total = len(tracks)
        return {
            "total": total,
            "truncated": total > limit,
            "tracks": [{**track_record(track), "enabled": track.track_id in self.selected} for track in tracks[:limit]],
        }

    def set_enabled(self, track_id: str, enabled: bool) -> None:
        if track_id not in self.by_id:
            raise KeyError(track_id)
        if enabled:
            if track_id not in self.selected:
                self.selection.append(track_id)
                self.selected.add(track_id)
            self.excluded.discard(track_id)
        elif track_id in self.selected:
            self.selection.remove(track_id)
            self.selected.remove(track_id)
            # An explicit removal is a durable opinion: nothing (seed merge,
            # agent picks, blend suggestions) re-adds it until re-enabled.
            self.excluded.add(track_id)
        save_selection(self.selection)
        save_exclusions(sorted(self.excluded))

    def add_seed(self) -> dict:
        matches = match_seed(self.tracks, load_seed())
        for match in matches:
            if match.track and match.track.track_id in self.excluded:
                continue
            if match.track and match.track.track_id not in self.selected:
                self.selection.append(match.track.track_id)
                self.selected.add(match.track.track_id)
        save_selection(self.selection)
        return {
            "matched": sum(match.track is not None for match in matches),
            "unmatched": [f"{match.artist} - {match.title}" for match in matches if match.track is None],
            "selected_count": len(self.selection),
        }

    def mix_order(self) -> dict:
        """Reorder the current enabled set for mixability (BPM/key/lineage).

        Does not drop user picks — only reorders them. Full hit+H-agent curation
        stays on the CLI (`brain.curate_playlist`) so the UI never silently
        replaces a good set with deep cuts.
        """
        from brain.mix_graph import greedy_mix_order, lineage_pairs, load_lineage, transition_report

        selected_tracks = [self.by_id[track_id] for track_id in self.selection if track_id in self.by_id]
        if not selected_tracks:
            return {"count": 0, "mean_score": 0.0, "message": "no enabled tracks to order"}
        lineage = lineage_pairs(selected_tracks, load_lineage())
        ordered = greedy_mix_order(selected_tracks, start=selected_tracks[0], lineage=lineage)
        self.selection = [track.track_id for track in ordered]
        self.selected = set(self.selection)
        save_selection(self.selection)
        report = transition_report(ordered, lineage=lineage)
        mean = sum(row["score"] for row in report) / len(report) if report else 0.0
        return {
            "count": len(ordered),
            "mean_score": round(mean, 3),
            "lineage_edges": len(lineage),
            "message": f"reordered {len(ordered)} user-enabled tracks for mix flow (mean transition {mean:.2f})",
        }

    def export(self) -> dict:
        selected = export_playlist(self.tracks, self.selection)
        missing = [
            {"artist": t.artist, "title": t.title, "track_id": t.track_id}
            for t in selected
            if not t.bpm
        ]
        analyzed = len(selected) - len(missing)
        # Stale any in-memory dry-run so the mix page reloads from disk + marks plan stale.
        self.mix_state["summary"] = None
        message = (
            f"Finalized {len(selected)} tracks ({analyzed} with BPM/key"
            + (f", {len(missing)} still need Mixxx analysis" if missing else "")
            + "). Create the mix uses this snapshot."
        )
        return {
            "count": len(selected),
            "analyzed_count": analyzed,
            "missing_bpm_count": len(missing),
            "missing_bpm": missing,
            "json": "brain/data/playlist.json",
            "m3u": "brain/data/playlist.m3u8",
            "message": message,
            "finalized": self.finalized_snapshot(),
        }

    def finalized_snapshot(self) -> dict | None:
        """What Finalize last wrote — the source of truth for Create the mix."""
        if not DEFAULT_PLAYLIST_JSON.exists():
            return None
        try:
            rows = json.loads(DEFAULT_PLAYLIST_JSON.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(rows, list):
            return None
        missing = [
            {"artist": r.get("artist"), "title": r.get("title"), "track_id": r.get("track_id")}
            for r in rows
            if not r.get("bpm")
        ]
        return {
            "count": len(rows),
            "analyzed_count": len(rows) - len(missing),
            "missing_bpm_count": len(missing),
            "missing_bpm": missing,
            "tracks": [
                {
                    "artist": r.get("artist"),
                    "title": r.get("title"),
                    "album": r.get("album"),
                    "bpm": r.get("bpm"),
                    "key": r.get("key"),
                    "track_id": r.get("track_id"),
                }
                for r in rows
            ],
            "path": "brain/data/playlist.json",
        }

    def _plan_stale(self, summary: dict | None, finalized: dict | None) -> bool:
        if not summary or not finalized:
            return False
        plan_ids = {
            t.get("track_id")
            for t in (summary.get("tracks") or [])
            if t.get("track_id")
        }
        # Plan only includes analyzed tracks; compare against analyzed finalized ids.
        final_analyzed = {
            t.get("track_id")
            for t in (finalized.get("tracks") or [])
            if t.get("track_id") and t.get("bpm")
        }
        if not plan_ids:
            return True
        return plan_ids != final_analyzed or summary.get("track_count") != len(final_analyzed)

    def _load_plan_summary(self) -> dict | None:
        if not MIX_PLAN_PATH.exists():
            return None
        from brain.build_mix_plan import plan_summary

        plan = json.loads(MIX_PLAN_PATH.read_text())
        return plan_summary(plan, plan_path=MIX_PLAN_PATH)

    def reexport_finalized(self) -> dict:
        """Rewrite playlist.json from current selection + latest crate bpm/key.

        Call after sync_mixxx_analysis or enrich so Create the mix sees new
        metadata without requiring another manual Finalize click.
        """
        self.reload()
        if not self.selection:
            # Fall back to whatever is already on disk (ids may have dropped).
            if DEFAULT_PLAYLIST_JSON.exists():
                return self.finalized_snapshot() or {"count": 0}
            raise ValueError("nothing selected to re-export")
        selected = export_playlist(self.tracks, self.selection)
        self.mix_state["summary"] = None  # plan may now be stale relative to new analysis
        return {
            "count": len(selected),
            "analyzed_count": sum(1 for t in selected if t.bpm),
            "finalized": self.finalized_snapshot(),
        }

    def rescan_finalized_tags(self) -> dict:
        """Re-read tags/filenames for the finalized (or selected) set.

        Picks up renames like Many Man → Many Men when ID3 still has the typo
        but the file name was fixed. Updates library index + crate + playlist.
        """
        from contextlib import closing
        from pathlib import Path

        from brain.library import DEFAULT_CRATE_CACHE
        from brain.library_index import connect, export_records
        from brain.scan_library import _read_record

        self.reload()
        targets = list(self.selection)
        if not targets and DEFAULT_PLAYLIST_JSON.exists():
            rows = json.loads(DEFAULT_PLAYLIST_JSON.read_text())
            targets = [r["track_id"] for r in rows if r.get("track_id")]
        if not targets:
            raise ValueError("nothing to rescan — enable tracks or finalize first")

        now = __import__("time").time()
        updated = []
        missing = []
        with closing(connect()) as db:
            for track_id in targets:
                path = Path(track_id)
                if not path.exists():
                    # Same-directory rename: old path gone, look for closest name.
                    parent = path.parent
                    if parent.is_dir():
                        stem_hint = path.stem.casefold().replace("many man", "many men")
                        candidates = [
                            p for p in parent.iterdir()
                            if p.suffix.casefold() == path.suffix.casefold() and p.is_file()
                        ]
                        match = None
                        for candidate in candidates:
                            if "many men" in candidate.stem.casefold() and "wish death" in candidate.stem.casefold():
                                match = candidate
                                break
                            if stem_hint and stem_hint[:12] in candidate.stem.casefold():
                                match = candidate
                        if match is not None:
                            result = _read_record(match, min_age_seconds=0, now=now)
                            if result and result[0] == "ok":
                                record = result[1]
                                # Migrate selection id
                                if track_id in self.selection:
                                    self.selection = [
                                        record["track_id"] if x == track_id else x
                                        for x in self.selection
                                    ]
                                db.execute(
                                    "UPDATE tracks SET available=0 WHERE track_id=?",
                                    (track_id,),
                                )
                                db.execute(
                                    "INSERT INTO tracks(track_id, root, size_bytes, mtime_ns, title, artist, "
                                    "album, genre, duration_seconds, available, first_seen_at, last_seen_at) "
                                    "VALUES (?,?,?,?,?,?,?,?,?,1,?,?) "
                                    "ON CONFLICT(track_id) DO UPDATE SET "
                                    "size_bytes=excluded.size_bytes, mtime_ns=excluded.mtime_ns, "
                                    "title=excluded.title, artist=excluded.artist, album=excluded.album, "
                                    "genre=excluded.genre, duration_seconds=excluded.duration_seconds, "
                                    "available=1, last_seen_at=excluded.last_seen_at",
                                    (
                                        record["track_id"],
                                        str(match.parent),
                                        record.get("size_bytes") or 0,
                                        match.stat().st_mtime_ns,
                                        record["title"],
                                        record["artist"],
                                        record.get("album"),
                                        record.get("genre"),
                                        record.get("duration_seconds"),
                                        now,
                                        now,
                                    ),
                                )
                                # Carry bpm/key from old row if new has none
                                old = db.execute(
                                    "SELECT bpm, key FROM tracks WHERE track_id=?", (track_id,)
                                ).fetchone()
                                if old and old[0]:
                                    db.execute(
                                        "UPDATE tracks SET bpm=COALESCE(bpm, ?), key=COALESCE(key, ?) "
                                        "WHERE track_id=?",
                                        (old[0], old[1], record["track_id"]),
                                    )
                                updated.append(
                                    f"{record['artist']} — {record['title']} (renamed path)"
                                )
                                continue
                    missing.append(track_id)
                    continue
                result = _read_record(path, min_age_seconds=0, now=now)
                if not result or result[0] != "ok":
                    missing.append(track_id)
                    continue
                record = result[1]
                db.execute(
                    "UPDATE tracks SET title=?, artist=?, album=?, genre=?, "
                    "duration_seconds=?, size_bytes=?, mtime_ns=?, last_seen_at=?, available=1 "
                    "WHERE track_id=?",
                    (
                        record["title"],
                        record["artist"],
                        record.get("album"),
                        record.get("genre"),
                        record.get("duration_seconds"),
                        record.get("size_bytes") or 0,
                        path.stat().st_mtime_ns,
                        now,
                        track_id,
                    ),
                )
                updated.append(f"{record['artist']} — {record['title']}")
            db.commit()
            records = export_records()
        if records:
            DEFAULT_CRATE_CACHE.write_text(json.dumps(records, indent=2) + "\n")
        save_selection(self.selection)
        result = self.reexport_finalized()
        sample = ", ".join(updated[:5]) + ("…" if len(updated) > 5 else "")
        message = f"Rescanned {len(updated)} track(s)."
        if sample:
            message += f" Updated: {sample}."
        if missing:
            message += f" {len(missing)} path(s) still missing on disk."
        # Highlight Many Men if present
        many = [
            t for t in (result.get("finalized") or {}).get("tracks") or []
            if "many men" in (t.get("title") or "").casefold()
            or "many man" in (t.get("title") or "").casefold()
        ]
        if many:
            message += f" Wish Death title now: {many[0].get('title')}."
        return {**result, "updated": len(updated), "missing": missing, "message": message}

    def reshuffle_opener(self, opener_track_id: str | None = None) -> dict:
        """Re-unfold the mix-graph tour from a new starting track.

        The set is a blend graph (BPM/key/lineage/chroma/lyrics affinities).
        Picking a different opener (or randomizing it) runs the same greedy
        nearest-neighbor tour from that node so adjacent pairs stay mixable
        while the overall narrative shifts. Writes the new order into
        selection + playlist.json; marks any dry-run plan stale.
        """
        import random

        from brain.library import Track
        from brain.mix_graph import (
            greedy_mix_order,
            lineage_pairs,
            load_chroma_pairs,
            load_lineage,
            transition_report,
        )

        self.reload()
        if DEFAULT_PLAYLIST_JSON.exists():
            rows = json.loads(DEFAULT_PLAYLIST_JSON.read_text())
        else:
            rows = [
                track_record(self.by_id[i])
                for i in self.selection
                if i in self.by_id
            ]
        if len(rows) < 2:
            raise ValueError("need at least 2 finalized tracks to reshuffle")

        tracks: list[Track] = []
        for row in rows:
            tid = row["track_id"]
            if tid in self.by_id:
                tracks.append(self.by_id[tid])
            else:
                tracks.append(
                    Track(
                        track_id=tid,
                        title=row.get("title") or "",
                        artist=row.get("artist") or "",
                        bpm=row.get("bpm"),
                        key=row.get("key"),
                        genre=row.get("genre"),
                    )
                )
        by_id = {t.track_id: t for t in tracks}
        analyzed = [t for t in tracks if t.bpm]
        pool = analyzed if len(analyzed) >= 2 else tracks

        if opener_track_id:
            start = by_id.get(opener_track_id)
            if start is None:
                raise ValueError(f"opener not in finalized set: {opener_track_id}")
        else:
            start = random.choice(pool)

        lineage = lineage_pairs(pool, load_lineage())
        chroma = load_chroma_pairs()
        ordered = greedy_mix_order(pool, start=start, lineage=lineage, chroma=chroma)
        # Append any unanalyzed leftovers at the end so nothing is dropped.
        ordered_ids = {t.track_id for t in ordered}
        for track in tracks:
            if track.track_id not in ordered_ids:
                ordered.append(track)

        self.selection = [t.track_id for t in ordered]
        self.selected = set(self.selection)
        save_selection(self.selection)
        export_playlist(self.tracks if self.tracks else ordered, self.selection)
        self.mix_state["summary"] = None

        report = transition_report(ordered, lineage=lineage, chroma=chroma)
        mean = sum(row["score"] for row in report) / len(report) if report else 0.0
        preview = [
            {"artist": t.artist, "title": t.title, "bpm": t.bpm, "key": t.key, "track_id": t.track_id}
            for t in ordered[:8]
        ]
        return {
            "opener": {
                "artist": start.artist,
                "title": start.title,
                "track_id": start.track_id,
                "bpm": start.bpm,
                "key": start.key,
            },
            "count": len(ordered),
            "mean_score": round(mean, 3),
            "preview": preview,
            "message": (
                f"Graph re-unfolded from opener “{start.artist} — {start.title}” "
                f"({len(ordered)} tracks, mean transition {mean:.2f}). "
                "Rebuild the mix plan to bake this order into events."
            ),
            "finalized": self.finalized_snapshot(),
        }

    def sync_from_mixxx(self) -> dict:
        """Pull BPM/key Mixxx already wrote into its DB → crate + finalized playlist.

        Use after a manual Mixxx Analyze. Note: some tracks report bpm=0 in
        Mixxx until analysis truly finishes — then use analyze & enrich instead.
        """
        from brain.sync_mixxx_analysis import fetch_analyzed, main as sync_main

        before = {t.track_id: t.bpm for t in self.tracks}
        analyzed = fetch_analyzed()
        mixxx_rows = sum(1 for hit in analyzed.values() if hit.get("bpm"))
        sync_main()  # writes library index + crate.json

        result = self.reexport_finalized()
        newly = []
        for track in (result.get("finalized") or {}).get("tracks") or []:
            tid = track.get("track_id")
            if track.get("bpm") and not before.get(tid):
                newly.append(f"{track.get('artist')} — {track.get('title')}")
        still_missing = [
            f"{t.get('artist')} — {t.get('title')}"
            for t in (result.get("finalized") or {}).get("tracks") or []
            if not t.get("bpm")
        ]
        message = (
            f"Synced Mixxx analysis ({mixxx_rows} library rows with bpm>0). "
            f"Finalized set now {result.get('analyzed_count')}/{result.get('count')} with BPM/key."
        )
        if newly:
            message += f" Newly filled: {', '.join(newly[:5])}."
        if still_missing:
            message += (
                f" Still missing ({len(still_missing)}): {', '.join(still_missing[:3])}"
                + ("…" if len(still_missing) > 3 else "")
                + " — Mixxx still has bpm=0 for these; use Analyze & enrich (control API)."
            )
        return {
            **result,
            "mixxx_analyzed_rows": mixxx_rows,
            "newly_filled": newly,
            "still_missing": still_missing,
            "message": message,
        }

    def start_enrich(self, *, port: int = 9995) -> dict:
        """Background: analyze missing bpm/key via Mixxx control API + lyrics/chroma/phrases."""
        if self.enrich_thread and self.enrich_thread.is_alive():
            return self.mix_status()
        if self.mix_thread and self.mix_thread.is_alive():
            raise ValueError("mix plan is building — wait before enriching")
        if self.mix_run_thread and self.mix_run_thread.is_alive():
            raise ValueError("live mix is running — stop before enriching")
        if not DEFAULT_PLAYLIST_JSON.exists():
            raise ValueError("no finalized playlist — Finalize for Mixxx first")

        # Ensure playlist.json matches current selection before enriching.
        if self.selection:
            export_playlist(self.tracks, self.selection)

        self.mix_state.update(
            enriching=1,
            enrich_error=None,
            enrich_message="Starting enrichment (bpm/key via Mixxx, then lyrics/chroma/phrases)…",
            enrich_report=None,
            enrich_log=[],
        )

        def work() -> None:
            try:
                from brain.enrich_set import run_enrich
                from hands.mixxx_control import MixxxControl, MixxxControlError

                def progress(msg: str) -> None:
                    log = list(self.mix_state.get("enrich_log") or [])
                    log.append(msg)
                    self.mix_state["enrich_log"] = log[-40:]
                    self.mix_state["enrich_message"] = msg

                # Fail fast if Mixxx control API is down (needed for missing bpm).
                try:
                    with MixxxControl(port=port, timeout_s=2.0) as mixxx:
                        if not mixxx.ping():
                            raise MixxxControlError("no pong")
                except Exception as error:
                    # Still allow lyrics/chroma/phrases if bpm already present;
                    # only hard-fail when something needs bpm analysis.
                    from brain.enrich_set import enrichment_status

                    gaps = enrichment_status(DEFAULT_PLAYLIST_JSON)
                    need_bpm = (gaps.get("missing") or {}).get("bpm_key", 0)
                    if need_bpm:
                        raise ValueError(
                            f"Mixxx control API not reachable on port {port} "
                            f"({error}); need it to analyze {need_bpm} track(s) "
                            "missing BPM/key. Launch: open -a Mixxx --args "
                            "--control-api-port 9995"
                        ) from error
                    progress(
                        f"Mixxx API down ({error}); skipping bpm analysis — "
                        "filling lyrics/chroma/phrases only."
                    )
                    report = run_enrich(
                        playlist_path=DEFAULT_PLAYLIST_JSON,
                        port=port,
                        skip_bpm=True,
                        progress=progress,
                    )
                else:
                    report = run_enrich(
                        playlist_path=DEFAULT_PLAYLIST_JSON,
                        port=port,
                        progress=progress,
                    )

                self.reexport_finalized()
                from brain.enrich_set import enrichment_status

                status = enrichment_status(DEFAULT_PLAYLIST_JSON)
                self.mix_state.update(
                    enriching=0,
                    enrich_error=None,
                    enrich_report=report,
                    enrich_message=(
                        f"Done — {report.get('complete')}/{report.get('track_count')} fully enriched. "
                        f"{status.get('message', '')}"
                    ),
                )
            except Exception as error:
                self.mix_state.update(
                    enriching=0,
                    enrich_error=str(error),
                    enrich_message=None,
                )

        self.enrich_thread = threading.Thread(target=work, daemon=True)
        self.enrich_thread.start()
        return self.mix_status()

    def mix_status(self) -> dict:
        from brain.mix_profiles import PROFILES

        status = dict(self.mix_state)
        if not status.get("summary"):
            try:
                status["summary"] = self._load_plan_summary()
            except Exception as error:  # surface corrupt plan without crashing the UI
                status["error"] = status.get("error") or f"could not read existing plan: {error}"
        finalized = self.finalized_snapshot()
        status["finalized"] = finalized
        status["profiles"] = [
            {"name": name, "description": profile.description}
            for name, profile in PROFILES.items()
        ]
        status["plan_ready"] = bool(status.get("summary")) and not self._plan_stale(
            status.get("summary"), finalized
        )
        status["plan_stale"] = self._plan_stale(status.get("summary"), finalized)
        status["playlist_ready"] = finalized is not None and (finalized.get("count") or 0) >= 2
        try:
            from brain.enrich_set import enrichment_status

            status["enrichment"] = enrichment_status(DEFAULT_PLAYLIST_JSON)
        except Exception as error:
            status["enrichment"] = {"ready": False, "error": str(error)}
        return status

    def build_mix(
        self,
        profile: str,
        mix_brief: str,
        tracks: int | None = None,
        order_engine: str = "nemoclaw",
    ) -> dict:
        """Build a mix plan in the background (profile + free-text brief).

        Mirrors `brain.build_mix_plan --profile … --mix-brief … --order-engine …`.
        When the brief mentions pairings / placement / a short subset and
        order_engine is nemoclaw or h-agent, the agent shapes the order first.
        """
        from brain.mix_profiles import PROFILES

        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r}; choose from {sorted(PROFILES)}")
        if order_engine not in ("none", "nemoclaw", "h-agent"):
            raise ValueError(f"unknown order engine {order_engine!r}")
        if self.mix_thread and self.mix_thread.is_alive():
            return self.mix_status()
        if self.mix_run_thread and self.mix_run_thread.is_alive():
            raise ValueError("a live mix is already running — stop it before rebuilding the plan")
        if not DEFAULT_PLAYLIST_JSON.exists():
            raise ValueError("no finalized playlist yet — click Finalize for Mixxx first")

        # Feel-only briefs don't need a slow agent call.
        engine = order_engine
        if not (mix_brief or "").strip():
            engine = "none"

        if self.enrich_thread and self.enrich_thread.is_alive():
            raise ValueError("enrichment is still running — wait before building the plan")

        self.mix_state = {
            "building": 1,
            "running": 0,
            "enriching": 0,
            "error": None,
            "profile": profile,
            "mix_brief": mix_brief,
            "order_engine": engine,
            "summary": None,
            "live_error": None,
            "live_message": None,
            "enrich_message": self.mix_state.get("enrich_message"),
            "enrich_error": self.mix_state.get("enrich_error"),
            "enrich_report": self.mix_state.get("enrich_report"),
            "enrich_log": self.mix_state.get("enrich_log") or [],
        }

        def work() -> None:
            try:
                from brain.build_mix_plan import compose_mix_plan, plan_summary

                plan = compose_mix_plan(
                    playlist=DEFAULT_PLAYLIST_JSON,
                    profile_name=profile,
                    mix_brief=mix_brief or "",
                    order_engine=engine,
                    tracks=tracks,
                    out=MIX_PLAN_PATH,
                )
                summary = plan_summary(plan, plan_path=MIX_PLAN_PATH)
                self.mix_state.update(
                    building=0,
                    error=None,
                    summary=summary,
                    profile=profile,
                    mix_brief=mix_brief,
                    order_engine=engine,
                )
            except Exception as error:  # surfaced in the local UI
                self.mix_state.update(building=0, error=str(error), summary=None)

        self.mix_thread = threading.Thread(target=work, daemon=True)
        self.mix_thread.start()
        return self.mix_status()

    def start_mix(self, *, confirm: bool, port: int = 9995) -> dict:
        """Perform the current mix plan live. Requires confirm=True (UI double-gate)."""
        if not confirm:
            raise ValueError(
                "refusing to start without explicit confirmation "
                "(POST {\"confirm\": true} after the dry-run summary looks right)"
            )
        if self.mix_thread and self.mix_thread.is_alive():
            raise ValueError("mix plan is still building — wait for the dry-run summary")
        if self.mix_run_thread and self.mix_run_thread.is_alive():
            return self.mix_status()
        if not MIX_PLAN_PATH.exists():
            raise ValueError("no mix plan yet — build one first")

        from hands.mixxx_control import MixxxControl, MixxxControlError

        try:
            with MixxxControl(port=port, timeout_s=2.0) as mixxx:
                if not mixxx.ping():
                    raise MixxxControlError("Mixxx control API did not pong")
        except Exception as error:
            raise ValueError(
                f"Mixxx control API not reachable on port {port}: {error}. "
                "Launch with: open -a Mixxx --args --control-api-port 9995"
            ) from error

        plan = json.loads(MIX_PLAN_PATH.read_text())
        self.mix_state.update(
            running=1,
            live_error=None,
            live_message=f"Starting live mix ({plan.get('track_count')} tracks, "
                         f"{len(plan.get('events') or [])} events)…",
        )

        def work() -> None:
            try:
                from hands.run_mix_plan import run_plan

                run_plan(plan, port=port, dry_run=False, max_events=None)
                self.mix_state.update(running=0, live_message="Mix finished.", live_error=None)
            except Exception as error:  # surfaced in the local UI
                self.mix_state.update(running=0, live_error=str(error), live_message=None)

        self.mix_run_thread = threading.Thread(target=work, daemon=True)
        self.mix_run_thread.start()
        return self.mix_status()


def make_handler(app: PlaylistApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/meta":
                self._json(app.metadata())
                return
            if parsed.path == "/api/tracks":
                self._json(app.search(parse_qs(parsed.query)))
                return
            if parsed.path == "/api/ingest":
                self._json(app.ingest_status())
                return
            if parsed.path == "/api/brain":
                self._json(app.brain_status())
                return
            if parsed.path == "/api/mix":
                self._json(app.mix_status())
                return
            if parsed.path in ("/", "/index.html"):
                body = (WEB_ROOT / "playlist.html").read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            try:
                if self.path == "/api/selection":
                    payload = self._body()
                    app.set_enabled(payload["track_id"], bool(payload["enabled"]))
                    self._json(app.metadata())
                    return
                if self.path == "/api/seed":
                    self._json(app.add_seed())
                    return
                if self.path == "/api/mix-order":
                    self._json(app.mix_order())
                    return
                if self.path == "/api/export":
                    self._json(app.export())
                    return
                if self.path == "/api/ingest/scan":
                    self._json(app.start_scan(), HTTPStatus.ACCEPTED)
                    return
                if self.path == "/api/brain/ask":
                    payload = self._body()
                    self._json(
                        app.ask_brain(
                            str(payload.get("brief", "")),
                            str(payload.get("engine", "nemoclaw")),
                            int(payload.get("count", 20)),
                        ),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/brain/apply":
                    payload = self._body()
                    self._json(app.apply_picks(list(payload.get("track_ids", []))))
                    return
                if self.path == "/api/suggest":
                    payload = self._body()
                    self._json(app.suggest_blends(int(payload.get("limit", 20))))
                    return
                if self.path == "/api/mix/build":
                    payload = self._body()
                    tracks = payload.get("tracks")
                    self._json(
                        app.build_mix(
                            str(payload.get("profile", "dj-showcase")),
                            str(payload.get("mix_brief", "")),
                            int(tracks) if tracks is not None else None,
                            str(payload.get("order_engine", "nemoclaw")),
                        ),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/mix/start":
                    payload = self._body()
                    port = int(payload.get("port", 9995))
                    self._json(
                        app.start_mix(confirm=bool(payload.get("confirm")), port=port),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/mix/sync":
                    self._json(app.sync_from_mixxx())
                    return
                if self.path == "/api/mix/enrich":
                    payload = self._body()
                    self._json(
                        app.start_enrich(port=int(payload.get("port", 9995))),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/mix/refresh":
                    self._json(app.reexport_finalized())
                    return
                if self.path == "/api/mix/rescan-tags":
                    self._json(app.rescan_finalized_tags())
                    return
                if self.path == "/api/mix/shuffle-opener":
                    payload = self._body()
                    opener = payload.get("opener_track_id")
                    self._json(
                        app.reshuffle_opener(
                            str(opener) if opener else None,
                        )
                    )
                    return
            except (KeyError, ValueError, json.JSONDecodeError) as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args()

    app = PlaylistApp()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    url = f"http://{args.host}:{args.port}"
    print(f"playlist editor: {url} ({len(app.tracks)} tracks, {len(app.selection)} selected)")
    if args.open_browser:
        threading.Timer(0.25, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
