"""Audition one planned transition live in Mixxx, then step to its neighbours.

A built mix can run for hours. Auditing transition 37 should not mean sitting
through the 36 before it, and the ffmpeg render (`brain/preview_transitions.py`,
deprecated) cannot reproduce how the live runner actually reaches a blend. This
puts Mixxx in the state the full runner would have just before transition N,
then hands control to the runner's own event loop:

  1. read the built plan fresh (``mix_plan.json``) and pick transition N
  2. load the outgoing song cued a few bars before the planned fade start --
     ``phase_anchor.planned_anchor_beat_index`` on its own grid, which already
     counts the previous fade, skips and backbeat nudges -- at the tempo and
     pitch the runner would be holding it (play_bpm holds, keep_blend_tempo,
     settle targets), and the incoming song cued exactly as the plan's
     load/preload event says
  3. run start -> play_body -> transition -> finale -> stop_all through
     ``hands.run_mix_plan._run_events``: the same sync / beatsync_phase,
     snare_align jump, EQ and fader curves and runtime bar guard
     (``wait_for_beats`` with the plan's ``phase_anchor``) as the full mix
  4. let the incoming song play a short tail, then stop both decks

Playback starts only when this command runs without ``--dry-run``. It refuses
while a full mix run (or another audition) is active, and will not take over
decks that are already playing unless ``--take-over`` is given. Ctrl-C (or the
GUI's Stop, which sends SIGTERM) stops both decks and resets their EQ/filter.

Usage:
    uv run python -m hands.audition_transition --plan nastribute --list
    uv run python -m hands.audition_transition --plan nastribute --transition 12 --dry-run
    uv run python -m hands.audition_transition --plan nastribute --transition 12
    uv run python -m hands.audition_transition --plan nastribute --transition 12 --lead-bars 4 --tail-bars 8

Story: user_stories/story__when_i_audit_a_mix_i_audition_one_transition_live_in_mixxx_and_step_between_them.md
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
from hands.run_mix_plan import (
    LOAD_TIMEOUT_S,
    _run_events,
    cue_options,
    load_deck,
    load_executable_plan,
    neutralize_deck_effects,
    reset_instrument,
    resolve_plan_argument,
)
from hands.transition import deck_group

BEATS_PER_BAR = 4
DEFAULT_LEAD_BARS = 8
DEFAULT_TAIL_BARS = 16
# Start half a beat before the lead-in downbeat, so the first beat_active edge
# the body counter sees is that downbeat rather than a race with the seek.
PREROLL_BEATS = 0.5
# Decks the runner's reset_instrument / stop_all touch.
RUNNER_DECKS = (1, 2)
REPO_ROOT = Path(__file__).resolve().parents[1]

# Command lines that drive Mixxx decks for a whole set (or another audition).
LIVE_RUNNER_MARKERS = (
    "hands.run_mix_plan",
    "hands/run_mix_plan.py",
    "hands.attended_mix_run",
    "hands/attended_mix_run.py",
    "hands.showcase_mix",
    "hands/showcase_mix.py",
    "hands.audition_transition",
    "hands/audition_transition.py",
)

EXIT_REFUSED = 2
EXIT_STOPPED = 130


class AuditionError(ValueError):
    """The plan cannot be auditioned as asked (bad number, unsupported plan)."""


class AuditionRefused(RuntimeError):
    """Mixxx is busy; auditioning now would hijack someone else's decks."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _bed_still_live(event: dict) -> bool:
    return bool(event.get("keep_outgoing_live") or event.get("technique") == "vocal_over_bed")


def _identity(event: dict | None) -> str | None:
    """Library identity of a load event (bounded source copies keep the original)."""
    if not event:
        return None
    return event.get("source_track_id") or event.get("track_id")


def _label(event: dict | None) -> str:
    if not event:
        return "?"
    if event.get("artist") or event.get("title"):
        return f"{event.get('artist') or '?'} — {event.get('title') or '?'}"
    if event.get("track"):
        return str(event["track"])
    return Path(str(_identity(event) or "?")).stem


def _track_bpms(plan: dict) -> dict[str, float]:
    result: dict[str, float] = {}
    for track in plan.get("tracks") or []:
        bpm = track.get("bpm")
        if not bpm:
            continue
        for key in (track.get("track_id"), track.get("source_track_id")):
            if key:
                result[key] = float(bpm)
    return result


def _settled_tempo(settle: float, native: float | None, blend: float | None) -> float | None:
    """Where ``settle_rate`` glides a synced deck that has an incoming_settle_bpm."""
    if not native or not blend or abs(blend - native) < 1e-6:
        return None
    fraction = max(0.0, min(1.0, (float(settle) - native) / (blend - native)))
    return native + fraction * (blend - native)


