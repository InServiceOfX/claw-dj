from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.library import Energy, Track
from brain.playlist import export_playlist, match_seed, normalize


class PlaylistTest(TestCase):
    def test_normalize_handles_punctuation_and_accents(self) -> None:
        self.assertEqual(normalize("Nite & Day!"), "nite day")
        self.assertEqual(normalize("Déjà Vu"), "deja vu")

    def test_seed_match_prefers_studio_track(self) -> None:
        tracks = [
            Track("/music/Compilations/Greatest Hits/03 Smooth Operator.mp3", "Smooth Operator", "Sade"),
            Track("/music/Albums/Diamond Life/05 Smooth Operator.mp3", "Smooth Operator", "Sade", bpm=119.0),
        ]
        matches = match_seed(tracks, [{"artist": "Sade", "title": "Smooth Operator", "source": "test"}])
        self.assertEqual(matches[0].track, tracks[1])

    def test_short_title_does_not_match_music_root(self) -> None:
        tracks = [Track("/Music/Erick Sermon/Home.mp3", "Home", "Erick Sermon")]
        matches = match_seed(tracks, [{"artist": "Erick Sermon", "title": "Music", "source": "test"}])
        self.assertIsNone(matches[0].track)

    def test_export_keeps_selection_order_and_analysis(self) -> None:
        tracks = [
            Track("/music/a.mp3", "First", "Artist", bpm=92.0, key="Cm", energy=Energy.HIGH),
            Track("/music/b.mp3", "Second", "Artist", bpm=101.5, key="Gm"),
        ]
        with TemporaryDirectory() as directory:
            json_path = Path(directory) / "set.json"
            m3u_path = Path(directory) / "set.m3u8"
            selected = export_playlist(
                tracks,
                [tracks[1].track_id, tracks[0].track_id],
                json_path=json_path,
                m3u_path=m3u_path,
            )
            self.assertEqual([track.title for track in selected], ["Second", "First"])
            self.assertIn('"bpm": 92.0', json_path.read_text())
            self.assertIn('"key": "Cm"', json_path.read_text())
            self.assertLess(m3u_path.read_text().index("/music/b.mp3"), m3u_path.read_text().index("/music/a.mp3"))
