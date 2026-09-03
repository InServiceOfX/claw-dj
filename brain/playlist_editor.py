"""Local playlist picker backed by the crate and Mixxx analysis snapshot.

Usage: uv run python -m brain.playlist_editor --open
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from brain import collection_registry, library_index
from brain.library import DEFAULT_CRATE_CACHE, Energy, Track, load_crate
from brain.track_preview import PreviewError, content_type, parse_byte_range, resolve_preview_path
from brain.library_index import configured_roots, export_records, scan_status
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

BRAIN_CACHE = {engine: DATA_DIR / f"brain_picks_{engine}.json" for engine in ("nemoclaw", "h-agent", "generic")}
MIX_PLAN_PATH = DATA_DIR / "mix_plan.json"
DEFAULT_PLAYLIST_JSON = DATA_DIR / "playlist.json"

WEB_ROOT = Path(__file__).parent / "web"


def ensure_plan_workspace() -> dict:
    """Promote legacy singleton state once, or create a safe empty workspace."""
    from brain import plan_migration, plan_paths, plan_store

    slugs = plan_paths.list_slugs()
    if slugs:
        if plan_store.get_active() is None:
            plan_store.set_active(slugs[0])
        return {"status": "existing", "slug": plan_store.get_active().slug}
    result = plan_migration.migrate()
    if plan_paths.list_slugs():
        return result
    legacy = plan_paths.legacy_paths()
    sources = {
        "selection": legacy.selection,
        "exclusions": legacy.exclusions,
        "playlist": legacy.playlist,
        "mix_plan": legacy.mix_plan,
    }
    has_legacy = any(path.exists() for path in sources.values())
    meta = plan_store.create(
        "Imported working mix" if has_legacy else "Working mix",
        origin="migrated" if has_legacy else "created",
        origin_ref=str(legacy.root) if has_legacy else None,
    )
    paths = plan_paths.resolve(meta.slug)
    for name, source in sources.items():
        if source.exists():
            shutil.copy2(source, getattr(paths, name))
    plan_store.set_active(meta.slug)
    return {"status": "bootstrapped", "slug": meta.slug, "legacy_preserved": has_legacy}


class PlaylistApp:
    def __init__(self, *, control_port: int | None = None) -> None:
        self.registry_path = collection_registry.DEFAULT_REGISTRY
        self.legacy_index = library_index.DEFAULT_INDEX
        self.control_port_override = int(control_port) if control_port is not None else None
        self.explicit_control_port = control_port is not None
        self.scan_thread: threading.Thread | None = None
        self.scan_error: str | None = None
        self.collection_error: str | None = None
        self.brain_thread: threading.Thread | None = None
        self.brain_state: dict = {"running": 0, "error": None, "picks": None,
                                  "brief": None, "engine": None}
        self.directives_thread: threading.Thread | None = None
        self.directives_state: dict = {"running": 0, "error": None, "preview": None,
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
            "dj_format": None,
            "mix_brief": None,
            "order_engine": None,
            "summary": None,
            "live_error": None,
            "live_message": None,
            "enrich_message": None,
            "enrich_error": None,
            "enrich_report": None,
            "enrich_log": [],
            "mixxx_control_port": self.control_port_override or 9995,
        }
        self.reload()

    def _active_slug(self) -> str | None:
        from brain import plan_store
        meta = plan_store.get_active()
        return meta.slug if meta is not None else None

    def _scoped_paths(self, slug: str | None = None):
        from brain import plan_paths
        chosen = slug or self._active_slug()
        return plan_paths.resolve(chosen) if chosen else None

    def _playlist_path(self, slug: str | None = None) -> Path:
        paths = self._scoped_paths(slug)
        return paths.playlist if paths else DEFAULT_PLAYLIST_JSON

    def _mix_plan_path(self, slug: str | None = None) -> Path:
        paths = self._scoped_paths(slug)
        return paths.mix_plan if paths else MIX_PLAN_PATH

    def _persist_control_port(self, port: int, slug: str | None = None) -> None:
        paths = self._scoped_paths(slug)
        if paths:
            runtime = paths.root / "runtime.json"
            runtime.write_text(json.dumps({"version": 1, "mixxx_control_port": int(port)}, indent=2) + "\n")

    def load_plan_control_port(self, slug: str) -> int | None:
        paths = self._scoped_paths(slug)
        runtime = paths.root / "runtime.json" if paths else None
        if runtime and runtime.exists():
            try:
                return int(json.loads(runtime.read_text())["mixxx_control_port"])
            except (KeyError, ValueError, json.JSONDecodeError):
                return None
        return None

    def reload(self) -> None:
        self.collection_error = None
        if Path(self.registry_path).exists():
            try:
                index_path = collection_registry.active_index_path(
                    registry_path=self.registry_path,
                    fallback=self.legacy_index,
                )
                records = export_records(index_path)
                self.tracks = [
                    Track(
                        track_id=record["track_id"],
                        title=record["title"],
                        artist=record["artist"],
                        genre=record.get("genre"),
                        album=record.get("album"),
                        bpm=record.get("bpm"),
                        key=record.get("key"),
                        energy=Energy(record.get("energy", Energy.MEDIUM.value)),
                        duration_seconds=record.get("duration_seconds"),
                        size_bytes=record.get("size_bytes"),
                        dj_notes=record.get("dj_notes") or "",
                    )
                    for record in records
                ]
                # Existing modules still consume the ignored crate compatibility
                # export. Keep it scoped to the same active database as Curate.
                DEFAULT_CRATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
                DEFAULT_CRATE_CACHE.write_text(json.dumps(records, indent=2))
            except collection_registry.CollectionUnavailable as error:
                # Keep the server/selector reachable without loading any other
                # collection. An explicit activation is required to recover.
                self.collection_error = str(error)
                self.tracks = []
        else:
            self.tracks = load_crate()
        self.by_id = {track.track_id: track for track in self.tracks}
        paths = self._scoped_paths()
        selection = load_selection(paths.selection) if paths else load_selection()
        exclusions = load_exclusions(paths.exclusions) if paths else load_exclusions()
        self.selection = [track_id for track_id in selection if track_id in self.by_id]
        self.selected = set(self.selection)
        self.excluded = set(exclusions)

    def _save_selection_compatible(self) -> None:
        """Keep the active workspace authoritative and legacy readers usable."""
        save_selection(self.selection)
        paths = self._scoped_paths()
        if paths:
            save_selection(self.selection, paths.selection)

    def _save_exclusions_compatible(self) -> None:
        save_exclusions(sorted(self.excluded))
        paths = self._scoped_paths()
        if paths:
            save_exclusions(sorted(self.excluded), paths.exclusions)

    def _export_playlist_compatible(self):
        selected = export_playlist(self.tracks, self.selection)
        paths = self._scoped_paths()
        if paths:
            selected = export_playlist(
                self.tracks,
                self.selection,
                json_path=paths.playlist,
                m3u_path=paths.root / "playlist.m3u8",
            )
        return selected

    def ingest_status(self) -> dict:
        if self.collection_error:
            return {
                "running": 0,
                "roots": [],
                "track_count": 0,
                "untagged_count": 0,
                "new_count": 0,
                "changed_count": 0,
                "unchanged_count": 0,
                "error": self.collection_error,
            }
        try:
            status = scan_status(self._collection_index_path())
        except Exception as error:  # never crash the HTTP thread on status polls
            scanning = bool(self.scan_thread and self.scan_thread.is_alive())
            return {
                "running": int(scanning),
                "roots": [],
                "track_count": 0,
                "untagged_count": 0,
                "new_count": 0,
                "changed_count": 0,
                "unchanged_count": 0,
                "discovered": 0,
                "processed": 0,
                "error": None if scanning else str(error),
                "locked": True,
            }
        # If a scan thread is alive, never report idle just because a locked
        # placeholder lacked running=1 yet or the writer lagged one commit.
        if self.scan_thread and self.scan_thread.is_alive():
            status["running"] = 1
        if self.scan_error:
            status["error"] = self.scan_error
        return status

    def start_scan(self, extra_root: str | None = None) -> dict:
        if self.scan_thread and self.scan_thread.is_alive():
            return self.ingest_status()
        index_path = self._collection_index_path()
        roots = [Path(path) for path in configured_roots(index_path)]
        if extra_root:
            candidate = Path(extra_root).expanduser()
            if not candidate.is_dir():
                raise ValueError(f"not a directory: {candidate}")
            if candidate not in roots:
                roots.append(candidate)
        if not roots:
            raise ValueError(
                "No music folders configured yet — use 'Add music folder' below."
            )

        def work() -> None:
            self.scan_error = None
            try:
                from brain.catalog import write_catalog
                from brain.library_index import export_records
                from brain.scan_library import incremental_scan

                summary = incremental_scan(roots, index_path=index_path)
                records = export_records(index_path)
                DEFAULT_CRATE_CACHE.write_text(json.dumps(records, indent=2))
                write_catalog(records, roots=[str(root) for root in roots])
                if summary.get("new"):
                    self._refresh_new_music_view(index_path)
                self.reload()
            except Exception as error:  # surfaced in the local UI
                self.scan_error = str(error)

        self.scan_thread = threading.Thread(target=work, daemon=True)
        self.scan_thread.start()
        return {**self.ingest_status(), "running": 1}

    def _collection_index_path(self) -> Path:
        return collection_registry.active_index_path(
            registry_path=self.registry_path,
            fallback=self.legacy_index,
        )

    def _refresh_new_music_view(self, index_path: Path | None = None) -> None:
        """Rebuild the agent-facing new-music view from the newest scan batch,
        so 'Ask the DJ brain' always reasons over what the last scan found."""
        from contextlib import closing

        from brain.library_index import connect

        with closing(connect(index_path or self._collection_index_path())) as db:
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

    def ask_brain(self, brief: str, engine: str, count: int, pool: str = "new") -> dict:
        """Run agent candidate-picking (one engine or both) in the background.

        pool="library" scopes candidates to the whole crate (keyword
        pre-filtered) instead of just the newest scan batch — needed for
        briefs about music that's been in the library for a while, since
        "new" pool can only ever see the most recent scan's delta.
        """
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

        # "count" is the user's total-picks budget, not a per-engine one —
        # split it across engines when running both, so asking for 50 with
        # "both" selected doesn't silently mean "up to 50 from EACH" (up to
        # 100 total). Each engine may still return fewer than its share;
        # the LLM's own count isn't hard-truncated downstream either.
        engine_counts = {
            name: count // len(engines) + (1 if i < count % len(engines) else 0)
            for i, name in enumerate(engines)
        }

        def work() -> None:
            errors = []
            for name in engines:
                try:
                    from brain.pick_candidates import run_pick

                    picks = run_pick(engine=name, brief=brief, count=engine_counts[name], pool=pool)
                    result = {"brief": brief, "engine": name, "pool": pool, "picks": picks}
                    self.brain_state["results"][name] = result
                    BRAIN_CACHE[name].write_text(json.dumps(result, indent=1) + "\n")
                except Exception as error:  # surfaced in the local UI
                    errors.append(f"{name}: {error}")
            self.brain_state.update(running=0, error="; ".join(errors) or None)

        self.brain_thread = threading.Thread(target=work, daemon=True)
        self.brain_thread.start()
        return self.brain_status()

    def directives_status(self) -> dict:
        return dict(self.directives_state)

    def ask_directives(self, brief: str, engine: str) -> dict:
        """Interpret a free-text DJ instruction into dj_notes edits + a
        possible reorder — brain.mix_directives, run in the background since
        the LLM call can take a while. Only builds a preview; nothing is
        written until apply_directives() confirms it."""
        from brain.pick_candidates import ENGINES

        if engine not in ENGINES and engine != "h-agent":
            raise ValueError(f"unknown engine {engine!r}")
        if not brief.strip():
            raise ValueError("brief is empty — say what you want changed")
        if self.directives_thread and self.directives_thread.is_alive():
            return self.directives_status()
        self.directives_state = {"running": 1, "error": None, "preview": None,
                                 "brief": brief, "engine": engine}

        def work() -> None:
            try:
                from brain.mix_directives import build_prompt, load_playlist, parse_directives
                from brain.pick_candidates import ask_h_agent
                from brain.library_index import current_index_path

                tracks = load_playlist(DEFAULT_PLAYLIST_JSON)
                prompt = build_prompt(tracks, brief, current_index_path())
                reply = ask_h_agent(prompt) if engine == "h-agent" else ENGINES[engine](prompt)
                notes, reorder = parse_directives(reply, tracks)
                by_id = {t["track_id"]: t for t in tracks}
                preview = {
                    "notes": [
                        {"track_id": tid, "artist": by_id[tid]["artist"], "title": by_id[tid]["title"],
                         "old": by_id[tid].get("dj_notes") or "", "new": note}
                        for tid, note in notes.items()
                    ],
                    "reorder": [
                        {"track_id": tid, "artist": by_id[tid]["artist"], "title": by_id[tid]["title"]}
                        for tid in reorder
                    ] if reorder else None,
                }
                self.directives_state.update(running=0, error=None, preview=preview)
            except Exception as error:  # surfaced in the local UI
                self.directives_state.update(running=0, error=str(error), preview=None)

        self.directives_thread = threading.Thread(target=work, daemon=True)
        self.directives_thread.start()
        return self.directives_status()

    def apply_directives(self) -> dict:
        """Commit the last preview: write dj_notes to SQLite + playlist.json,
        and reorder playlist.json/playlist_selection.json if requested."""
        preview = self.directives_state.get("preview")
        if not preview:
            raise ValueError("nothing to apply — ask the brain for edits first")
        from brain.mix_directives import apply_directives as write_directives, load_playlist

        tracks = load_playlist(DEFAULT_PLAYLIST_JSON)
        notes = {row["track_id"]: row["new"] for row in preview.get("notes") or []}
        reorder = [row["track_id"] for row in preview["reorder"]] if preview.get("reorder") else None
        write_directives(tracks, notes, reorder)
        self.reload()
        self.mix_state["summary"] = None  # plan is stale relative to the new notes/order
        self.directives_state["preview"] = None
        return {
            "applied_notes": len(notes),
            "applied_reorder": bool(reorder),
            "finalized": self.finalized_snapshot(),
        }

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
        self._save_selection_compatible()
        self._save_exclusions_compatible()
        return {"added": added, "unknown": unknown, "selected_count": len(self.selection)}

    def clear_selection(self, *, archive: bool = True, label: str | None = None) -> dict:
        """Empty the enabled set to start a new mix from scratch.

        Archives the current playlist.json + mix_plan.json first by
        default (best-effort — skipped, not failed, if nothing's been
        finalized/built yet) so the outgoing mix isn't lost. Leaves
        playlist_exclusions.json alone; that's a separate durable opinion
        about specific tracks, not part of "what's currently enabled".
        """
        archived_path = None
        if archive:
            from brain.archive_mix_plan import archive_mix_plan

            try:
                archived_path = str(
                    archive_mix_plan(label=label or "before-clear")
                )
            except FileNotFoundError:
                pass
        cleared_count = len(self.selection)
        self.selection = []
        self.selected = set()
        self._save_selection_compatible()
        return {
            "archived_path": archived_path,
            "cleared_count": cleared_count,
            "selected_count": 0,
        }

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
                if query in f"{track.artist} {track.title} {track.album or ''} {track.track_id}".casefold()
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
        self._save_selection_compatible()
        self._save_exclusions_compatible()

    def add_seed(self) -> dict:
        matches = match_seed(self.tracks, load_seed())
        for match in matches:
            if match.track and match.track.track_id in self.excluded:
                continue
            if match.track and match.track.track_id not in self.selected:
                self.selection.append(match.track.track_id)
                self.selected.add(match.track.track_id)
        self._save_selection_compatible()
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
        self._save_selection_compatible()
        report = transition_report(ordered, lineage=lineage)
        mean = sum(row["score"] for row in report) / len(report) if report else 0.0
        return {
            "count": len(ordered),
            "mean_score": round(mean, 3),
            "lineage_edges": len(lineage),
            "message": f"reordered {len(ordered)} user-enabled tracks for mix flow (mean transition {mean:.2f})",
        }

    def export(self) -> dict:
        selected = self._export_playlist_compatible()
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

    def finalized_snapshot(self, slug: str | None = None) -> dict | None:
        """What Finalize last wrote — the source of truth for Create the mix."""
        playlist_path = self._playlist_path(slug)
        if not playlist_path.exists():
            return None
        try:
            rows = json.loads(playlist_path.read_text())
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
            "path": str(playlist_path),
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

    def _load_plan_summary(self, slug: str | None = None) -> dict | None:
        mix_plan_path = self._mix_plan_path(slug)
        if not mix_plan_path.exists():
            return None
        from brain.build_mix_plan import plan_summary

        plan = json.loads(mix_plan_path.read_text())
        return plan_summary(plan, plan_path=mix_plan_path)

    def reexport_finalized(self, slug: str | None = None) -> dict:
        """Rewrite playlist.json from current selection + latest crate bpm/key.

        Call after sync_mixxx_analysis or enrich so Create the mix sees new
        metadata without requiring another manual Finalize click.
        """
        self.reload()
        paths = self._scoped_paths(slug)
        selection = self.selection
        if paths:
            selection = load_selection(paths.selection)
        if not selection:
            # Fall back to whatever is already on disk (ids may have dropped).
            if self._playlist_path(slug).exists():
                return self.finalized_snapshot(slug) or {"count": 0}
            raise ValueError("nothing selected to re-export")
        if paths:
            selected = export_playlist(
                self.tracks,
                selection,
                json_path=paths.playlist,
                m3u_path=paths.root / "playlist.m3u8",
            )
        else:
            selected = export_playlist(self.tracks, selection)
        self.mix_state["summary"] = None  # plan may now be stale relative to new analysis
        return {
            "count": len(selected),
            "analyzed_count": sum(1 for t in selected if t.bpm),
            "finalized": self.finalized_snapshot(slug),
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
        self._save_selection_compatible()
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
        self._save_selection_compatible()
        if self.tracks:
            self._export_playlist_compatible()
        else:
            export_playlist(ordered, self.selection)
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

    def set_control_port(self, port: int, *, slug: str | None = None) -> dict:
        if not 1 <= int(port) <= 65535:
            raise ValueError(f"invalid Mixxx control port {port}")
        self.control_port_override = int(port)
        self.explicit_control_port = True
        self.mix_state["mixxx_control_port"] = int(port)
        self._persist_control_port(int(port), slug)
        return self.mix_status()

    def start_enrich(self, *, port: int | None = None, slug: str | None = None) -> dict:
        """Background: analyze missing bpm/key via Mixxx control API + lyrics/chroma/phrases."""
        if port is not None:
            self.control_port_override = int(port)
            self.explicit_control_port = True
        port = int(port if port is not None else self.mix_state["mixxx_control_port"])
        self.mix_state["mixxx_control_port"] = port
        self._persist_control_port(port, slug)
        playlist_path = self._playlist_path(slug)
        if self.enrich_thread and self.enrich_thread.is_alive():
            return self.mix_status()
        if self.mix_thread and self.mix_thread.is_alive():
            raise ValueError("mix plan is building — wait before enriching")
        if self.mix_run_thread and self.mix_run_thread.is_alive():
            raise ValueError("live mix is running — stop before enriching")
        if not playlist_path.exists():
            raise ValueError("no finalized playlist — Finalize for Mixxx first")

        # Ensure playlist.json matches current selection before enriching.
        if self._scoped_paths(slug):
            self.reexport_finalized(slug)
        elif self.selection:
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

                    gaps = enrichment_status(playlist_path)
                    need_bpm = (gaps.get("missing") or {}).get("bpm_key", 0)
                    if need_bpm:
                        raise ValueError(
                            f"Mixxx control API not reachable on port {port} "
                            f"({error}); need it to analyze {need_bpm} track(s) "
                            "missing BPM/key. Launch: open -a Mixxx --args "
                            f"--control-api-port {port}"
                        ) from error
                    progress(
                        f"Mixxx API down ({error}); skipping bpm analysis — "
                        "filling lyrics/chroma/phrases only."
                    )
                    report = run_enrich(
                        playlist_path=playlist_path,
                        port=port,
                        skip_bpm=True,
                        progress=progress,
                    )
                else:
                    report = run_enrich(
                        playlist_path=playlist_path,
                        port=port,
                        progress=progress,
                    )

                self.reexport_finalized(slug)
                from brain.enrich_set import enrichment_status

                status = enrichment_status(playlist_path)
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
        from brain.dj_formats import visible_formats
        from brain.mix_profiles import PROFILES

        status = dict(self.mix_state)
        active_slug = self._active_slug()
        if not status.get("summary"):
            try:
                status["summary"] = self._load_plan_summary(active_slug)
            except Exception as error:  # surface corrupt plan without crashing the UI
                status["error"] = status.get("error") or f"could not read existing plan: {error}"
        summary_port = (status.get("summary") or {}).get("mixxx_control_port")
        if self.control_port_override is not None:
            status["mixxx_control_port"] = self.control_port_override
        elif summary_port is not None:
            status["mixxx_control_port"] = int(summary_port)
            self.mix_state["mixxx_control_port"] = int(summary_port)
        # Build-control default is always "none" (No expert format). Do not
        # restore the last on-disk plan's format into the dropdown — ear tests
        # preferred plain none, and experimental formats must stay opt-in.
        if not status.get("dj_format"):
            status["dj_format"] = "none"
        finalized = self.finalized_snapshot(active_slug)
        status["finalized"] = finalized
        status["profiles"] = [
            {"name": name, "description": profile.description}
            for name, profile in PROFILES.items()
        ]
        status["dj_formats"] = [
            {
                "name": name,
                "label": dj_format.label,
                "description": dj_format.description,
                "strict": dj_format.strict,
                "status": dj_format.status,
                "enforcement": (
                    "strict"
                    if dj_format.strict
                    else ("guided" if dj_format.planner else "off")
                ),
            }
            for name, dj_format in visible_formats().items()
        ]
        if active_slug:
            from brain.plan_staleness import is_stale
            stale = is_stale(active_slug)["stale"]
        else:
            stale = self._plan_stale(status.get("summary"), finalized)
        status["plan_ready"] = bool(status.get("summary")) and not stale
        status["plan_stale"] = stale
        status["playlist_ready"] = finalized is not None and (finalized.get("count") or 0) >= 2
        try:
            from brain.enrich_set import enrichment_status

            status["enrichment"] = enrichment_status(self._playlist_path(active_slug))
        except Exception as error:
            status["enrichment"] = {"ready": False, "error": str(error)}
        return status

    def build_mix(
        self,
        profile: str,
        mix_brief: str,
        tracks: int | None = None,
        order_engine: str = "nemoclaw",
        dj_format: str = "none",
        slug: str | None = None,
    ) -> dict:
        """Build a mix plan in the background (profile + DJ format + brief).

        Mirrors `brain.build_mix_plan --profile … --mix-brief … --order-engine …`.
        When the brief mentions pairings / placement / a short subset and
        order_engine is nemoclaw or h-agent, the agent shapes the order first.
        """
        from brain.dj_formats import FORMATS
        from brain.mix_profiles import PROFILES

        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile!r}; choose from {sorted(PROFILES)}")
        if dj_format not in FORMATS:
            raise ValueError(
                f"unknown DJ format {dj_format!r}; choose from {sorted(FORMATS)}"
            )
        if order_engine not in ("none", "nemoclaw", "h-agent"):
            raise ValueError(f"unknown order engine {order_engine!r}")
        if self.mix_thread and self.mix_thread.is_alive():
            return self.mix_status()
        if self.mix_run_thread and self.mix_run_thread.is_alive():
            raise ValueError("a live mix is already running — stop it before rebuilding the plan")
        playlist_path = self._playlist_path(slug)
        mix_plan_path = self._mix_plan_path(slug)
        chosen_slug = slug or self._active_slug()
        if not playlist_path.exists():
            raise ValueError("no finalized playlist yet — click Finalize for Mixxx first")

        # Feel-only briefs don't need a slow agent call.
        engine = order_engine
        if not (mix_brief or "").strip():
            engine = "none"

        if self.enrich_thread and self.enrich_thread.is_alive():
            raise ValueError("enrichment is still running — wait before building the plan")

        # Rebuilding overwrites mix_plan.json in place — archive whatever's
        # there first (best-effort) so a plan that was actually played/
        # recorded is never silently lost to the next build. Mirrors
        # clear_selection's existing archive-before-destroy pattern.
        if mix_plan_path.exists() and chosen_slug is None:
            from brain.archive_mix_plan import archive_mix_plan

            try:
                prev_format = "none"
                try:
                    prev_format = (
                        json.loads(mix_plan_path.read_text())
                        .get("dj_format", {})
                        .get("name", "none")
                    )
                except Exception:
                    pass
                archive_mix_plan(label=f"auto-before-rebuild-{prev_format}")
            except FileNotFoundError:
                pass

        self.mix_state = {
            "building": 1,
            "running": 0,
            "enriching": 0,
            "error": None,
            "profile": profile,
            "dj_format": dj_format,
            "mix_brief": mix_brief,
            "order_engine": engine,
            "summary": None,
            "live_error": None,
            "live_message": None,
            "enrich_message": self.mix_state.get("enrich_message"),
            "enrich_error": self.mix_state.get("enrich_error"),
            "enrich_report": self.mix_state.get("enrich_report"),
            "enrich_log": self.mix_state.get("enrich_log") or [],
            "mixxx_control_port": self.mix_state.get("mixxx_control_port", 9995),
        }

        def work() -> None:
            try:
                from brain.build_mix_plan import compose_mix_plan, plan_summary
                if chosen_slug:
                    from brain.plan_mix_build import build
                    plan = build(
                        chosen_slug,
                        profile=profile,
                        dj_format=dj_format,
                        mix_brief=mix_brief or "",
                        order_engine=engine,
                        tracks=tracks,
                        control_port=int(self.mix_state["mixxx_control_port"]),
                    )
                else:
                    plan = compose_mix_plan(
                        playlist=playlist_path,
                        profile_name=profile,
                        dj_format_name=dj_format,
                        mix_brief=mix_brief or "",
                        order_engine=engine,
                        tracks=tracks,
                        out=mix_plan_path,
                        control_port=int(self.mix_state["mixxx_control_port"]),
                    )
                self._persist_control_port(int(self.mix_state["mixxx_control_port"]), chosen_slug)
                summary = plan_summary(plan, plan_path=mix_plan_path)
                self.mix_state.update(
                    building=0,
                    error=None,
                    summary=summary,
                    profile=profile,
                    dj_format=dj_format,
                    mix_brief=mix_brief,
                    order_engine=engine,
                )
            except Exception as error:  # surfaced in the local UI
                self.mix_state.update(building=0, error=str(error), summary=None)

        self.mix_thread = threading.Thread(target=work, daemon=True)
        self.mix_thread.start()
        return self.mix_status()

    def start_mix(self, *, confirm: bool, port: int | None = None, slug: str | None = None) -> dict:
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
        mix_plan_path = self._mix_plan_path(slug)
        if not mix_plan_path.exists():
            raise ValueError("no mix plan yet — build one first")

        plan = json.loads(mix_plan_path.read_text())
        preserved_port = (plan.get("runtime") or {}).get("mixxx_control_port")
        port = int(
            port
            if port is not None
            else self.control_port_override
            if self.control_port_override is not None
            else preserved_port
            if preserved_port is not None
            else self.mix_state["mixxx_control_port"]
        )
        if port is not None:
            self.control_port_override = port
            self.explicit_control_port = True
        self.mix_state["mixxx_control_port"] = port
        self._persist_control_port(port, slug)

        from hands.mixxx_control import MixxxControl, MixxxControlError

        try:
            with MixxxControl(port=port, timeout_s=2.0) as mixxx:
                if not mixxx.ping():
                    raise MixxxControlError("Mixxx control API did not pong")
        except Exception as error:
            raise ValueError(
                f"Mixxx control API not reachable on port {port}: {error}. "
                f"Launch with: open -a Mixxx --args --control-api-port {port}"
            ) from error

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
    from brain import api_router, plan_paths
    from brain.api import (
        api_collections,
        api_bunch_item,
        api_bunches_collection,
        api_plan_arrange,
        api_plan_bunches,
        api_plan_detail,
        api_plan_duplicate,
        api_plan_journal,
        api_plan_notes,
        api_plan_order,
        api_plan_tracks,
        api_plan_transitions,
        api_plans_active,
        api_plans_collection,
        api_static_assets,
    )

    api_router.clear()
    route_modules = (
        api_static_assets, api_collections, api_plans_collection, api_plans_active, api_plan_detail,
        api_plan_duplicate, api_plan_journal, api_plan_arrange, api_plan_order,
        api_plan_tracks, api_plan_notes, api_plan_transitions, api_plan_bunches,
        api_bunches_collection, api_bunch_item,
    )
    for module in route_modules:
        api_router.register(module.PATTERN, module.METHODS, module.handle)
    legacy_methods = {
        "/api/meta": ("GET",), "/api/tracks": ("GET",), "/api/ingest": ("GET",),
        "/api/brain": ("GET",), "/api/directives": ("GET",), "/api/mix": ("GET",),
        "/api/preview": ("GET", "HEAD"),
        "/api/selection": ("POST",), "/api/selection/clear": ("POST",),
        "/api/seed": ("POST",), "/api/mix-order": ("POST",), "/api/export": ("POST",),
        "/api/ingest/scan": ("POST",), "/api/ingest/add-root": ("POST",),
        "/api/brain/ask": ("POST",), "/api/brain/apply": ("POST",),
        "/api/directives/ask": ("POST",), "/api/directives/apply": ("POST",),
        "/api/suggest": ("POST",), "/api/mix/build": ("POST",),
        "/api/mix/start": ("POST",), "/api/mix/sync": ("POST",),
        "/api/mix/enrich": ("POST",), "/api/mix/control-port": ("POST",),
        "/api/mix/refresh": ("POST",), "/api/mix/rescan-tags": ("POST",),
        "/api/mix/shuffle-opener": ("POST",),
    }

    def legacy_route(*args, **kwargs):
        raise AssertionError("legacy routes are dispatched by PlaylistApp")

    for pattern, methods in legacy_methods.items():
        api_router.register(pattern, methods, legacy_route)

    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK, headers=None) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            for name, value in (headers or {}).items():
                self.send_header(name, str(value))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def _dispatch_plan_route(self, method: str, parsed, body=None) -> bool:
            from brain.api.common import ApiError
            try:
                handler, params = api_router.route(method, parsed.path)
            except api_router.NotFound:
                return False
            except api_router.MethodNotAllowed as error:
                self._json({"error": "method_not_allowed", "message": str(error)}, HTTPStatus.METHOD_NOT_ALLOWED, error.headers)
                return True
            if handler is legacy_route:
                return False
            try:
                result = api_router.invoke(
                    handler, app, params, method, body or {}, parse_qs(parsed.query), self.headers
                )
                if len(result) == 2:
                    payload, status = result
                    response_headers = {}
                else:
                    payload, status, response_headers = result
                if isinstance(payload, bytes):
                    self.send_response(status)
                    for name, value in response_headers.items():
                        self.send_header(name, str(value))
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    if status != HTTPStatus.NOT_MODIFIED:
                        self.wfile.write(payload)
                else:
                    self._json(payload, status, response_headers)
            except ApiError as error:
                self._json(error.payload, error.status)
            except collection_registry.CollectionUnavailable as error:
                logging.getLogger(__name__).warning("%s", error)
                self._json({"error": "collection_unavailable", "message": str(error)}, HTTPStatus.SERVICE_UNAVAILABLE)
            except (plan_paths.PlanNotFound, KeyError) as error:
                self._json({"error": "not_found", "message": str(error)}, HTTPStatus.NOT_FOUND)
            except (ValueError, json.JSONDecodeError) as error:
                self._json({"error": "bad_request", "message": str(error)}, HTTPStatus.BAD_REQUEST)
            return True

        def _send_preview(self, parsed) -> None:
            params = parse_qs(parsed.query)
            track_id = (params.get("track_id") or [""])[0]
            try:
                path = resolve_preview_path(app.by_id, track_id)
                size = path.stat().st_size
                start, end, partial = parse_byte_range(self.headers.get("Range"), size)
            except PreviewError as error:
                status = HTTPStatus(error.status)
                if error.status == 416:
                    self.send_response(status)
                    self.send_header("Content-Range", "bytes */0")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self._json({"error": error.code, "message": error.message}, status)
                return
            length = end - start + 1
            status = HTTPStatus.PARTIAL_CONTENT if partial else HTTPStatus.OK
            self.send_response(status)
            self.send_header("Content-Type", content_type(path))
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "private, max-age=0")
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if self.command == "HEAD":
                return
            with path.open("rb") as handle:
                handle.seek(start)
                remaining = length
                while remaining:
                    chunk = handle.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def do_HEAD(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/preview":
                self._send_preview(parsed)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if self._dispatch_plan_route("GET", parsed):
                return
            if parsed.path == "/api/preview":
                self._send_preview(parsed)
                return
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
            if parsed.path == "/api/directives":
                self._json(app.directives_status())
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
                parsed = urlparse(self.path)
                try:
                    candidate, _ = api_router.route("POST", parsed.path)
                except api_router.NotFound:
                    candidate = None
                except api_router.MethodNotAllowed as error:
                    self._json({"error": "method_not_allowed", "message": str(error)}, HTTPStatus.METHOD_NOT_ALLOWED, error.headers)
                    return
                if candidate is not None and candidate is not legacy_route:
                    payload = self._body()
                    if self._dispatch_plan_route("POST", parsed, payload):
                        return
                if self.path == "/api/selection":
                    payload = self._body()
                    app.set_enabled(payload["track_id"], bool(payload["enabled"]))
                    self._json(app.metadata())
                    return
                if self.path == "/api/selection/clear":
                    payload = self._body()
                    self._json(
                        app.clear_selection(
                            archive=bool(payload.get("archive", True)),
                            label=payload.get("label"),
                        )
                    )
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
                if self.path == "/api/ingest/add-root":
                    payload = self._body()
                    self._json(app.start_scan(extra_root=str(payload.get("path", ""))), HTTPStatus.ACCEPTED)
                    return
                if self.path == "/api/brain/ask":
                    payload = self._body()
                    self._json(
                        app.ask_brain(
                            str(payload.get("brief", "")),
                            str(payload.get("engine", "nemoclaw")),
                            int(payload.get("count", 20)),
                            str(payload.get("pool", "library")),
                        ),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/brain/apply":
                    payload = self._body()
                    self._json(app.apply_picks(list(payload.get("track_ids", []))))
                    return
                if self.path == "/api/directives/ask":
                    payload = self._body()
                    self._json(
                        app.ask_directives(
                            str(payload.get("brief", "")),
                            str(payload.get("engine", "nemoclaw")),
                        ),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/directives/apply":
                    self._json(app.apply_directives())
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
                            str(payload.get("dj_format", "none")),
                            slug=str(payload["plan"]) if payload.get("plan") else None,
                        ),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/mix/start":
                    payload = self._body()
                    raw_port = payload.get("port")
                    self._json(
                        app.start_mix(
                            confirm=bool(payload.get("confirm")),
                            port=int(raw_port) if raw_port is not None else None,
                            slug=str(payload["plan"]) if payload.get("plan") else None,
                        ),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/mix/sync":
                    self._json(app.sync_from_mixxx())
                    return
                if self.path == "/api/mix/enrich":
                    payload = self._body()
                    raw_port = payload.get("port")
                    self._json(
                        app.start_enrich(
                            port=int(raw_port) if raw_port is not None else None,
                            slug=str(payload["plan"]) if payload.get("plan") else None,
                        ),
                        HTTPStatus.ACCEPTED,
                    )
                    return
                if self.path == "/api/mix/control-port":
                    payload = self._body()
                    self._json(app.set_control_port(int(payload["port"]), slug=str(payload["plan"]) if payload.get("plan") else None))
                    return
                if self.path == "/api/mix/refresh":
                    payload = self._body()
                    self._json(app.reexport_finalized(slug=str(payload["plan"]) if payload.get("plan") else None))
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

        def _unsupported(self, method: str) -> None:
            parsed = urlparse(self.path)
            if self._dispatch_plan_route(method, parsed):
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_DELETE(self) -> None:  # noqa: N802
            self._unsupported("DELETE")

        def do_PUT(self) -> None:  # noqa: N802
            self._unsupported("PUT")

        def do_PATCH(self) -> None:  # noqa: N802
            self._unsupported("PATCH")

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument(
        "--mixxx-control-port",
        type=int,
        default=(
            int(os.environ["CLAWDJ_MIXXX_CONTROL_PORT"])
            if os.environ.get("CLAWDJ_MIXXX_CONTROL_PORT")
            else None
        ),
        help="effective validated Mixxx control API port shared by all editor actions",
    )
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args()

    bootstrap = ensure_plan_workspace()
    app = PlaylistApp(control_port=args.mixxx_control_port)
    active = app._active_slug()
    if args.mixxx_control_port is None and active:
        persisted_port = app.load_plan_control_port(active)
        if persisted_port is not None:
            app.control_port_override = persisted_port
            app.explicit_control_port = False
            app.mix_state["mixxx_control_port"] = persisted_port
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    url = f"http://{args.host}:{args.port}"
    print(
        f"playlist editor: {url} ({len(app.tracks)} tracks, {len(app.selection)} selected; "
        f"Mixxx control port {app.mix_state['mixxx_control_port']}; plan {bootstrap.get('slug')})"
    )
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
