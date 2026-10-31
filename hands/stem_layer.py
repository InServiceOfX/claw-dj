"""Play one vocal over one instrumental, live in Mixxx, for the vocal's length.

The plan comes from brain.stem_layer_plan (measured snare timing in source
seconds; nothing rendered). Deck 1 plays the instrumental (bed) from its cue
at the vocal's tempo with keylock on; the vocal plays at its own speed on
deck 2, so the voice is never time-stretched. The crossfader sits at center
(additive curve: both decks at full) for the whole layer, not a crossfade.

Timing: both records carry beat maps (brain.stem_layer_plan), so the plan
knows where every beat really falls, even on a drifting, live-drummed record.
The vocal deck starts off the instrumental's audio-callback source clock one
bar before its first word. From then on the instrumental's deck rides its
tempo slider 20 times a second (feed-forward from both beat maps plus a
gentle correction), the way a DJ rides the pitch, so its snares stay on the
vocal's. After the last word the instrumental fades over 16 beats (gentle,
never a cut).

    python -m hands.stem_layer --vocal TRACK_ID --bed TRACK_ID [--vocal-from 20.5]
        [--count-shift 2] [--lead-bars 8] [--port 9995] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

from hands.mixxx_control import DEFAULT_PORT, MixxxControl

BED_DECK = 1
VOCAL_DECK = 2
EQ_KEYS = {"low": "parameter1", "mid": "parameter2", "high": "parameter3"}
REPO_ROOT = Path(__file__).resolve().parents[1]


class LayerRefused(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


RATE_RANGE = 0.08          # +/-8% on the instrumental's tempo slider
MAX_CORRECTION = 0.03      # the follower never moves more than 3% off the feed-forward
FOLLOW_GAIN = 0.4          # speed correction per beat of error: ~2 s time constant
FOLLOW_INTERVAL_S = 0.05


def _maps(plan: dict):
    from brain.stem_layer_plan import BeatMap

    return BeatMap.from_dict(plan["bed"]["beat_map"]), BeatMap.from_dict(plan["vocal"]["beat_map"])


def schedule(plan: dict, *, bed_rate: float | None = None) -> dict:
    """Real-time offsets (seconds after the instrumental starts) for the layer."""
    bed_map, vocal_map = _maps(plan)
    vocal, bed = plan["vocal"], plan["bed"]
    rate = float(bed_rate or plan["tempo"]["bed_rate"])
    cue_index = vocal_map.index_at(vocal["cue_seconds"])
    preroll = vocal["anchor_index"] - cue_index              # beats of vocal before its anchor
    start_bed_index = bed["entry_index"] - preroll
    bed_lead = (bed_map.time_at(start_bed_index) - bed["cue_seconds"]) / rate
    if bed_lead < 0:
        raise ValueError("the instrumental lead-in is shorter than the vocal's pre-roll; raise --lead-bars")
    layer_end = bed_lead + (vocal_map.time_at(vocal["end_index"]) - vocal["cue_seconds"])
    fade = int(plan.get("fade_beats", 16)) * 60.0 / float(vocal["bpm"])
    last_bed_index = len(bed_map.beats) - 1 - int(plan.get("fade_beats", 16))
    bed_end_after = (bed_map.time_at(last_bed_index) - bed["cue_seconds"]) / rate
    layer_end = min(layer_end, max(bed_lead, bed_end_after))
    return {
        "bed_rate": round(rate, 6),
        "vocal_start_bed_index": round(start_bed_index, 4),
        "vocal_start_after_s": round(bed_lead, 4),
        "layer_end_after_s": round(layer_end, 3),
        "fade_seconds": round(fade, 3),
        "total_seconds": round(layer_end + fade, 3),
    }


def lock_error_beats(plan: dict, bed_index: float, vocal_index: float) -> float:
    """+ means the instrumental is ahead of the vocal (in beats)."""
    return (bed_index - plan["bed"]["entry_index"]) - (vocal_index - plan["vocal"]["anchor_index"])


def follow_speed(plan: dict, bed_map, vocal_map, bed_index: float, vocal_index: float | None) -> float:
    """Instrumental deck speed (source seconds per real second).

    Feed-forward: the bed's local beat length over the vocal's, so the bed's
    beats arrive at the vocal's tempo even where the bed's own tempo drifts.
    Feedback: close the remaining beat error with a ~2 s time constant.
    """
    if vocal_index is None:       # before the vocal: the vocal's tempo at its anchor
        vocal_period = vocal_map.period_at(plan["vocal"]["anchor_index"])
        return bed_map.period_at(bed_index) / vocal_period
    ff = bed_map.period_at(bed_index) / vocal_map.period_at(vocal_index)
    error = lock_error_beats(plan, bed_index, vocal_index)
    correction = max(-MAX_CORRECTION, min(MAX_CORRECTION, -FOLLOW_GAIN * error))
    return ff * (1.0 + correction)


def describe_schedule(plan: dict, timing: dict) -> list[str]:
    return [
        f"deck {BED_DECK} instrumental from {plan['bed']['cue_seconds']:.2f}s at about x{timing['bed_rate']}, "
        "riding its tempo beat by beat (keylock on)",
        f"deck {VOCAL_DECK} vocal from {plan['vocal']['cue_seconds']:.2f}s at its own speed, "
        f"{timing['vocal_start_after_s']:.2f}s after the instrumental starts",
        f"both at full (crossfader center) until {timing['layer_end_after_s']:.1f}s, "
        f"then the instrumental fades over {timing['fade_seconds']:.1f}s; total {timing['total_seconds']:.0f}s",
    ]


def _calibrate_origin(mixxx, group: str, cue_seconds: float, grid_bpm: float) -> float:
    """Mixxx grid origin from beat_distance at a known, stopped position."""
    period = 60.0 / grid_bpm
    fraction = mixxx.get(group, "beat_distance")
    return cue_seconds - fraction * period


class _Clock:
    """Source seconds of one deck: the audio-callback clock when Mixxx has a
    grid for it, else the 15 Hz position (plus elapsed time) as a fallback."""

    def __init__(self, mixxx, group: str, cue: float, clock) -> None:
        self.mixxx, self.group, self.clock = mixxx, group, clock
        self.duration = mixxx.get(group, "duration")
        self.grid_bpm = mixxx.get(group, "file_bpm")
        self.origin = _calibrate_origin(mixxx, group, cue, self.grid_bpm) if self.grid_bpm > 0 else None

    def read(self) -> tuple[float, float]:
        from hands.run_mix_plan import CueVerificationError, read_source_clock

        if self.origin is not None:
            try:
                return read_source_clock(self.mixxx, self.group, self.duration,
                                         {"grid_bpm": self.grid_bpm, "first_beat_seconds": self.origin})
            except CueVerificationError:
                pass
        at = self.clock()
        return self.mixxx.get(self.group, "playposition") * self.duration, at


class _Speed:
    """Sets a deck's playback speed through its rate slider (orientation probed)."""

    def __init__(self, mixxx, group: str, sleep) -> None:
        self.mixxx, self.group = mixxx, group
        mixxx.set(group, "rateRange", RATE_RANGE)
        mixxx.set(group, "rate", 0.5)
        sleep(0.1)
        file_bpm = mixxx.get(group, "file_bpm")
        self.sign = 1.0 if file_bpm <= 0 or mixxx.get(group, "bpm") >= file_bpm else -1.0
        mixxx.set(group, "rate", 0.0)
        self.current = 1.0

    def set(self, speed: float) -> None:
        slider = max(-1.0, min(1.0, (speed - 1.0) / (self.sign * RATE_RANGE)))
        if abs(speed - self.current) >= 0.0002:
            self.mixxx.set(self.group, "rate", slider)
            self.current = speed


