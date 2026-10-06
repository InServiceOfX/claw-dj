"""Opt-in translation of a generic plan onto the measured native-source clock.

Recipes are local human-approved evidence, never model output. Failure leaves
the conventional plan intact. No audio is rendered or played by this module.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path

from brain.build_mix_plan import track_directives
from brain.performance_author import Grid
from shared.gentle_faders import GENTLE_BLEND_BEATS
from shared.performance import compile_events, duration, fingerprint, validate

ORIGIN = "generic-measured-v1"


def _number(value, label, low=-math.inf, high=math.inf):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label}: invalid measurement")
    return float(value)


def _note_number(notes, name):
    values = re.findall(r"\b" + re.escape(name) + r"\s*=\s*(\d+(?:\.\d+)?)", notes, re.I)
    return float(values[-1]) if values else None


def _has(notes, token):
    return bool(re.search(r"\b" + re.escape(token) + r"\b", notes, re.I))


def _limits(notes):
    rule = {}
    for name, target in (("mandatory_start_seconds", "min"), ("mandatory_end_seconds", "max")):
        value = _note_number(notes, name)
        if value is not None:
            rule[target] = value
    if _has(notes, "mandatory_skip"):
        a, b = _note_number(notes, "skip_from_seconds"), _note_number(notes, "skip_to_seconds")
        if a is None or b is None or b <= a:
            raise ValueError("mandatory_skip needs a forward source interval")
        rule["exclude"] = [[a, b]]
    return rule


def _measure(tid, evidence, *, max_rate, tempo):
    if not isinstance(evidence, dict) or evidence.get("measured") is not True:
        raise ValueError(f"{tid}: missing measured source evidence")
    bpm = _number(evidence.get("bpm"), "source BPM", 20, 400)
    zero = _number(evidence.get("zero"), "pattern zero", -1000, 1000)
    _number(evidence.get("confidence"), "measurement confidence", .9, 1)
    _number(evidence.get("pitch_residual_cents"), "measured pitch residual", -15, 15)
    rate = tempo / bpm
    if not 1 - max_rate <= rate <= 1 + max_rate:
        raise ValueError(f"{tid}: measured tempo change exceeds approved range")
    expected = evidence.get("sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"{tid}: missing source hash")
    with Path(tid).open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"{tid}: source changed since measurement")
    return {"track_id": tid, "bpm": bpm, "zero": zero}


def _intro_segments(clip, loop, notes, grid, name):
    if not _has(notes, "allow_intro_extension"):
        raise ValueError("intro extension needs an explicit DJ-note approval")
    verse = _note_number(notes, "observed_first_verse_start_seconds")
    start = _number(loop.get("start_seconds"), "intro loop start", 0)
    end = _number(loop.get("end_seconds"), "intro loop end", start + .001)
    plays = loop.get("plays", 3)
    if isinstance(plays, bool) or plays not in (2, 3):
        raise ValueError("intro extension allows two or three plays only")
    cue = clip["segments"][0]["source_start"]
    source_end = clip["segments"][0]["source_end"]
    if verse is None or not cue <= start < end <= verse or end >= source_end:
        raise ValueError("intro loop must be inside the approved pre-verse source region")
    rate = grid.rate(name)
    extra = (plays - 1) * (end - start) / rate
    if clip["fade_in"] * rate > verse - cue + extra * rate + 1e-6:
        raise ValueError("intro loop cannot cover the entire gentle incoming blend")
    segments = [{"source_start": cue, "source_end": end, "local_start": 0.0}]
    cursor = (end - cue) / rate
    for _ in range(plays - 1):
        segments.append({"source_start": start, "source_end": end, "local_start": cursor})
        cursor += (end - start) / rate
    segments.append({"source_start": end, "source_end": source_end, "local_start": cursor})
    clip["segments"] = segments
    clip["length"] += extra
    clip["advanced_technique"] = "short_intro_extension"


def _handoff(clip, move, notes, grid, name):
    a = _number(move.get("from_seconds"), "handoff source", 0)
    b = _number(move.get("to_seconds"), "handoff destination", 0)
    directive = track_directives({"dj_notes": notes})
    if b > a:
        if not directive["skip_handoff"] or directive["skip_from_seconds"] != a or directive["skip_to_seconds"] != b:
            raise ValueError("forward handoff must match the effective skip_handoff DJ notes")
    elif b < a:
        if not _has(notes, "allow_reentry"):
            raise ValueError("backward handoff needs an explicit re-entry DJ-note approval")
    else:
        raise ValueError("handoff cannot return to its current source point")
    beats = _number(move.get("blend_beats", 4), "same-song handoff beats", 4, 4)
    rate = grid.rate(name)
    fade = beats * grid.beat
    cue = clip["segments"][0]["source_start"]
    after = (a - cue) / rate - fade
    if after < clip["fade_in"] or after + fade >= clip["length"] - clip["fade_out"]:
        raise ValueError("handoff overlaps an entry/exit blend or lies outside the chosen body")
    # The two copies overlap, so no foreground source seek is audible.
    left = copy.deepcopy(clip)
    left["id"] += "-before-handoff"
    left["length"] = after + fade
    left["fade_out"] = fade
    left["segments"][0]["source_end"] = a
    right = grid.clip(clip["id"] + "-after-handoff", name, b,
                      b + (clip["length"] - after) * rate, clip["start"] + after,
                      fade_in=fade, fade_out=clip["fade_out"],
                      artist=clip["artist"], title=clip["title"])
    left["advanced_technique"] = right["advanced_technique"] = "same_song_handoff"
    return [left, right]


def compile_generic(plan, recipe):
    """Return a native performance only when every foreground has valid evidence."""
    if not isinstance(recipe, dict) or recipe.get("version") != 1 or recipe.get("approved") is not True:
        raise ValueError("advanced recipe must be version 1 and explicitly approved")
    if recipe.get("support"):
        raise ValueError("instrumental support is not enabled by this compiler stage")
    sources = recipe.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("advanced recipe needs a sources mapping")
    tempo = _number(recipe.get("tempo_bpm"), "mix tempo", 20, 400)
    pattern = recipe.get("pattern_beats", 4)
    if pattern not in (4, 8, 16):
        raise ValueError("pattern_beats must be 4, 8 or 16")
    tracks = plan["tracks"]
    if set(sources) != {t["track_id"] for t in tracks}:
        raise ValueError("measurement sources must cover exactly the finalized foreground set")
    transitions = [e for e in plan["events"] if e.get("op") == "transition"]
    bodies = {e["track_id"]: e for e in plan["events"] if e.get("op") == "play_body"}
    finale = next(e for e in plan["events"] if e.get("op") == "finale")
    if len(transitions) != len(tracks) - 1 or len(bodies) != len(tracks) - 1:
        raise ValueError("layered or incomplete conventional schedules cannot be translated")
    forbidden = {"hard_cut", "brake_out", "spinback_out", "key_blend", "snare_align"}
    for event in transitions:
        if event.get("keep_outgoing_live") or forbidden.intersection(event.get("moves", [])) or not "crossfade" in event.get("moves", []):
            raise ValueError("advanced clock cannot replace this explicit transition recipe")
        if event.get("incoming_bpm_target") or event.get("incoming_settle_bpm") or event.get("incoming_pitch_semitones"):
            raise ValueError("explicit tempo/pitch holds conflict with the measured common clock")
    measure = {}
    limits = {}
    for track in tracks:
        tid = track["track_id"]
        note = track.get("dj_notes") or ""
        d = track_directives(track)
        if d["exit_bpm"] or d["play_bpm"] or d["pitch_adjust_semitones"] or d["opener_style"]:
            raise ValueError("explicit opener, tempo or pitch notes must retain their conventional execution")
        measure[tid] = _measure(tid, sources[tid], max_rate=.08, tempo=tempo)
        if sources[tid].get("sample_unison"):
            raise ValueError("sample unison is not enabled by this compiler stage")
        limits[tid] = _limits(note)
    first = tracks[0]
    cue = _number(first.get("cue_seconds"), "first cue", 0)
    grid = Grid(tempo, measure, anchor=first["track_id"], anchor_source=cue, pattern_beats=pattern)
    clips = []
    foregrounds = []
    previous = None
    for index, track in enumerate(tracks):
        tid = track["track_id"]
        note = track.get("dj_notes") or ""
        evidence = sources[tid]
        cue = _number(track.get("cue_seconds"), "foreground cue", 0)
        incoming_beats = transitions[index - 1]["transition_beats"] if index else 0
        outgoing_beats = transitions[index]["transition_beats"] if index < len(transitions) else 0
        # Native envelopes are eased: 1.5 * sixteen counts keeps their maximum
        # channel-fader speed within the same gentle rule as a linear ramp.
        for beats in (incoming_beats, outgoing_beats):
            if beats and beats < 1.5 * GENTLE_BLEND_BEATS:
                raise ValueError("native eased blends need at least 24 counts; retain the original gentle plan")
        if index < len(tracks) - 1:
            body = bodies[tid]
            if body.get("exit_bpm_target") or body.get("skip_beats"):
                raise ValueError("audible skip or tempo ramp needs its explicit conventional execution")
            if body.get("handoff") and not evidence.get("handoff"):
                raise ValueError("a required skip handoff is missing from measured evidence")
            total_beats = incoming_beats + _number(body.get("beats"), "body beats", 0) + 1 + outgoing_beats
            length = total_beats * grid.beat
        elif finale.get("play_to_end"):
            length = _number(finale.get("seconds"), "finale remainder", .001) / grid.rate(tid)
        else:
            length = (incoming_beats + _number(finale.get("beats"), "finale beats", 1)) * grid.beat
        start = 0.0 if previous is None else Grid.end(previous) - incoming_beats * grid.beat
        aligned = grid.aligned_start(tid, cue, start)
        if abs(aligned - start) > 1e-5:
            raise ValueError(f"{tid}: approved cue does not match the common backbeat/pattern phase")
        clip = grid.clip(f"foreground-{index}", tid, cue, cue + length * grid.rate(tid), start,
                         fade_in=incoming_beats * grid.beat, fade_out=outgoing_beats * grid.beat,
                         artist=track.get("artist", ""), title=track.get("title", ""))
        if evidence.get("intro_loop") and evidence.get("handoff"):
            raise ValueError("intro extension and handoff need separate approved performances")
        if evidence.get("intro_loop"):
            _intro_segments(clip, evidence["intro_loop"], note, grid, tid)
        parts = _handoff(clip, evidence["handoff"], note, grid, tid) if evidence.get("handoff") else [clip]
        for part in parts:
            part["source_duration_seconds"] = _number(evidence.get("duration_seconds"), "measured source duration", .001)
            limits[tid]["max"] = min(limits[tid].get("max", math.inf), part["source_duration_seconds"])
        clips.extend(parts)
        foregrounds.append(parts)
        previous = parts[-1]
    performance = grid.performance(clips, source_limits=limits)
    performance["source_sha256"] = {tid: evidence["sha256"] for tid, evidence in sources.items()}
    validate(performance)
    result = copy.deepcopy(plan)
    result.update(performance=performance, performance_sha256=fingerprint(performance),
                  execution_mode="live_source_tracks", performance_origin=ORIGIN,
                  duration_seconds=duration(performance), events=compile_events(performance))
    result["advanced_mix"] = {"recipe_sha256": fingerprint(recipe), "stage": 1,
                              "techniques": sorted({c.get("advanced_technique", "measured_gentle_blend") for c in clips})}
    for index, segment in enumerate(result.get("segments", [])):
        segment.update(start_seconds=foregrounds[index + 1][0]["start"],
                       transition_seconds=foregrounds[index + 1][0]["fade_in"],
                       advanced_techniques=result["advanced_mix"]["techniques"],
                       technique="measured_native_blend", showcase_move=None)
    result["execution_note"] = "Measured original sources; native loops, same-song handoffs and gentle channel faders. No prepared or rendered audio."
    return result


def upgrade(plan, recipe_path):
    """Optional upgrade; invalid evidence returns the original plan plus a reason."""
    path = Path(recipe_path)
    if not path.exists():
        return plan
    try:
        recipe = json.loads(path.read_text())
        return compile_generic(plan, recipe)
    except (ValueError, TypeError, KeyError, OSError, StopIteration) as error:
        result = copy.deepcopy(plan)
        result["advanced_mix"] = {"status": "fallback", "reason": str(error)}
        result.setdefault("profile", {}).setdefault("order_notes", []).append("Advanced techniques declined: " + str(error))
        return result
