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
import sqlite3
from pathlib import Path

from brain.build_mix_plan import track_directives
from brain.performance_author import Grid
from shared.gentle_faders import GENTLE_BLEND_BEATS
from shared.performance import compile_events, duration, fingerprint, validate

ORIGIN = "generic-measured-v1"


def is_generated(plan):
    """Only an untouched compiled output remains owned by generic Build."""
    if plan.get("performance_origin") != ORIGIN:
        return False
    try:
        performance = plan["performance"]
        return (plan["advanced_mix"]["performance_sha256"] == fingerprint(performance)
                and plan["events"] == compile_events(performance))
    except (KeyError, TypeError, ValueError):
        return False


def _number(value, label, low=-math.inf, high=math.inf):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label}: invalid measurement")
    return float(value)


def _note_number(notes, name):
    values = re.findall(r"\b" + re.escape(name) + r"\s*=\s*(\d+(?:\.\d+)?)", notes, re.I)
    return float(values[-1]) if values else None


def _has(notes, token):
    return bool(re.search(r"\b" + re.escape(token) + r"\b", notes, re.I))


def _permission(notes, token):
    values = re.findall(r"\b" + re.escape(token) + r"\b(?:\s*=\s*(true|false|yes|no|1|0))?", notes, re.I)
    return bool(values) and values[-1].lower() not in ("false", "no", "0")


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
    if not _permission(notes, "allow_intro_extension"):
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
        if not _permission(notes, "skip_handoff") or directive["skip_from_seconds"] != a or directive["skip_to_seconds"] != b:
            raise ValueError("forward handoff must match the effective skip_handoff DJ notes")
    elif b < a:
        if not _permission(notes, "allow_reentry"):
            raise ValueError("backward handoff needs an explicit re-entry DJ-note approval")
    else:
        raise ValueError("handoff cannot return to its current source point")
    beats = _number(move.get("blend_beats", 4), "same-song handoff beats", 4, 4)
    if directive.get("skip_handoff_beats") is not None and directive["skip_handoff_beats"] != beats:
        raise ValueError("handoff blend conflicts with the effective DJ-note length")
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
    right_end = clip["segments"][0]["source_end"] if clip.get("play_to_end") else b + (clip["length"] - after) * rate
    right = grid.clip(clip["id"] + "-after-handoff", name, b,
                      right_end, clip["start"] + after,
                      fade_in=fade, fade_out=clip["fade_out"],
                      artist=clip["artist"], title=clip["title"])
    left["advanced_technique"] = right["advanced_technique"] = "same_song_handoff"
    return [left, right]


def _sample_pairs(tracks, sources):
    by_id = {t["track_id"]: t for t in tracks}
    indices = {t["track_id"]: i for i, t in enumerate(tracks)}
    pairs = []
    occupied = set()
    for sampler in tracks:
        tid = sampler["track_id"]
        evidence = sources.get(tid)
        if not isinstance(evidence, dict):
            raise ValueError("source evidence must be an object")
        move = evidence.get("sample_unison")
        if move is None:
            continue
        if not isinstance(move, dict) or move.get("approved") is not True or move.get("backbeat_verified") is not True:
            raise ValueError("sample unison needs approved measured backbeat evidence")
        other = move.get("source_track_id")
        if other not in by_id or abs(indices[tid] - indices[other]) != 1:
            raise ValueError("sample source and sampling record must be adjacent in the optimized order")
        if tid in occupied or other in occupied:
            raise ValueError("sample-unison pairs cannot share an overlapping role")
        if not _permission(sampler.get("dj_notes", ""), "allow_sample_unison") or _has(sampler.get("dj_notes", ""), "no_flourish"):
            raise ValueError("sample unison needs unconflicted DJ-note approval on the sampling record")
        _number(move.get("alignment_error_ms"), "sample alignment error", -20, 20)
        _number(move.get("residual_pitch_cents"), "sample/source pitch residual", -15, 15)
        _number(move.get("confidence"), "sample relation confidence", .9, 1)
        _number(move.get("sample_start_seconds"), "sample bar start", 0)
        _number(move.get("source_start_seconds"), "original sampled bar start", 0)
        if move.get("entry_region_instrumental") is not True:
            raise ValueError("sample-bar repetition requires an approved instrumental entry region")
        beats = move.get("sample_beats")
        if isinstance(beats, bool) or beats not in (8, 16, 32):
            raise ValueError("sample unison needs an 8/16/32-beat measured sampled span")
        for record in (tid, other):
            if sources[record].get("intro_loop") or sources[record].get("handoff"):
                raise ValueError("sample pairs with other structural moves require an authored performance")
        pairs.append((tid, other, move))
        occupied.update((tid, other))
    return pairs, occupied


