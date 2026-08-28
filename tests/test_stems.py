"""Vocals-only / instrumental-only stem pairing."""
from __future__ import annotations

from unittest import TestCase

from brain.stems import apply_vocal_layers, classify_stem, pair_vocals


class ClassifyStemTests(TestCase):
    def test_acapella_is_vocals_only_vocal_remix_is_not(self) -> None:
        self.assertEqual(
            classify_stem("Get Up (Acapella)", "/x/04 - 50 Cent - Get Up (Acapella).mp3"),
            "vocals_only",
        )
        self.assertEqual(
            classify_stem("Jimmy Crack Corn (Vocal Remix)", "/x/vocal-remix.mp3"),
            "full_mix",
        )
        self.assertEqual(
            classify_stem(
                "Jimmy Crack Corn (Vocal Remix) (Feat. Cashis) (Acapella)",
                "/x/a.mp3",
            ),
            "vocals_only",
        )

    def test_dashed_instrumental_title_is_a_stem(self) -> None:
        self.assertEqual(
            classify_stem("Outta Control - Instrumental", "/x/outta.mp3"),
            "instrumental_only",
        )
        self.assertEqual(
            classify_stem("Get Up (Instrumental)", "/x/get-up-inst.mp3"),
            "instrumental_only",
        )


class PairVocalsTests(TestCase):
    def test_neighbor_instrumental_wins_over_a_distant_mash(self) -> None:
        tracks = [
            {
                "track_id": "/jcc-inst",
                "title": "Jimmy Crack Corn (Vocal Remix) (Instrumental)",
                "bpm": 95.86,
                "key": "Fm",
                "dj_notes": "",
            },
            {
                "track_id": "/jcc-acapella",
                "title": "Jimmy Crack Corn (Vocal Remix) (Feat. Cashis) (Acapella)",
                "bpm": 97.0,
                "key": "Fm",
                "dj_notes": "",
            },
            {
                "track_id": "/jcc-full",
                "title": "Eminem & 50 Cent - Jimmy Crack Corn",
                "bpm": 95.86,
                "key": "Fm",
                "dj_notes": "",
            },
            {
                "track_id": "/hands-up-inst",
                "title": "Hands Up (Instrumental)",
                "bpm": 95.0,
                "key": "Fm",
                "dj_notes": "",
            },
        ]
        report = pair_vocals(tracks)
        self.assertEqual(report["pairs"][0]["bed_id"], "/jcc-inst")

    def test_get_up_prefers_adjacent_different_song_instrumental(self) -> None:
        tracks = [
            {"track_id": "/best-friend", "title": "Best Friend", "bpm": 90.8, "key": "Db", "dj_notes": ""},
            {"track_id": "/get-up-acapella", "title": "Get Up (Acapella)", "bpm": 186.0, "key": "F#", "dj_notes": ""},
            {"track_id": "/outta-inst", "title": "Outta Control - Instrumental", "bpm": 92.0, "key": "Ebm", "dj_notes": ""},
            {"track_id": "/get-up-inst", "title": "Get Up (Instrumental)", "bpm": 93.0, "key": "F#", "dj_notes": ""},
        ]
        report = pair_vocals(tracks)
        self.assertEqual(len(report["pairs"]), 1)
        self.assertEqual(report["pairs"][0]["vocal_id"], "/get-up-acapella")
        self.assertEqual(report["pairs"][0]["bed_id"], "/outta-inst")
        self.assertFalse(report["pairs"][0]["same_song"])
        self.assertFalse(report["pairs"][0]["loop_bed"])

    def test_showcase_acapella_is_not_paired(self) -> None:
        tracks = [
            {
                "track_id": "/banks",
                "title": "On Fire (Acapella)",
                "bpm": 94.0,
                "key": "F#m",
                "dj_notes": "showcase_acapella",
            },
            {"track_id": "/inst", "title": "On Fire (Instrumental)", "bpm": 94.0, "key": "F#m", "dj_notes": ""},
        ]
        self.assertEqual(pair_vocals(tracks)["pairs"], [])

    def test_apply_vocal_layers_moves_bed_immediately_before_vocal(self) -> None:
        tracks = [
            {"track_id": "/best-friend", "title": "Best Friend", "artist": "50 Cent", "bpm": 90.8, "key": "Db", "dj_notes": ""},
            {"track_id": "/get-up-acapella", "title": "Get Up (Acapella)", "artist": "50 Cent", "bpm": 186.0, "key": "F#", "dj_notes": "Short acapella break. ride_beats=32; trust_ride_beats"},
            {"track_id": "/outta-inst", "title": "Outta Control - Instrumental", "artist": "50 Cent", "bpm": 92.0, "key": "Ebm", "dj_notes": ""},
        ]
        layered, notes = apply_vocal_layers(tracks)
        ids = [row["track_id"] for row in layered]
        self.assertEqual(ids, ["/best-friend", "/outta-inst", "/get-up-acapella"])
        vocal = layered[2]
        self.assertIn("vocal_over_bed", vocal["dj_notes"])
        self.assertIn("ride_beats=96", vocal["dj_notes"])
        self.assertTrue(any("Get Up" in item for item in notes))

    def test_key_clash_does_not_beat_same_song_instrumental(self) -> None:
        tracks = [
            {
                "track_id": "/cream-acapella",
                "title": "C.R.E.A.M. (A Cappella)",
                "bpm": 141.0,
                "key": "Ab",
                "dj_notes": "",
            },
            {
                "track_id": "/cream-inst",
                "title": "C.R.E.A.M. (Instrumental)",
                "bpm": 93.0,
                "key": "Ab",
                "dj_notes": "",
            },
            {
                "track_id": "/patiently-inst",
                "title": "Patiently Waiting (Instrumental)",
                "bpm": 79.0,
                "key": "Bm",
                "dj_notes": "",
            },
        ]
        report = pair_vocals(tracks)
        self.assertEqual(report["pairs"][0]["bed_id"], "/cream-inst")

    def test_already_layered_neighbor_is_not_stolen(self) -> None:
        tracks = [
            {
                "track_id": "/jcc-inst",
                "title": "Jimmy Crack Corn (Vocal Remix) (Instrumental)",
                "bpm": 95.86,
                "key": "Fm",
                "dj_notes": "",
            },
            {
                "track_id": "/jcc-acapella",
                "title": "Jimmy Crack Corn (Vocal Remix) (Feat. Cashis) (Acapella)",
                "bpm": 97.0,
                "key": "Fm",
                "dj_notes": "entry_style=vocal_over_bed; ride_beats=96",
            },
            {
                "track_id": "/ydk-acapella",
                "title": "You Don't Know [Acapella]",
                "bpm": 85.7,
                "key": "Ab",
                "dj_notes": "",
            },
            {
                "track_id": "/ydk-inst",
                "title": "You Don't Know [Instrumental]",
                "bpm": 85.7,
                "key": "Ab",
                "dj_notes": "",
            },
        ]
        report = pair_vocals(tracks)
        beds = {pair["vocal_id"]: pair["bed_id"] for pair in report["pairs"]}
        self.assertEqual(beds["/jcc-acapella"], "/jcc-inst")
        self.assertEqual(beds["/ydk-acapella"], "/ydk-inst")

    def test_already_noted_vocal_still_moves_onto_its_bed(self) -> None:
        tracks = [
            {
                "track_id": "/still-kill-inst",
                "title": "I'll Still Kill (Instrumental)",
                "bpm": 88.0,
                "key": "Dm",
                "dj_notes": "",
            },
            {
                "track_id": "/still-kill-acapella",
                "title": "I'll Still Kill (Acappella)",
                "bpm": 110.0,
                "key": "F",
                "dj_notes": "entry_style=vocal_over_bed; ride_beats=192",
            },
        ]
        report = pair_vocals(tracks)
        self.assertEqual(len(report["pairs"]), 1)
        self.assertEqual(report["pairs"][0]["bed_id"], "/still-kill-inst")
        layered, _ = apply_vocal_layers(tracks)
        self.assertIn("ride_beats=192", layered[1]["dj_notes"])

    def test_get_up_with_notes_still_moves_outta_control_in_front(self) -> None:
        tracks = [
            {"track_id": "/best-friend", "title": "Best Friend", "artist": "50 Cent", "bpm": 90.8, "key": "Db", "dj_notes": ""},
            {
                "track_id": "/get-up-acapella",
                "title": "Get Up (Acapella)",
                "artist": "50 Cent",
                "bpm": 186.0,
                "key": "F#",
                "dj_notes": "entry_style=vocal_over_bed; ride_beats=96; trust_ride_beats; no_flourish",
            },
            {
                "track_id": "/outta-inst",
                "title": "Outta Control - Instrumental",
                "artist": "50 Cent",
                "bpm": 92.0,
                "key": "Ebm",
                "dj_notes": "",
            },
        ]
        layered, _ = apply_vocal_layers(tracks)
        self.assertEqual(
            [row["track_id"] for row in layered],
            ["/best-friend", "/outta-inst", "/get-up-acapella"],
        )

    def test_unpaired_vocal_fails_the_layer_step(self) -> None:
        tracks = [
            {
                "track_id": "/get-up-acapella",
                "title": "Get Up (Acapella)",
                "bpm": 186.0,
                "key": "F#",
                "dj_notes": "",
            }
        ]
        with self.assertRaisesRegex(ValueError, "no instrumental bed"):
            apply_vocal_layers(tracks)
