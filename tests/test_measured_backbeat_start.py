"""No sockets/audio playback: source-time starts preserve intros and heard seams."""
import copy
import io
import math
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import numpy as np

from brain.onset_analysis import fit_backbeat_timing
from hands import run_mix_plan as runner
from shared.backbeat import (next_start_source, phase_error_ms, target_grid_bpm,
                             validate_backbeat_start)


def spec(out_grid=75., in_grid=154.):
    return {'version': 1, 'cue_seconds': 0., 'tolerance_ms': 30.,
            'outgoing': {'grid_bpm': out_grid, 'real_bpm': 75.,
                         'first_beat_seconds': 0.,
                         'snare_phase_seconds': .8, 'confidence': .8},
            'incoming': {'grid_bpm': in_grid, 'real_bpm': 77.,
                         'first_beat_seconds': 0.,
                         'snare_phase_seconds': 1.1, 'confidence': .8}}


def event(model=None):
    return {'op': 'transition', 'from_deck': 1, 'to_deck': 2,
            'technique': 'smooth_blend', 'transition_beats': 32,
            'moves': ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore'],
            'backbeat_start': model or spec()}


class CoordinateTests(unittest.TestCase):
    def test_approved_delay_exactly_matches_the_heard_one_count_comparison(self):
        base=spec(out_grid=98.,in_grid=98.)
        base['outgoing']['real_bpm']=base['incoming']['real_bpm']=98.
        heard=copy.deepcopy(base)
        heard['approved_launch_delay']={'beats':1,'author':'human','approved':True,'quote':"let's just keep it."}
        heard=validate_backbeat_start(heard)
        for current in np.arange(130.,133.,.007):
            original=next_start_source(base,current,0.)
            delayed=next_start_source(heard,current,0.)
            self.assertAlmostEqual(delayed,original+60/98.,places=10)
            self.assertAlmostEqual(phase_error_ms(heard,delayed,0.,98.),0.,places=7)
            self.assertAlmostEqual(abs(phase_error_ms(base,delayed,0.,98.)),60000/98.,places=7)
        self.assertEqual(heard['outgoing'],base['outgoing'])
        self.assertEqual(heard['incoming'],base['incoming'])

    def test_unapproved_or_arbitrary_delay_is_rejected(self):
        for approval in [{}, {'beats':True,'author':'human','approved':True,'quote':'yes'},
                         {'beats':2,'author':'human','approved':True,'quote':'yes'},
                         {'beats':1,'author':'agent','approved':True,'quote':'yes'},
                         {'beats':1,'author':'human','approved':False,'quote':'yes'},
                         {'beats':1,'author':'human','approved':True,'quote':''}]:
            s=spec();s['approved_launch_delay']=approval
            with self.subTest(approval=approval),self.assertRaises(ValueError):validate_backbeat_start(s)

    def test_two_grid_ticks_per_real_beat_do_not_double_the_music(self):
        self.assertEqual(target_grid_bpm(validate_backbeat_start(spec()), 75.), 150.)

    def test_source_start_preserves_zero_and_matches_real_snare_cycle(self):
        s=validate_backbeat_start(spec())
        start=next_start_source(s, 130.4, 0.)
        self.assertGreater(start, 130.4)
        self.assertLess(start, 132.)
        self.assertAlmostEqual(phase_error_ms(s,start,0.,75.),0.,places=7)

    def test_nonzero_and_late_intro_phase_are_not_assumed_downbeats(self):
        s=spec();s['cue_seconds']=19.6337
        s['incoming'].update(real_bpm=98.,grid_bpm=98.,snare_phase_seconds=.021183)
        s['outgoing'].update(real_bpm=98.,grid_bpm=98.,snare_phase_seconds=.075238)
        start=next_start_source(s,286.6267,s['cue_seconds'])
        self.assertAlmostEqual(phase_error_ms(s,start,s['cue_seconds'],98.),0.,places=7)

    def test_fractional_cue_has_no_rounding_to_a_grid_index(self):
        s=validate_backbeat_start(spec())
        start=next_start_source(s,130.43,.132792)
        self.assertAlmostEqual(phase_error_ms(s,start,.132792,75.),0.,places=7)

    def test_invalid_numbers_and_weak_measurements_are_refused(self):
        for key,value in [('grid_bpm',0),('real_bpm',float('nan')),('confidence',.19),('snare_phase_seconds',-1)]:
            s=spec();s['incoming'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_backbeat_start(s)


class DetectorTests(unittest.TestCase):
    def test_late_first_snare_is_measured_in_source_seconds(self):
        times=np.arange(0.,40.,.005);env=np.zeros_like(times)
        for t in np.arange(12.13,40,1.2):env+=np.exp(-((times-t)/.009)**2)
        read=fit_backbeat_timing(env,times,real_bpm=100.)
        self.assertLess(abs(read['snare_phase_seconds']-.13),.02)
        self.assertGreater(read['first_observed_hit_seconds'],12.)
        self.assertFalse(read['count1_verified'])

    def test_constant_hats_cannot_be_certified_as_a_backbeat(self):
        times=np.arange(0.,32.,.005);env=np.zeros_like(times)
        for t in np.arange(.1,32.,.6):env+=np.exp(-((times-t)/.009)**2)
        with self.assertRaises(ValueError):fit_backbeat_timing(env,times,real_bpm=100.)

    def test_same_audio_phase_does_not_depend_on_a_grid_zero_assumption(self):
        times=np.arange(7.,39.,.005);env=np.zeros_like(times)
        for t in np.arange(7.31,39.,1.6):env+=np.exp(-((times-t)/.012)**2)
        read=fit_backbeat_timing(env,times,real_bpm=75.)
        self.assertLess(abs(read['snare_phase_seconds']-(7.31%1.6)),.02)

    def test_nonfinite_and_short_windows_do_not_invent_phase(self):
        with self.assertRaises(ValueError):fit_backbeat_timing([0.,float('nan'),1.],[0.,1.,2.],real_bpm=100.)
        with self.assertRaises(ValueError):fit_backbeat_timing(np.ones(100),np.arange(100)/100,real_bpm=100.)


class Engine:
    """Advancing original source clocks, including engine-applied write faults."""
    def __init__(self,model,*,snap=False,bad_tempo=False,stopped=False):
        self.model=model;self.now=0.;self.snap=snap;self.bad_tempo=bad_tempo
        self.v={('[Master]','crossfader'):-1.,('[Channel1]','play'):0. if stopped else 1.,
                ('[Channel2]','play'):0.,('[Channel1]','duration'):400.,('[Channel2]','duration'):300.,
                ('[Channel1]','file_bpm'):model['outgoing']['grid_bpm'],
                ('[Channel2]','file_bpm'):model['incoming']['grid_bpm'],
                ('[Channel1]','bpm'):model['outgoing']['grid_bpm'],
                ('[Channel2]','bpm'):model['incoming']['grid_bpm'],
                ('[Channel1]','playposition'):130.4/400,
                ('[Channel2]','playposition'):model['cue_seconds']/300,
                ('[Channel2]','quantize'):1.}
        self.writes=[]
    def advance(self,seconds):
        self.now+=seconds
        for deck in (1,2):
            g=f'[Channel{deck}]'
            if self.v.get((g,'play'),0):
                self.v[(g,'playposition')]+=seconds*self.v[(g,'bpm')]/self.v[(g,'file_bpm')]/self.v[(g,'duration')]
    def get(self,g,k):
        if k=='beat_distance':
            model=self.model['outgoing' if g=='[Channel1]' else 'incoming']
            seconds=self.v[g,'playposition']*self.v[g,'duration']
            return ((seconds-model['first_beat_seconds'])*model['grid_bpm']/60)%1.
        return self.v.get((g,k),0.)
    def set(self,g,k,v):
        self.writes.append((g,k,v));self.v[g,k]=float(v)
        if g=='[Channel2]' and k=='beatsync_tempo':
            self.v[g,'bpm']=75. if self.bad_tempo else target_grid_bpm(self.model,self.v['[Channel1]','bpm'])
        if g=='[Channel2]' and k=='quantize' and v and self.snap and self.v[g,'play']:
            self.v[g,'playposition']+=.6/300.
    def monotonic(self):
        self.advance(.001);return self.now


class SampledEngine(Engine):
    """Real source clock; 15Hz display snapshots and nonzero TCP read latency."""
    def __init__(self,model,*,read_rtt=.0,**kwargs):
        super().__init__(model,**kwargs)
        self.read_rtt=read_rtt
        self.started={'[Channel1]':0.,'[Channel2]':None}
    def get(self,g,k):
        self.advance(self.read_rtt/2)
        value=super().get(g,k)
        if k=='playposition' and self.v.get((g,'play'),0):
            q=1/15
            phase=0.027 if g=='[Channel1]' else .011
            last=math.floor((self.now+phase)/q)*q-phase
            age=min(self.now-last,self.now-self.started[g])
            value-=max(0.,age)*self.v[g,'bpm']/self.v[g,'file_bpm']/self.v[g,'duration']
        self.advance(self.read_rtt/2)
        return value
    def set(self,g,k,v):
        if k=='play' and v:self.started[g]=self.now
        return super().set(g,k,v)


class TransportEngine(SampledEngine):
    """TCP reads/writes and engine queue time all advance the source clocks."""
    def __init__(self,model,*,write_rtt=.012,queue_s=.004,callback_s=.005,**kwargs):
        super().__init__(model,**kwargs)
        self.write_rtt=write_rtt;self.queue_s=queue_s;self.callback_s=callback_s
    def monotonic(self):
        return self.now
    def get(self,g,k):
        value=super().get(g,k)
        if k=='beat_distance' and self.v.get((g,'play'),0) and self.callback_s:
            sampled=self.now-self.read_rtt/2
            age=sampled%self.callback_s
            value=(value-age*self.v[g,'bpm']/60)%1.
        return value
    def set(self,g,k,v):
        self.advance(self.write_rtt/2+self.queue_s)
        super().set(g,k,v)
        self.advance(self.write_rtt/2)


class RuntimeTests(unittest.TestCase):
    def run_start(self,m):
        with patch.object(runner.time,'sleep',side_effect=m.advance),patch.object(runner.time,'monotonic',side_effect=m.monotonic),redirect_stdout(io.StringIO()):
            runner.start_on_measured_backbeat(m,event(m.model),outgoing_bpm=m.v['[Channel1]','bpm'])

    def test_zero_intro_uses_tempo_only_sync_without_a_seek_after_start(self):
        m=Engine(spec());self.run_start(m)
        started=next(i for i,w in enumerate(m.writes) if w==('[Channel2]','play',1))
        self.assertIn(('[Channel2]','beatsync_tempo',1),m.writes)
        self.assertEqual(m.get('[Channel2]','quantize'),1.)
        self.assertEqual(m.get('[Channel2]','bpm'),150.)
        self.assertFalse(any(k in ('beatsync','beatsync_phase','beatjump_1_forward') for _,k,_ in m.writes))
        self.assertFalse(any(k=='playposition' for _,k,_ in m.writes[started:]))
        self.assertAlmostEqual(m.get('[Master]','crossfader'),-1.)

    def test_approved_delay_runs_without_a_seek_or_detector_phase_edit(self):
        s=spec();s['approved_launch_delay']={'beats':1,'author':'human','approved':True,'quote':'keep it'}
        original=copy.deepcopy(s);m=SampledEngine(s,read_rtt=.001)
        self.run_start(m)
        self.assertEqual(s,original)
        self.assert_actual_phase(m)
        start=m.writes.index(('[Channel2]','play',1))
        self.assertFalse(any(k in ('playposition','beatsync','beatsync_phase') for _,k,_ in m.writes[start:]))

    def test_approved_target_still_refuses_an_extra_engine_count_jump(self):
        s=spec();s['approved_launch_delay']={'beats':1,'author':'human','approved':True,'quote':'keep it'}
        m=Engine(s,snap=True)
        with self.assertRaises(runner.CueVerificationError):self.run_start(m)
        self.assertEqual(m.get('[Channel2]','play'),0.)
        self.assertEqual(m.get('[Master]','crossfader'),-1.)

    def test_15hz_playposition_does_not_make_a_valid_start_fail(self):
        m=SampledEngine(spec())
        self.run_start(m)
        self.assertEqual(m.get('[Channel2]','play'),1.)
        self.assertEqual(m.model['tolerance_ms'],30.)
        self.assert_actual_phase(m)

    def test_phase_check_accounts_for_sequential_tcp_read_times(self):
        m=SampledEngine(spec(),read_rtt=.008)
        self.run_start(m)
        self.assertEqual(m.get('[Channel2]','play'),1.)
        self.assert_actual_phase(m)

    def test_launch_does_not_wait_for_late_tcp_reads_before_sending_play(self):
        for read_rtt,write_rtt in [(.004,.012),(.008,.016),(.012,.020)]:
            for offset in [0.,.037,.18,.43]:
                with self.subTest(read_rtt=read_rtt,write_rtt=write_rtt,offset=offset):
                    m=TransportEngine(spec(),read_rtt=read_rtt,write_rtt=write_rtt)
                    m.advance(offset)
                    self.run_start(m)
                    self.assert_actual_phase(m)
                    self.assertEqual(m.model['tolerance_ms'],30.)
                    start=m.writes.index(('[Channel2]','play',1))
                    self.assertFalse(any(k in ('playposition','beatsync','beatsync_phase') for _,k,_ in m.writes[start:]))

    def test_stalled_deadline_is_refused_before_start(self):
        m=TransportEngine(spec(),read_rtt=.004)
        def stalled_sleep(seconds):
            m.advance(seconds+(.025 if seconds>.03 else 0.))
        with patch.object(runner.time,'sleep',side_effect=stalled_sleep),patch.object(runner.time,'monotonic',side_effect=m.monotonic):
            with self.assertRaisesRegex(runner.CueVerificationError,'scheduling stalled'):
                runner.start_on_measured_backbeat(m,event(m.model),outgoing_bpm=75.)
        self.assertNotIn(('[Channel2]','play',1),m.writes)
        self.assertEqual(m.v['[Master]','crossfader'],-1.)

    def test_slow_control_write_refuses_before_start(self):
        m=TransportEngine(spec(),write_rtt=.06)
        with self.assertRaisesRegex(runner.CueVerificationError,'write too slow'):self.run_start(m)
        self.assertNotIn(('[Channel2]','play',1),m.writes)

    def test_full_mix_cli_reports_safe_stop_without_traceback(self):
        with patch('sys.argv',['run_mix_plan','--plan','example','--dry-run']),patch.object(runner,'resolve_plan_argument',return_value='example.json'),patch.object(runner,'load_executable_plan',return_value={}),patch.object(runner,'run_plan',side_effect=runner.CueVerificationError('phase miss')),redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(SystemExit,r'\[mix\] stopped safely: phase miss'):
                runner.main()

    def assert_actual_phase(self,m):
        # Check the true engine positions, independently of the reported clock.
        error=phase_error_ms(m.model,m.v['[Channel1]','playposition']*400.,
                            m.v['[Channel2]','playposition']*300.,
                            m.v['[Channel1]','bpm'])
        self.assertLessEqual(abs(error),30.)

    def test_invalid_or_slow_fast_clock_is_refused(self):
        for fault in ['invalid_fraction','stale_slider','slow_read']:
            m=SampledEngine(spec(),read_rtt=.05 if fault=='slow_read' else 0.)
            get=m.get
            def faulty_get(g,k):
                if fault=='invalid_fraction' and k=='beat_distance':return float('nan')
                if fault=='stale_slider' and k=='playposition':return get(g,k)-.3/400.
                return get(g,k)
            with self.subTest(fault=fault),patch.object(m,'get',side_effect=faulty_get):
                with patch.object(runner.time,'monotonic',side_effect=m.monotonic):
                    with self.assertRaises(runner.CueVerificationError):
                        runner.read_source_clock(m,'[Channel1]',400.,m.model['outgoing'])

    def test_fast_source_clock_uses_grid_origin_and_survives_wrap(self):
        m=SampledEngine(spec());m.model['outgoing']['first_beat_seconds']=.132792
        m.advance(.041)
        seconds,stamp=runner.read_source_clock(m,'[Channel1]',400.,m.model['outgoing'])
        self.assertAlmostEqual(seconds,m.v['[Channel1]','playposition']*400.,delta=.003)
        self.assertGreater(stamp,0.)

    def test_engine_snap_after_start_is_detected_before_fader_open(self):
        m=Engine(spec(),snap=True)
        with self.assertRaises(runner.CueVerificationError):self.run_start(m)
        self.assertEqual(m.get('[Channel2]','play'),0.)
        self.assertEqual(m.get('[Master]','crossfader'),-1.)
        self.assertEqual(m.get('[Channel2]','quantize'),1.)

    def test_wrong_double_time_multiplier_does_not_start(self):
        m=Engine(spec(),bad_tempo=True)
        with self.assertRaises(runner.CueVerificationError):self.run_start(m)
        self.assertNotIn(('[Channel2]','play',1),m.writes)

    def test_stopped_outgoing_or_changed_grid_refuse_before_writes(self):
        for fault in ['stopped','changed']:
            m=Engine(spec(),stopped=fault=='stopped')
            if fault=='changed':m.v['[Channel2]','file_bpm']=160.
            with self.subTest(fault=fault),self.assertRaises(runner.CueVerificationError):self.run_start(m)
            self.assertEqual(m.writes,[])

    def test_source_clock_anchor_survives_different_preload_delays(self):
        e={'op':'play_body','deck':1,'source_clock_anchor':True,
           'phase_anchor':{'grid_bpm':75.,'first_beat_seconds':0.,'planned_anchor_beat_index':165}}
        endings=[]
        for start in [120.,130.4]:
            m=Engine(spec());m.v['[Channel1]','playposition']=start/400
            with patch.object(runner.time,'sleep',side_effect=m.advance),patch.object(runner.time,'monotonic',side_effect=m.monotonic),redirect_stdout(io.StringIO()):
                runner.wait_for_source_anchor(m,e)
            endings.append(m.get('[Channel1]','playposition')*400)
            self.assertEqual(m.writes,[])
        for end in endings:
            self.assertGreaterEqual(end,132.-.35*.8)
            self.assertLess(end,132.)
        self.assertLess(abs(endings[0]-endings[1]),.03)

    def test_late_source_anchor_is_refused_without_rewinding(self):
        m=Engine(spec())
        e={'op':'play_body','deck':1,'source_clock_anchor':True,
           'phase_anchor':{'grid_bpm':75.,'first_beat_seconds':0.,'planned_anchor_beat_index':150}}
        with self.assertRaises(runner.CueVerificationError):runner.wait_for_source_anchor(m,e)
        self.assertEqual(m.writes,[])

    def test_source_clock_does_not_replace_skips_or_handoffs(self):
        e={'op':'play_body','source_clock_anchor':True,'handoff':{'to_deck':2}}
        with self.assertRaises(ValueError):runner.source_clock_anchor(e)

    def test_measured_window_cannot_be_extrapolated_across_the_song(self):
        s=spec();s['outgoing'].update(window_start_seconds=0.,window_end_seconds=100.)
        m=Engine(s)
        with self.assertRaises(runner.CueVerificationError):self.run_start(m)
        self.assertNotIn(('[Channel2]','play',1),m.writes)

    def test_invalid_clock_duration_or_cue_refuses_before_writes(self):
        for fault in ['duration','cue','crossfader']:
            s=spec()
            if fault=='cue':s['cue_seconds']=400.
            m=Engine(s)
            if fault=='duration':m.v['[Channel2]','duration']=float('nan')
            if fault=='crossfader':m.v['[Master]','crossfader']=float('nan')
            with self.subTest(fault=fault),self.assertRaises(runner.CueVerificationError):self.run_start(m)
            self.assertEqual(m.writes,[])

    def test_failed_preflight_read_uses_existing_full_run_cleanup_error_type(self):
        m=Engine(spec())
        with patch.object(m,'get',side_effect=OSError('read lost')):
            with self.assertRaises(runner.CueVerificationError):self.run_start(m)
        self.assertEqual(m.writes,[])

    def test_old_recipe_does_not_opt_in(self):
        self.assertIsNone(runner.backbeat_options({'op':'transition','moves':['sync']}))

    def test_full_transition_uses_measured_start_without_post_play_sync(self):
        m=Engine(spec())
        with patch.object(runner,'_wait_for_anchor_or_continue',return_value=True),patch.object(runner.time,'sleep',side_effect=m.advance),patch.object(runner.time,'monotonic',side_effect=m.monotonic),redirect_stdout(io.StringIO()):
            runner.perform_transition(m,event(m.model),port=9995)
        self.assertEqual(m.get('[Master]','crossfader'),1.)
        self.assertEqual(m.get('[Channel1]','play'),0.)
        self.assertFalse(any(k in ('beatsync','beatsync_phase') for _,k,_ in m.writes))

    def test_legacy_transition_retains_post_play_sync_control_sequence(self):
        m=Engine(spec());e=event();e.pop('backbeat_start')
        with patch.object(runner,'_wait_for_anchor_or_continue',return_value=True),patch.object(runner.time,'sleep',side_effect=m.advance),patch.object(runner.time,'monotonic',side_effect=m.monotonic),redirect_stdout(io.StringIO()):
            runner.perform_transition(m,e,port=9995)
        play=m.writes.index(('[Channel2]','play',1))
        sync=m.writes.index(('[Channel2]','beatsync',1))
        self.assertLess(play,sync)
        self.assertFalse(any(k=='beatsync_tempo' for _,k,_ in m.writes))

    def test_conflicting_jump_or_nudge_is_rejected(self):
        for fault in ['jump','nudge']:
            e=event()
            if fault=='jump':e['moves'].append('snare_align')
            else:e['incoming_nudge_ms']=20
            with self.subTest(fault=fault),self.assertRaises(ValueError):runner.backbeat_options(e)

    def test_invalid_model_full_run_refused_before_connect(self):
        e=event();e['backbeat_start']['incoming']['confidence']=0.
        with patch('hands.source_cutoffs.prepare_plan',side_effect=lambda p,**kw:p),patch.object(runner,'MixxxControl') as control:
            with self.assertRaises(ValueError):runner.run_plan({'events':[e]},port=9995,dry_run=False,max_events=None)
            control.assert_not_called()


if __name__=='__main__':unittest.main()
