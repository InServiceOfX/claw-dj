from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.catalog import agent_view, build_catalog, short_id
from brain.curate_playlist import all_hit_seeds, match_hits, merge_keep_user
from brain.library import Track
from brain.playlist import export_playlist, save_selection


def _tracks() -> list[Track]:
    return [
        Track(
            "/Volumes/USB322FD/Music/RnB/Sade/Smooth Operator.mp3",
            "Smooth Operator",
            "Sade",
            genre="R&B",
            album="Diamond Life",
            bpm=119.0,
            key="Am",
        ),
        Track(
            "/Volumes/USB322FD/Music/HipHop/Snoop/Gin And Juice.mp3",
            "Gin And Juice",
            "Snoop Doggy Dogg",
            genre="Hip-Hop",
            bpm=94.0,
            key="Bbm",
        ),
        Track(
            "/Volumes/USB322FD/Music/HipHop/Snoop/Drop It Like It's Hot.mp3",
            "Drop It Like It's Hot",
            "Snoop Dogg",
            genre="Hip-Hop",
            bpm=92.0,
            key="Cm",
        ),
        Track(
            "/Volumes/USB322FD/Music/RnB/Maxwell/Pretty Wings.mp3",
            "Pretty Wings",
            "Maxwell",
            genre="R&B",
        ),
    ]


class CatalogCurateTest(TestCase):
    def test_build_catalog_short_ids_and_agent_view_strips_paths(self) -> None:
        catalog = build_catalog(_tracks(), roots=["/Volumes/USB322FD/Music/RnB"])
        self.assertEqual(catalog["track_count"], 4)
        self.assertEqual(catalog["tracks"][0]["id"], "t00000")
        view = agent_view(catalog)
        self.assertNotIn("track_id", view["tracks"][0])
        self.assertEqual(view["tracks"][0]["artist"], "Sade")

    def test_hit_seeds_include_researched_and_extra_folder_hits(self) -> None:
        seeds = all_hit_seeds()
        titles = {(s["artist"].casefold(), s["title"].casefold()) for s in seeds}
        self.assertIn(("snoop dogg", "drop it like it's hot"), titles)
        self.assertIn(("da brat", "funkdafied"), titles)

    def test_match_hits_only_returns_available_crate_tracks(self) -> None:
        hits = match_hits(_tracks())
        hit_titles = {track.title for track in hits}
        self.assertIn("Gin And Juice", hit_titles)
        self.assertIn("Drop It Like It's Hot", hit_titles)
        self.assertIn("Smooth Operator", hit_titles)
        self.assertNotIn("Pretty Wings", hit_titles)

    def test_merge_keep_user_preserves_user_first(self) -> None:
        tracks = _tracks()
        hits = [tracks[0], tracks[1]]
        merged = merge_keep_user(hits, [tracks[2].track_id], tracks)
        self.assertEqual(merged[0].title, "Drop It Like It's Hot")
        self.assertEqual({t.title for t in merged}, {"Drop It Like It's Hot", "Smooth Operator", "Gin And Juice"})

    def test_export_only_available_selection(self) -> None:
        tracks = _tracks()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            selection = root / "sel.json"
            playlist = root / "pl.json"
            m3u = root / "pl.m3u8"
            ids = [tracks[1].track_id, tracks[0].track_id]
            save_selection(ids, selection)
            export_playlist(tracks, ids, json_path=playlist, m3u_path=m3u)
            text = playlist.read_text()
            self.assertIn("Gin And Juice", text)
            self.assertIn("Smooth Operator", text)

    def test_short_id_format(self) -> None:
        self.assertEqual(short_id(12), "t00012")