class _Decks:
    """Replays the runner's deck bookkeeping without Mixxx.

    Mirrors ``_run_events``: ``load`` lands at once, a ``preload_after_transition``
    lands on the deck the next transition frees, a same-song handoff moves the
    song to the copy deck and loads ``then_load`` onto the original, and every
    transition leaves its incoming deck at the tempo the runner would hold
    (play_bpm hold, keep_blend_tempo, settle target, otherwise native).
    """

    def __init__(self, track_bpms: dict[str, float]) -> None:
        self.track_bpms = track_bpms
        self.decks: dict[int, dict] = {}
        self.pending: dict | None = None
        self.transitions_seen = 0

    def _deck(self, deck: int) -> dict:
        return self.decks.setdefault(deck, {"load": None, "tempo": None, "pitch": 0.0, "why": "opening track"})

    def _put(self, deck: int, load: dict) -> None:
        self.decks[deck] = {"load": load, "tempo": None, "pitch": 0.0, "why": "opening track"}

    def native(self, deck: int) -> float | None:
        return self.track_bpms.get(_identity(self._deck(deck)["load"]) or "")

    def effective(self, deck: int) -> float | None:
        state = self._deck(deck)
        return state["tempo"] or self.native(deck)

    def snapshot(self, deck: int) -> dict:
        return dict(self._deck(deck))

    def apply(self, event: dict) -> None:
        op = event.get("op")
        if op == "load":
            self._put(int(event["deck"]), event)
        elif op == "start":
            state = self._deck(int(event["deck"]))
            if event.get("bpm_target") is not None:
                state["tempo"] = float(event["bpm_target"])
                state["why"] = "start bpm_target"
        elif op == "preload_after_transition":
            self.pending = event
        elif op == "play_body":
            deck = int(event["deck"])
            ramp_deck = deck
            handoff = event.get("handoff")
            if handoff:
                source = self._deck(deck)
                copy = self._deck(int(handoff["to_deck"]))
                copy.update(tempo=source["tempo"], pitch=source["pitch"], why=source["why"])
                ramp_deck = int(handoff["to_deck"])
                nxt = handoff.get("then_load")
                if nxt:
                    self._put(deck, {**nxt, "op": "load", "deck": deck})
            if event.get("tempo_ramp_beats") and event.get("exit_bpm_target") is not None:
                state = self._deck(ramp_deck)
                state["tempo"] = float(event["exit_bpm_target"])
                state["why"] = "exit_bpm ramp"
        elif op == "transition":
            self.transitions_seen += 1
            from_deck, to_deck = int(event["from_deck"]), int(event["to_deck"])
            moves = list(event.get("moves") or [])
            synced = "sync" in moves and event.get("technique") != "half_time_or_cut"
            incoming = self._deck(to_deck)
            tempo, why = None, f"settled back after transition {self.transitions_seen}"
            if event.get("incoming_bpm_target") is not None:
                tempo = float(event["incoming_bpm_target"])
                why = f"play_bpm hold from transition {self.transitions_seen}"
            elif not synced:
                why = f"entered without sync at transition {self.transitions_seen}"
            elif event.get("keep_blend_tempo"):
                tempo = self.effective(from_deck)
                why = f"keep_blend_tempo from transition {self.transitions_seen}"
            elif event.get("incoming_settle_bpm") is not None:
                native = event.get("incoming_native_bpm") or self.native(to_deck)
                tempo = _settled_tempo(
                    float(event["incoming_settle_bpm"]),
                    float(native) if native else None,
                    self.effective(from_deck),
                )
                why = f"settle target from transition {self.transitions_seen}"
            native = self.native(to_deck)
            if tempo is not None and native and abs(tempo - native) < 0.01:
                tempo = None
            incoming.update(tempo=tempo, pitch=float(event.get("incoming_pitch_semitones") or 0.0), why=why)
            freed = to_deck if _bed_still_live(event) else from_deck
            if self.pending and int(self.pending.get("deck", -1)) == freed:
                self._put(freed, self.pending)
                self.pending = None


def _transition_indexes(events: list[dict]) -> list[int]:
    return [index for index, event in enumerate(events) if event.get("op") == "transition"]


def list_transitions(plan: dict) -> list[dict]:
    """Every transition of a built plan, numbered from 1, with the songs on each deck."""
    events = plan.get("events") or []
    decks = _Decks(_track_bpms(plan))
    result: list[dict] = []
    for event in events:
        if event.get("op") == "transition":
            out_load = decks.snapshot(int(event["from_deck"]))["load"]
            in_load = decks.snapshot(int(event["to_deck"]))["load"]
            result.append({
                "number": len(result) + 1,
                "from_deck": int(event["from_deck"]),
                "to_deck": int(event["to_deck"]),
                "from_track_id": _identity(out_load),
                "to_track_id": _identity(in_load),
                "from_label": event.get("from_track") or _label(out_load),
                "to_label": event.get("to_track") or _label(in_load),
                "technique": event.get("technique"),
                "transition_beats": event.get("transition_beats"),
                "moves": list(event.get("moves") or []),
            })
        decks.apply(event)
    return result