def _sample_blends(foregrounds, tracks, pairs, grid):
    indices = {t["track_id"]: i for i, t in enumerate(tracks)}
    for sampler, source, move in pairs:
        index = min(indices[sampler], indices[source])
        outgoing = foregrounds[index][-1]
        incoming = foregrounds[index + 1][0]
        cue_a = move["sample_start_seconds"] if outgoing["track_id"] == sampler else move["source_start_seconds"]
        cue_b = move["sample_start_seconds"] if incoming["track_id"] == sampler else move["source_start_seconds"]
        actual_a = outgoing["segments"][0]["source_end"] - outgoing["fade_out"] * outgoing["rate"]
        actual_b = incoming["segments"][0]["source_start"]
        if abs(actual_a - cue_a) > .02 or abs(actual_b - cue_b) > .02:
            raise ValueError("sample blend does not enter on the measured sampled bar; keep the approved cues")
        window = _number(move.get("verified_beats"), "verified sample overlap", move["sample_beats"], 128)
        blend_beats = incoming["fade_in"] / grid.beat
        if window < blend_beats:
            raise ValueError("sample relation was not verified throughout the whole blend")
        plays = blend_beats / move["sample_beats"]
        if abs(plays - round(plays)) > 1e-6 or round(plays) not in (1, 2, 3):
            raise ValueError("sample bar must cover the blend in one, two or three whole plays")
        # Repetition belongs to the entering original, never a prepared loop.
        if round(plays) > 1:
            end = cue_b + move["sample_beats"] * grid.beat * incoming["rate"]
            old_end = incoming["segments"][0]["source_end"]
            if end >= old_end:
                raise ValueError("sample span leaves no foreground body after the blend")
            segments = []
            cursor = 0.0
            for _ in range(round(plays)):
                segments.append({"source_start": cue_b, "source_end": end, "local_start": cursor})
                cursor += move["sample_beats"] * grid.beat
            segments.append({"source_start": end, "source_end": old_end, "local_start": cursor})
            extra = (round(plays) - 1) * move["sample_beats"] * grid.beat
            incoming["segments"] = segments
            incoming["length"] += extra
            # All later foregrounds move by complete measured pattern periods.
            for group in foregrounds[index + 2:]:
                for clip in group:
                    clip["start"] += extra
        incoming["advanced_technique"] = "measured_sample_unison"
        incoming["sample_relation"] = {"sampling_track_id": sampler, "source_track_id": source,
                                       "sample_beats": move["sample_beats"], "alignment_error_ms": move["alignment_error_ms"],
                                       "residual_pitch_cents": move["residual_pitch_cents"]}
        # Native playback already uses keylock=0, pitch_adjust=0 and exact
        # source rate, undoing turntable-style sample slowdown without guessed tuning.


