"""Cue-preserving backbeat entrances and live position evidence.

The Rust solver chooses the entrance; this module owns the existing Python
control connection. No audible-deck beat jumps, and no post-launch beatsync
that could undo the solved entrance. Logs describe positions, not live audio.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import math
import subprocess
import time
import uuid
from collections import deque
from statistics import median
from datetime import datetime, timezone
from pathlib import Path

from brain.rhythm import FADE_POLICY_VERSION, alignment, identity_matches, phase_error, section_at
from hands.transition import wait_for_next_beat

_TRACE = contextvars.ContextVar("backbeat_trace", default=None)


class FadeEnvelope:
    """Continuous fade; only corroborated physical audio limits may shorten it."""
    def __init__(self, now: float, seconds: float):
        self.start_at = now
        self.end_at = now + max(0.0, seconds)
        self.start_progress = 0.0

    def progress(self, now: float) -> float:
        duration = self.end_at - self.start_at
        fraction = 1.0 if duration <= 0 else min(1.0, max(0.0, (now - self.start_at) / duration))
        return self.start_progress + (1.0 - self.start_progress) * fraction

    def shorten(self, now: float, seconds: float) -> bool:
        end = now + max(0.0, seconds)
        if end >= self.end_at - 0.02:
            return False
        self.start_progress = self.progress(now)
        self.start_at, self.end_at = now, end
        return True


def classify_errors(errors, tolerance_ms=60.0):
    """Require several consistent samples; never average opposite errors to zero."""
    valid = [v for v in errors if v is not None and math.isfinite(v)]
    if len(valid) < 3:
        return "unverified", None
    center = median(valid)
    if sum(abs(v - center) <= 0.060 for v in valid) < 3:
        return "unverified", center
    if abs(center) * 1000 <= tolerance_ms and sum(abs(v) * 1000 <= tolerance_ms for v in valid) >= 3:
        return "verified", center
    if all(v > 0.100 for v in valid) or all(v < -0.100 for v in valid):
        return "mismatch", center
    return "unverified", center


def evidence(kind: str, **fields) -> None:
    handle = _TRACE.get()
    if handle:
        handle.write(json.dumps({"event":kind,"monotonic":time.monotonic(),**fields}, allow_nan=False)+"\n")
        handle.flush()


@contextlib.contextmanager
def trace_run(plan: dict):
    root = Path(__file__).resolve().parents[1]/"brain/data/runs"
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = root/f"backbeat-{stamp}-{uuid.uuid4().hex[:8]}.jsonl"
    with path.open("x") as handle:
        token = _TRACE.set(handle)
        try:
            evidence("run", plan_id=plan.get("plan_id"), plan_slug=plan.get("plan_slug"),
                     evidence_kind="analyzed_audio_and_live_positions_not_recording", backbeat=plan.get("backbeat"),
                     fade_policy_version=FADE_POLICY_VERSION, automatic_short_handoffs=0)
            print(f"Backbeat (snare/clap) position log: {path}")
            print(f"Crossfade policy: gradual-v{FADE_POLICY_VERSION} — zero automatic backbeat-triggered short handoffs; keep the planned blend.")
            yield path
        finally:
            evidence("run_end")
            _TRACE.reset(token)


def snapshot(mixxx, group: str, rhythm: dict) -> dict:
    playing = float(mixxx.get(group,"play")) >= 0.5
    duration = float(mixxx.get(group,"duration"))
    bpm = float(mixxx.get(group,"bpm"))
    native_bpm = float(mixxx.get(group,"file_bpm"))
    rate = float(mixxx.get(group,"rate_ratio"))
    before = time.monotonic()
    fraction = float(mixxx.get(group,"playposition"))
    after = time.monotonic()
    if not all(math.isfinite(v) for v in (duration,bpm,native_bpm,rate,fraction)) or duration <= 0 or bpm <= 0 or rate <= 0 or not 0 <= fraction <= 1:
        raise ValueError(f"{group} has no valid live position/tempo")
    if abs(native_bpm-float(rhythm["bpm"])) > max(0.1,float(rhythm["bpm"])*0.005):
        raise ValueError(f"{group} source beatgrid BPM changed; reanalyze and rebuild")
    if abs(duration-rhythm["duration_seconds"]) > max(0.25,duration*0.002):
        raise ValueError(f"{group} audio duration differs from prepared evidence")
    if after-before > 0.080:
        raise ValueError(f"{group} position read latency too high to certify alignment")
    return {"seconds":duration*fraction, "rate":rate,
            "playing":playing,
            "at":(before+after)/2, "roundtrip_seconds":after-before, "duration":duration}


class Guard:
    def __init__(self, mixxx, event):
        self.mixxx, self.event = mixxx, event
        self.metadata = event["backbeat"]
        self.out_group, self.in_group = f"[Channel{event['from_deck']}]", f"[Channel{event['to_deck']}]"
        self.outgoing, self.incoming = self.metadata.get("outgoing"), self.metadata.get("incoming")
        self.ready = False
        self.reason = self.metadata.get("reason", "unresolved backbeat")
        self.last_check = -math.inf
        self.saved = {}
        self.verification = "unverified"
        self.observations = deque(maxlen=3)
        self.observation_kind = "unverified"
        self.end_at = None
        self.limit_reason = None

    def save(self, key, value):
        self.saved[key] = self.mixxx.get(self.in_group,key)
        self.mixxx.set(self.in_group,key,value)

    def restore(self):
        for key,value in self.saved.items():
            try:
                self.mixxx.set(self.in_group,key,value)
            except (OSError,RuntimeError,ValueError) as error:
                print(f"  WARNING: could not restore {self.in_group} {key}: {error}")
        self.saved.clear()

    def observe(self, stage):
        self.observation_kind = "unverified"
        if not self.outgoing or not self.incoming:
            return None
        out = snapshot(self.mixxx,self.out_group,self.outgoing)
        inc = snapshot(self.mixxx,self.in_group,self.incoming)
        if not out["playing"] or not inc["playing"]:
            return None
        # Compare positions at one time despite sequential TCP requests.
        at = max(out["at"],inc["at"])
        out_s = out["seconds"]+(at-out["at"])*out["rate"]
        in_s = inc["seconds"]+(at-inc["at"])*inc["rate"]
        error = phase_error(self.outgoing,self.incoming,out_s,in_s,out["rate"],inc["rate"])
        if error is not None:
            self.observation_kind = "measured"
        else:
            sections = section_at(self.outgoing, out_s), section_at(self.incoming, in_s)
            if all(s and s["confidence"] >= 0.45 for s in sections):
                cycles = [s["cadence_beats"] * 60 / r["bpm"] / rate
                          for s, r, rate in zip(sections, (self.outgoing, self.incoming), (out["rate"], inc["rate"]))]
                if abs(cycles[0] - cycles[1]) > 0.010:
                    self.observation_kind = "incompatible"
        evidence("position", stage=stage, from_deck=self.event["from_deck"], to_deck=self.event["to_deck"],
                 outgoing_seconds=out_s,incoming_seconds=in_s,outgoing_rate=out["rate"],incoming_rate=inc["rate"],
                 error_ms=None if error is None else error*1000, observation_kind=self.observation_kind)
        return error

    def refresh_limit(self):
        """Transport bounds are independent of uncertain percussion evidence."""
        try:
            before = time.monotonic()
            playing = self.mixxx.get(self.out_group, "play") >= 0.5
            duration = float(self.mixxx.get(self.out_group, "duration"))
            fraction = float(self.mixxx.get(self.out_group, "playposition"))
            position_at = time.monotonic()
            rate = float(self.mixxx.get(self.out_group, "rate_ratio"))
            now = time.monotonic()
            if not all(math.isfinite(v) for v in (duration, fraction, rate)) or duration <= 0 or rate <= 0 or not 0 <= fraction <= 1:
                return
            remaining = max(0.0, duration * (1 - fraction) / rate - (now - before) - 0.15) if playing else 0.0
            candidate_end = now + remaining
            if not playing or self.end_at is None or candidate_end < self.end_at - 0.25:
                # A single stale control read must never slam the fader. Confirm
                # any materially earlier deadline (including near-EOF, not just
                # fraction == 1), or a genuinely stationary stopped transport.
                initial = fraction
                for _ in range(2):
                    time.sleep(0.04)
                    check_playing = self.mixxx.get(self.out_group, "play") >= 0.5
                    check_position = float(self.mixxx.get(self.out_group, "playposition"))
                    if not math.isfinite(check_position) or not 0 <= check_position <= 1:
                        return
                    if playing:
                        expected = min(1.0, initial + (time.monotonic() - position_at) * rate / duration)
                        if abs(check_position - expected) * duration > 0.20:
                            return
                    elif check_playing or abs(check_position - initial) * duration > 0.010:
                        return
                now = time.monotonic()
            self.end_at = candidate_end
            self.limit_reason = "remaining audio on outgoing deck" if playing else "outgoing deck stopped"
        except (OSError, ValueError, RuntimeError):
            pass  # A failed read is not evidence that audio has ended.

    def seconds_left(self, now=None):
        return None if self.end_at is None else max(0.0, self.end_at - (time.monotonic() if now is None else now))

    def check(self):
        now = time.monotonic()
        if now-self.last_check < 0.5:
            return self.verification == "verified"
        self.last_check = now
        self.refresh_limit()
        try:
            error = self.observe("overlap")
        except (OSError, ValueError, RuntimeError) as failure:
            error = None
            self.observation_kind = "unverified"
            evidence("observation_unavailable", stage="overlap", reason=str(failure))
        self.observations.append((error, self.observation_kind))
        classification, _ = classify_errors([v for v, _ in self.observations], self.metadata.get("tolerance_ms", 60))
        incompatible = len(self.observations) == 3 and all(k == "incompatible" for _, k in self.observations)
        if classification == "mismatch" or incompatible:
            if self.verification != "mismatch":
                self.reason = "sustained measured backbeat mismatch during overlap"
                print(f"  backbeat: {self.reason}; keeping planned gradual blend (needs review)")
                evidence("mismatch", reason=self.reason, verification="mismatch", planned_fade_retained=True)
            self.verification = "mismatch"
        elif error is None or classification == "unverified":
            if self.verification != "unverified":
                print("  backbeat: local verification unavailable; keeping the gradual blend")
                evidence("unverified", stage="overlap", reason="local evidence unavailable; planned fade retained")
            self.verification = "unverified"
        elif classification == "verified":
            self.verification = "verified"
        return self.verification == "verified"


def launch(mixxx, event: dict, *, port: int) -> Guard:
    guard = Guard(mixxx,event)
    meta = event["backbeat"]
    try:
        guard.save("volume",0.0)
        guard.save("quantize",0.0)
        guard.save("sync_enabled",0.0)
        # Tempo only; beatsync after starting would move the selected cue phase.
        if event.get("incoming_bpm_target") is None:
            mixxx.set(guard.in_group,"beatsync_tempo",1)
            # Tempo propagation runs on Mixxx's engine callback. The solver
            # must see its settled rate, not the pre-command readback.
            time.sleep(0.05)
        initial_duration = float(mixxx.get(guard.in_group,"duration"))
        initial_fraction = float(mixxx.get(guard.in_group,"playposition"))
        if initial_duration <= 0 or not 0 <= initial_fraction < 1:
            raise ValueError("incoming cue is not seekable")
        cue_seconds = initial_fraction*initial_duration
        incoming_started = False
        # Re-evaluate on live positions even when preview was uncertain: an EOF
        # clamp or delay can put the outgoing deck in another analyzed section.
        if guard.outgoing and guard.incoming and not all(identity_matches(r, meta[k]) for r,k in ((guard.outgoing,"outgoing_id"),(guard.incoming,"incoming_id"))):
            guard.reason = "audio identity changed or missing; rebuild the mix"
            guard.outgoing = guard.incoming = None
        if guard.outgoing and guard.incoming:
            for attempt in range(2):
                try:
                    out = snapshot(mixxx,guard.out_group,guard.outgoing)
                    inc = snapshot(mixxx,guard.in_group,guard.incoming)
                    if not out["playing"]:
                        raise ValueError("outgoing deck reports stopped; cannot time entrance")
                    now = time.monotonic()
                    source = out["seconds"]+(now-out["at"])*out["rate"]
                    overlap = float(event.get("transition_beats") or 16)*60/(guard.outgoing["bpm"]*out["rate"])
                    decision = alignment(guard.outgoing,guard.incoming,source,cue_seconds,out["rate"],inc["rate"],overlap)
                except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
                    guard.reason = f"live alignment unavailable: {error}"
                    break
                deadline = now+decision["delay_seconds"]
                evidence("entrance", attempt=attempt, outgoing_id=meta["outgoing_id"], incoming_id=meta["incoming_id"],
                         outgoing_seconds=source,incoming_seconds=cue_seconds,decision=decision)
                # If computing/reading took too long, choose the next same-phase
                # cycle rather than fire a stale launch deadline.
                if decision["cycle_seconds"] <= 0:
                    guard.reason = decision["reason"]
                    break
                while deadline < time.monotonic()-0.015:
                    deadline += decision["cycle_seconds"]
                if source+(deadline-now)*out["rate"] > out["duration"]-0.15:
                    guard.reason = "not enough remaining audio for a delayed entrance"
                    break
                while (remaining := deadline-time.monotonic()) > 0:
                    time.sleep(min(remaining,0.010))
                mixxx.set(guard.in_group,"play",1)
                incoming_started = True
                if decision["status"] != "ready":
                    guard.verification = "mismatch" if decision["status"] == "incompatible" else "unverified"
                    guard.reason = decision["reason"]
                    break
                time.sleep(0.12)
                errors = []
                for sample in range(5):
                    try:
                        errors.append(guard.observe("before_fader"))
                    except (OSError, RuntimeError, ValueError) as failure:
                        errors.append(None)
                        evidence("observation_unavailable", stage="before_fader", reason=str(failure))
                    if sample < 4:
                        time.sleep(0.04)
                guard.verification, error = classify_errors(errors, meta.get("tolerance_ms", 60))
                evidence("entrance_verification", attempt=attempt, classification=guard.verification,
                         median_error_ms=None if error is None else error * 1000,
                         errors_ms=[None if v is None else v * 1000 for v in errors])
                if guard.verification == "verified":
                    guard.ready = True
                    guard.reason = "position_verified"
                    print(f"  backbeat: positions verified ({error*1000:+.0f} ms median); opening gradual blend")
                    evidence("position_verified", error_ms=error*1000,attempt=attempt)
                    break
                guard.reason = ("sustained measured entrance mismatch" if guard.verification == "mismatch"
                                else "entrance verification inconclusive")
                # At most one muted retry on actual measured timing. If still
                # inconclusive, keep the timed launch, not an unrelated re-start.
                if attempt == 1 or error is None:
                    break
                mixxx.set(guard.in_group,"play",0)
                mixxx.set(guard.in_group,"playposition",initial_fraction)
                incoming_started = False
                time.sleep(0.05)
        if not guard.ready:
            print(f"  backbeat: {guard.verification} — {guard.reason}; keeping planned gradual blend")
            evidence(guard.verification, reason=guard.reason,
                     verification=guard.verification, outgoing_id=meta.get("outgoing_id"), incoming_id=meta.get("incoming_id"))
            if not incoming_started:
                try:
                    if mixxx.get(guard.out_group,"play") >= 0.5:
                        wait_for_next_beat(port,guard.out_group,timeout_s=2.0)
                except TimeoutError:
                    pass
                mixxx.set(guard.in_group,"play",1)
        guard.refresh_limit()
        # The crossfader is still on the outgoing side. The caller now opens it.
        mixxx.set(guard.in_group,"volume",guard.saved["volume"])
        return guard
    except BaseException:
        mixxx.set(guard.in_group,"play",0)
        guard.restore()
        raise