def find_transition(transitions: list[dict], from_track_id: str, to_track_id: str) -> int:
    """Number of the built transition between two library tracks."""
    for item in transitions:
        if item["from_track_id"] == from_track_id and item["to_track_id"] == to_track_id:
            return int(item["number"])
    raise AuditionError(
        "that pair is not a transition in the built mix — the order or tracks changed "
        "since the last build; rebuild the mix, then audition it"
    )


def _grid_seconds(grid: dict, beat: float) -> float:
    return float(grid["first_beat_seconds"]) + float(beat) * 60.0 / float(grid["grid_bpm"])


def _grid_beat(grid: dict, seconds: float) -> int:
    return int(round((float(seconds) - float(grid["first_beat_seconds"])) * float(grid["grid_bpm"]) / 60.0))


def plan_audition(
    plan: dict,
    number: int,
    *,
    lead_bars: int = DEFAULT_LEAD_BARS,
    tail_bars: int = DEFAULT_TAIL_BARS,
) -> dict:
    """Work out, without Mixxx, exactly how transition ``number`` will be auditioned.

    Returns the outgoing/incoming setup (deck, track, cue, tempo, pitch), the
    lead-in placement on the outgoing grid, any approximations made, and the
    event list handed to ``_run_events``.
    """
    if plan.get("execution_mode"):
        raise AuditionError(
            f"this plan is a {plan['execution_mode']} performance, not a transition-by-transition "
            "mix; audition supports built event plans"
        )
    events = plan.get("events") or []
    indexes = _transition_indexes(events)
    if not indexes:
        raise AuditionError("this plan has no transitions to audition")
    if not 1 <= int(number) <= len(indexes):
        raise AuditionError(f"no transition {number}: this mix has {len(indexes)} (1–{len(indexes)})")
    number = int(number)
    t_index = indexes[number - 1]
    transition = dict(events[t_index])
    from hands.run_mix_plan import check_no_abrupt_exits

    try:
        check_no_abrupt_exits([transition])
    except ValueError as error:
        raise AuditionError(str(error)) from error
    from_deck, to_deck = int(transition["from_deck"]), int(transition["to_deck"])
    bpms = _track_bpms(plan)
    notes: list[str] = []

    # The ride that leads into this transition. After a vocal-over-bed layer
    # the bed keeps playing with no new ride: walk back over those layers.
    body_index: int | None = None
    layered_beats = 0
    cursor = t_index - 1
    while cursor >= 0:
        event = events[cursor]
        if event.get("op") == "play_body":
            body_index = cursor
            break
        if event.get("op") == "transition":
            if _bed_still_live(event) and int(event["from_deck"]) == from_deck:
                layered_beats += int(event.get("transition_beats", 16)) + 1
            else:
                break
        cursor -= 1
    body = dict(events[body_index]) if body_index is not None else None

    # Deck contents and tempo state just before the ride (or the transition).
    before_body = _Decks(bpms)
    before_transition = _Decks(bpms)
    entry_beats = 0
    for index, event in enumerate(events[:t_index]):
        if body_index is not None and index < body_index:
            before_body.apply(event)
            if (
                event.get("op") == "transition"
                and body is not None
                and int(event["to_deck"]) == int(body["deck"])
                and not _bed_still_live(event)
            ):
                entry_beats = int(event.get("transition_beats", 16))
        before_transition.apply(event)
    out_state = before_transition.snapshot(from_deck)
    in_state = before_transition.snapshot(to_deck)
    out_load, in_load = out_state["load"], in_state["load"]
    if not out_load:
        raise AuditionError(f"transition {number}: cannot tell which song is playing on deck {from_deck}")
    if not in_load:
        raise AuditionError(f"transition {number}: cannot tell which song is cued on deck {to_deck}")
    tempo_deck = int(body["deck"]) if body is not None else from_deck
    tempo_state = (before_body if body is not None else before_transition).snapshot(tempo_deck)
    native_bpm = bpms.get(_identity(out_load) or "")

    # Where the transition starts on the outgoing song's own grid.
    phase_anchor = dict((body or {}).get("phase_anchor") or {}) or None
    guard_anchor = phase_anchor
    handoff = (body or {}).get("handoff")
    if phase_anchor:
        grid = {"grid_bpm": float(phase_anchor["grid_bpm"]),
                "first_beat_seconds": float(phase_anchor["first_beat_seconds"])}
        anchor = int(phase_anchor["planned_anchor_beat_index"])
        grid_label = "plan phase_anchor"
    else:
        # Older artifacts / off-grid cues: count from the cue at native tempo.
        bpm = native_bpm or float((body or {}).get("native_bpm") or 0) or None
        if not bpm:
            raise AuditionError(
                f"transition {number}: no phase_anchor and no BPM for the outgoing song — "
                "rebuild the plan so the lead-in can be placed"
            )
        grid = {"grid_bpm": float(bpm), "first_beat_seconds": float(out_load.get("cue_seconds") or 0.0)}
        anchor = entry_beats + int((body or {}).get("beats") or 0) + 1
        grid_label = "cue + beat count (no phase_anchor; approximate)"
        notes.append("no phase_anchor on this ride: lead-in placed by beat arithmetic from the cue; no runtime bar guard")
    if out_load.get("cue_beat_index") is not None and phase_anchor:
        earliest = int(out_load["cue_beat_index"])
    elif out_load.get("cue_seconds") is not None:
        earliest = max(0, _grid_beat(grid, float(out_load["cue_seconds"])))
    else:
        earliest = 0
    if body is not None and handoff:
        # The song continues on a second copy cued at skip_to; the runner does
        # not guard the copy's bar position, so the landing is estimated.
        steady = int(body.get("beats") or 0) - int(body.get("tempo_ramp_beats") or 0)
        earliest = max(0, _grid_beat(grid, float(handoff["skip_to_seconds"])))
        anchor = earliest + max(0, steady - int(handoff.get("after_beats") or 0)) + 1
        notes.append("same-song handoff before this transition: lead-in starts on the copy after the skip (approximate landing)")
        guard_anchor = None
    elif body is not None and int(body.get("skip_beats") or 0) > 0 and int(body.get("skip_after_beats") or 0) < int(body.get("beats") or 0):
        # The planned count excludes the beats jumped over; the source position
        # does not. Never let the lead-in cross the skipped section.
        skip_beats = int(body["skip_beats"])
        anchor += skip_beats
        earliest = max(earliest, anchor - (int(body["beats"]) - int(body.get("skip_after_beats") or 0)) - 1)
        notes.append(f"ride skips {skip_beats} beats before this transition: lead-in starts after the skip")
    if layered_beats:
        anchor += layered_beats
        guard_anchor = None
        notes.append("transition follows a vocal-over-bed layer with no ride of its own: landing estimated from the layer length")
    if guard_anchor is None and phase_anchor:
        # Keep the computed bar position audible even where the runner itself
        # has no guard: a synthesized anchor on the same grid.
        guard_anchor = {
            **grid,
            "planned_anchor_beat_index": anchor,
            "target_beat_mod4": anchor % 4,
            "target_beat_parity": anchor % 2,
            "synthesized_for_audition": True,
        }

    lead_beats = max(1, int(lead_bars)) * BEATS_PER_BAR
    ramp_beats = int((body or {}).get("tempo_ramp_beats") or 0) if body is not None and not layered_beats else 0
    if ramp_beats and lead_beats < ramp_beats + BEATS_PER_BAR:
        lead_beats = ramp_beats + BEATS_PER_BAR
        notes.append(f"lead-in lengthened to {lead_beats} beats to include the planned {ramp_beats}-beat tempo ramp")
    start_beat = anchor - lead_beats
    if start_beat < earliest:
        start_beat = earliest
        notes.append(f"lead-in shortened to {anchor - start_beat} beats: the outgoing song does not play earlier than beat {earliest} in the mix")
    start_beat = max(0, start_beat)
    lead_actual = anchor - start_beat
    if lead_actual < 2:
        raise AuditionError(f"transition {number} starts too close to the outgoing entry to audition")
    preroll = PREROLL_BEATS if start_beat > earliest else 0.0
    # With the pre-roll the first counted edge is start_beat itself; without
    # it the counter starts on the following beat. The runtime guard corrects
    # either way when the anchor is known.
    body_beats = lead_actual if preroll else lead_actual - 1
    seek_seconds = max(0.0, _grid_seconds(grid, start_beat - preroll))
    anchor_seconds = _grid_seconds(grid, anchor)

    tempo = tempo_state["tempo"]
    pitch = float(tempo_state["pitch"] or 0.0)
    play_bpm = tempo or native_bpm or grid["grid_bpm"]
    out_track_id = out_load["track_id"]
    out_setup = {
        "op": "load",
        "deck": from_deck,
        "track_id": out_track_id,
        "artist": out_load.get("artist"),
        "title": out_load.get("title"),
        "cue_seconds": round(seek_seconds, 4),
        "audition_role": "outgoing lead-in",
    }
    in_setup = {**in_load, "op": "load", "deck": to_deck, "audition_role": "incoming at planned cue"}
    start = {"op": "start", "deck": from_deck, "detail": "audition lead-in"}
    if tempo is not None:
        start["bpm_target"] = round(float(tempo), 4)
    lead_body = {
        "op": "play_body",
        "deck": from_deck,
        "beats": body_beats,
        "seconds": round(body_beats * 60.0 / play_bpm, 3),
        "track": _label(out_load),
        "track_id": out_track_id,
        "audition_lead_in": True,
    }
    if guard_anchor:
        lead_body["phase_anchor"] = guard_anchor
    if ramp_beats and body.get("exit_bpm_target") is not None:
        lead_body["tempo_ramp_beats"] = ramp_beats
        lead_body["exit_bpm_target"] = body["exit_bpm_target"]
        lead_body["native_bpm"] = body.get("native_bpm") or native_bpm
    tail_deck = from_deck if _bed_still_live(transition) else to_deck
    play_events = [start, lead_body, transition]
    tail_beats = max(0, int(tail_bars)) * BEATS_PER_BAR
    if tail_beats:
        play_events.append({"op": "finale", "deck": tail_deck, "beats": tail_beats, "track": "audition tail"})
    play_events.append({"op": "stop_all"})

    moves = list(transition.get("moves") or [])
    try:
        for load in (out_setup, in_setup):
            cue_options(load)  # reject invalid strict options before live setup
    except (TypeError, ValueError) as error:
        raise AuditionError(str(error)) from error
    return {
        "number": number,
        "count": len(indexes),
        "event_index": t_index,
        "transition": transition,
        "snare_align": "snare_align" in moves,
        "outgoing": {
            "deck": from_deck,
            "track_id": _identity(out_load),
            "label": transition.get("from_track") or _label(out_load),
            "grid": grid,
            "grid_source": grid_label,
            "entry_beat_index": earliest,
            "lead_in_beat_index": start_beat,
            "lead_in_seconds": round(seek_seconds, 4),
            "preroll_beats": preroll,
            "anchor_beat_index": anchor,
            "anchor_seconds": round(anchor_seconds, 4),
            "lead_beats": lead_actual,
            "native_bpm": native_bpm,
            "bpm_target": tempo,
            "tempo_reason": tempo_state["why"],
            "pitch_semitones": pitch,
        },
        "incoming": {
            "deck": to_deck,
            "track_id": _identity(in_load),
            "label": transition.get("to_track") or _label(in_load),
            "cue_seconds": in_load.get("cue_seconds"),
            "cue_beat_index": in_load.get("cue_beat_index"),
            "cue_fraction": in_load.get("cue_fraction"),
            "source_op": in_load.get("op"),
        },
        "phase_anchor": guard_anchor,
        "tail_beats": tail_beats,
        "tail_deck": tail_deck,
        "notes": notes,
        "setup": [{"op": "reset_instrument"}, out_setup, in_setup],
        "events": play_events,
    }


