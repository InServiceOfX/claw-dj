"""Measured entrances: real Rust solver, simulated transport, no live Mixxx."""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from brain import rhythm
from brain.preview_transitions import transition_specs
from hands import backbeat
from hands.run_mix_plan import perform_transition
from hands.transition import wait_for_beats


def pattern(phase=1.0, cadence=2.0, confidence=0.95):
    return {"version":1, "bpm":120.0,"first_beat_seconds":0.0,"duration_seconds":200.0,
            "onsets":[{"seconds":(phase+i*cadence)*0.5,"strength":2.0} for i in range(200)],
            "sections":[{"start_seconds":0.0,"end_seconds":200.0,"cadence_beats":cadence,
                         "phase_beats":phase,"confidence":confidence,"coverage":1.0,"spread_beats":0.0,"source":"fixture"}]}


def event(outgoing=None, incoming=None, from_deck=1, to_deck=2):
    return {"op":"transition","from_deck":from_deck,"to_deck":to_deck,
            "from_track":"A — One","to_track":"B — Two","technique":"smooth_blend",
            "moves":["sync","snare_align_back","crossfade"],"transition_beats":16,
            "backbeat":{"version":1,"status":"ready","outgoing_id":"a","incoming_id":"b",
                        "outgoing":outgoing or pattern(0),"incoming":incoming or pattern(1),
                        "fallback_beats":2,"tolerance_ms":60}}


class Clock:
    def __init__(self): self.now=0.0
    def monotonic(self): return self.now
    def sleep(self, seconds): self.now+=max(0,seconds)


class Transport:
    def __init__(self, clock, latency=0.005):
        self.clock, self.latency = clock, latency
        self.values={('[Master]','crossfader'):-1.0}
        self.positions={1:8.0,2:0.0}
        self.at=clock.now
        self.writes=[]
        self.drift_at=None
        for n in (1,2):
            for k,v in {'bpm':120.0,'duration':200.0,'play':float(n==1),'volume':0.8,'quantize':1.0,'sync_enabled':0.0}.items():
                self.values[(f'[Channel{n}]',k)]=v

    def advance(self):
        self.clock.sleep(self.latency)
        elapsed=self.clock.now-self.at
        for n in (1,2):
            g=f'[Channel{n}]'
            if self.values[(g,'play')]:
                self.positions[n]+=elapsed*self.values[(g,'bpm')]/self.values.get((g,'file_bpm'),120)
        self.at=self.clock.now
        if self.drift_at is not None and self.clock.now>self.drift_at:
            self.positions[2]+=0.25
            self.drift_at=None

    def get(self, group, key):
        self.advance()
        if key=='playposition': return self.positions[int(group[8])]/self.values[(group,'duration')]
        if key=='file_bpm': return self.values.get((group,'file_bpm'),120.0)
        if key=='rate_ratio': return self.values[(group,'bpm')]/self.values.get((group,'file_bpm'),120.0)
        return self.values.get((group,key),0.0)

    def set(self,group,key,value):
        self.advance()
        self.writes.append((group,key,value,self.clock.now))
        if key=='playposition': self.positions[int(group[8])]=value*self.values[(group,'duration')]
        elif key=='beatsync_tempo':
            other='[Channel1]' if group=='[Channel2]' else '[Channel2]'
            self.values[(group,'bpm')]=self.values[(other,'bpm')]
        else: self.values[(group,key)]=value


class BackbeatTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock()
        self.patches=[patch('hands.backbeat.time.monotonic',self.clock.monotonic),
                      patch('hands.backbeat.time.sleep',self.clock.sleep),
                      patch('hands.backbeat.identity_matches',return_value=True),
                      patch('hands.backbeat.wait_for_next_beat')]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def test_later_overlap_evidence_times_weak_entrance_without_shortening_fade(self):
        for from_deck, to_deck in ((1, 2), (2, 1)):
            with self.subTest(from_deck=from_deck), redirect_stdout(io.StringIO()):
                self.clock.now = 0
                mixxx = Transport(self.clock)
                mixxx.positions = {from_deck: 8.0, to_deck: 0.0}
                mixxx.values[('[Master]', 'crossfader')] = -1 if from_deck == 1 else 1
                for deck in (1, 2):
                    mixxx.values[(f'[Channel{deck}]', 'play')] = float(deck == from_deck)
                outgoing = pattern(0)
                strong = outgoing['sections'][0]
                outgoing['sections'] = [
                    {**strong, 'end_seconds': 12.0, 'confidence': 0.40},
                    {**strong, 'start_seconds': 12.0},
                ]
                blend = event(outgoing, pattern(1), from_deck, to_deck)
                blend['transition_beats'] = 32
                with patch('hands.backbeat.evidence') as log:
                    perform_transition(mixxx, blend, port=9995)
                entrances = [c.kwargs['decision'] for c in log.call_args_list if c.args[0] == 'entrance']
                self.assertIn('later overlap backbeats', entrances[0]['reason'])
                self.assertEqual(entrances[0]['status'], 'uncertain')
                self.assertEqual(entrances[0]['cycle_seconds'], 1.0)
                measured = [c.kwargs['error_ms'] for c in log.call_args_list
                            if c.args[0] == 'position' and c.kwargs.get('error_ms') is not None]
                self.assertGreater(len(measured), 3)
                self.assertTrue(all(abs(v) <= 60 for v in measured), measured)
                self.assertFalse(any(k in {'playposition', 'beatsync', 'beatjump_1_forward'}
                                     for _, k, _, _ in mixxx.writes))
                self.assertGreater(self.clock.now, 16)

    def test_three_track_chain_across_variable_load_and_command_delays(self):
        for delay in (0.0,0.21,0.78,2.2):
            for latency in (0.001,0.012,0.025):
                with self.subTest(load_delay=delay,latency=latency), redirect_stdout(io.StringIO()):
                    self.clock.now=0
                    mixxx=Transport(self.clock,latency)
                    mixxx.positions[1]+=delay
                    first=event()
                    with patch('hands.backbeat.evidence') as log:
                        perform_transition(mixxx,first,port=9995)
                        self.assertTrue(any(c.args[0]=='position_verified' for c in log.call_args_list))
                        # Second track keeps playing through load work and body.
                        self.clock.sleep(delay+16)
                        mixxx.advance()
                        mixxx.positions[1]=0.0
                        next_event=event(pattern(1),pattern(1),2,1)
                        perform_transition(mixxx,next_event,port=9995)
                        verified=[c for c in log.call_args_list if c.args[0]=='position_verified']
                        self.assertEqual(len(verified),2)
                        self.assertTrue(all(abs(c.kwargs['error_ms'])<=60 for c in verified))
                    self.assertFalse(any(k in {'beatjump_1_forward','beatsync','beatsync_phase','playposition'} for _,k,_,_ in mixxx.writes))
                    self.assertEqual(mixxx.values[('[Channel1]','quantize')],1)
                    self.assertEqual(mixxx.values[('[Channel2]','quantize')],1)
                    self.assertEqual(mixxx.values[('[Channel2]','volume')],0.8)

    def test_unknown_rhythm_retains_gradual_blend_without_claiming_verified(self):
        mixxx=Transport(self.clock)
        with redirect_stdout(io.StringIO()), patch('hands.backbeat.evidence') as log:
            perform_transition(mixxx,event(incoming=pattern(confidence=0.1)),port=9995)
        self.assertGreater(self.clock.now,8.0)
        self.assertTrue(any(c.args[0]=='unverified' for c in log.call_args_list))
        self.assertFalse(any(c.args[0]=='position_verified' for c in log.call_args_list))

    def test_drift_is_reported_without_shortening_or_jumping(self):
        mixxx=Transport(self.clock)
        mixxx.drift_at=2.0
        with redirect_stdout(io.StringIO()),patch('hands.backbeat.evidence') as log:
            perform_transition(mixxx,event(),port=9995)
        self.assertGreater(self.clock.now,8.0)
        self.assertTrue(any(c.args[0]=='mismatch' for c in log.call_args_list))
        self.assertFalse(any(k=='playposition' for _,k,_,_ in mixxx.writes))

    def test_volume_stays_closed_until_position_verification(self):
        mixxx=Transport(self.clock)
        def verify(kind, **fields):
            if kind=='position_verified':
                self.assertEqual(mixxx.values[('[Channel2]','volume')],0)
                self.assertEqual(mixxx.values[('[Master]','crossfader')],-1)
        with redirect_stdout(io.StringIO()),patch('hands.backbeat.evidence',side_effect=verify):
            guard=backbeat.launch(mixxx,event(),port=9995)
        self.assertTrue(guard.ready)
        guard.restore()

    def test_interrupt_restores_controls_and_stops_muted_incoming(self):
        mixxx=Transport(self.clock)
        with patch('hands.backbeat.alignment',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): backbeat.launch(mixxx,event(),port=9995)
        self.assertEqual(mixxx.values[('[Channel2]','play')],0)
        self.assertEqual(mixxx.values[('[Channel2]','volume')],0.8)
        self.assertEqual(mixxx.values[('[Channel2]','quantize')],1)
        self.assertEqual(mixxx.values[('[Channel2]','sync_enabled')],0)

    def test_solver_timeout_falls_back(self):
        import subprocess
        with patch('hands.backbeat.alignment',side_effect=subprocess.TimeoutExpired('solver',10)),redirect_stdout(io.StringIO()):
            guard=backbeat.launch(Transport(self.clock),event(),port=9995)
        self.assertFalse(guard.ready)
        guard.restore()

    def test_changed_source_grid_and_excessive_latency_fail_closed(self):
        for latency, native in ((0.005,240.0),(0.100,120.0)):
            mixxx=Transport(self.clock,latency)
            mixxx.values[('[Channel2]','file_bpm')]=native
            with redirect_stdout(io.StringIO()):
                guard=backbeat.launch(mixxx,event(),port=9995)
            self.assertFalse(guard.ready)
            self.assertIn('live alignment unavailable',guard.reason)
            guard.restore()

    def test_trusted_body_still_observes_live_grid(self):
        conn=MagicMock()
        conn.__enter__.return_value=conn
        conn.get.side_effect=lambda group,key: 120.0 if key=='bpm' else 1.0
        conn.events.return_value=iter([{'value':v} for _ in range(8) for v in (1,0)])
        anchor={'grid_bpm':120,'first_beat_seconds':0,'target_beat_mod4':0}
        with patch('hands.transition.MixxxControl',return_value=conn),patch('hands.transition._current_grid_beat_index',return_value=11) as index,redirect_stdout(io.StringIO()):
            wait_for_beats(9995,'[Channel1]',8,phase_anchor=anchor,trust_ride_beats=True)
        index.assert_called_once()