def _support_layer(recipe, foregrounds, tracks, grid, limits, support_notes):
    requests = recipe.get("support", [])
    if not isinstance(requests, list) or len(requests) > 1:
        raise ValueError("use at most one continuous supporting layer")
    if not requests:
        return [], None, {}
    request = requests[0]
    if not isinstance(request, dict) or request.get("approved") is not True:
        raise ValueError("instrumental support needs an approved measured recipe")
    ids = request.get("foreground_track_ids") or [request.get("foreground_track_id")]
    ordered = [t["track_id"] for t in tracks]
    if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids) or any(tid not in ordered for tid in ids):
        raise ValueError("support must identify included foreground recordings")
    positions = sorted(ordered.index(tid) for tid in ids)
    if positions != list(range(positions[0], positions[-1] + 1)):
        raise ValueError("continuous support needs consecutive foregrounds")
    from brain.stems import classify_stem
    for position in positions:
        track = tracks[position]
        note = track.get("dj_notes") or ""
        if classify_stem(track.get("title", ""), track["track_id"]) != "full_mix":
            raise ValueError("full-mix support cannot reclassify an acapella or instrumental foreground")
        if not _permission(note, "allow_instrumental_support") or _has(note, "no_instrumental_support"):
            raise ValueError("full-mix support needs unconflicted effective DJ-note approval")
    tid = request.get("track_id")
    if not isinstance(tid, str) or not tid or tid in ordered:
        raise ValueError("support is an independent instrumental source, not a duplicate foreground identity")
    if request.get("instrumental_verified") is not True or request.get("backbeat_verified") is not True:
        raise ValueError("support needs a verified instrumental and measured backbeat relationship")
    _number(request.get("alignment_error_ms"), "support alignment error", -20, 20)
    _number(request.get("residual_pitch_cents"), "support pitch residual", -15, 15)
    if support_notes is None or tid not in support_notes:
        raise ValueError("current effective support-source DJ notes are required")
    limits[tid] = _limits(support_notes[tid])
    evidence = request.get("source")
    grid.m[tid] = _measure(tid, evidence, max_rate=.08, tempo=grid.tempo)
    limits[tid]["max"] = min(limits[tid].get("max", math.inf), _number(evidence.get("duration_seconds"), "support source duration", .001))
    start = foregrounds[positions[0]][0]["start"]
    end = Grid.end(foregrounds[positions[-1]][-1])
    _number(request.get("verified_seconds"), "verified support duration", end - start)
    fade = 1.5 * GENTLE_BLEND_BEATS * grid.beat
    if end - start < 2 * fade:
        raise ValueError("support body is too short for both gentle fades")
    beats = request.get("loop_beats")
    if isinstance(beats, bool) or beats not in (8, 16, 32, 64):
        raise ValueError("support needs an 8/16/32/64-beat measured instrumental loop")
    s0 = _number(request.get("source_start_seconds"), "support loop start", 0)
    s1 = _number(request.get("source_end_seconds"), "support loop end", s0 + .001)
    loop = {"track_id": tid, "source_start": s0, "source_end": s1,
            "rate": grid.rate(tid), "beats": beats,
            "gain_db": _number(request.get("gain_db", -6), "support gain", -9, -3)}
    eq = request.get("bed_eq", [1, .25, .25])
    foreground_eq = request.get("foreground_eq", [.35, 1, 1])
    if not isinstance(eq, list) or not isinstance(foreground_eq, list) or len(eq) != 3 or len(foreground_eq) != 3:
        raise ValueError("support needs calibrated low/mid/high EQ triples")
    _number(eq[0], "support low EQ", .5, 1)
    for gain in eq[1:]: _number(gain, "support mid/high EQ", 0, .5)
    _number(foreground_eq[0], "foreground low EQ", 0, .5)
    for gain in foreground_eq[1:]: _number(gain, "foreground vocal EQ", .75, 1)
    for position in positions:
        for clip in foregrounds[position]:
            clip["live_eq"] = list(foreground_eq)
            clip["instrumental_support"] = tid
    bed = grid.bed("support-bed", tid, loop, start, end,
                   fade_in=fade, fade_out=fade, support={"transition_seconds": .001,
                   "low_gain": eq[0], "mid_gain": eq[1], "high_gain": eq[2]},
                   artist=request.get("artist", "Instrumental"), title=request.get("title", "Continuous support"))
    bed["advanced_technique"] = "continuous_instrumental_support"
    bed["foreground_track_ids"] = ids
    return [bed], loop, {tid: evidence["sha256"]}