def describe(spec: dict, *, plan_path: Path | str | None = None) -> list[str]:
    """Human summary of an audition, one line per fact."""
    out, inc, tr = spec["outgoing"], spec["incoming"], spec["transition"]
    lines = []
    if plan_path:
        lines.append(f"[audition] plan: {plan_path}")
    lines.append(
        f"[audition] transition {spec['number']} of {spec['count']}: "
        f"{out['label']} (deck {out['deck']}) -> {inc['label']} (deck {inc['deck']})"
    )
    lines.append(
        f"[audition] {tr.get('technique')}, {tr.get('transition_beats')} beats, "
        f"moves: {', '.join(tr.get('moves') or []) or 'none'}"
    )
    if out["bpm_target"] is not None:
        tempo = f"held at {out['bpm_target']:.2f} BPM ({out['tempo_reason']})"
    elif out["native_bpm"]:
        tempo = f"native {out['native_bpm']:.2f} BPM ({out['tempo_reason']})"
    else:
        tempo = f"native ({out['tempo_reason']})"
    lines.append(
        f"[audition] outgoing: {out['lead_beats']}-beat lead-in from grid beat {out['lead_in_beat_index']} "
        f"(seek {out['lead_in_seconds']:.3f}s{', half-beat pre-roll' if out['preroll_beats'] else ''}) "
        f"to the planned fade start at beat {out['anchor_beat_index']} ({out['anchor_seconds']:.3f}s; "
        f"{out['grid_source']}); tempo {tempo}"
        + (f"; pitch held {out['pitch_semitones']:+g} st" if out["pitch_semitones"] else "")
    )
    cue = inc["cue_seconds"]
    lines.append(
        "[audition] incoming: cued "
        + (f"{float(cue):.3f}s" if cue is not None else f"at {float(inc['cue_fraction'] or 0.1):.0%}")
        + (f" (beat {inc['cue_beat_index']})" if inc["cue_beat_index"] is not None else "")
        + f" from the plan's {inc['source_op']} event"
    )
    if spec["snare_align"]:
        lines.append("[audition] snare_align: the incoming deck jumps one beat after sync, as in the full mix")
    anchor = spec["phase_anchor"]
    if anchor:
        lines.append(
            f"[audition] runtime bar guard: lands on beat-in-bar {anchor['target_beat_mod4']} "
            f"of the outgoing grid{' (synthesized for this audition)' if anchor.get('synthesized_for_audition') else ''}"
        )
    lines.append(
        f"[audition] tail: {spec['tail_beats'] // BEATS_PER_BAR} bars on deck {spec['tail_deck']} after the landing, then both decks stop"
        if spec["tail_beats"]
        else "[audition] tail: none; both decks stop at the landing"
    )
    lines.extend(f"[audition] note: {note}" for note in spec["notes"])
    return lines