class BuildEvidenceTests(unittest.TestCase):
    def plan(self):
        tracks=[{'track_id':k,'artist':k,'title':k,'bpm':120,'cue_seconds':0,'cue_beat_index':0} for k in ('a','b','c')]
        events=[{'op':'load','deck':1,**tracks[0]},{'op':'load','deck':2,**tracks[1]},
                {'op':'play_body','deck':1,'track':'a — a','beats':16},
                {'op':'preload_after_transition','deck':1,**tracks[2]},event(),
                {'op':'play_body','deck':2,'track':'b — b','beats':16},event(from_deck=2,to_deck=1)]
        events[4].update(from_track='a — a',to_track='b — b')
        events[-1].update(from_track='b — b',to_track='c — c')
        return {'tracks':tracks,'events':events,'segments':[{},{}]}

    def test_both_profiles_prepare_first_transition_and_chain_preview(self):
        for profile in ('club-set','mix-to-listen'):
            plan=self.plan();plan['profile']={'name':profile}
            rhythm.prepare_plan(plan,analyze=lambda track,**kw:pattern())
            self.assertEqual(plan['backbeat']['ready'],2)
            transitions=[e for e in plan['events'] if e['op']=='transition']
            self.assertGreater(transitions[1]['backbeat']['preview']['outgoing_seconds'],16)
            self.assertFalse(any('snare_align' in m for e in transitions for m in e['moves']))
            specs=transition_specs(plan['events'],{t['track_id']:t for t in plan['tracks']})
            self.assertEqual(specs[1]['out_start_s'],transitions[1]['backbeat']['preview']['outgoing_seconds']-12)

    def test_unverified_preview_advances_next_track_by_full_gradual_overlap(self):
        plan=self.plan()
        rhythm.prepare_plan(plan,analyze=lambda track,**kw:pattern(confidence=0.1 if track['track_id']=='a' else 0.95))
        transitions=[e for e in plan['events'] if e['op']=='transition']
        self.assertEqual(transitions[0]['backbeat']['status'],'fallback')
        self.assertEqual(transitions[0]['backbeat']['preview']['overlap_seconds'],8)
        self.assertGreater(transitions[1]['backbeat']['preview']['outgoing_seconds'],16)

    def test_missing_audio_is_explicit_not_false_ready(self):
        plan=self.plan()
        rhythm.prepare_plan(plan,analyze=MagicMock(side_effect=FileNotFoundError('missing audio')))
        self.assertEqual(plan['backbeat']['ready'],0)
        self.assertEqual(plan['backbeat']['fallback'],2)
        self.assertIn('a',plan['backbeat']['analysis_failures'])

    def test_failed_analysis_still_advances_nominal_blend_and_next_preview(self):
        plan = self.plan()
        for track in plan['tracks']:
            track['duration_seconds'] = 200
        def analyze(track, **kwargs):
            if track['track_id'] == 'a':
                raise RuntimeError('decoder unavailable')
            return pattern()
        rhythm.prepare_plan(plan, analyze=analyze)
        first, second = [e['backbeat'] for e in plan['events'] if e['op'] == 'transition']
        self.assertEqual(first['verification'], 'unverified')
        self.assertNotIn('outgoing', first)
        self.assertEqual(first['preview']['outgoing_seconds'], 8.5)
        self.assertEqual(first['preview']['overlap_seconds'], 8)
        self.assertGreaterEqual(second['preview']['outgoing_seconds'], 16.5)

    def test_off_grid_cue_retains_source_grid_without_moving_cue(self):
        plan=self.plan()
        plan['tracks'][0].pop('cue_beat_index')
        plan['tracks'][0]['cue_seconds']=0.12
        plan['tracks'][0]['source_grid']={'grid_bpm':120,'first_beat_seconds':0}
        analyze=MagicMock(side_effect=lambda track,**kw:pattern())
        rhythm.prepare_plan(plan,analyze=analyze)
        self.assertEqual(analyze.call_count,3)
        self.assertEqual(plan['tracks'][0]['cue_seconds'],0.12)

    def test_audit_keeps_prediction_separate_from_live_position_evidence(self):
        from brain.backbeat_audit import audit
        plan=self.plan()
        rhythm.prepare_plan(plan,analyze=lambda track,**kw:pattern())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'plan.json';rhythm.atomic_json(source,plan)
            log=root/'positions.jsonl'
            log.write_text(json.dumps({'event':'position','error_ms':-12})+'\n')
            report=audit(source,root/'audit',telemetry=log)
            self.assertEqual(len(report['transitions']),2)
            self.assertEqual(report['live_position_evidence']['max_absolute_error_ms'],12)
            self.assertFalse(report['live_position_evidence']['audio_verified'])
            self.assertIn('not_live_or_ear_verified',report['evidence_kind'])
            self.assertTrue((root/'audit'/'index.html').is_file())

    def test_independent_model_downbeats_are_adopted_only_with_agreement(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);audio=root/'test.raw';audio.write_bytes(b'audio-fixture')
            marker=root/'annotations'/f'{rhythm._digest(audio)}.json'
            model={'beats':[i*0.5 for i in range(64)],'downbeats':[i*2.0 for i in range(16)]}
            rhythm.atomic_json(marker,{'beat_model':model})
            with patch('brain.rhythm.core',side_effect=lambda *a,**kw:copy.deepcopy(pattern())):
                result=rhythm.analyze_track({'track_id':str(audio),'bpm':120},first_beat=0,cache_dir=root)
                self.assertEqual(result['sections'][0]['downbeat_seconds'],0)
                model['beats']=[b+0.2 for b in model['beats']]
                rhythm.atomic_json(marker,{'beat_model':model})
                result=rhythm.analyze_track({'track_id':str(audio),'bpm':120},first_beat=0,cache_dir=root)
                self.assertEqual(result['sections'][0]['confidence'],0)
                self.assertNotIn('downbeat_seconds',result['sections'][0])

    def test_cache_invalidated_by_audio_grid_and_reviewed_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);audio=root/'test.raw';audio.write_bytes(b'audio-fixture')
            track={'track_id':str(audio),'bpm':120}
            with patch('brain.rhythm.core',side_effect=lambda *a,**kw:copy.deepcopy(pattern())) as core:
                one=rhythm.analyze_track(track,first_beat=0,cache_dir=root)
                rhythm.analyze_track(track,first_beat=0,cache_dir=root)
                self.assertEqual(core.call_count,1)
                rhythm.analyze_track(track,first_beat=0.1,cache_dir=root)
                self.assertEqual(core.call_count,2)
                marker=root/'annotations'/f"{one['identity']['audio_sha256']}.json"
                rhythm.atomic_json(marker,{'regions':[{'start_seconds':0,'end_seconds':16,'backbeat_seconds':0,'cadence_beats':2,'author':'test'}]})
                reviewed=rhythm.analyze_track(track,first_beat=0,cache_dir=root)
                self.assertEqual(core.call_count,3)
                self.assertEqual(rhythm.section_at(reviewed,4)['source'],'human_reviewed')
                self.assertTrue(rhythm.identity_matches(one,str(audio)))
                audio.write_bytes(b'changed-audio')
                self.assertFalse(rhythm.identity_matches(one,str(audio)))
                rhythm.analyze_track(track,first_beat=0,cache_dir=root)
                self.assertEqual(core.call_count,4)


if __name__=='__main__': unittest.main()
