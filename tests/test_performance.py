"""Musical invariants and original-source execution/export boundaries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from shared.performance import validate, compile_events, fingerprint, validate_artifact, source_state, live_envelope
from hands.performance_runner import native_payload, run_performance


def fixture():
    return {'schema_version':1,'tempo_bpm':120.,'sample_rate':44100,'pattern_beats':4,
      'global_pattern_zero_seconds':0.,'source_limits':{'voice':{'min':10,'exclude':[[13,16]]}},
      'loop':{'track_id':'bed','source_start':0.,'source_end':4.,'rate':1.,'gain_db':-6.,'beats':8},
      'clips':[{'id':'voice','track_id':'voice','start':0.,'length':8.,'rate':1.,'gain_db':-6.,'zero':0.,'fade_in':1.,'fade_out':1.,'live_eq':[.4,1,1],
       'segments':[{'source_start':10.,'source_end':13.,'local_start':0.},{'source_start':16.,'source_end':20.,'local_start':4.}],
       'skip_fills':[{'start':3.,'end':4.}]}]}


def artifact(p):
    return {'performance':p,'performance_sha256':fingerprint(p),'events':compile_events(p),'execution_mode':'live_source_tracks'}


class PerformanceTests(unittest.TestCase):
    def test_forbidden_audio_cannot_be_selected(self):
        p=fixture();validate(p)
        self.assertIsNone(source_state(p,p['clips'][0],3.5))
        self.assertEqual(source_state(p,p['clips'][0],4)[0],16)
        p['clips'][0]['segments'][0]['source_end']=13.01
        with self.assertRaisesRegex(ValueError,'excluded'):validate(p)

    def test_minimum_cue_includes_any_preroll(self):
        p=fixture();p['clips'][0]['segments'][0]['source_start']=9.99
        with self.assertRaisesRegex(ValueError,'boundary'):validate(p)

    def test_global_cutoff_overrides_saved_plan(self):
        p=fixture()
        with self.assertRaisesRegex(ValueError,'boundary'):validate(p,{'voice':{'max':19}})

    def test_wrong_backbeat_parity_is_rejected(self):
        p=fixture();p['clips'][0]['start']+=.5
        with self.assertRaisesRegex(ValueError,'backbeat'):validate(p)

    def test_skip_must_preserve_backbeat_too(self):
        p=fixture();p['clips'][0]['segments'][1]['local_start']-=.5
        with self.assertRaisesRegex(ValueError,'backbeat'):validate(p)

    def test_performance_cannot_fall_back_to_finished_master(self):
        from hands.run_mix_plan import run_plan
        plan=artifact(fixture());plan['execution_mode']='rendered_master'
        with self.assertRaisesRegex(ValueError,'original live sources'):validate_artifact(plan)
        with patch('hands.run_mix_plan.MixxxControl',side_effect=AssertionError('must not connect')):
            with self.assertRaisesRegex(ValueError,'live_source_tracks'):run_plan(plan,port=9995,dry_run=False,max_events=None)

    def test_forbidden_loop_audio_rejected(self):
        p=fixture();p['source_limits']['bed']={'max':3.9}
        with self.assertRaisesRegex(ValueError,'boundary'):validate(p)

    def test_overcommitted_decks_fail(self):
        p=fixture();base=p['clips'][0];base['skip_fills']=[]
        p['clips']=[{**copy.deepcopy(base),'id':str(i)} for i in range(5)]
        with self.assertRaisesRegex(ValueError,'four decks'):validate(p)

    def test_changed_events_or_performance_need_compile(self):
        plan=artifact(fixture());plan['events'][0]['source_track_id']='finished.wav'
        with self.assertRaisesRegex(ValueError,'events'):validate_artifact(plan)
        plan=artifact(fixture());plan['performance']['clips'][0]['gain_db']=-7
        with self.assertRaisesRegex(ValueError,'changed'):validate_artifact(plan)

    def test_gap_cover_is_a_separate_original_source_deck(self):
        p=fixture();payload=native_payload(p,{'voice':Path('/music/song.mp3'),'bed':Path('/music/instrumental.mp3')})
        voice,fill=payload['clips'];self.assertNotEqual(voice['deck'],fill['deck'])
        self.assertEqual(fill['path'],'/music/instrumental.mp3')
        self.assertEqual(fill['live_eq'],[1,1,1])
        self.assertEqual(live_envelope(p,p['clips'][0],3.5),0)
        self.assertAlmostEqual(live_envelope(p,p['clips'][0],2.5),.5)
        self.assertNotIn('path',p['clips'][0])

    def test_live_dry_run_never_processes_audio_or_connects(self):
        with patch('hands.performance_validation.current_limits',return_value={}),patch('subprocess.Popen',side_effect=AssertionError('must not decode/render')),patch('hands.performance_runner.MixxxControl',side_effect=AssertionError('must not connect')):
            run_performance(artifact(fixture()),port=9995,dry_run=True)

    def test_compile_derives_display_and_events_from_same_decisions(self):
        from brain.performance_cli import compile_plan
        plan=artifact(fixture());plan['segments']=[{'obsolete':True}]
        plan['tracks']=[{'track_id':'voice','cue_seconds':99,'rendered_start_seconds':99}]
        with patch('hands.performance_validation.current_limits',return_value={}):result=compile_plan(plan)
        self.assertEqual(result['tracks'][0]['cue_seconds'],10)
        self.assertNotIn('rendered_start_seconds',result['tracks'][0])
        self.assertEqual(result['segments'],[])
        self.assertEqual(result['events'],compile_events(result['performance']))
        self.assertEqual(plan['tracks'][0]['cue_seconds'],99)

    def test_live_wrapper_uses_only_original_paths_without_audio_processing(self):
        from types import SimpleNamespace
        p=fixture();plan=artifact(p)
        class FakeMixxx:
            def __init__(self,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def get(self,g,k):return 0. if k=='play' else 1.
            def set(self,*args):pass
        with patch('hands.performance_validation.current_limits',return_value={}),patch('hands.performance_validation.check_sources',return_value={'voice':Path('/original/song.mp3'),'bed':Path('/original/beat.mp3')}),patch('hands.run_mix_plan.clawdj_binary',return_value=Path('/rust')),patch('hands.performance_runner.subprocess.run',return_value=SimpleNamespace(returncode=0)),patch('hands.performance_runner.MixxxControl',FakeMixxx),patch('hands.performance_runner.execute_rust') as execute,patch('hands.offline_mix.prepare_clips',side_effect=AssertionError('live must not prepare audio')):
            run_performance(plan,port=9995)
        paths={c['path'] for c in execute.call_args.args[2]['clips']}
        self.assertEqual(paths,{'/original/song.mp3','/original/beat.mp3'})
        self.assertEqual(execute.call_count,2)
        self.assertEqual(execute.call_args_list[0].kwargs,{'preflight_only':True})

    def test_preflight_failure_never_starts_recording_or_performance(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        m=MagicMock();m.__enter__.return_value=m
        m.get.side_effect=lambda g,k: 0. if k=='play' else 1.
        with patch('hands.performance_validation.current_limits',return_value={}),patch('hands.performance_validation.check_sources',return_value={'voice':Path('/song.mp3'),'bed':Path('/bed.mp3')}),patch('hands.run_mix_plan.clawdj_binary',return_value=Path('/rust')),patch('hands.performance_runner.subprocess.run',return_value=SimpleNamespace(returncode=0)),patch('hands.performance_runner.MixxxControl',return_value=m),patch('hands.performance_runner.execute_rust',side_effect=RuntimeError('preflight invalid source')) as execute,patch('hands.run_mix_plan.start_recording') as record:
            with self.assertRaisesRegex(RuntimeError,'preflight invalid source'):
                run_performance(artifact(fixture()),port=9995,record=True)
        record.assert_not_called()
        self.assertEqual(execute.call_count,1)
        self.assertEqual(execute.call_args.kwargs,{'preflight_only':True})
        m.set.assert_any_call('[Channel1]','play',0)
        m.set.assert_any_call('[Channel2]','play',0)

    def test_firm_verse_observation_is_not_a_mandatory_end(self):
        from brain.build_mix_plan import track_directives
        from hands.performance_validation import current_limits
        note='observed_final_verse_end_seconds=151; final verse ends at 2:31; blending from there is optional; later audio remains allowed.'
        self.assertIsNone(track_directives({'dj_notes':note})['mandatory_end_seconds'])
        with patch('hands.source_cutoffs.library_notes',return_value={'voice':note}):
            self.assertEqual(current_limits(artifact(fixture()))['voice'],{})

    def test_generic_build_never_replaces_authored_performance(self):
        from types import SimpleNamespace
        from brain.plan_mix_build import build
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'mix_plan.json';data=json.dumps(artifact(fixture()));path.write_text(data)
            with patch('brain.plan_mix_build.plan_paths.resolve',return_value=SimpleNamespace(mix_plan=path)),patch('brain.plan_mix_build.compose_mix_plan',side_effect=AssertionError('must not compose')):
                with self.assertRaisesRegex(ValueError,'explicit musical performance'):build('example')
            self.assertEqual(path.read_text(),data)

    def test_export_never_overwrites_original_or_live_plan(self):
        from hands.offline_mix import render
        with tempfile.TemporaryDirectory() as tmp:
            p=fixture();plan=artifact(p);source=Path(tmp)/'mix.wav';source.write_bytes(b'original')
            before=copy.deepcopy(plan)
            with patch('hands.offline_mix.validate_current'),patch('hands.offline_mix.check_sources',return_value={'voice':source}):
                with self.assertRaisesRegex(ValueError,'original source'):render(plan,tmp)
            self.assertEqual(source.read_bytes(),b'original');self.assertEqual(plan,before)

    def test_offline_exclusion_and_cleanup_with_real_decoder(self):
        import numpy as np
        import soundfile as sf
        from hands.offline_mix import prepare_clips
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'source.wav';audio=np.zeros((5*44100,2),dtype='float32');audio[44100:2*44100]=.75
            sf.write(src,audio,44100,subtype='FLOAT')
            p=fixture();p['pattern_beats']=2;p['source_limits']={'voice':{'exclude':[[1,2]]}};p.pop('loop')
            c=p['clips'][0];c.update(length=4.,fade_in=0.,fade_out=0.,skip_fills=[],segments=[{'source_start':0.,'source_end':1.,'local_start':0.},{'source_start':2.,'source_end':5.,'local_start':1.}])
            with tempfile.TemporaryDirectory(dir=root) as work:
                clips=prepare_clips(p,Path(work),{'voice':str(src)});out,_=sf.read(clips['voice']['path'])
                self.assertEqual(float(np.max(np.abs(out))),0.)
                self.assertEqual(len(list(Path(work).iterdir())),1)
            self.assertFalse(Path(work).exists())

class PatternAnalysisTests(unittest.TestCase):
    def test_shared_pattern_finds_backbeat_without_one_beat_alias(self):
        import numpy as np
        from brain.audio_patterns import template,match
        t=np.arange(0,40,.005)
        def channels(zero):
            phase=(t-zero)%4
            return np.array([sum(amp*np.exp(-((phase-hit)/.03)**2) for hit,amp in [(0,1),(1,0.7),(2.5,.4)]),sum(amp*np.exp(-((phase-hit)/.03)**2) for hit,amp in [(.5,1),(1.5,.6),(2.5,1),(3.5,.8)])])
        reference=template(t,channels(0),120,0)
        found=match(t,channels(.5),reference,120,span=.1)
        self.assertAlmostEqual(found['bpm'],120,delta=.02)
        self.assertAlmostEqual(found['pattern_zero_seconds'],.5,delta=.015)
        self.assertGreater(min(found['correlation_bass_backbeat']),.9)


if __name__=='__main__':unittest.main()