def _process_table(ps_output: str | None) -> list[tuple[int, int, str]]:
    if ps_output is None:
        ps_output = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,args="], check=False, capture_output=True, text=True
        ).stdout
    rows = []
    for line in ps_output.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) < 3:
            continue
        try:
            rows.append((int(fields[0]), int(fields[1]), fields[2]))
        except ValueError:
            continue
    return rows


def running_mix_processes(*, ps_output: str | None = None, own_pid: int | None = None) -> list[str]:
    """Command lines of live runners (or other auditions) already driving Mixxx.

    Dry runs and listings do not count, nor does this process or its own
    launchers (``uv run ...`` carries the same module name).
    """
    rows = _process_table(ps_output)
    parents = {pid: ppid for pid, ppid, _ in rows}
    own = os.getpid() if own_pid is None else own_pid
    lineage = set()
    cursor = own
    while cursor and cursor not in lineage:
        lineage.add(cursor)
        cursor = parents.get(cursor, 0)
    found = []
    for pid, _, args in rows:
        if pid in lineage:
            continue
        if not any(marker in args for marker in LIVE_RUNNER_MARKERS):
            continue
        if "python" not in args.lower() and "uv run" not in args:
            continue
        if "--dry-run" in args or "--list" in args:
            continue
        found.append(f"pid {pid}: {args}")
    return found


