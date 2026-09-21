"""Hard source boundaries must survive overlays, stale plans, and playback rate."""
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from brain.build_mix_plan import build_plan, track_directives
from brain.plan_notes import carry_library_skips


class SourceCutoffTests(unittest.TestCase):
    def test_library_end_overrides_plan_and_full_track(self):
        note = carry_library_skips('mandatory_end_seconds=92',
                                  'full_track; mandatory_end_seconds=110; ride_beats=999')
        self.assertEqual(track_directives({'dj_notes': note})['mandatory_end_seconds'], 92)
        self.assertIn('full_track', note)

    def tracks(self):
        return [dict(track_id=f'/music/{i}.wav', artist='Artist', title=str(i),
                     bpm=120, key='Am', duration_seconds=180,
                     dj_notes='cue_seconds=0; trust_cue_seconds') for i in range(2)]

    def test_trusted_ride_reserves_complete_outgoing_fade(self):
        tracks = self.tracks()
        tracks[0]['dj_notes'] += '; mandatory_end_seconds=92; ride_beats=999; trust_ride_beats'
        plan = build_plan(tracks, count=2, seconds_per_track=180, affinity_lookup={})
        body = next(e for e in plan['events'] if e['op'] == 'play_body')
        fade = next(e for e in plan['events'] if e['op'] == 'transition')
        self.assertLess((body['beats'] + fade['transition_beats'] + 1) * .5, 92)
        self.assertEqual(body['beats'] % 4, 999 % 4)
        self.assertEqual(tracks[0]['duration_seconds'], 180)

    def test_cue_at_cutoff_rejected_and_full_track_finale_bounded(self):
        tracks = self.tracks()
        tracks[1]['dj_notes'] += '; mandatory_end_seconds=92; full_track'
        plan = build_plan(tracks, count=2, seconds_per_track=180, affinity_lookup={})
        finale = next(e for e in plan['events'] if e['op'] == 'finale')
        self.assertEqual(finale['seconds'], 92)
        tracks[1]['dj_notes'] += '; cue_seconds=92'
        with self.assertRaisesRegex(ValueError, 'mandatory_end_seconds'):
            build_plan(tracks, count=2, seconds_per_track=180, affinity_lookup={})

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg required for PCM boundary test')
    def test_runtime_uses_bounded_copy_and_preserves_original(self):
        from hands.source_cutoffs import prepare_plan
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.wav'
            with wave.open(str(source), 'wb') as stream:
                stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
                stream.writeframes(b'\x01\x00' * 8000 + b'\xff\x7f' * 8000)
            original = source.read_bytes()
            tid = str(source)
            plan = {'tracks': [{'track_id': tid}], 'events': [
                {'op': 'load', 'track_id': tid, 'cue_seconds': 0},
                {'op': 'preload_after_transition', 'track_id': tid, 'cue_seconds': .5},
                {'op': 'load', 'track_id': '/music/another-version.wav', 'cue_seconds': 0}]}
            before = copy.deepcopy(plan)
            with patch('hands.source_cutoffs.library_notes', return_value={tid: 'mandatory_end_seconds=1'}):
                result = prepare_plan(plan, cache_dir=root / 'cache')
            bounded = Path(result['events'][0]['track_id'])
            self.assertNotEqual(bounded, source)
            self.assertEqual(result['events'][1]['track_id'], str(bounded))
            self.assertEqual(result['events'][2], plan['events'][2])
            with wave.open(str(bounded)) as stream:
                self.assertEqual(stream.getnframes(), 8000)
                self.assertLess(max(stream.readframes(8000)), 10)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(plan, before)

    def test_rendered_master_rejects_old_source_tail_and_hash_mismatch(self):
        from hands.source_cutoffs import prepare_plan
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            master = root / 'master.wav'
            master.write_bytes(b'fixture')
            recipe = root / 'recipe.json'
            payload = {'clips': [{'track_id': 'exact-recording', 'source_cue': 0,
                'source_end': 109, 'segments': [{'source_start': 0, 'source_end': 109}]}]}
            recipe.write_text(json.dumps(payload))
            plan = {'execution_mode': 'rendered_master_playback', 'render_recipe': str(recipe),
                'master_sha256': hashlib.sha256(b'fixture').hexdigest(),
                'tracks': [{'track_id': 'exact-recording', 'dj_notes': 'mandatory_end_seconds=92'}],
                'events': [{'op': 'load', 'track_id': str(master)}]}
            with patch('hands.source_cutoffs.library_notes', return_value={}):
                with self.assertRaisesRegex(ValueError, 'mandatory_end_seconds'):
                    prepare_plan(plan)
                from hands.run_mix_plan import run_plan
                with patch('hands.run_mix_plan.MixxxControl') as connect:
                    with self.assertRaisesRegex(ValueError, 'mandatory_end_seconds'):
                        run_plan(plan, port=9995, dry_run=False, max_events=None)
                    connect.assert_not_called()
                payload['clips'][0]['source_end'] = 92
                payload['clips'][0]['segments'][0]['source_end'] = 92
                recipe.write_text(json.dumps(payload))
                plan['render_recipe_sha256'] = hashlib.sha256(recipe.read_bytes()).hexdigest()
                self.assertEqual(prepare_plan(plan), plan)
                recipe.write_text(json.dumps(payload, indent=2))
                with self.assertRaisesRegex(ValueError, 'recipe hash'):
                    prepare_plan(plan)
                plan['render_recipe_sha256'] = hashlib.sha256(recipe.read_bytes()).hexdigest()
                master.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'hash'):
                    prepare_plan(plan)

    def test_missing_encoder_never_falls_back_to_original(self):
        from hands.source_cutoffs import prepare_plan
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'source.wav'
            source.write_bytes(b'fixture')
            tid = str(source)
            plan = {'tracks': [{'track_id': tid, 'dj_notes': 'mandatory_end_seconds=1'}],
                    'events': [{'op': 'load', 'track_id': tid}]}
            with patch('hands.source_cutoffs.library_notes', return_value={}), patch('hands.source_cutoffs.subprocess.run', side_effect=FileNotFoundError):
                with self.assertRaisesRegex(ValueError, 'bounded audio'):
                    prepare_plan(plan, cache_dir=Path(td) / 'cache')


if __name__ == '__main__':
    unittest.main()
