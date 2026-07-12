from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.catalog import agent_view, build_catalog, short_id
from brain.curate_playlist import (
    candidate_pool,
    filter_tracks,
    parse_agent_ids,
    resolve_picks,
    short_id_map_for,
)
from brain.library import Track
from brain.playlist import export_playlist, save_selection


def _tracks() -> list[Track]:
    return [
        Track("/Volumes/USB322FD/Music/RnB/Sade/Smooth Operator.mp3", "Smooth Operator", "Sade", genre="R&B", album="Diamond Life"),
        Track("/Volumes/USB322FD/Music/HipHop/Snoop/Gin And Juice.mp3", "Gin And Juice", "Snoop Doggy Dogg", genre="Hip-Hop"),
        Track("/Volumes/USB322FD/Music/HipHop/Snoop/Drop It Like It's Hot.mp3", "Drop It Like It's Hot", "Snoop Dogg", genre="Hip-Hop"),
        Track("/Volumes/USB322FD/Music/RnB/Maxwell/Pretty Wings.mp3", "Pretty Wings", "Maxwell", genre="R&B"),
        Track("/Volumes/USB322FD/Music/Rock/Foo/Bar.mp3", "Bar", "Foo", genre="Rock"),
    ]


class CatalogCurateTest(TestCase):
    def test_build_catalog_short_ids_and_agent_view_strips_paths(self) -> None:
        catalog = build_catalog(_tracks(), roots=["/Volumes/USB322FD/Music/RnB"])
        self.assertEqual(catalog["track_count"], 5)
        self.assertEqual(catalog["tracks"][0]["id"], "t00000")
        view = agent_view(catalog)
        self.assertNotIn("track_id", view["tracks"][0])
        self.assertEqual(view["tracks"][0]["artist"], "Sade")

    def test_filter_roots_and_keywords(self) -> None:
        tracks = _tracks()
        only_hiphop = filter_tracks(tracks, roots=[Path("/Volumes/USB322FD/Music/HipHop")])
        self.assertEqual(len(only_hiphop), 2)
        snoopish = filter_tracks(tracks, query="snoop")
        self.assertEqual(len(snoopish), 2)

    def test_candidate_pool_prefers_brief_hits(self) -> None:
        pool = candidate_pool(_tracks(), "west coast snoop hip-hop", limit=3)
        artists = {track.artist for track in pool}
        self.assertTrue({"Snoop Dogg", "Snoop Doggy Dogg"} & artists)

    def test_resolve_picks_short_id_path_and_artist_title(self) -> None:
        tracks = _tracks()
        pool = candidate_pool(tracks, "snoop r&b sade", limit=5)
        id_map = short_id_map_for(pool)
        first_id = next(iter(id_map))
        selected = resolve_picks(
            tracks,
            [
                first_id,
                {"artist": "Maxwell", "title": "Pretty Wings"},
                tracks[2].track_id,
            ],
            short_id_map=id_map,
        )
        self.assertGreaterEqual(len(selected), 2)
        self.assertTrue(any(track.title == "Pretty Wings" for track in selected))

    def test_parse_agent_ids_ignores_unknown(self) -> None:
        ids = parse_agent_ids(
            'Here you go: ["t00001", "t09999", "t00002"] done',
            {"t00001", "t00002"},
            count=2,
        )
        self.assertEqual(ids, ["t00001", "t00002"])

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
            self.assertNotIn("invented", text)

    def test_short_id_format(self) -> None:
        self.assertEqual(short_id(12), "t00012")