def playing_decks(mixxx, decks=(1, 2, 3, 4)) -> list[int]:
    playing = []
    for deck in decks:
        try:
            if mixxx.get(deck_group(deck), "play") >= 0.5:
                playing.append(deck)
        except Exception:
            continue
    return playing


def silence_decks(port: int, *, control_factory=MixxxControl, decks=RUNNER_DECKS) -> None:
    """Stop the audition decks and reset EQ/filter on a fresh connection."""
    try:
        with control_factory(port=port, timeout_s=2.0) as mixxx:
            for deck in decks:
                try:
                    mixxx.set(deck_group(deck), "play", 0)
                except Exception:
                    pass
            neutralize_deck_effects(mixxx, decks)
    except Exception as error:
        print(f"[audition] WARNING: could not reach Mixxx to stop the decks ({error})")


def _setup(mixxx, spec: dict, expected_bpms: dict) -> None:
    """Reset, then load both songs with the runner's own load_deck."""
    reset_instrument(mixxx)
    for event in spec["setup"][1:]:
        load_deck(
            mixxx,
            int(event["deck"]),
            event["track_id"],
            event.get("cue_fraction", 0.1),
            event.get("cue_seconds"),
            expected_bpms.get(event["track_id"]),
            **cue_options(event),
        )
    pitch = spec["outgoing"]["pitch_semitones"]
    if pitch:
        mixxx.set(deck_group(spec["outgoing"]["deck"]), "pitch_adjust", float(pitch))
        print(f"  holding deck {spec['outgoing']['deck']} pitch at {pitch:+g} st (as in the mix)")


