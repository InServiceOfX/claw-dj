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

    def support_recipe(self, ids=None):
        path = self.root/'bed.wav';path.write_bytes(b'synthetic-instrumental')
        tid = str(path)
        selected = ids or [self.tracks[1]['track_id']]
        for track in self.plan['tracks']:
            if track['track_id'] in selected:track['dj_notes'] += '; allow_instrumental_support'
        request = dict(approved=True,foreground_track_ids=selected,track_id=tid,
            instrumental_verified=True,backbeat_verified=True,alignment_error_ms=0,
            residual_pitch_cents=0,verified_seconds=300,source_start_seconds=0,
            source_end_seconds=8,loop_beats=16,
            source=dict(measured=True,bpm=120,zero=0,confidence=.98,pitch_residual_cents=0,
                        duration_seconds=120,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        self.recipe['support'] = [request]
        return request,{tid:''}

    def test_full_mix_support_covers_body_without_changing_foreground_identity(self):
        request,notes = self.support_recipe()
        result = compile_generic(self.plan,self.recipe,support_notes=notes)
        foreground = result['performance']['clips'][1]
        bed = result['performance']['clips'][-1]
        self.assertEqual(result['tracks'],self.plan['tracks'])
        self.assertEqual(result['track_count'],3)
        self.assertEqual(bed['start'],foreground['start'])
        self.assertEqual(bed['start']+bed['length'],foreground['start']+foreground['length'])
        self.assertEqual(foreground['live_eq'],[.35,1,1])
        self.assertEqual(bed['support']['low_gain'],1)
        self.assertEqual(bed['support']['high_gain'],.25)
        starts=[e for e in result['events'] if e['op']=='start_clip' and e['at']==foreground['start']]
        self.assertEqual(len({e['deck'] for e in starts}),2)
        live=[c for c in result['performance']['clips'] if c['start']<=foreground['start']<c['start']+c['length']]
        self.assertEqual(len(live),3)
        validate_artifact(result)

    def test_one_bed_can_span_consecutive_approved_full_mixes(self):
        request,notes=self.support_recipe([t['track_id'] for t in self.tracks])
        result=compile_generic(self.plan,self.recipe,support_notes=notes)
        bed=result['performance']['clips'][-1]
        self.assertEqual(bed['start'],0)
        self.assertEqual(bed['length'],result['duration_seconds'])
        self.assertEqual(sum(bool(c.get('support')) for c in result['performance']['clips']),1)
        validate_artifact(result)

    def test_support_requires_full_coverage_instrumental_phase_pitch_and_loop_evidence(self):
        request,notes=self.support_recipe()
        for key,value in [('verified_seconds',2),('source_end_seconds',7),('instrumental_verified',False),
                          ('backbeat_verified',False),('alignment_error_ms',21),('residual_pitch_cents',16),
                          ('bed_eq',[1,1,1]),('foreground_eq',[1,1,1]),('loop_beats',4)]:
            existed=key in request; old=request.get(key); request[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):compile_generic(self.plan,self.recipe,support_notes=notes)
            if existed:request[key]=old
            else:request.pop(key)
        request['source']['zero']=.5
        with self.assertRaisesRegex(ValueError,'pattern'):
            compile_generic(self.plan,self.recipe,support_notes=notes)

    def test_support_respects_latest_source_notes_on_the_bed(self):
        request,notes=self.support_recipe()
        for note in ('mandatory_end_seconds=6','mandatory_start_seconds=2',
                     'mandatory_skip; skip_from_seconds=2; skip_to_seconds=4'):
            with self.subTest(note=note),self.assertRaisesRegex(ValueError,'boundary|excluded'):
                compile_generic(self.plan,self.recipe,support_notes={request['track_id']:note})
        with self.assertRaisesRegex(ValueError,'current effective'):
            compile_generic(self.plan,self.recipe)

    def test_two_beds_disconnected_bodies_and_acapella_reclassification_are_refused(self):
        request,notes=self.support_recipe()
        self.recipe['support'].append(copy.deepcopy(request))
        with self.assertRaisesRegex(ValueError,'one continuous'):
            compile_generic(self.plan,self.recipe,support_notes=notes)
        self.recipe['support'].pop()
        request['foreground_track_ids']=[self.tracks[0]['track_id'],self.tracks[2]['track_id']]
        with self.assertRaisesRegex(ValueError,'consecutive'):
            compile_generic(self.plan,self.recipe,support_notes=notes)
        request['foreground_track_ids']=[self.tracks[1]['track_id']]
        self.plan['tracks'][1]['title']='Song (Acapella)'
        with self.assertRaisesRegex(ValueError,'reclassify'):
            compile_generic(self.plan,self.recipe,support_notes=notes)

    def test_support_permission_and_source_hash_are_rechecked(self):
        request,notes=self.support_recipe()
        self.plan['tracks'][1]['dj_notes'] += '; no_instrumental_support'
        with self.assertRaisesRegex(ValueError,'DJ-note approval'):
            compile_generic(self.plan,self.recipe,support_notes=notes)
        self.plan['tracks'][1]['dj_notes']=self.plan['tracks'][1]['dj_notes'].replace('no_instrumental_support','')
        Path(request['track_id']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'source changed'):
            compile_generic(self.plan,self.recipe,support_notes=notes)

    def test_new_support_plan_restores_owned_decks_on_failure_and_interrupt(self):
        from hands.performance_runner import run_performance
        from types import SimpleNamespace
        request,notes=self.support_recipe()
        result=compile_generic(self.plan,self.recipe,support_notes=notes)
        class FakeMixxx:
            def __init__(self):self.writes=[]
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def get(self,g,k):return 0 if k in ('play','loop_enabled') else .75
            def set(self,g,k,v):self.writes.append((g,k,v))
        used={e['deck'] for e in result['events']}
        for failure in (RuntimeError('simulated drift'), KeyboardInterrupt()):
            m=FakeMixxx()
            def execute(*args,**kwargs):
                if not kwargs.get('preflight_only'):raise failure
            with patch('hands.performance_validation.current_limits',return_value={}), patch('hands.run_mix_plan.clawdj_binary',return_value=Path('/synthetic/rust')), patch('hands.performance_runner.subprocess.run',return_value=SimpleNamespace(returncode=0)), patch('hands.performance_runner.MixxxControl',return_value=m), patch('hands.performance_runner.execute_rust',side_effect=execute):
                if isinstance(failure,RuntimeError):
                    with self.assertRaisesRegex(RuntimeError,'drift'):run_performance(result,port=9995)
                else:run_performance(result,port=9995)
            for deck in used:
                stops=[v for g,k,v in m.writes if g==f'[Channel{deck}]' and k=='play']
                self.assertEqual(stops[-1],0)
                restored=[v for g,k,v in m.writes if g==f'[Channel{deck}]' and k=='orientation']
                self.assertEqual(restored[-1],.75)
            self.assertEqual([v for g,k,v in m.writes if g=='[Master]' and k=='gain'][-1],.75)

    def test_a_playing_third_deck_is_never_taken_over(self):
        from hands.performance_runner import run_performance
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        request,notes=self.support_recipe()
        result=compile_generic(self.plan,self.recipe,support_notes=notes)
        m=MagicMock();m.__enter__.return_value=m
        m.get.side_effect=lambda g,k:1 if g=='[Channel3]' and k=='play' else 0
        with patch('hands.performance_validation.current_limits',return_value={}), patch('hands.run_mix_plan.clawdj_binary',return_value=Path('/synthetic/rust')), patch('hands.performance_runner.subprocess.run',return_value=SimpleNamespace(returncode=0)), patch('hands.performance_runner.MixxxControl',return_value=m), patch('hands.performance_runner.execute_rust') as execute, self.assertRaisesRegex(ValueError,'Deck 3 is playing'):
            run_performance(result,port=9995)
        m.set.assert_not_called();execute.assert_not_called()

    def test_upgrade_loads_effective_bed_notes_for_the_named_plan(self):
        from types import SimpleNamespace
        request,notes=self.support_recipe()
        path=self.root/'advanced_mix.json';path.write_text(json.dumps(self.recipe))
        with patch('brain.plan_notes.get_effective',return_value=[SimpleNamespace(track_id=request['track_id'],note='mandatory_end_seconds=6')]) as load:
            result=upgrade(self.plan,path,slug='synthetic')
        load.assert_called_once_with('synthetic',[request['track_id']])
        self.assertEqual(result['advanced_mix']['status'],'fallback')
        self.assertEqual(result['events'],self.plan['events'])

    def test_explicit_styles_formats_and_pair_overrides_are_never_lost(self):
        for token in ('entry_style=brake_drop','exit_style=echo_out','format_recipe=intro_loop_under_entry',
                      'pickup_beats=4','keep_blend_tempo','settle_bpm=120'):
            plan=copy.deepcopy(self.plan);plan['tracks'][1]['dj_notes'] += '; '+token
            with self.subTest(token=token),self.assertRaisesRegex(ValueError,'conventional'):
                compile_generic(plan,self.recipe)
        plan=copy.deepcopy(self.plan);plan['dj_format']={'name':'hiphop-rnb-guided'}
        with self.assertRaisesRegex(ValueError,'conventional'):
            compile_generic(plan,self.recipe)
        plan=copy.deepcopy(self.plan)
        next(e for e in plan['events'] if e['op']=='transition')['author']='user'
        with self.assertRaisesRegex(ValueError,'overrides'):
            compile_generic(plan,self.recipe)

    def test_all_handoff_copies_keep_the_noted_blend_length(self):
        tid=self.tracks[1]['track_id'];self.plan['tracks'][1]['dj_notes'] += '; allow_reentry; skip_handoff_beats=8'
        self.sources[tid]['handoff']={'from_seconds':24,'to_seconds':8,'blend_beats':4}
        with self.assertRaisesRegex(ValueError,'DJ-note length'):
            compile_generic(self.plan,self.recipe)

    def test_malformed_optional_recipe_reports_fallback_without_replacing_events(self):
        path=self.root/'advanced_mix.json'
        for data in ([], {'version':True,'approved':True}, {'version':1,'approved':True,'sources':{'bad':7}}):
            path.write_text(json.dumps(data)); result=upgrade(self.plan,path)
            self.assertEqual(result['events'],self.plan['events'])
            self.assertEqual(result['advanced_mix']['status'],'fallback')

    def test_false_permissions_and_malformed_structural_moves_decline(self):
        tid=self.tracks[1]['track_id']
        self.sources[tid]['handoff']={'from_seconds':24,'to_seconds':8}
        self.plan['tracks'][1]['dj_notes'] += '; allow_reentry=false'
        with self.assertRaisesRegex(ValueError,'approval'):compile_generic(self.plan,self.recipe)
        path=self.root/'advanced_mix.json'
        for move in (True,[],{}):
            self.sources[tid]['handoff']=move;path.write_text(json.dumps(self.recipe))
            result=upgrade(self.plan,path)
            self.assertEqual(result['advanced_mix']['status'],'fallback')
            self.assertEqual(result['events'],self.plan['events'])

    def test_finale_reentry_still_plays_to_the_original_source_end(self):
        tid=self.tracks[-1]['track_id']
        self.plan['tracks'][-1]['dj_notes'] += '; allow_reentry; full_track'
        finale=next(e for e in self.plan['events'] if e['op']=='finale')
        finale.update(play_to_end=True,seconds=300);finale.pop('beats',None)
        self.sources[tid]['handoff']={'from_seconds':24,'to_seconds':8}
        result=compile_generic(self.plan,self.recipe)
        self.assertEqual(result['performance']['clips'][-1]['segments'][0]['source_end'],300)
        validate_artifact(result)

    def test_measured_timing_cannot_move_a_confirmed_verse_exit_earlier(self):
        tid=self.tracks[0]['track_id']
        self.plan['tracks'][0]['dj_notes'] += '; observed_final_verse_end_seconds=32'
        self.sources[tid]['bpm']=121
        with self.assertRaisesRegex(ValueError,'confirmed final verse'):
            compile_generic(self.plan,self.recipe)

    def test_manual_edits_to_a_generated_performance_are_protected_from_rebuild(self):
        from brain.plan_mix_build import build
        from brain.plan_paths import _paths
        from brain.performance_cli import compile_plan
        paths=_paths(self.root)
        result=compile_generic(self.plan,self.recipe)
        result['performance']['clips'][0]['gain_db']=-3
        with patch('hands.performance_validation.current_limits',return_value={}):
            authored=compile_plan(result)
        paths.mix_plan.write_text(json.dumps(authored))
        with patch('brain.plan_paths.resolve',return_value=paths), patch('brain.plan_mix_build.compose_mix_plan') as compose,self.assertRaisesRegex(ValueError,'explicit musical performance'):
            build('synthetic')
        compose.assert_not_called()
