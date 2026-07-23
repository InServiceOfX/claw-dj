#!/usr/bin/env python3
"""Render and verify a branded 9:16 claw-dj transition teaser on macOS."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audio", type=Path, required=True, help="Source WAV/audio file")
    p.add_argument("--before-image", type=Path, required=True)
    p.add_argument("--after-image", type=Path, required=True)
    p.add_argument("--source-start", type=float, required=True, help="Excerpt start in source seconds")
    p.add_argument("--cut-offset", type=float, required=True, help="Artwork cut in output seconds")
    p.add_argument("--duration", type=float, default=30.0)
    p.add_argument("--label", required=True, help="Transition label, e.g. 'BRANDY → LL COOL J'")
    p.add_argument("--series", default="QUICK MIX 001")
    p.add_argument("--output", type=Path, required=True)
    return p


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, text=True, capture_output=True)


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"required command not found: {name}")


def require_file(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise SystemExit(f"{label} not found: {resolved}")
    return resolved


def scene_times(path: Path, threshold: float) -> list[float]:
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    return [float(value) for value in re.findall(r"pts_time:([0-9.]+)", result.stderr)]


def main() -> int:
    args = parser().parse_args()
    for name in ("ffmpeg", "ffprobe", "swift"):
        require_command(name)

    audio = require_file(args.audio, "audio")
    before_image = require_file(args.before_image, "before image")
    after_image = require_file(args.after_image, "after image")
    if args.source_start < 0:
        raise SystemExit("--source-start must be non-negative")
    if args.duration <= 0:
        raise SystemExit("--duration must be positive")
    if not 0 < args.cut_offset < args.duration:
        raise SystemExit("--cut-offset must be greater than zero and less than duration")

    script_dir = Path(__file__).resolve().parent
    card_script = require_file(script_dir / "render_teaser_card.swift", "card renderer")
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="clawdj-teaser-") as tmp:
        tmpdir = Path(tmp)
        before_card = tmpdir / "before.png"
        after_card = tmpdir / "after.png"
        for source, destination in ((before_image, before_card), (after_image, after_card)):
            run(
                [
                    "swift",
                    str(card_script),
                    str(source),
                    str(destination),
                    args.label,
                    args.series,
                ]
            )

        before_duration = args.cut_offset
        after_duration = args.duration - args.cut_offset
        fade_out_start = max(0.0, args.duration - 0.5)
        filter_graph = (
            "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p[v];"
            f"[2:a]afade=t=in:st=0:d=0.15,"
            f"afade=t=out:st={fade_out_start}:d=0.5[a]"
        )
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-loop",
                "1",
                "-framerate",
                "30",
                "-t",
                str(before_duration),
                "-i",
                str(before_card),
                "-loop",
                "1",
                "-framerate",
                "30",
                "-t",
                str(after_duration),
                "-i",
                str(after_card),
                "-ss",
                str(args.source_start),
                "-t",
                str(args.duration),
                "-i",
                str(audio),
                "-filter_complex",
                filter_graph,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-profile:v",
                "high",
                "-level:v",
                "4.2",
                "-c:a",
                "aac",
                "-b:a",
                "320k",
                "-ar",
                "48000",
                "-movflags",
                "+faststart",
                "-shortest",
                str(output),
            ]
        )

    probe = json.loads(
        run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels,bit_rate",
                "-of",
                "json",
                str(output),
            ]
        ).stdout
    )
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    errors: list[str] = []
    if not video or video.get("codec_name") != "h264":
        errors.append("video codec is not H.264")
    if video and (video.get("width"), video.get("height")) != (1080, 1920):
        errors.append("video is not 1080x1920")
    if video and video.get("r_frame_rate") != "30/1":
        errors.append("video is not 30 fps")
    if not audio_stream or audio_stream.get("codec_name") != "aac":
        errors.append("audio codec is not AAC")
    if audio_stream and audio_stream.get("sample_rate") != "48000":
        errors.append("audio is not 48 kHz")
    if audio_stream and audio_stream.get("channels") != 2:
        errors.append("audio is not stereo")
    actual_duration = float(probe.get("format", {}).get("duration", 0))
    if abs(actual_duration - args.duration) > 0.05:
        errors.append(f"duration {actual_duration:.3f}s differs from requested {args.duration:.3f}s")

    decode = run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"], check=False)
    if decode.returncode != 0:
        errors.append(f"full decode failed: {decode.stderr.strip()}")

    detected = scene_times(output, 0.10)
    used_threshold = 0.10
    if not any(abs(t - args.cut_offset) <= 0.10 for t in detected):
        detected = scene_times(output, 0.005)
        used_threshold = 0.005
    if not any(abs(t - args.cut_offset) <= 0.10 for t in detected):
        errors.append(f"no scene change detected near {args.cut_offset:.3f}s; got {detected}")
    unexpected = [t for t in detected if abs(t - args.cut_offset) > 0.10]
    if unexpected:
        errors.append(f"unexpected scene changes: {unexpected}")

    volume = run(
        ["ffmpeg", "-hide_banner", "-i", str(output), "-af", "volumedetect", "-f", "null", "-"],
        check=False,
    )
    mean_match = re.search(r"mean_volume:\s*([^\s]+) dB", volume.stderr)
    max_match = re.search(r"max_volume:\s*([^\s]+) dB", volume.stderr)
    if not mean_match or mean_match.group(1) == "-inf":
        errors.append("audio appears silent or volumedetect failed")

    report = {
        "output": str(output),
        "duration": actual_duration,
        "size": int(probe.get("format", {}).get("size", 0)),
        "video": video,
        "audio": audio_stream,
        "decode_exit": decode.returncode,
        "scene_threshold": used_threshold,
        "scene_times": detected,
        "mean_volume_db": mean_match.group(1) if mean_match else None,
        "max_volume_db": max_match.group(1) if max_match else None,
        "verified": not errors,
        "errors": errors,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
