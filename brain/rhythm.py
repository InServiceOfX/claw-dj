"""Rust-backed rhythm analysis, local cache, reviewed markers, and build preparation.

Backbeat = the snare/clap accent. No Mixxx connection, network, or model download
is made here. Optional learned beat/downbeat evidence uses an explicit local
checkpoint. The deterministic multiband analyzer is available without a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "brain/data/rhythm"
VERSION = 1
FADE_POLICY_VERSION = 3


def blend_seconds(planned_seconds: float, bpm: float, *,
                  remaining_seconds: float | None = None) -> float:
    """Shared policy: only available audio, never rhythm evidence, limits a fade."""
    if not math.isfinite(planned_seconds) or planned_seconds < 0 or not math.isfinite(bpm) or bpm <= 0:
        raise ValueError("blend needs a finite nonnegative duration and positive BPM")
    duration = planned_seconds
    if remaining_seconds is not None:
        if not math.isfinite(remaining_seconds):
            raise ValueError("remaining audio duration must be finite")
        duration = min(duration, max(0.0, remaining_seconds))
    return duration


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, allow_nan=False)
            handle.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def core(command: str, *, args=(), payload=None, timeout=180) -> dict:
    binary = Path(os.environ.get("CLAWDJ_RHYTHM_BIN", ROOT / "core-rust/target/release/clawdj"))
    if not binary.is_file():
        raise RuntimeError("Backbeat analyzer unavailable: run cargo build --release in core-rust")
    result = subprocess.run(
        [str(binary), "rhythm", command, *map(str, args)],
        input=None if payload is None else json.dumps(payload, allow_nan=False),
        text=True, capture_output=True, timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Backbeat {command}: {result.stderr.strip()[:800]}")
    return json.loads(result.stdout)


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


@lru_cache(maxsize=16)
def _tool_digest(path: str, size: int, mtime: int, ctime: int) -> str:
    """Memoize small tool fingerprints, never the audio content hash."""
    return _digest(Path(path))


def _analyzer_identity() -> dict:
    paths = {
        "analyzer_sha256": ROOT / "core-rust/clawdj/src/rhythm.rs",
        "binary_sha256": Path(os.environ.get("CLAWDJ_RHYTHM_BIN", ROOT / "core-rust/target/release/clawdj")),
    }
    result = {"version": VERSION}
    for key, path in paths.items():
        stat = path.stat()
        result[key] = _tool_digest(str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    return result


def _reference_path(track: dict, first_beat: float, cache_dir: Path) -> Path:
    # Different plans may use different analyzed grids for the same file.
    # Keep separate references so one plan cannot hide another's valid cache.
    key = json.dumps([str(Path(track["track_id"]).resolve()), float(track["bpm"]), float(first_beat)])
    return cache_dir / "references" / f"{hashlib.sha256(key.encode()).hexdigest()}.json"


def _publish_reference(track: dict, first_beat: float, cache_dir: Path, cached: Path, result: dict) -> None:
    stat = cached.stat()
    sections = result["sections"]
    atomic_json(_reference_path(track, first_beat, cache_dir), {
        "identity": result["identity"], "cache_file": cached.name,
        "cache_size": stat.st_size, "cache_mtime_ns": stat.st_mtime_ns,
        "section_count": len(sections),
        "uncertain_sections": sum(s["confidence"] < 0.45 for s in sections),
    })


def analysis_status(track: dict, *, first_beat: float, cache_dir: Path | None = None) -> dict | None:
    """Read-only, cheap cache check for UI polling; no audio hash/decode or DSP.

    An uncertain but successfully analyzed section is cached, not missing.
    Missing/stale tracks are content-hashed when analyzed; Build always
    rechecks content identity, even when the lightweight reference is current.
    """
    cache_dir = CACHE if cache_dir is None else cache_dir
    try:
        reference = json.loads(_reference_path(track, first_beat, cache_dir).read_text())
        identity = reference["identity"]
        if not isinstance(identity, dict):
            return None
        if not identity_matches(reference, track["track_id"]):
            return None
        if identity["bpm"] != float(track["bpm"]) or identity["first_beat_seconds"] != float(first_beat):
            return None
        if any(identity.get(key) != value for key, value in _analyzer_identity().items()):
            return None
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        if reference["cache_file"] != f"{key}.json":
            return None
        stat = (cache_dir / reference["cache_file"]).stat()
        if stat.st_size != reference["cache_size"] or stat.st_mtime_ns != reference["cache_mtime_ns"]:
            return None
        audio_hash = identity["audio_sha256"]
        if len(audio_hash) != 64 or any(c not in "0123456789abcdef" for c in audio_hash):
            return None
        marker = cache_dir / "annotations" / f"{audio_hash}.json"
        annotations = json.loads(marker.read_text()) if marker.is_file() else {}
        if annotations != identity.get("annotations", {}):
            return None
        return {"cached": True, "section_count": int(reference["section_count"]),
                "uncertain_sections": int(reference["uncertain_sections"])}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def identity_matches(rhythm: dict, path: str) -> bool:
    """Cheap live stale-file check; full content hashing is done at build time."""
    identity = rhythm.get("identity", {})
    try:
        stat = Path(path).stat()
        return (identity.get("version") == VERSION and stat.st_size == identity.get("size")
                and stat.st_mtime_ns == identity.get("mtime_ns"))
    except OSError:
        return False


def analyze_track(track: dict, *, first_beat: float, cache_dir: Path | None = None) -> dict:
    cache_dir = CACHE if cache_dir is None else cache_dir
    path = Path(track["track_id"])
    stat = path.stat()
    audio_hash = _digest(path)
    marker_file = cache_dir / "annotations" / f"{audio_hash}.json"
    annotations = json.loads(marker_file.read_text()) if marker_file.is_file() else {}
    identity = {
        "audio_sha256": audio_hash, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
        "bpm": float(track["bpm"]), "first_beat_seconds": first_beat,
        **_analyzer_identity(),
        "annotations": annotations,
    }
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cached = cache_dir / f"{key}.json"
    if cached.is_file():
        try:
            result = json.loads(cached.read_text())
            if result["identity"] != identity or not isinstance(result["sections"], list):
                raise ValueError("stale rhythm cache")
            _publish_reference(track, first_beat, cache_dir, cached, result)
            return result
        except (ValueError, KeyError, TypeError):
            pass  # Interrupted/corrupt derived caches are safe to regenerate.
    result = core("analyze", args=[path, "--bpm", track["bpm"], "--first-beat", first_beat])
    if annotations.get("drum_evidence"):
        result["onsets"] = annotations["drum_evidence"]["onsets"]
        result = core("refit", payload=result)
        for section in result["sections"]:
            section["source"] = "independent_drum_transcription"
        result["drum_evidence"] = annotations["drum_evidence"]
    result["identity"] = identity
    result["analysis_kind"] = "multiband_transients"
    result["confidence_kind"] = "heuristic_agreement_not_instrument_probability"
    for marker in annotations.get("regions", []):
        start, end = marker["start_seconds"], marker["end_seconds"]
        beat_s = 60.0 / result["bpm"]
        seconds = marker["backbeat_seconds"]
        phase = ((seconds - first_beat) / beat_s) % marker["cadence_beats"]
        # A reviewed region replaces only overlapping analysis within its bounds.
        sections = []
        for section in result["sections"]:
            if section["end_seconds"] <= start or section["start_seconds"] >= end:
                sections.append(section)
            else:
                if section["start_seconds"] < start:
                    sections.append({**section, "end_seconds": start})
                if section["end_seconds"] > end:
                    sections.append({**section, "start_seconds": end})
        sections.append({"start_seconds": start, "end_seconds": end,
                         "cadence_beats": marker["cadence_beats"], "phase_beats": phase,
                         "confidence": 1.0, "coverage": 1.0, "spread_beats": 0.0,
                         "source": "human_reviewed"})
        result["sections"] = sorted(sections, key=lambda s: s["start_seconds"])
    if annotations.get("downbeat_seconds") is not None:
        result["downbeat_seconds"] = annotations["downbeat_seconds"]
    if annotations.get("beat_model"):
        result["beat_model"] = annotations["beat_model"]
        # A model output is independent evidence, not a silent rewrite of the
        # Mixxx source grid. Dynamic/mismatched grids need explicit reanalysis.
        beat_s = 60.0 / result["bpm"]
        for section in result["sections"]:
            beats = [b for b in result["beat_model"]["beats"] if section["start_seconds"] <= b < section["end_seconds"]]
            errors = sorted(abs(((b-first_beat)/beat_s+0.5) % 1.0-0.5)*beat_s for b in beats)
            if errors and errors[int((len(errors)-1)*0.9)] > 0.08:
                section["confidence"] = 0.0
                section["source"] = "beat_model_disagrees_with_mixxx_grid"
                continue
            downbeats = [b for b in result["beat_model"]["downbeats"] if section["start_seconds"] <= b < section["end_seconds"]]
            # Adopt bar phase only with repeated independent agreement. Never
            # infer musical 1 just because a beatgrid begins at this timestamp.
            if len(beats) >= 8 and len(downbeats) >= 3:
                intervals = [(b-a)/beat_s for a,b in zip(downbeats,downbeats[1:])]
                phases = [abs(((b-downbeats[0])/beat_s+2) % 4-2) for b in downbeats]
                if all(abs(v-4)<0.20 for v in intervals) and max(phases)<0.15:
                    section["downbeat_seconds"] = downbeats[0]
    after = path.stat()
    if (after.st_size, after.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise RuntimeError("audio changed during analysis; rebuild after edits finish")
    atomic_json(cached, result)
    _publish_reference(track, first_beat, cache_dir, cached, result)
    return result


def section_at(rhythm: dict, seconds: float) -> dict | None:
    candidates = [s for s in rhythm.get("sections", []) if s["start_seconds"] <= seconds < s["end_seconds"]]
    return min(candidates, key=lambda s: abs(seconds-(s["start_seconds"]+s["end_seconds"])/2)) if candidates else None


def alignment(outgoing, incoming, out_seconds, in_seconds, out_rate, in_rate, overlap) -> dict:
    return core("align", payload={
        "outgoing": outgoing, "incoming": incoming,
        "outgoing_seconds": out_seconds, "incoming_seconds": in_seconds,
        "outgoing_rate": out_rate, "incoming_rate": in_rate,
        "overlap_seconds": overlap,
    }, timeout=10)


def phase_error(outgoing, incoming, out_seconds, in_seconds, out_rate, in_rate) -> float | None:
    """Signed seconds to the corresponding backbeat, from observed positions.

    This checks the timing of analyzed audio, not a microphone recording.
    Keep it cheap enough to run during the fader movement without subprocesses.
    """
    out, inc = section_at(outgoing, out_seconds), section_at(incoming, in_seconds)
    if not out or not inc or min(out["confidence"], inc["confidence"]) < 0.45:
        return None
    out_beat, in_beat = 60.0/outgoing["bpm"], 60.0/incoming["bpm"]
    cycle = out["cadence_beats"]*out_beat/out_rate
    other = inc["cadence_beats"]*in_beat/in_rate
    if abs(cycle-other) > 0.01:
        return None
    out_phase = (outgoing["first_beat_seconds"]+out["phase_beats"]*out_beat-out_seconds)/out_rate
    in_phase = (incoming["first_beat_seconds"]+inc["phase_beats"]*in_beat-in_seconds)/in_rate
    return (out_phase-in_phase+cycle/2) % cycle-cycle/2


def prepare_plan(plan: dict, *, analyze=analyze_track) -> dict:
    """Apply to FINAL events, including plan-scoped technique/beat overrides.

    Replay source positions for previews; the live runner always solves again
    from observed deck positions. All unresolved transitions stay explicit.
    """
    lookup = {}
    failures = {}
    grids = {}
    source_timing = {}
    for event in plan.get("events", []):
        if event.get("op") == "play_body" and event.get("phase_anchor"):
            grids[event.get("track")] = event["phase_anchor"]
    for track in plan.get("tracks", []):
        tid = track["track_id"]
        label = f"{track.get('artist')} — {track.get('title')}"
        grid = track.get("source_grid") or grids.get(label, {})
        bpm = float(grid.get("grid_bpm") or track.get("bpm") or 0)
        source_timing[tid] = {"bpm": bpm, "duration_seconds": track.get("duration_seconds")}
        cue = float(track.get("cue_seconds") or 0)
        first = grid.get("first_beat_seconds")
        if first is None and track.get("cue_beat_index") is not None and bpm:
            first = cue-float(track["cue_beat_index"])*60/bpm
        try:
            if not bpm or first is None:
                raise ValueError("missing analyzed source beatgrid")
            lookup[tid] = analyze({**track, "bpm": bpm}, first_beat=float(first))
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            failures[tid] = str(error)
    tracks = {t["track_id"]: t for t in plan.get("tracks", [])}
    decks, pending = {}, None
    summary = {"ready": 0, "fallback": 0, "not_applicable": 0}
    transition_index = 0
    for i, event in enumerate(plan.get("events", [])):
        op = event.get("op")
        if op == "load":
            decks[event["deck"]] = {"id": event["track_id"], "seconds": float(event.get("cue_seconds") or 0), "rate": 1.0}
        elif op == "start" and event["deck"] in decks:
            state = decks[event["deck"]]
            bpm = float(tracks.get(state["id"], {}).get("bpm") or 0)
            if event.get("bpm_target") and bpm:
                state["rate"] = float(event["bpm_target"])/bpm
        elif op == "recue" and event["deck"] in decks:
            decks[event["deck"]]["seconds"] = float(event.get("cue_seconds") or 0)
        elif op == "preload_after_transition":
            pending = event
        elif op == "play_body" and event["deck"] in decks:
            state = decks[event["deck"]]
            rhythm = lookup.get(state["id"]) or source_timing.get(state["id"], {})
            if rhythm.get("bpm"):
                beat_s = 60/rhythm["bpm"]
                beats = int(event.get("beats") or 0)
                next_fade = next((float(e.get("transition_beats") or 16) for e in plan["events"][i+1:] if e.get("op") == "transition"), 0)
                if rhythm.get("duration_seconds"):
                    available = math.floor((rhythm["duration_seconds"]-state["seconds"])/beat_s-next_fade-5)
                    if beats > max(0, available):
                        reduction = max(0, math.ceil((beats-max(0,available))/4)*4)
                        beats = max(0, beats-reduction)
                state["seconds"] += (beats+int(event.get("skip_beats") or 0))*beat_s
                if event.get("exit_bpm_target"):
                    state["rate"] = float(event["exit_bpm_target"])/rhythm["bpm"]
        elif op == "transition":
            outgoing = decks.get(event["from_deck"], {})
            incoming = decks.get(event["to_deck"], {})
            out = lookup.get(outgoing.get("id"))
            inc = lookup.get(incoming.get("id"))
            legacy = [m for m in event.get("moves", []) if m in {"snare_align", "snare_align_back"}]
            event["moves"] = [m for m in event.get("moves", []) if m not in {"snare_align", "snare_align_back"}]
            metadata = {"version": VERSION, "outgoing_id": outgoing.get("id"), "incoming_id": incoming.get("id"),
                        "status": "fallback", "reason": "missing local rhythm evidence", "legacy_moves_superseded": legacy,
                        "fade_policy_version": FADE_POLICY_VERSION, "automatic_short_handoffs": 0,
                        "verification": "unverified", "tolerance_ms": 60.0}
            moves = event.get("moves", [])
            rhythmic = "sync" in moves and not ({"hard_cut", "echo_out_exit"} & set(moves)) and event.get("technique") not in {"vocal_over_bed", "half_time_or_cut", "key_clash_cut", "beat_drop_entry"}
            if not rhythmic or event.get("keep_outgoing_live"):
                metadata.update(status="not_applicable", reason="separate vocal layer or non-overlapping transition recipe")
            elif out and inc:
                out_rate = outgoing["rate"]
                incoming_rate = float(event.get("incoming_bpm_target") or out["bpm"]*out_rate)/inc["bpm"]
                overlap = float(event.get("transition_beats") or 16)*60/(out["bpm"]*out_rate)
                # The old body assumes a following beat edge; retain that nominal
                # reference only for preview. Live launch uses actual positions.
                nominal = outgoing["seconds"]+60/out["bpm"]
                try:
                    decision = alignment(out, inc, nominal, incoming["seconds"], out_rate, incoming_rate, overlap)
                    metadata.update(status="ready" if decision["status"] == "ready" else "fallback", reason=decision["reason"], predicted=decision)
                    metadata["verification"] = {"ready": "predicted", "incompatible": "mismatch"}.get(decision["status"], "unverified")
                    launch = nominal + decision["delay_seconds"]*out_rate
                    if launch+overlap*out_rate > out["duration_seconds"]-0.1:
                        metadata.update(status="fallback", reason="not enough outgoing audio for aligned overlap")
                    overlap = blend_seconds(overlap, out["bpm"] * out_rate,
                                            remaining_seconds=(out["duration_seconds"] - launch) / out_rate - 0.15)
                    metadata["preview"] = {"outgoing_seconds": launch, "incoming_seconds": incoming["seconds"],
                                           "outgoing_rate": out_rate, "incoming_rate": incoming_rate, "overlap_seconds": overlap}
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                    metadata["reason"] = str(error)
                    overlap = blend_seconds(overlap, out["bpm"] * out_rate,
                                            remaining_seconds=(out["duration_seconds"] - nominal) / out_rate - 0.15)
                    metadata["preview"] = {"outgoing_seconds": nominal, "incoming_seconds": incoming["seconds"],
                                           "outgoing_rate": out_rate, "incoming_rate": incoming_rate, "overlap_seconds": overlap}
                metadata["outgoing"] = out
                metadata["incoming"] = inc
                incoming["seconds"] += overlap*incoming_rate
                incoming["rate"] = incoming_rate if event.get("keep_blend_tempo") or event.get("incoming_bpm_target") else float(event.get("incoming_settle_bpm") or inc["bpm"])/inc["bpm"]
            else:
                metadata["reason"] = "; ".join(failures.get(s.get("id"), "missing deck/grid") for s in (outgoing,incoming) if s.get("id") not in lookup)
                # Failed DSP does not mean playback skipped the body or blend.
                # Preserve nominal chain timing without inventing drum evidence.
                out_timing = out or source_timing.get(outgoing.get("id"), {})
                in_timing = inc or source_timing.get(incoming.get("id"), {})
                if out_timing.get("bpm") and in_timing.get("bpm"):
                    out_rate = outgoing["rate"]
                    bpm = out_timing["bpm"] * out_rate
                    incoming_rate = float(event.get("incoming_bpm_target") or bpm) / in_timing["bpm"]
                    nominal = outgoing["seconds"] + 60 / out_timing["bpm"]
                    remaining = None
                    if out_timing.get("duration_seconds"):
                        remaining = (out_timing["duration_seconds"] - nominal) / out_rate - 0.15
                    overlap = blend_seconds(float(event.get("transition_beats") or 16) * 60 / bpm,
                                            bpm, remaining_seconds=remaining)
                    metadata["preview"] = {"outgoing_seconds": nominal, "incoming_seconds": incoming["seconds"],
                                           "outgoing_rate": out_rate, "incoming_rate": incoming_rate,
                                           "overlap_seconds": overlap}
                    incoming["seconds"] += overlap * incoming_rate
                    incoming["rate"] = incoming_rate if event.get("keep_blend_tempo") or event.get("incoming_bpm_target") else float(event.get("incoming_settle_bpm") or in_timing["bpm"]) / in_timing["bpm"]
            event["backbeat"] = metadata
            summary[metadata["status"]] += 1
            if transition_index < len(plan.get("segments", [])):
                plan["segments"][transition_index]["backbeat"] = {k: v for k,v in metadata.items() if k not in {"outgoing","incoming"}}
            transition_index += 1
            freed = event["to_deck"] if event.get("keep_outgoing_live") else event["from_deck"]
            if pending and pending.get("deck") == freed:
                decks[freed] = {"id": pending["track_id"], "seconds": float(pending.get("cue_seconds") or 0), "rate": 1.0}
                pending = None
    plan["backbeat"] = {"version": VERSION, **summary, "analysis_failures": failures,
                        "note": "Backbeat = snare/clap accents. Readiness is predicted; live positions and listening verify playback."}
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Upgrade an existing plan in place without reordering; preserves a backup")
    prepare.add_argument("--plan", type=Path, required=True)
    analysis = sub.add_parser("analyze")
    analysis.add_argument("path", type=Path)
    analysis.add_argument("--bpm", type=float, required=True)
    analysis.add_argument("--first-beat", type=float, required=True)
    annotation = sub.add_parser("annotate", help="Store a reviewed local backbeat region, reusable in all plans")
    annotation.add_argument("path", type=Path)
    annotation.add_argument("--start", type=float, required=True)
    annotation.add_argument("--end", type=float, required=True)
    annotation.add_argument("--backbeat", type=float, required=True)
    annotation.add_argument("--cadence", type=float, choices=[1,2,4], default=2)
    annotation.add_argument("--downbeat", type=float)
    annotation.add_argument("--author", required=True)
    model = sub.add_parser("model", help="Add independent beat/downbeat evidence from an explicit local Beat This checkpoint")
    model.add_argument("path", type=Path)
    model.add_argument("--checkpoint", type=Path, required=True)
    drum = sub.add_parser("import-drums", help="Import explicit local snare/clap onset evidence, never generic beat ticks")
    drum.add_argument("path", type=Path)
    drum.add_argument("--evidence", type=Path, required=True, help='JSON: {"instrument":"snare|clap|backbeat", "onsets":[{"seconds":0.5,"strength":1.0}]}')
    drum.add_argument("--source", required=True, help="Model/checkpoint identity or human author")
    args = parser.parse_args()
    if args.command == "prepare":
        from brain.plan_revision import file_rev, write_checked
        path = args.plan.resolve()
        before = file_rev(path)
        if not before:
            parser.error("plan must already exist")
        original = json.loads(path.read_text())
        plan = json.loads(json.dumps(original))
        prepare_plan(plan)
        backup = path.parent / "backups" / f"{path.stem}-before-backbeat-{uuid.uuid4().hex[:12]}.json"
        atomic_json(backup, original)
        write_checked(path, plan, before)
        print(json.dumps(plan["backbeat"], indent=2))
        print(f"Prepared {path}; previous artifact: {backup}")
        return
    if args.command == "analyze":
        print(json.dumps(analyze_track({"track_id": str(args.path.resolve()), "bpm": args.bpm}, first_beat=args.first_beat), indent=2))
        return
    audio_hash = _digest(args.path)
    target = CACHE/"annotations"/f"{audio_hash}.json"
    data = json.loads(target.read_text()) if target.is_file() else {"audio_sha256": audio_hash, "regions": []}
    if args.command == "annotate":
        if not all(math.isfinite(v) for v in (args.start,args.end,args.backbeat)) or not 0 <= args.start <= args.backbeat < args.end:
            parser.error("require finite 0 <= start <= backbeat < end")
        data["regions"].append({"start_seconds":args.start,"end_seconds":args.end,"backbeat_seconds":args.backbeat,"cadence_beats":args.cadence,"author":args.author})
        if args.downbeat is not None:
            if not math.isfinite(args.downbeat) or args.downbeat < 0:
                parser.error("downbeat must be a finite nonnegative source timestamp")
            data["downbeat_seconds"] = args.downbeat
    elif args.command == "import-drums":
        supplied = json.loads(args.evidence.read_text())
        if supplied.get("instrument") not in {"snare","clap","backbeat"} or not supplied.get("onsets"):
            parser.error("supply nonempty snare/clap/backbeat onsets, not generic beat/downbeat timestamps")
        for hit in supplied["onsets"]:
            if not all(isinstance(hit.get(k), (int,float)) and math.isfinite(hit[k]) for k in ("seconds","strength")) or hit["seconds"]<0 or hit["strength"]<=0:
                parser.error("onsets require finite nonnegative seconds and positive strength")
        data["drum_evidence"] = {**supplied,"source":args.source,"evidence_sha256":_digest(args.evidence)}
    else:
        if not args.checkpoint.is_file():
            parser.error("checkpoint must be an existing local file; no automatic downloads")
        try:
            from beat_this.inference import File2Beats
        except ImportError:
            parser.error("optional Beat This! backend is not installed; see docs/BACKBEAT_MATCHING.md")
        beats, downbeats = File2Beats(checkpoint_path=str(args.checkpoint), device="cpu", dbn=False)(str(args.path))
        data["beat_model"] = {"name":"Beat This!", "checkpoint_sha256":_digest(args.checkpoint), "beats":[float(b) for b in beats], "downbeats":[float(b) for b in downbeats]}
    atomic_json(target, data)
    print(f"Saved rhythm evidence to {target}. Rebuild the mix to use it.")


if __name__ == "__main__":
    main()