def run_layer(plan: dict, *, port: int = DEFAULT_PORT, dry_run: bool = False, take_over: bool = False,
              control_factory=MixxxControl, clock=time.monotonic, sleep=time.sleep,
              ps_output: str | None = None) -> dict:
    from brain.stem_layer_plan import describe
    from hands.audition_transition import playing_decks, running_mix_processes
    from hands.run_mix_plan import deck_group, eq_group, load_deck, reset_instrument

    timing = schedule(plan)
    for line in [*describe(plan), *describe_schedule(plan, timing)]:
        print(line)
    if dry_run:
        print("dry-run: no Mixxx connection")
        return {"plan": plan, "schedule": timing}
    others = running_mix_processes(ps_output=ps_output)
    if others:
        raise LayerRefused("mix_running", "a live mix or audition is driving Mixxx (" + others[0] + "); stop it first")
    bed_map, vocal_map = _maps(plan)
    bed_g, vocal_g = deck_group(BED_DECK), deck_group(VOCAL_DECK)
    report: dict = {"plan": plan, "schedule": timing, "errors_ms": []}
    with control_factory(port=port, timeout_s=40.0) as mixxx:
        busy = playing_decks(mixxx)
        if busy and not take_over:
            raise LayerRefused("decks_playing", f"Mixxx deck {', '.join(map(str, busy))} is playing; stop it first")
        try:
            print("[layer] phase: loading")
            reset_instrument(mixxx)
            mixxx.set("[Master]", "crossfader", 0.0)
            load_deck(mixxx, BED_DECK, plan["bed"]["track_id"], cue_seconds=plan["bed"]["cue_seconds"],
                      expected_bpm=plan["bed"].get("mixxx_bpm"))
            load_deck(mixxx, VOCAL_DECK, plan["vocal"]["track_id"], cue_seconds=plan["vocal"]["cue_seconds"])
            for group in (bed_g, vocal_g):
                mixxx.set(group, "quantize", 0)        # no snapping to Mixxx's acapella grid
                mixxx.set(group, "sync_enabled", 0)
            mixxx.set(vocal_g, "rate", 0.0)
            speed = _Speed(mixxx, bed_g, sleep)
            levels = plan["levels"]
            mixxx.set(vocal_g, "pregain", float(levels["vocal_pregain"]))
            mixxx.set(bed_g, "pregain", float(levels["bed_pregain"]))
            for band, value in levels["bed_eq"].items():
                mixxx.set(eq_group(BED_DECK), EQ_KEYS[band], float(value))
            bed_clock = _Clock(mixxx, bed_g, plan["bed"]["cue_seconds"], clock)
            vocal_clock = _Clock(mixxx, vocal_g, plan["vocal"]["cue_seconds"], clock)
            speed.set(follow_speed(plan, bed_map, vocal_map, bed_map.index_at(plan["bed"]["cue_seconds"]), None))

            print("[layer] phase: instrumental")
            mixxx.set(bed_g, "play", 1)
            started = clock()
            start_index = timing["vocal_start_bed_index"]
            vocal_on = False
            fading_from = None
            last_print = -1
            while True:
                bed_s, bed_at = bed_clock.read()
                bed_index = bed_map.index_at(bed_s)
                if not vocal_on:
                    beats_left = start_index - bed_index
                    seconds_left = beats_left * bed_map.period_at(bed_index) / max(speed.current, 1e-6) - (clock() - bed_at)
                    if seconds_left <= 0.004:
                        mixxx.set(vocal_g, "play", 1)
                        vocal_on = True
                        print("[layer] phase: vocal")
                        continue
                    speed.set(follow_speed(plan, bed_map, vocal_map, bed_index, None))
                    sleep(min(FOLLOW_INTERVAL_S, max(0.0, seconds_left - 0.004)))
                    continue
                vocal_s, vocal_at = vocal_clock.read()
                # both clocks at one instant
                common = max(bed_at, vocal_at)
                bed_index = bed_map.index_at(bed_s + (common - bed_at) * speed.current)
                vocal_index = vocal_map.index_at(vocal_s + (common - vocal_at))
                error = lock_error_beats(plan, bed_index, vocal_index)
                error_ms = error * vocal_map.period_at(vocal_index) * 1000
                if vocal_index >= plan["vocal"]["anchor_index"]:
                    report["errors_ms"].append(round(error_ms, 1))
                bar = int((vocal_index - plan["vocal"]["anchor_index"]) // 4)
                if bar != last_print and bar >= 0 and bar % 8 == 0:
                    print(f"  bar {bar + 1}: instrumental {error_ms:+.0f} ms against the vocal")
                    last_print = bar
                if fading_from is None and (vocal_index >= plan["vocal"]["end_index"]
                                            or clock() - started >= timing["layer_end_after_s"]):
                    print("[layer] phase: fade")
                    fading_from = clock()
                if fading_from is not None:
                    level = max(0.0, 1.0 - (clock() - fading_from) / timing["fade_seconds"])
                    mixxx.set(bed_g, "volume", level)
                    mixxx.set(vocal_g, "volume", level)
                    if level <= 0.0:
                        break
                speed.set(follow_speed(plan, bed_map, vocal_map, bed_index, vocal_index))
                sleep(FOLLOW_INTERVAL_S)
            settled = report["errors_ms"][int(4 / FOLLOW_INTERVAL_S):] or report["errors_ms"]
            if settled:
                worst = sorted(abs(e) for e in settled)[int(0.95 * (len(settled) - 1))]
                report["held_within_ms"] = round(worst, 1)
                print(f"  held the snares within {worst:.0f} ms (95% of the layer)")
            print("[layer] phase: finished")
        except KeyboardInterrupt:
            print("\n[layer] stopped — fading both decks")
            try:
                _fade(mixxx, [bed_g, vocal_g], 1.5, sleep)
            except Exception:
                pass
            report["stopped"] = True
        finally:
            _restore(mixxx)
    return report


def _fade(mixxx, groups: list[str], seconds: float, sleep) -> None:
    steps = max(1, int(seconds / 0.05))
    starts = {group: mixxx.get(group, "volume") for group in groups}
    for step in range(1, steps + 1):
        level = 1.0 - step / steps
        for group in groups:
            mixxx.set(group, "volume", starts[group] * level)
        sleep(seconds / steps)


def _restore(mixxx) -> None:
    from hands.run_mix_plan import deck_group, neutralize_deck_effects

    for deck in (BED_DECK, VOCAL_DECK):
        group = deck_group(deck)
        for key, value in (("play", 0), ("volume", 1.0), ("pregain", 1.0), ("rate", 0.0), ("quantize", 1)):
            try:
                mixxx.set(group, key, value)
            except Exception:
                pass
    neutralize_deck_effects(mixxx, (BED_DECK, VOCAL_DECK))


# --------------------------------------------------------------------------
# GUI child-process session


_PHASE = re.compile(r"^\[layer\] phase: (\S+)")
_STOPPED = re.compile(r"^\[layer\] stopped")
_REFUSED = re.compile(r"^\[layer\] refused \(([^)]+)\): (.*)$")
_ERROR = re.compile(r"^\[layer\] error: (.*)$")


class StemLayerSession:
    """Runs this CLI in a child process so the GUI's Stop always works."""

    def __init__(self, *, popen=subprocess.Popen, python: str | None = None, cwd: Path = REPO_ROOT,
                 log_lines: int = 40) -> None:
        self._popen = popen
        self._python = python or sys.executable
        self._cwd = cwd
        self._lock = threading.Lock()
        self._proc = None
        self._log: deque[str] = deque(maxlen=log_lines)
        self._state: dict = {"playing": False, "phase": "idle"}

    def status(self) -> dict:
        with self._lock:
            return {**self._state, "log": list(self._log)}

    def command(self, *, vocal_id: str, bed_id: str, port: int, options: dict) -> list[str]:
        cmd = [self._python, "-u", "-m", "hands.stem_layer", "--vocal", vocal_id, "--bed", bed_id,
               "--port", str(int(port))]
        for flag, key in (("--vocal-from", "vocal_from_seconds"), ("--vocal-to", "vocal_to_seconds"),
                          ("--count-shift", "count_shift_beats"), ("--lead-bars", "lead_bars"),
                          ("--bed-cue", "bed_cue_seconds")):
            if options.get(key) is not None:
                cmd += [flag, str(options[key])]
        if options.get("take_over"):
            cmd.append("--take-over")
        if options.get("dry_run"):
            cmd.append("--dry-run")
        if options.get("index_path"):
            cmd += ["--index", str(options["index_path"])]
        return cmd

    def start(self, *, vocal_id: str, bed_id: str, port: int, options: dict | None = None,
              index_path=None, info: dict | None = None) -> dict:
        self.stop()
        options = {**(options or {}), "index_path": str(index_path) if index_path else None}
        proc = self._popen(self.command(vocal_id=vocal_id, bed_id=bed_id, port=port, options=options),
                           cwd=str(self._cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        with self._lock:
            self._proc = proc
            self._log.clear()
            self._state = {**(info or {}), "playing": True, "phase": "planning", "port": int(port),
                           "dry_run": bool(options.get("dry_run")),
                           "vocal_id": vocal_id, "bed_id": bed_id, "options": options,
                           "error": None, "refused": None, "returncode": None, "started_at": time.time()}
        threading.Thread(target=self._follow, args=(proc,), daemon=True).start()
        return self.status()

    def _follow(self, proc) -> None:
        for raw in proc.stdout or ():
            line = raw.rstrip("\n")
            with self._lock:
                if proc is not self._proc:
                    continue
                if line.strip():
                    self._log.append(line)
                if (match := _PHASE.match(line)):
                    self._state["phase"] = match.group(1)
                elif (match := _REFUSED.match(line)):
                    self._state.update(refused=match.group(1), error=match.group(2))
                elif (match := _ERROR.match(line)):
                    self._state["error"] = match.group(1)
        returncode = proc.wait()
        with self._lock:
            if proc is not self._proc:
                return
            self._state.update(playing=False, returncode=returncode)
            if self._state.get("phase") == "stopped by user":
                return
            if returncode == 0:
                self._state["phase"] = "finished"
            else:
                self._state["phase"] = "refused" if self._state.get("refused") else "failed"
                if not self._state.get("error"):
                    tail = [line for line in self._log if line.strip()][-3:]
                    self._state["error"] = " / ".join(tail) or f"exited with code {returncode}"

    def stop(self, timeout_s: float = 8.0) -> dict:
        with self._lock:
            proc = self._proc
        if proc is None or proc.poll() is not None:
            return self.status()
        with self._lock:
            self._state["phase"] = "stopped by user"
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)
        with self._lock:
            if proc is self._proc:
                self._state.update(playing=False, returncode=proc.returncode)
        return self.status()


def _raise_interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    from brain.stem_layer_plan import DEFAULT_LEAD_BARS, LayerPlanError, plan_layer

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vocal", required=True, help="vocals-only track_id (library path)")
    parser.add_argument("--bed", required=True, help="instrumental track_id (library path)")
    parser.add_argument("--vocal-from", type=float, default=0.0, help="start of the vocal section to use (s)")
    parser.add_argument("--vocal-to", type=float, help="end of the vocal section (s)")
    parser.add_argument("--count-shift", type=int, default=0, help="A/B count 1: a whole snare cycle, e.g. 2 or -2")
    parser.add_argument("--lead-bars", type=int, default=DEFAULT_LEAD_BARS)
    parser.add_argument("--bed-cue", type=float, default=0.0, help="where the instrumental starts (s)")
    parser.add_argument("--vocal-bpm", type=float, help="the vocal's true BPM if no full mix is analyzed")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--index", type=Path, help="library.sqlite3 (default: the current collection)")
    parser.add_argument("--take-over", action="store_true", help="use decks 1-2 even if one is playing")
    parser.add_argument("--dry-run", action="store_true", help="plan and print; never touch Mixxx")
    parser.add_argument("--save-plan", type=Path, help="also write the layer plan JSON here")
    args = parser.parse_args(argv)
    signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        plan = plan_layer(args.vocal, args.bed, vocal_bpm=args.vocal_bpm, bed_cue_seconds=args.bed_cue,
                          vocal_from_seconds=args.vocal_from, vocal_to_seconds=args.vocal_to,
                          lead_bars=args.lead_bars, count_shift_beats=args.count_shift, index_path=args.index)
    except (LayerPlanError, OSError, ValueError) as error:
        print(f"[layer] error: {error}")
        return 1
    if args.save_plan:
        args.save_plan.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    try:
        run_layer(plan, port=args.port, dry_run=args.dry_run, take_over=args.take_over)
    except LayerRefused as error:
        print(f"[layer] refused ({error.code}): {error}")
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception as error:  # surfaced to the GUI log
        print(f"[layer] error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
