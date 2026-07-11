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
from brain.playlist import export_playlist, load_seed, load_selection, match_seed, save_selection, track_record

WEB_ROOT = Path(__file__).parent / "web"


class PlaylistApp:
    def __init__(self) -> None:
        self.tracks = load_crate()
        self.by_id = {track.track_id: track for track in self.tracks}
        self.selection = [track_id for track_id in load_selection() if track_id in self.by_id]
        self.selected = set(self.selection)

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
        if enabled and track_id not in self.selected:
            self.selection.append(track_id)
            self.selected.add(track_id)
        elif not enabled and track_id in self.selected:
            self.selection.remove(track_id)
            self.selected.remove(track_id)
        save_selection(self.selection)

    def add_seed(self) -> dict:
        matches = match_seed(self.tracks, load_seed())
        for match in matches:
            if match.track and match.track.track_id not in self.selected:
                self.selection.append(match.track.track_id)
                self.selected.add(match.track.track_id)
        save_selection(self.selection)
        return {
            "matched": sum(match.track is not None for match in matches),
            "unmatched": [f"{match.artist} - {match.title}" for match in matches if match.track is None],
            "selected_count": len(self.selection),
        }

    def export(self) -> dict:
        selected = export_playlist(self.tracks, self.selection)
        return {"count": len(selected), "json": "brain/data/playlist.json", "m3u": "brain/data/playlist.m3u8"}


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
                if self.path == "/api/export":
                    self._json(app.export())
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
