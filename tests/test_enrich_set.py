"""brain.enrich_set pipeline wiring — beat_phase must run as a real step.

fill_beat_phase existed as a standalone function but was never called from
run_enrich() -- it only ever ran via ad-hoc scripts during one long session
(2026-07-19). A freshly-set-up machine running the documented enrichment
command would silently never populate beat_phase, and build_mix_plan's
snare-parity auto-correction (a real, ear-validated feature) would be
inert with no error at all. These tests pin the wiring, not the DSP
(brain.onset_analysis's own detector is covered in test_onset_analysis.py).
"""
import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from brain.library_index import connect as real_connect
from brain.enrich_set import enrichment_status, run_enrich, status


class BeatPhaseWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.index_path = Path(self._tmp.name) / "library.sqlite3"
        self.playlist_path = Path(self._tmp.name) / "playlist.json"
        self.track_id = "/music/song.mp3"
        self.playlist_path.write_text(json.dumps([
            {"track_id": self.track_id, "artist": "Artist", "title": "Song",
             "bpm": 100.0, "key": "Am", "duration_seconds": 180.0}
        ]))
        with closing(real_connect(self.index_path)) as db:
            db.execute(
                """INSERT INTO tracks
                (track_id, root, size_bytes, mtime_ns, title, artist, album,
                 genre, duration_seconds, bpm, key, energy, first_seen_at,
                 last_seen_at, available, tag_status, dj_notes)
                VALUES (?,'/music',1,1,'Song','Artist',NULL,NULL,180.0,100.0,
                        'Am',NULL,0,0,1,'ok','')""",
                (self.track_id,),
            )
            db.execute(
                "INSERT INTO phrases(track_id, analyzed_at, payload) VALUES (?,0,?)",
                (self.track_id, json.dumps({"bpm": 100.0, "first_beat_seconds": 0.2})),
            )
            db.commit()
        self._connect_patch = patch(
            "brain.enrich_set.connect", lambda *a, **k: real_connect(self.index_path)
        )
        self._connect_patch.start()
        self.addCleanup(self._connect_patch.stop)

    def test_run_enrich_calls_fill_beat_phase_and_it_lands_in_the_table(self) -> None:
        calls = []

        def fake_fill_beat_phase(db, tracks, **kwargs):
            calls.append([t["track_id"] for t in tracks])
            for t in tracks:
                db.execute(
                    "INSERT INTO beat_phase(track_id, analyzed_at, snare_parity, "
                    "confidence, bpm, first_beat_seconds) VALUES (?,0,1,0.5,100.0,0.2)",
                    (t["track_id"],),
                )
            db.commit()
            return len(tracks)

        with patch("brain.enrich_set.fill_beat_phase", side_effect=fake_fill_beat_phase):
            summary = run_enrich(
                playlist_path=self.playlist_path,
                skip_bpm=True, skip_lyrics=True, skip_chroma=True,
                skip_phrases=True, skip_timelines=True,  # phrases already seeded above
            )

        self.assertEqual(calls, [[self.track_id]])
        self.assertEqual(summary["beat_phase_analyzed"], 1)
        with closing(real_connect(self.index_path)) as db:
            row = db.execute(
                "SELECT track_id FROM beat_phase WHERE track_id=?", (self.track_id,)
            ).fetchone()
        self.assertIsNotNone(row)

    def test_status_and_enrichment_status_report_beat_phase_gap(self) -> None:
        with closing(real_connect(self.index_path)) as db:
            gaps = status(db, [self.track_id])
        self.assertIn("beat_phase", gaps[self.track_id])
        self.assertFalse(gaps[self.track_id]["beat_phase"])

        report = enrichment_status(self.playlist_path)
        self.assertEqual(report["missing"]["beat_phase"], 1)
        self.assertIn("beat_phase", report["message"])

    def test_skip_beat_phase_flag_prevents_the_call(self) -> None:
        with patch("brain.enrich_set.fill_beat_phase") as mock_fill:
            run_enrich(
                playlist_path=self.playlist_path,
                skip_bpm=True, skip_lyrics=True, skip_chroma=True,
                skip_phrases=True, skip_beat_phase=True, skip_timelines=True,
            )
        mock_fill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