def run_audition(
    plan: dict,
    number: int,
    *,
    port: int,
    lead_bars: int = DEFAULT_LEAD_BARS,
    tail_bars: int = DEFAULT_TAIL_BARS,
    dry_run: bool = False,
    take_over: bool = False,
    plan_path: Path | str | None = None,
    control_factory=MixxxControl,
    ps_output: str | None = None,
) -> dict:
    """Audition transition ``number`` (1-based). Dry runs never touch Mixxx."""
    from hands.source_cutoffs import prepare_plan

    if plan.get("execution_mode"):
        plan_audition(plan, number)  # raises the explanatory AuditionError
    # Mandatory source ends apply here exactly as in a full run.
    prepared = prepare_plan(plan, dry_run=dry_run)
    spec = plan_audition(prepared, number, lead_bars=lead_bars, tail_bars=tail_bars)
    for line in describe(spec, plan_path=plan_path):
        print(line)
    if dry_run:
        for i, event in enumerate([*spec["setup"], *spec["events"]], 1):
            body = {k: v for k, v in event.items() if k != "op"}
            print(f"{i:03d}  {event['op']:24}  {json.dumps(body)[:160]}")
        print("dry-run: no Mixxx connection")
        return spec

    others = running_mix_processes(ps_output=ps_output)
    if others:
        raise AuditionRefused(
            "mix_running",
            "a live mix run is already driving Mixxx (" + others[0] + "); stop it first — "
            "the audition will not take over its decks",
        )
    expected_bpms = {
        track.get("track_id"): track.get("bpm")
        for track in (prepared.get("tracks") or [])
        if track.get("track_id")
    }
    with control_factory(port=port, timeout_s=LOAD_TIMEOUT_S + 5) as mixxx:
        busy = playing_decks(mixxx)
        if busy and not take_over:
            raise AuditionRefused(
                "decks_playing",
                f"Mixxx deck {', '.join(map(str, busy))} is playing; stop it in Mixxx first, "
                "or take over the decks explicitly",
            )
        print("[audition] phase: loading")
        try:
            _setup(mixxx, spec, expected_bpms)
            _run_events(mixxx, spec["events"], expected_bpms, port=port)
        except KeyboardInterrupt:
            print("\n[audition] stopped — stopping both decks")
            spec["stopped"] = True
        finally:
            silence_decks(port, control_factory=control_factory)
    return spec


def _raise_interrupt(signum, frame) -> None:
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audition one planned transition live in Mixxx (lead-in, the real transition, a short tail)."
    )
    parser.add_argument(
        "--plan", default=None,
        help="built mix plan: slug, plan directory, or mix_plan.json (default: the active GUI plan)",
    )
    parser.add_argument("--transition", type=int, help="transition number, 1-based (see --list)")
    parser.add_argument("--list", action="store_true", help="list the plan's transitions and exit")
    parser.add_argument("--lead-bars", type=int, default=DEFAULT_LEAD_BARS,
                        help=f"bars of the outgoing song before the planned fade start (default {DEFAULT_LEAD_BARS})")
    parser.add_argument("--tail-bars", type=int, default=DEFAULT_TAIL_BARS,
                        help=f"bars of the incoming song after the landing, then stop (default {DEFAULT_TAIL_BARS})")
    parser.add_argument("--port", type=int, default=None,
                        help="explicit Mixxx control port; otherwise plan metadata, then validated discovery")
    parser.add_argument("--dry-run", action="store_true", help="print what would happen; never connects to Mixxx")
    parser.add_argument("--take-over", action="store_true",
                        help="allow loading over decks that are already playing")
    parser.add_argument("--nudge-ms", type=float, default=None, metavar="MS",
                        help="try this incoming nudge instead of the plan's incoming_nudge_ms "
                             "(positive = incoming hits earlier; 0 = none; the plan file is not changed)")
    args = parser.parse_args(argv)

    plan_path = resolve_plan_argument(args.plan)
    plan = load_executable_plan(plan_path)
    if args.nudge_ms is not None and args.transition is not None:
        from hands.run_mix_plan import MAX_NUDGE_MS

        if abs(args.nudge_ms) > MAX_NUDGE_MS:
            parser.error(f"--nudge-ms must be within ±{MAX_NUDGE_MS:g}")
        indexes = _transition_indexes(plan.get("events") or [])
        if not 1 <= args.transition <= len(indexes):
            parser.error(f"--transition must be 1-{len(indexes)}")
        event = plan["events"][indexes[args.transition - 1]]
        planned = event.get("incoming_nudge_ms")
        if args.nudge_ms:
            event["incoming_nudge_ms"] = args.nudge_ms
        else:
            event.pop("incoming_nudge_ms", None)
        print(f"[audition] nudge for this run: {args.nudge_ms:+g} ms (plan: {planned if planned is not None else 'none'}; plan file unchanged)")
    if args.list:
        for item in list_transitions(plan):
            print(
                f"{item['number']:4d}  {item['from_label']} -> {item['to_label']}  "
                f"[{item['technique']}, {item['transition_beats']} beats]"
            )
        return 0
    if args.transition is None:
        parser.error("--transition N is required (or --list)")
    if args.dry_run:
        port = args.port or DEFAULT_PORT
    else:
        from hands.mixxx_control import MixxxControlError, discover_mixxx_control_port, plan_control_port

        try:
            port = discover_mixxx_control_port(
                preferred=plan_control_port(plan) or DEFAULT_PORT,
                explicit=args.port,
            )
        except MixxxControlError as error:
            print(f"[audition] error: {error}")
            return 1
    previous_handler = signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        spec = run_audition(
            plan,
            args.transition,
            port=port,
            lead_bars=args.lead_bars,
            tail_bars=args.tail_bars,
            dry_run=args.dry_run,
            take_over=args.take_over,
            plan_path=plan_path,
        )
    except AuditionRefused as error:
        print(f"[audition] refused ({error.code}): {error}")
        return EXIT_REFUSED
    except AuditionError as error:
        print(f"[audition] error: {error}")
        return EXIT_REFUSED
    except KeyboardInterrupt:
        return EXIT_STOPPED
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
    if spec.get("stopped"):
        return EXIT_STOPPED
    print("[audition] done")
    return 0


