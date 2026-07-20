"""Render every planned transition as a listenable audio snippet.

Reading a mix plan's JSON tells a human nothing about how a transition
FEELS — and a full live Mixxx run costs ~40 minutes per iteration loop.
This renders each transition in `mix_plan.json` as a short audio file
(~12s of the outgoing track, the real crossfade at the planned length and
tempo treatment, ~12s of the incoming track from its real cue), plus an
`index.html` with play buttons, so a whole set's transitions can be
auditioned by ear in a few minutes.

Faithfulness notes (approximation, deliberately):
  - cue points, ride lengths, fade lengths, and tempo targets come from the
    actual plan + dj_notes play_bpm holds — the same numbers the live
    runner uses
  - tempo treatment uses ffmpeg `atempo` (pitch-preserving, like Mixxx
    keylock); sync'd entries are rendered at the outgoing deck's live bpm
  - EQ moves, filter sweeps, and flourishes are NOT rendered — this
    previews beat/tempo/cue alignment, which is what keeps needing ear
    checks, not the seasoning
  - hard cuts (brake/beat_drop) render as a butt splice instead of a fade

Usage:
    uv run python -m brain.preview_transitions            # all transitions
    uv run python -m brain.preview_transitions --only 3   # just transition 3
    open brain/data/previews/index.html
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path

from brain.build_mix_plan import track_directives

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_PLAN = DATA_DIR / "mix_plan.json"
DEFAULT_OUT_DIR = DATA_DIR / "previews"
CONTEXT_SECONDS = 12.0


def transition_specs(events: list[dict], tracks_by_id: dict[str, dict]) -> list[dict]:
    """Walk the plan's event list and produce one render spec per transition.

    Pure function (no audio work) so the sequencing logic is unit-testable:
    cue per track comes from load/preload events, ride length from the
    play_body immediately preceding each transition, tempo treatment from
    incoming_bpm_target / each track's own play_bpm directive.
    """
    cue_by_id: dict[str, float] = {}
    id_by_label: dict[str, str] = {}
    for event in events:
        if event.get("op") in ("load", "preload_after_transition") and event.get("track_id"):
            tid = event["track_id"]
            if event.get("cue_seconds") is not None:
                cue_by_id[tid] = float(event["cue_seconds"])
            if event.get("artist") and event.get("title"):
                id_by_label[f"{event['artist']} — {event['title']}"] = tid

    def play_rate(tid: str) -> float:
        track = tracks_by_id.get(tid) or {}
        native = track.get("bpm")
        if not native:
            return 1.0
        directive = track_directives(track)
        if directive.get("play_bpm"):
            return float(directive["play_bpm"]) / float(native)
        return 1.0

    specs = []
    last_ride_beats: float | None = None
    last_body_label: str | None = None
    for event in events:
        if event.get("op") == "play_body":
            last_ride_beats = float(event.get("beats") or 0)
            last_body_label = event.get("track")
        if event.get("op") != "transition":
            continue
        out_label = event.get("from_track")
        in_label = event.get("to_track")
        out_tid = id_by_label.get(out_label)
        in_tid = id_by_label.get(in_label)
        if not out_tid or not in_tid:
            specs.append({"error": f"missing track file for {out_label} -> {in_label}"})
            continue
        out_track = tracks_by_id.get(out_tid) or {}
        in_track = tracks_by_id.get(in_tid) or {}
        out_native = float(out_track.get("bpm") or 0)
        in_native = float(in_track.get("bpm") or 0)
        if not out_native or not in_native:
            specs.append({"error": f"missing bpm for {out_label} -> {in_label}"})
            continue
        out_cue = cue_by_id.get(out_tid, 0.0)
        ride_beats = last_ride_beats if last_body_label == out_label else None
        if ride_beats is None:
            specs.append({"error": f"no ride length for {out_label}"})
            continue
        # Beats consumed map to file time via the track's OWN grid,
        # regardless of playback rate.
        anchor_file_s = out_cue + ride_beats * 60.0 / out_native
        out_rate = play_rate(out_tid)
        out_played_bpm = out_native * out_rate

        fade_beats = float(event.get("transition_beats") or 16)
        echo_out = "echo_out_exit" in (event.get("moves") or [])
        hard = "hard_cut" in (event.get("moves") or []) or event.get("technique") in (
            "beat_drop_entry", "half_time_or_cut", "key_clash_cut"
        )
        fade_wall_s = 0.0 if (hard or echo_out) else fade_beats * 60.0 / out_played_bpm

        if event.get("incoming_bpm_target") is not None:
            in_rate = float(event["incoming_bpm_target"]) / in_native
        elif "sync" in (event.get("moves") or []) and not hard and not echo_out:
            in_rate = out_played_bpm / in_native
        else:
            in_rate = 1.0

        specs.append({
            "index": len([s for s in specs if "error" not in s]) + 1,
            "from_label": out_label,
            "to_label": in_label,
            "technique": event.get("technique"),
            "out_path": out_tid,
            "in_path": in_tid,
            "out_start_s": max(0.0, anchor_file_s - CONTEXT_SECONDS * out_rate),
            "out_duration_s": CONTEXT_SECONDS * out_rate + fade_wall_s * out_rate,
            "out_rate": out_rate,
            "in_start_s": cue_by_id.get(in_tid, 0.0),
            "in_duration_s": (fade_wall_s + CONTEXT_SECONDS) * in_rate,
            "in_rate": in_rate,
            "fade_wall_s": round(fade_wall_s, 3),
            "hard_cut": hard,
            "echo_out": echo_out,
        })
    return specs


def _atempo_chain(rate: float) -> str:
    """ffmpeg atempo accepts 0.5-2.0 per instance; chain for safety."""
    filters = []
    remaining = rate
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters)


ECHO_OUT_RAMP_S = 1.0  # matches the live ~1s echo_out_exit ramp


def render_spec(spec: dict, out_file: Path) -> None:
    fade = spec["fade_wall_s"]
    out_filter = _atempo_chain(spec["out_rate"])
    if spec.get("echo_out"):
        # Approximate the live echo-out: a rising echo on the outgoing
        # segment's last second, crossfaded into the incoming track (NOT
        # spliced) -- the runner fix, 2026-07-19, makes the incoming deck
        # start and the crossfader move DURING the same ramp so there is
        # never a silent gap; concat here would misrepresent that as a
        # sequential cut-to-silence-then-start.
        out_filter += ",aecho=0.8:0.85:80|160:0.5|0.35"
    joiner = (
        "[a][b]concat=n=2:v=0:a=1[out]"
        if spec["hard_cut"] or fade < 0.1
        else f"[a][b]acrossfade=d={(ECHO_OUT_RAMP_S if spec.get('echo_out') else fade):.3f}[out]"
    )
    command = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{spec['out_start_s']:.3f}", "-t", f"{spec['out_duration_s']:.3f}",
        "-i", spec["out_path"],
        "-ss", f"{spec['in_start_s']:.3f}", "-t", f"{spec['in_duration_s']:.3f}",
        "-i", spec["in_path"],
        "-filter_complex",
        f"[0:a]{out_filter}[a];"
        f"[1:a]{_atempo_chain(spec['in_rate'])}[b];{joiner}",
        "-map", "[out]", "-codec:a", "libmp3lame", "-qscale:a", "4",
        str(out_file),
    ]
    subprocess.run(command, check=True, capture_output=True)


def write_index(specs: list[dict], out_dir: Path) -> Path:
    rows = []
    for spec in specs:
        if "error" in spec:
            rows.append(f"<li class='err'>{html.escape(spec['error'])}</li>")
            continue
        name = f"{spec['index']:02d}.mp3"
        label = html.escape(f"{spec['from_label']}  →  {spec['to_label']}")
        detail = html.escape(
            f"{spec['technique']} · fade {spec['fade_wall_s']}s"
            + (" · HARD CUT" if spec["hard_cut"] else "")
        )
        rows.append(
            f"<li><div class='t'>{spec['index']:02d}. {label}</div>"
            f"<div class='d'>{detail}</div>"
            f"<audio controls preload='none' src='{name}'></audio></li>"
        )
    page = (
        "<!doctype html><meta charset='utf-8'><title>Transition previews</title>"
        "<style>body{font:14px -apple-system,sans-serif;max-width:760px;margin:2rem auto;"
        "padding:0 1rem}li{margin:1rem 0;list-style:none}.t{font-weight:600}"
        ".d{color:#666;font-size:12px;margin:2px 0 4px}audio{width:100%}"
        ".err{color:#b00}</style>"
        "<h1>Transition previews</h1><p>Beat/tempo/cue alignment only — EQ moves "
        "and flourishes are not rendered.</p><ul>" + "".join(rows) + "</ul>"
    )
    index = out_dir / "index.html"
    index.write_text(page)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--only", type=int, default=None,
                        help="render just this transition number")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text())
    events = plan["events"] if isinstance(plan, dict) else plan
    from brain.library_index import connect

    with connect() as db:
        tracks_by_id = {
            row["track_id"]: dict(row)
            for row in db.execute("SELECT track_id, bpm, dj_notes FROM tracks")
        }
    specs = transition_specs(events, tracks_by_id)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rendered = failed = 0
    for spec in specs:
        if "error" in spec:
            print(f"  SKIP: {spec['error']}")
            continue
        if args.only is not None and spec["index"] != args.only:
            continue
        out_file = args.out_dir / f"{spec['index']:02d}.mp3"
        try:
            render_spec(spec, out_file)
            rendered += 1
            print(f"  [{spec['index']:02d}] {spec['from_label']} -> {spec['to_label']}")
        except subprocess.CalledProcessError as error:
            failed += 1
            print(f"  FAILED [{spec['index']:02d}]: {error.stderr.decode()[:200]}")
    index = write_index(specs, args.out_dir)
    print(f"\n{rendered} rendered, {failed} failed -> {args.out_dir}")
    print(f"listen: open {index}")


if __name__ == "__main__":
    main()
