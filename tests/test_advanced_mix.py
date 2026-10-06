"""Advanced plans must be executable originals with evidence and hard guards."""
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from brain.advanced_mix import compile_generic, upgrade
from brain.build_mix_plan import build_plan
from shared.performance import validate_artifact, compile_events


class AdvancedMixTest(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tracks = []
        self.sources = {}
        for name in ('a', 'b', 'c'):
            path = self.root / (name + '.wav')
            path.write_bytes(('synthetic-' + name).encode())
            tid = str(path)
            self.tracks.append(dict(track_id=tid, artist=name, title='Song', bpm=120,
                                    key='Am', duration_seconds=300,
                                    dj_notes='cue_seconds=0; no_flourish; ride_beats=63; trust_ride_beats'))
            self.sources[tid] = dict(measured=True, bpm=120, zero=0, confidence=.98,
                                     pitch_residual_cents=0, duration_seconds=300,
                                     sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.recipe = dict(version=1, approved=True, tempo_bpm=120, pattern_beats=4, sources=self.sources)
        self.plan = build_plan(self.tracks, count=3, seconds_per_track=32, affinity_lookup={})
        for event in self.plan['events']:
            if event['op'] == 'transition':
                event.update(transition_beats=32, moves=['sync', 'crossfade', 'eq_restore'])

    def test_measured_clock_preserves_foreground_order_and_no_playback(self):
        result = compile_generic(self.plan, self.recipe)
        self.assertEqual(result['tracks'], self.plan['tracks'])
        self.assertEqual(result['events'], compile_events(result['performance']))
        validate_artifact(result)
        self.assertEqual(result['execution_mode'], 'live_source_tracks')
        self.assertTrue(all(c['track_id'] in self.sources for c in result['performance']['clips']))

    def test_bad_evidence_keeps_identical_original_events(self):
        cases = []
        for key, value in [('approved', False), ('tempo_bpm', float('nan')), ('pattern_beats', 3)]:
            r = copy.deepcopy(self.recipe); r[key] = value; cases.append(r)
        for key, value in [('sha256', '0'*64), ('confidence', .5), ('pitch_residual_cents', 16), ('bpm', 60)]:
            r = copy.deepcopy(self.recipe); r['sources'][self.tracks[0]['track_id']][key] = value; cases.append(r)
        for recipe in cases:
            with self.subTest(recipe=recipe):
                path = self.root/'advanced_mix.json';path.write_text(json.dumps(recipe))
                result = upgrade(self.plan, path)
                self.assertEqual(result['events'], self.plan['events'])
                self.assertNotIn('performance', result)
                self.assertEqual(result['advanced_mix']['status'], 'fallback')

    def test_missing_recipe_has_no_behavior_change(self):
        self.assertIs(upgrade(self.plan, self.root/'absent.json'), self.plan)

    def test_mismatched_pattern_fails_instead_of_moving_approved_cue(self):
        self.sources[self.tracks[1]['track_id']]['zero'] = .5
        with self.assertRaisesRegex(ValueError, 'backbeat'):
            compile_generic(self.plan, self.recipe)

    def test_fast_different_song_fade_cannot_use_the_handoff_exception(self):
        next(e for e in self.plan['events'] if e['op']=='transition')['transition_beats'] = 16
        with self.assertRaisesRegex(ValueError, '24 counts'):
            compile_generic(self.plan, self.recipe)

    def test_short_intro_repeats_only_approved_region_and_extends_life(self):
        tid = self.tracks[1]['track_id']
        self.plan['tracks'][1]['dj_notes'] += '; allow_intro_extension; observed_first_verse_start_seconds=8'
        self.sources[tid]['intro_loop'] = dict(start_seconds=0, end_seconds=8, plays=2)
        baseline = compile_generic(self.plan, {**self.recipe, 'sources':{k:{x:y for x,y in v.items() if x!='intro_loop'} for k,v in self.sources.items()}})
        result = compile_generic(self.plan, self.recipe)
        clip = result['performance']['clips'][1]
        self.assertEqual(len(clip['segments']), 3)
        self.assertEqual(clip['segments'][1]['source_start'], 0)
        self.assertEqual(clip['segments'][1]['source_end'], 8)
        self.assertEqual(result['duration_seconds'], baseline['duration_seconds']+8)
        validate_artifact(result)

    def test_intro_never_loops_a_verse_or_four_passes(self):
        tid = self.tracks[1]['track_id']
        self.plan['tracks'][1]['dj_notes'] += '; allow_intro_extension; observed_first_verse_start_seconds=8'
        for loop in (dict(start_seconds=0,end_seconds=9,plays=2), dict(start_seconds=0,end_seconds=8,plays=4),dict(start_seconds=0,end_seconds=2,plays=2)):
            self.sources[tid]['intro_loop'] = loop
            with self.subTest(loop=loop), self.assertRaises(ValueError):
                compile_generic(self.plan, self.recipe)

    def test_reentry_uses_two_original_copies_and_keeps_total_ride(self):
        tid = self.tracks[1]['track_id']
        self.plan['tracks'][1]['dj_notes'] += '; allow_reentry'
        self.sources[tid]['handoff'] = dict(from_seconds=24,to_seconds=8)
        result = compile_generic(self.plan, self.recipe)
        clips = [c for c in result['performance']['clips'] if c['track_id']==tid]
        self.assertEqual(len(clips), 2)
        self.assertEqual(clips[0]['segments'][0]['source_end'],24)
        self.assertEqual(clips[1]['segments'][0]['source_start'],8)
        self.assertEqual(clips[0]['fade_out'],2)
        self.assertEqual(clips[1]['fade_in'],2)
        events = [e for e in result['events'] if e.get('clip_id') in {c['id'] for c in clips} and e['op']=='start_clip']
        self.assertNotEqual(events[0]['deck'],events[1]['deck'])
        validate_artifact(result)

    def test_forward_skip_matches_notes_and_excludes_every_forbidden_sample(self):
        tid = self.tracks[1]['track_id']
        self.plan['tracks'][1]['dj_notes'] += '; skip_handoff; mandatory_skip; skip_from_seconds=24; skip_to_seconds=40'
        self.sources[tid]['handoff'] = dict(from_seconds=24,to_seconds=40)
        result = compile_generic(self.plan, self.recipe)
        for clip in result['performance']['clips']:
            if clip['track_id']==tid:
                for s in clip['segments']:
                    self.assertTrue(s['source_end']<=24 or s['source_start']>=40)
        validate_artifact(result)

    def test_mandatory_end_limits_all_copies_and_repeated_segments(self):
        tid = self.tracks[1]['track_id']
        self.plan['tracks'][1]['dj_notes'] += '; mandatory_end_seconds=30; allow_reentry'
        self.sources[tid]['handoff'] = dict(from_seconds=24,to_seconds=8)
        with self.assertRaisesRegex(ValueError, 'boundary'):
            compile_generic(self.plan, self.recipe)

    def test_missing_reentry_permission_and_late_handoff_are_refused(self):
        tid = self.tracks[1]['track_id']
        self.sources[tid]['handoff'] = dict(from_seconds=24,to_seconds=8)
        with self.assertRaisesRegex(ValueError, 'approval'):
            compile_generic(self.plan, self.recipe)
        self.plan['tracks'][1]['dj_notes'] += '; allow_reentry'
        self.sources[tid]['handoff']['from_seconds'] = 2
        self.sources[tid]['handoff']['to_seconds'] = 0
        with self.assertRaisesRegex(ValueError, 'chosen body'):
            compile_generic(self.plan, self.recipe)

    def test_recipe_participates_in_revision_only_when_present(self):
        from brain.plan_paths import _paths
        from brain.plan_revision import plan_rev
        paths = _paths(self.root)
        before = plan_rev(paths)
        self.assertNotIn('advanced_mix', before.files)
        (self.root/'advanced_mix.json').write_text('{}')
        after = plan_rev(paths)
        self.assertNotEqual(before.token,after.token)
        self.assertIn('advanced_mix', after.files)

    def test_authored_performance_still_refuses_generic_build(self):
        from brain.plan_mix_build import build
        from brain.plan_paths import _paths
        paths = _paths(self.root)
        paths.mix_plan.write_text(json.dumps({'performance':{'clips':[]}}))
        with patch('brain.plan_paths.resolve', return_value=paths), patch('brain.plan_mix_build.compose_mix_plan') as compose, self.assertRaisesRegex(ValueError, 'explicit musical performance'):
            build('synthetic')
        compose.assert_not_called()

    def test_plan_aware_build_compiles_rebuilds_and_tracks_recipe_changes(self):
        from brain.plan_mix_build import build
        from brain.plan_paths import _paths
        from types import SimpleNamespace
        paths = _paths(self.root)
        paths.plan_json.write_text(json.dumps({'plan_id':'synthetic-id'}))
        paths.playlist.write_text(json.dumps(self.tracks))
        (self.root/'advanced_mix.json').write_text(json.dumps(self.recipe))
        notes = [SimpleNamespace(track_id=t['track_id'],note=t['dj_notes']) for t in self.tracks]
        with patch('brain.plan_paths.resolve',return_value=paths), patch('brain.plan_notes.get_effective',return_value=notes), patch('brain.order_constraints.from_activations',return_value=SimpleNamespace(groups=[])), patch('brain.plan_mix_build.compose_mix_plan',return_value=self.plan):
            first = build('synthetic')
            second = build('synthetic')
        self.assertEqual(first['performance'],second['performance'])
        self.assertIn('advanced_mix',second['source_revs'])
        self.assertEqual(json.loads(paths.mix_plan.read_text())['events'],second['events'])

    def test_native_dry_run_uses_original_sources_without_render_or_device(self):
        from hands.run_mix_plan import run_plan
        result = compile_generic(self.plan,self.recipe)
        with patch('hands.performance_validation.current_limits',return_value={}), patch('hands.performance_runner.MixxxControl',side_effect=AssertionError('must not connect')), patch('subprocess.Popen',side_effect=AssertionError('must not render')):
            run_plan(result,port=9995,dry_run=True,max_events=None)

    def sample_recipe(self):
        tid = self.tracks[0]['track_id']
        source = self.tracks[1]['track_id']
        self.plan['tracks'][0]['dj_notes'] = 'cue_seconds=0; ride_beats=63; trust_ride_beats; allow_sample_unison'
        self.sources[tid]['sample_unison'] = dict(approved=True, backbeat_verified=True,
            source_track_id=source, sample_start_seconds=32, source_start_seconds=0,
            sample_beats=16, verified_beats=32, alignment_error_ms=0,
            residual_pitch_cents=0, confidence=.98,entry_region_instrumental=True)
        return self.sources[tid]['sample_unison']

    def test_sample_unison_repeats_the_measured_bar_and_restores_turntable_pitch(self):
        self.sample_recipe()
        self.recipe['tempo_bpm'] = 138
        for track in self.tracks[1:]:self.sources[track['track_id']]['bpm'] = 138
        result = compile_generic(self.plan,self.recipe)
        clips = result['performance']['clips']
        self.assertAlmostEqual(clips[0]['rate'],1.15)
        self.assertEqual(clips[1]['advanced_technique'],'measured_sample_unison')
        self.assertEqual(clips[1]['segments'][0]['source_start'],0)
        self.assertEqual(clips[1]['segments'][1]['source_start'],0)
        self.assertEqual(clips[1]['segments'][0]['source_end'],clips[1]['segments'][1]['source_end'])
        validate_artifact(result)

    def test_sample_requires_pitch_alignment_confidence_and_full_blend_evidence(self):
        move = self.sample_recipe()
        cases = [('residual_pitch_cents',16),('alignment_error_ms',21),('confidence',.5),
                 ('verified_beats',16),('entry_region_instrumental',False),('backbeat_verified',False),
                 ('sample_start_seconds',32.5),('source_start_seconds',2),('sample_beats',4)]
        for key,value in cases:
            before = move[key]; move[key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):compile_generic(self.plan,self.recipe)
            move[key] = before

    def test_lineage_or_model_suggestion_alone_cannot_authorize_unison(self):
        move = self.sample_recipe()
        self.plan['tracks'][0]['dj_notes'] = 'sample lineage, no_flourish'
        with self.assertRaisesRegex(ValueError,'DJ-note approval'):
            compile_generic(self.plan,self.recipe)
        self.plan['tracks'][0]['dj_notes'] = 'allow_sample_unison'
        move['source_track_id'] = self.tracks[2]['track_id']
        with self.assertRaisesRegex(ValueError,'adjacent'):
            compile_generic(self.plan,self.recipe)

    def test_sample_repeats_still_obey_source_exclusions(self):
        self.sample_recipe()
        self.plan['tracks'][1]['dj_notes'] += '; mandatory_end_seconds=6'
        with self.assertRaisesRegex(ValueError,'boundary'):
            compile_generic(self.plan,self.recipe)

    def test_sampler_can_be_the_entering_record(self):
        outgoing = self.tracks[0]['track_id']; sampler = self.tracks[1]['track_id']
        self.plan['tracks'][1]['dj_notes'] = 'allow_sample_unison'
        self.sources[sampler]['sample_unison'] = dict(approved=True,backbeat_verified=True,
            source_track_id=outgoing,sample_start_seconds=0,source_start_seconds=32,
            sample_beats=16,verified_beats=32,alignment_error_ms=0,
            residual_pitch_cents=0,confidence=.98,entry_region_instrumental=True)
        result=compile_generic(self.plan,self.recipe)
        self.assertEqual(result['performance']['clips'][1]['sample_relation']['sampling_track_id'],sampler)
        validate_artifact(result)