# --- GUI session: one audition at a time, always stoppable -----------------

_EVENT_LINE = re.compile(r"^\[(\d+)/(\d+)\] (\w+)")
_REFUSED_LINE = re.compile(r"^\[audition\] refused \((\w+)\): (.*)$")
_ERROR_LINE = re.compile(r"^\[audition\] error: (.*)$")
_PHASE_BY_OP = {
    "start": "lead-in",
    "play_body": "lead-in",
    "transition": "transition",
    "finale": "tail",
    "stop_all": "stopping",
}


class AuditionSession:
    """Runs the audition CLI in a child process for the playlist editor.

    A child process (not a thread) so Stop always works: the runner's waits
    are blocking socket reads with no cancel hook. Stop sends SIGTERM, which
    the child turns into its Ctrl-C path (stop both decks, reset EQ/filter);
    if it does not exit in time it is killed and the decks are silenced here.
    Starting a new audition stops the current one first, so stepping
    Previous / Next never stacks two auditions on the decks.
    """

    def __init__(self, *, popen=subprocess.Popen, python: str | None = None, cwd: Path = REPO_ROOT,
                 silence=silence_decks, log_lines: int = 40) -> None:
        self._popen = popen
        self._python = python or sys.executable
        self._cwd = cwd
        self._silence = silence
        self._lock = threading.Lock()
        self._proc = None
        self._log: deque[str] = deque(maxlen=log_lines)
        self._state: dict = {"playing": False, "phase": "idle", "transition": None}

    def status(self) -> dict:
        with self._lock:
            return {**self._state, "log": list(self._log)}

    def is_playing(self) -> bool:
        with self._lock:
            return bool(self._state.get("playing"))

    def command(self, *, plan_path, number: int, lead_bars: int, tail_bars: int, port: int,
                take_over: bool = False) -> list[str]:
        cmd = [
            self._python, "-u", "-m", "hands.audition_transition",
            "--plan", str(plan_path),
            "--transition", str(int(number)),
            "--lead-bars", str(int(lead_bars)),
            "--tail-bars", str(int(tail_bars)),
            "--port", str(int(port)),
        ]
        if take_over:
            cmd.append("--take-over")
        return cmd

    def start(self, *, plan_path, number: int, port: int, lead_bars: int = DEFAULT_LEAD_BARS,
              tail_bars: int = DEFAULT_TAIL_BARS, take_over: bool = False, info: dict | None = None) -> dict:
        self.stop()
        cmd = self.command(plan_path=plan_path, number=number, lead_bars=lead_bars,
                           tail_bars=tail_bars, port=port, take_over=take_over)
        proc = self._popen(
            cmd,
            cwd=str(self._cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        with self._lock:
            self._proc = proc
            self._log.clear()
            self._state = {
                **(info or {}),
                "playing": True,
                "phase": "loading",
                "transition": int(number),
                "lead_bars": int(lead_bars),
                "tail_bars": int(tail_bars),
                "port": int(port),
                "take_over": bool(take_over),
                "refused": None,
                "error": None,
                "returncode": None,
                "started_at": time.time(),
            }
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
                event = _EVENT_LINE.match(line)
                refused = _REFUSED_LINE.match(line)
                error = _ERROR_LINE.match(line)
                if event and event.group(3) in _PHASE_BY_OP:
                    self._state["phase"] = _PHASE_BY_OP[event.group(3)]
                elif refused:
                    self._state.update(refused=refused.group(1), error=refused.group(2))
                elif error:
                    self._state["error"] = error.group(1)
        returncode = proc.wait()
        with self._lock:
            if proc is not self._proc:
                return
            self._state["playing"] = False
            self._state["returncode"] = returncode
            if self._state.get("phase") == "stopped by user":
                return
            if returncode == 0:
                self._state["phase"] = "finished"
            elif self._state.get("refused"):
                self._state["phase"] = "refused"
            else:
                self._state["phase"] = "failed"
                if not self._state.get("error"):
                    tail = [line for line in self._log if line.strip()][-3:]
                    self._state["error"] = " / ".join(tail) or f"audition exited with code {returncode}"

    def stop(self, timeout_s: float = 8.0) -> dict:
        with self._lock:
            proc = self._proc
            port = self._state.get("port")
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
            if port is not None:
                self._silence(int(port))
        with self._lock:
            if proc is self._proc:
                self._state["playing"] = False
                self._state["returncode"] = proc.returncode
        return self.status()


if __name__ == "__main__":
    raise SystemExit(main())