def compile_generic(plan, recipe, *, support_notes=None):
    """Return a native performance only when every foreground has valid evidence."""
    if not isinstance(recipe, dict) or type(recipe.get("version")) is not int or recipe.get("version") != 1 or recipe.get("approved") is not True:
        raise ValueError("advanced recipe must be version 1 and explicitly approved")
    sources = recipe.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("advanced recipe needs a sources mapping")
    if any(not isinstance(v, dict) for v in sources.values()):
        raise ValueError("source evidence must be an object")
    for evidence in sources.values():
        for name in ("intro_loop", "handoff", "sample_unison"):
            if evidence.get(name) is not None and (not isinstance(evidence[name], dict) or not evidence[name]):
                raise ValueError(f"{name} must contain an approved structural recipe")
    tempo = _number(recipe.get("tempo_bpm"), "mix tempo", 20, 400)
    pattern = recipe.get("pattern_beats", 4)
    if pattern not in (4, 8, 16):
        raise ValueError("pattern_beats must be 4, 8 or 16")
    tracks = plan["tracks"]
    if (plan.get("dj_format") or {}).get("name", "none") != "none":
        raise ValueError("explicit DJ formats retain their conventional recipes")
    if set(sources) != {t["track_id"] for t in tracks}:
        raise ValueError("measurement sources must cover exactly the finalized foreground set")
    pairs, sample_ids = _sample_pairs(tracks, sources)
    transitions = [e for e in plan["events"] if e.get("op") == "transition"]
    bodies = {e["track_id"]: e for e in plan["events"] if e.get("op") == "play_body"}
    finale = next(e for e in plan["events"] if e.get("op") == "finale")
    if len(transitions) != len(tracks) - 1 or len(bodies) != len(tracks) - 1:
        raise ValueError("layered or incomplete conventional schedules cannot be translated")
    forbidden = {"hard_cut", "brake_out", "spinback_out", "key_blend", "snare_align"}
    for event in transitions:
        if event.get("author"):
            raise ValueError("authored pair overrides retain their conventional execution")
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
        if any(d[key] for key in ("exit_bpm", "play_bpm", "pitch_adjust_semitones", "opener_style",
                                 "entry_style", "exit_style", "format_recipe", "landing_seconds",
                                 "pickup_beats", "settle_bpm", "keep_blend_tempo")):
            raise ValueError("explicit style, format, tempo or pitch notes must retain their conventional execution")
        measure[tid] = _measure(tid, sources[tid], max_rate=.16 if tid in sample_ids else .08, tempo=tempo)
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
        if index == len(tracks) - 1 and finale.get("play_to_end"):
            clip["play_to_end"] = True
        if evidence.get("intro_loop") and evidence.get("handoff"):
            raise ValueError("intro extension and handoff need separate approved performances")
        if evidence.get("intro_loop"):
            _intro_segments(clip, evidence["intro_loop"], note, grid, tid)
        parts = _handoff(clip, evidence["handoff"], note, grid, tid) if evidence.get("handoff") else [clip]
        verse_end = _note_number(note, "observed_final_verse_end_seconds")
        if verse_end is not None and index < len(tracks) - 1:
            original_exit = cue + (incoming_beats + bodies[tid]["beats"] + 1) * 60 / _number(track.get("bpm"), "original source BPM", 20, 400)
            native_exit = parts[-1]["segments"][-1]["source_end"] - parts[-1]["fade_out"] * parts[-1]["rate"]
            if original_exit >= verse_end and native_exit < verse_end - 1e-6:
                raise ValueError("measured timing would begin the exit before the confirmed final verse ends")
        for part in parts:
            part["source_duration_seconds"] = _number(evidence.get("duration_seconds"), "measured source duration", .001)
            limits[tid]["max"] = min(limits[tid].get("max", math.inf), part["source_duration_seconds"])
        clips.extend(parts)
        foregrounds.append(parts)
        previous = parts[-1]
    _sample_blends(foregrounds, tracks, pairs, grid)
    beds, loop, bed_hashes = _support_layer(recipe, foregrounds, tracks, grid, limits, support_notes)
    clips.extend(beds)
    performance = grid.performance(clips, loop=loop, source_limits=limits)
    performance["source_sha256"] = {**{tid: evidence["sha256"] for tid, evidence in sources.items()}, **bed_hashes}
    validate(performance)
    result = copy.deepcopy(plan)
    result.update(performance=performance, performance_sha256=fingerprint(performance),
                  execution_mode="live_source_tracks", performance_origin=ORIGIN,
                  duration_seconds=duration(performance), events=compile_events(performance))
    result["advanced_mix"] = {"recipe_sha256": fingerprint(recipe), "stage": 3,
                              "performance_sha256": fingerprint(performance),
                              "techniques": sorted({c.get("advanced_technique", "measured_gentle_blend") for c in clips})}
    for index, segment in enumerate(result.get("segments", [])):
        segment.update(start_seconds=foregrounds[index + 1][0]["start"],
                       transition_seconds=foregrounds[index + 1][0]["fade_in"],
                       advanced_techniques=result["advanced_mix"]["techniques"],
                       technique="measured_native_blend", showcase_move=None)
    result["execution_note"] = "Measured original sources; native loops, same-song handoffs and gentle channel faders. No prepared or rendered audio."
    return result


def upgrade(plan, recipe_path, *, slug=None):
    """Optional upgrade; invalid evidence returns the original plan plus a reason."""
    path = Path(recipe_path)
    if not path.exists():
        return plan
    try:
        recipe = json.loads(path.read_text())
        support_notes = None
        if isinstance(recipe, dict) and recipe.get("support"):
            from brain.plan_notes import get_effective
            requests = recipe["support"]
            if not isinstance(requests, list) or any(not isinstance(r, dict) for r in requests):
                raise ValueError("support must be a list of measured requests")
            ids = [r["track_id"] for r in requests if isinstance(r.get("track_id"), str)]
            support_notes = {item.track_id: item.note for item in get_effective(slug, ids)}
        return compile_generic(plan, recipe, support_notes=support_notes)
    except (ValueError, TypeError, KeyError, OSError, StopIteration, sqlite3.Error) as error:
        result = copy.deepcopy(plan)
        result["advanced_mix"] = {"status": "fallback", "reason": str(error)}
        result.setdefault("profile", {}).setdefault("order_notes", []).append("Advanced techniques declined: " + str(error))
        return result
