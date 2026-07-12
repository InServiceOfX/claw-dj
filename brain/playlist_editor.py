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
        self.mix_state: dict = {
            "building": 0,
            "running": 0,
            "error": None,
            "profile": None,
            "mix_brief": None,
            "order_engine": None,
            "summary": None,
            "live_error": None,
            "live_message": None,
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
        """
        from brain.mix_graph import lineage_pairs, load_chroma_pairs, load_lineage, pair_score

        set_tracks = [self.by_id[i] for i in self.selection if i in self.by_id]
        if not set_tracks:
            raise ValueError("enabled set is empty — nothing to blend against")
        candidates = [
            track for track in self.tracks
            if track.bpm and track.track_id not in self.selected
            and track.track_id not in self.excluded
        ]
        lineage = lineage_pairs(set_tracks + candidates, load_lineage())
        chroma = load_chroma_pairs()
        scored = []
        for candidate in candidates:
            edge, anchor = max(
                ((pair_score(anchor, candidate, lineage=lineage, chroma=chroma), anchor)
                 for anchor in set_tracks),
                key=lambda row: row[0].score,
            )
            scored.append((edge.score, candidate, anchor, edge.reasons))
        scored.sort(key=lambda row: -row[0])
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
            for i, (score, candidate, anchor, reasons) in enumerate(scored[:limit])
        ]
        return {
            "engine": "mix-graph",
            "brief": "analyzed tracks that blend with the current set",
            "candidates_considered": len(candidates),
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
        return {"count": len(selected), "json": "brain/data/playlist.json", "m3u": "brain/data/playlist.m3u8"}

    def _load_plan_summary(self) -> dict | None:
        if not MIX_PLAN_PATH.exists():
            return None
        from brain.build_mix_plan import plan_summary

        plan = json.loads(MIX_PLAN_PATH.read_text())
        return plan_summary(plan, plan_path=MIX_PLAN_PATH)

    def mix_status(self) -> dict:
        from brain.mix_profiles import PROFILES

        status = dict(self.mix_state)
        if not status.get("summary"):
            try:
                status["summary"] = self._load_plan_summary()
            except Exception as error:  # surface corrupt plan without crashing the UI
                status["error"] = status.get("error") or f"could not read existing plan: {error}"
        status["profiles"] = [
            {"name": name, "description": profile.description}
            for name, profile in PROFILES.items()
        ]
        status["plan_ready"] = bool(status.get("summary"))
        status["playlist_ready"] = DEFAULT_PLAYLIST_JSON.exists()
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

        self.mix_state = {
            "building": 1,
            "running": 0,
            "error": None,
            "profile": profile,
            "mix_brief": mix_brief,
            "order_engine": engine,
            "summary": None,
            "live_error": None,
            "live_message": None,
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
