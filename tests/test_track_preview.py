"""Preview must stream only indexed library files, without Mixxx."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
import wave
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.library import Track
from brain.playlist_editor import make_handler
from brain.track_preview import PreviewError, parse_byte_range, resolve_preview_path


def _silence_wav(path: Path, frames: int = 240) -> None:
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * frames)


class ResolvePreviewTest(TestCase):
    def test_unknown_and_relative_ids_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            audio = Path(directory) / "hit.wav"
            _silence_wav(audio)
            outsider = Path(directory) / "secret.wav"
            _silence_wav(outsider)
            track = Track(track_id=str(audio), title="Hit", artist="A")
            by_id = {track.track_id: track}
            with self.assertRaises(PreviewError) as missing:
                resolve_preview_path(by_id, str(outsider))
            self.assertEqual(missing.exception.status, 404)
            with self.assertRaises(PreviewError):
                resolve_preview_path(by_id, "hit.wav")
            with self.assertRaises(PreviewError):
                resolve_preview_path(by_id, "")

    def test_indexed_file_resolves(self) -> None:
        with TemporaryDirectory() as directory:
            audio = Path(directory) / "hit.wav"
            _silence_wav(audio)
            track = Track(track_id=str(audio), title="Hit", artist="A")
            path = resolve_preview_path({track.track_id: track}, track.track_id)
            self.assertEqual(path, audio.resolve())

    def test_range_parser(self) -> None:
        start, end, partial = parse_byte_range(None, 100)
        self.assertEqual((start, end, partial), (0, 99, False))
        start, end, partial = parse_byte_range("bytes=10-19", 100)
        self.assertEqual((start, end, partial), (10, 19, True))
        start, end, partial = parse_byte_range("bytes=90-", 100)
        self.assertEqual((start, end, partial), (90, 99, True))
        with self.assertRaises(PreviewError) as error:
            parse_byte_range("bytes=200-210", 100)
        self.assertEqual(error.exception.status, 416)


class PreviewHttpTest(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.audio = Path(self.temp.name) / "hit.wav"
        _silence_wav(self.audio, frames=400)
        track = Track(track_id=str(self.audio), title="Hit", artist="Artist")
        app = type("App", (), {"by_id": {track.track_id: track}})()
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
        except PermissionError:
            self.temp.cleanup()
            self.skipTest("execution sandbox does not permit a loopback listener")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"
        self.track_id = track.track_id

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def test_preview_streams_indexed_wav_and_rejects_strangers(self) -> None:
        query = urllib.parse.urlencode({"track_id": self.track_id})
        with urllib.request.urlopen(f"{self.base}/api/preview?{query}", timeout=2) as response:
            body = response.read()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "audio/wav")
            self.assertEqual(response.headers["Accept-Ranges"], "bytes")
            self.assertGreater(len(body), 40)
            self.assertTrue(body.startswith(b"RIFF"))

        request = urllib.request.Request(
            f"{self.base}/api/preview?{query}",
            headers={"Range": "bytes=0-15"},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(len(response.read()), 16)

        stranger = Path(self.temp.name) / "other.wav"
        _silence_wav(stranger)
        bad = urllib.parse.urlencode({"track_id": str(stranger)})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(f"{self.base}/api/preview?{bad}", timeout=2)
        self.assertEqual(error.exception.code, 404)
        payload = json.loads(error.exception.read())
        self.assertEqual(payload["error"], "unknown_track")


class PreviewUiContractTest(TestCase):
    def test_gui_has_native_player_and_preview_controls(self) -> None:
        html = (Path(__file__).parents[1] / "brain" / "web" / "playlist.html").read_text()
        self.assertIn('id="preview-audio"', html)
        self.assertIn("data-preview-id", html)
        self.assertIn("/api/preview?track_id=", html)
        self.assertNotIn("howler", html.lower())
        arrange = (Path(__file__).parents[1] / "brain" / "web" / "arrange.js").read_text()
        self.assertIn("data-preview-id", arrange)
