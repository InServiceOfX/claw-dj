#!/usr/bin/env python3
"""Generate vertical short-form clips (9:16, 1080x1920) from claw-dj transitions.

Two templates:
1. 'same_beat' — Sample reveal: shows which track sampled which, with a
   simple animated waveform visualizer and hook text.
2. 'watch_ai_mix' — Shows the LLM's plan/reasoning as paced on-screen
   captions over the transition audio.

Both end with a branded end card ('AI DJ 🦞 — repo in bio').

Usage:
    python -m hands.clip --plan <slug> --transition <N> --template same_beat
    python -m hands.clip --plan <slug> --transition <N> --template watch_ai_mix

Outputs: MP4 (H.264/AAC, 1080x1920, 30fps) + sidecar JSON with suggested
title, caption, and hashtags.

IMPORTANT: Clips with copyrighted tracks may be claimed by content owners.
Use royalty-free, licensed, or Suno-generated music for monetizable content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1080, 1920
FPS = 30
BRAND = "AI DJ 🦞 — repo in bio"
END_CARD_SECONDS = 2.5


@dataclass
class TransitionData:
    """Extracted transition info from a mix plan."""
    index: int
    from_artist: str
    from_title: str
    to_artist: str
    to_title: str
    technique: str
    transition_beats: int
    from_bpm: float
    to_bpm: float
    from_cue_seconds: float
    to_cue_seconds: float
    ride_beats: int
    reasoning: str = ""
    from_path: str = ""
    to_path: str = ""


@dataclass
class ClipConfig:
    """Configuration for clip generation."""
    template: str
    start_offset: float = 0.0
    duration: float = 20.0
    hook_text: str | None = None
    brand_image: str | None = None
    output_path: str = "clip.mp4"
    seed: int | None = None


def load_transition_from_plan(plan_path: Path, transition_index: int) -> TransitionData:
    """Load transition data from a mix plan JSON file."""
    data = json.loads(plan_path.read_text())
    events = data.get("events", data if isinstance(data, list) else [])
    
    track_info: dict[str, dict] = {}
    cue_by_id: dict[str, float] = {}
    id_by_label: dict[str, str] = {}
    
    for event in events:
        if event.get("op") in ("load", "preload_after_transition"):
            tid = event.get("track_id", "")
            if tid:
                track_info[tid] = {
                    "artist": event.get("artist", "Unknown"),
                    "title": event.get("title", "Unknown"),
                    "bpm": event.get("bpm", 0),
                }
                if event.get("cue_seconds") is not None:
                    cue_by_id[tid] = float(event["cue_seconds"])
                label = f"{event.get('artist', '')} — {event.get('title', '')}"
                id_by_label[label] = tid
    
    transitions = [e for e in events if e.get("op") == "transition"]
    if not transitions:
        raise ValueError("No transitions found in plan")
    if transition_index < 1 or transition_index > len(transitions):
        raise ValueError(f"Transition index {transition_index} out of range (1-{len(transitions)})")
    
    trans = transitions[transition_index - 1]
    from_label = trans.get("from_track", "")
    to_label = trans.get("to_track", "")
    from_id = id_by_label.get(from_label, "")
    to_id = id_by_label.get(to_label, "")
    
    from_info = track_info.get(from_id, {})
    to_info = track_info.get(to_id, {})
    
    ride_beats = 0
    for i, event in enumerate(events):
        if event.get("op") == "play_body" and event.get("track") == from_label:
            if i + 1 < len(events) and events[i + 1] == trans:
                ride_beats = int(event.get("beats", 0))
                break
    
    reasoning = trans.get("reasoning", "")
    if not reasoning:
        moves = trans.get("moves", [])
        tech = trans.get("technique", "blend")
        if moves:
            reasoning = f"Using {tech} technique with {', '.join(moves)}"
    
    return TransitionData(
        index=transition_index,
        from_artist=from_info.get("artist", from_label.split(" — ")[0] if " — " in from_label else "Unknown"),
        from_title=from_info.get("title", from_label.split(" — ")[-1] if " — " in from_label else from_label),
        to_artist=to_info.get("artist", to_label.split(" — ")[0] if " — " in to_label else "Unknown"),
        to_title=to_info.get("title", to_label.split(" — ")[-1] if " — " in to_label else to_label),
        technique=trans.get("technique", "standard_blend"),
        transition_beats=int(trans.get("transition_beats", 16)),
        from_bpm=float(from_info.get("bpm", 0) or trans.get("from_bpm", 100)),
        to_bpm=float(to_info.get("bpm", 0) or trans.get("to_bpm", 100)),
        from_cue_seconds=cue_by_id.get(from_id, 0.0),
        to_cue_seconds=cue_by_id.get(to_id, 0.0),
        ride_beats=ride_beats,
        reasoning=reasoning,
        from_path=from_id,
        to_path=to_id,
    )


def _font_path() -> str:
    """Find a suitable font path for text rendering."""
    candidates = [
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font with fallback to default."""
    font_path = _font_path()
    if font_path:
        try:
            index = 0 if not bold else 1
            return ImageFont.truetype(font_path, size, index=index)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = font.getbbox(test_line)
        if bbox[2] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(" ".join(current_line))
    
    return lines or [""]


def render_same_beat_frame(
    draw: ImageDraw.ImageDraw,
    frame_num: int,
    total_frames: int,
    transition: TransitionData,
    config: ClipConfig,
    waveform_data: list[float] | None = None,
) -> None:
    """Render a single frame for the 'same_beat' template."""
    progress = frame_num / max(1, total_frames - 1)
    
    bg_color = (15, 15, 25)
    accent = (92, 224, 168)
    text_color = (245, 247, 250)
    secondary = (150, 156, 170)
    
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=bg_color)
    
    hook = config.hook_text or f"{transition.from_artist} → {transition.to_artist}"
    if "same beat" in hook.lower() or config.hook_text is None:
        hook = "These use the same beat"
    
    title_font = _load_font(56, bold=True)
    hook_lines = _wrap_text(hook, title_font, WIDTH - 120)
    
    y_start = 280
    for line in hook_lines:
        bbox = title_font.getbbox(line)
        x = (WIDTH - bbox[2]) // 2
        draw.text((x, y_start), line, fill=accent, font=title_font)
        y_start += bbox[3] + 10
    
    track_font = _load_font(42)
    from_text = f"{transition.from_artist}"
    to_text = f"{transition.to_artist}"
    
    y_tracks = 500
    bbox_from = track_font.getbbox(from_text)
    x_from = (WIDTH - bbox_from[2]) // 2
    draw.text((x_from, y_tracks), from_text, fill=text_color, font=track_font)
    
    title_sm_font = _load_font(32)
    from_title_text = f'"{transition.from_title}"'
    bbox_ft = title_sm_font.getbbox(from_title_text)
    x_ft = (WIDTH - bbox_ft[2]) // 2
    draw.text((x_ft, y_tracks + 55), from_title_text, fill=secondary, font=title_sm_font)
    
    arrow_y = y_tracks + 140
    arrow_font = _load_font(64)
    draw.text((WIDTH // 2 - 30, arrow_y), "↓", fill=accent, font=arrow_font)
    
    y_to = arrow_y + 100
    bbox_to = track_font.getbbox(to_text)
    x_to = (WIDTH - bbox_to[2]) // 2
    draw.text((x_to, y_to), to_text, fill=text_color, font=track_font)
    
    to_title_text = f'"{transition.to_title}"'
    bbox_tt = title_sm_font.getbbox(to_title_text)
    x_tt = (WIDTH - bbox_tt[2]) // 2
    draw.text((x_tt, y_to + 55), to_title_text, fill=secondary, font=title_sm_font)
    
    wave_y = 1000
    wave_height = 200
    wave_width = WIDTH - 160
    wave_x = 80
    
    seed = config.seed or int(hashlib.md5(f"{transition.from_title}{transition.to_title}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed + frame_num // 3)
    
    num_bars = 48
    bar_width = wave_width // num_bars - 2
    
    for i in range(num_bars):
        base_height = 0.3 + 0.7 * abs(math.sin(i * 0.15 + progress * math.pi * 4))
        variation = rng.random() * 0.3
        bar_height = int((base_height + variation) * wave_height)
        
        x = wave_x + i * (wave_width // num_bars)
        y = wave_y + (wave_height - bar_height) // 2
        
        color_blend = (i / num_bars + progress) % 1.0
        r = int(92 + (255 - 92) * color_blend * 0.5)
        g = int(224 - 60 * color_blend)
        b = int(168 + (255 - 168) * color_blend * 0.3)
        
        draw.rectangle([x, y, x + bar_width, y + bar_height], fill=(r, g, b))
    
    bpm_font = _load_font(28)
    bpm_text = f"{transition.from_bpm:.0f} BPM → {transition.to_bpm:.0f} BPM"
    bbox_bpm = bpm_font.getbbox(bpm_text)
    x_bpm = (WIDTH - bbox_bpm[2]) // 2
    draw.text((x_bpm, wave_y + wave_height + 40), bpm_text, fill=secondary, font=bpm_font)
    
    is_end_card = frame_num >= total_frames - int(END_CARD_SECONDS * FPS)
    if is_end_card:
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (15, 15, 25, 200))
        
        brand_font = _load_font(48, bold=True)
        brand_lines = BRAND.split(" — ")
        y_brand = HEIGHT // 2 - 60
        
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(15, 15, 25))
        
        for line in brand_lines:
            bbox = brand_font.getbbox(line)
            x = (WIDTH - bbox[2]) // 2
            draw.text((x, y_brand), line, fill=accent, font=brand_font)
            y_brand += 70


def render_watch_ai_frame(
    draw: ImageDraw.ImageDraw,
    frame_num: int,
    total_frames: int,
    transition: TransitionData,
    config: ClipConfig,
    caption_segments: list[tuple[float, float, str]] | None = None,
) -> None:
    """Render a single frame for the 'watch_ai_mix' template."""
    progress = frame_num / max(1, total_frames - 1)
    current_time = frame_num / FPS
    
    bg_color = (12, 12, 20)
    accent = (80, 200, 255)
    text_color = (245, 247, 250)
    secondary = (150, 156, 170)
    highlight = (255, 84, 160)
    
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=bg_color)
    
    header_font = _load_font(36, bold=True)
    header = "Watch the AI mix"
    bbox = header_font.getbbox(header)
    x = (WIDTH - bbox[2]) // 2
    draw.text((x, 120), header, fill=accent, font=header_font)
    
    label_font = _load_font(28)
    track_font = _load_font(38)
    
    from_label = "NOW PLAYING"
    to_label = "UP NEXT"
    
    y_from = 220
    draw.text((80, y_from), from_label, fill=secondary, font=label_font)
    draw.text((80, y_from + 35), transition.from_artist, fill=text_color, font=track_font)
    
    title_font = _load_font(30)
    draw.text((80, y_from + 85), f'"{transition.from_title}"', fill=secondary, font=title_font)
    
    y_to = 380
    draw.text((80, y_to), to_label, fill=secondary, font=label_font)
    draw.text((80, y_to + 35), transition.to_artist, fill=text_color, font=track_font)
    draw.text((80, y_to + 85), f'"{transition.to_title}"', fill=secondary, font=title_font)
    
    panel_y = 540
    panel_height = 600
    draw.rectangle([60, panel_y, WIDTH - 60, panel_y + panel_height], 
                   fill=(25, 25, 35), outline=accent, width=2)
    
    panel_title_font = _load_font(32, bold=True)
    draw.text((80, panel_y + 20), "DJ Brain Analysis", fill=accent, font=panel_title_font)
    
    reasoning_parts = []
    
    tech_display = transition.technique.replace("_", " ").title()
    reasoning_parts.append(f"Technique: {tech_display}")
    reasoning_parts.append(f"Transition: {transition.transition_beats} beats")
    reasoning_parts.append(f"BPM match: {transition.from_bpm:.0f} → {transition.to_bpm:.0f}")
    
    if transition.reasoning:
        reason_clean = transition.reasoning.replace("Using ", "").replace(" technique", "")
        reasoning_parts.append(f"Strategy: {reason_clean}")
    
    moves_text = "EQ swap + crossfade"
    if "echo" in transition.technique.lower():
        moves_text = "Echo out → hard drop"
    elif "cut" in transition.technique.lower():
        moves_text = "Beat-synced hard cut"
    reasoning_parts.append(f"Moves: {moves_text}")
    
    content_font = _load_font(28)
    y_content = panel_y + 70
    
    for i, part in enumerate(reasoning_parts):
        reveal_time = (i / len(reasoning_parts)) * 0.7
        if progress >= reveal_time:
            alpha = min(1.0, (progress - reveal_time) / 0.1)
            color = tuple(int(c * alpha + bg_color[j] * (1 - alpha)) for j, c in enumerate(text_color))
            
            lines = _wrap_text(part, content_font, WIDTH - 180)
            for line in lines:
                draw.text((100, y_content), line, fill=color, font=content_font)
                y_content += 45
            y_content += 15
    
    prog_y = panel_y + panel_height + 60
    prog_width = WIDTH - 160
    prog_height = 8
    
    draw.rectangle([80, prog_y, 80 + prog_width, prog_y + prog_height], fill=(40, 40, 50))
    
    fill_width = int(prog_width * progress)
    if fill_width > 0:
        draw.rectangle([80, prog_y, 80 + fill_width, prog_y + prog_height], fill=accent)
    
    time_font = _load_font(24)
    elapsed = f"{int(current_time // 60)}:{int(current_time % 60):02d}"
    total = config.duration
    total_str = f"{int(total // 60)}:{int(total % 60):02d}"
    draw.text((80, prog_y + 20), elapsed, fill=secondary, font=time_font)
    bbox_total = time_font.getbbox(total_str)
    draw.text((WIDTH - 80 - bbox_total[2], prog_y + 20), total_str, fill=secondary, font=time_font)
    
    is_end_card = frame_num >= total_frames - int(END_CARD_SECONDS * FPS)
    if is_end_card:
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=bg_color)
        
        brand_font = _load_font(48, bold=True)
        brand_lines = BRAND.split(" — ")
        y_brand = HEIGHT // 2 - 60
        
        for line in brand_lines:
            bbox = brand_font.getbbox(line)
            x = (WIDTH - bbox[2]) // 2
            draw.text((x, y_brand), line, fill=accent, font=brand_font)
            y_brand += 70


def generate_sidecar(transition: TransitionData, config: ClipConfig, output_path: Path) -> dict:
    """Generate suggested title, caption, and hashtags for the clip."""
    seed = config.seed or int(time.time())
    rng = random.Random(seed)
    
    title_templates = [
        f"{transition.from_artist} → {transition.to_artist} transition",
        f"AI DJ blends {transition.from_artist} into {transition.to_artist}",
        f"Watch this {transition.from_artist} to {transition.to_artist} mix",
        f"{transition.technique.replace('_', ' ').title()}: {transition.from_artist} → {transition.to_artist}",
    ]
    
    if config.template == "same_beat":
        title_templates.extend([
            f"Same beat: {transition.from_artist} vs {transition.to_artist}",
            f"These tracks use the same beat 🔥",
            f"Sample reveal: {transition.from_title} → {transition.to_title}",
        ])
    
    title = rng.choice(title_templates)
    
    caption_templates = [
        f"🦞 AI DJ mixing {transition.from_artist} into {transition.to_artist}\n\n{transition.transition_beats}-beat transition using {transition.technique.replace('_', ' ')}\n\nLink in bio for the full project",
        f"Watch how the AI DJ handles this {transition.from_bpm:.0f} → {transition.to_bpm:.0f} BPM transition\n\n{transition.from_artist} → {transition.to_artist}\n\n🦞 claw-dj",
        f"The AI picked a {transition.technique.replace('_', ' ')} for this blend\n\n{transition.from_title} → {transition.to_title}\n\nFull mix coming soon 🎧",
    ]
    
    caption = rng.choice(caption_templates)
    
    base_hashtags = ["#AIDJ", "#clawdj", "#DJTransition", "#mixing", "#DJlife"]
    genre_hashtags = ["#hiphop", "#rnb", "#beats", "#samples"]
    tech_hashtags = ["#AImusic", "#MachineLearning", "#MusicTech"]
    
    hashtags = base_hashtags + rng.sample(genre_hashtags, 2) + rng.sample(tech_hashtags, 1)
    
    sidecar = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "transition_index": transition.index,
        "from_track": f"{transition.from_artist} — {transition.from_title}",
        "to_track": f"{transition.to_artist} — {transition.to_title}",
        "template": config.template,
        "duration_seconds": config.duration,
        "suggested_title": title,
        "suggested_caption": caption,
        "suggested_hashtags": hashtags,
        "output_file": str(output_path),
        "copyright_notice": "Clips with copyrighted tracks may be claimed. Use royalty-free, licensed, or Suno-generated music for monetizable content.",
    }
    
    return sidecar


def run_ffmpeg(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run ffmpeg with standard options."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def probe_audio(path: Path) -> dict:
    """Get audio duration and format info."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=sample_rate,channels",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def generate_clip(
    transition: TransitionData,
    config: ClipConfig,
    audio_path: Path | None = None,
) -> tuple[Path, dict]:
    """Generate a vertical clip and return the output path and sidecar data."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")
    
    output_path = Path(config.output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    total_frames = int(config.duration * FPS)
    
    with tempfile.TemporaryDirectory(prefix="clawdj-clip-") as tmpdir:
        tmp = Path(tmpdir)
        frames_dir = tmp / "frames"
        frames_dir.mkdir()
        
        for frame_num in range(total_frames):
            img = Image.new("RGB", (WIDTH, HEIGHT), (15, 15, 25))
            draw = ImageDraw.Draw(img)
            
            if config.template == "same_beat":
                render_same_beat_frame(draw, frame_num, total_frames, transition, config)
            elif config.template == "watch_ai_mix":
                render_watch_ai_frame(draw, frame_num, total_frames, transition, config)
            else:
                raise ValueError(f"Unknown template: {config.template}")
            
            frame_path = frames_dir / f"frame_{frame_num:05d}.png"
            img.save(frame_path, "PNG")
        
        video_only = tmp / "video.mp4"
        run_ffmpeg([
            "-framerate", str(FPS),
            "-i", str(frames_dir / "frame_%05d.png"),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(video_only),
        ])
        
        if audio_path and audio_path.exists():
            run_ffmpeg([
                "-i", str(video_only),
                "-ss", str(config.start_offset),
                "-t", str(config.duration),
                "-i", str(audio_path),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "320k",
                "-ar", "48000",
                "-shortest",
                str(output_path),
            ])
        else:
            silent_audio = tmp / "silence.wav"
            run_ffmpeg([
                "-f", "lavfi",
                "-i", f"anullsrc=r=48000:cl=stereo",
                "-t", str(config.duration),
                str(silent_audio),
            ])
            run_ffmpeg([
                "-i", str(video_only),
                "-i", str(silent_audio),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path),
            ])
    
    sidecar = generate_sidecar(transition, config, output_path)
    sidecar_path = output_path.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    
    return output_path, sidecar


def verify_output(path: Path, expected_duration: float) -> dict:
    """Verify the generated clip meets requirements."""
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True
    )
    probe = json.loads(result.stdout)
    
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    
    errors = []
    
    if not video or video.get("codec_name") != "h264":
        errors.append("Video codec is not H.264")
    if video and (video.get("width"), video.get("height")) != (WIDTH, HEIGHT):
        errors.append(f"Dimensions are not {WIDTH}x{HEIGHT}")
    if video and video.get("r_frame_rate") != f"{FPS}/1":
        errors.append(f"Frame rate is not {FPS} fps")
    
    if not audio or audio.get("codec_name") != "aac":
        errors.append("Audio codec is not AAC")
    
    actual_duration = float(probe.get("format", {}).get("duration", 0))
    if abs(actual_duration - expected_duration) > 0.5:
        errors.append(f"Duration {actual_duration:.1f}s differs from expected {expected_duration:.1f}s")
    
    decode = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True
    )
    if decode.returncode != 0:
        errors.append(f"Full decode failed: {decode.stderr[:200]}")
    
    return {
        "path": str(path),
        "size_bytes": int(probe.get("format", {}).get("size", 0)),
        "duration": actual_duration,
        "video": video,
        "audio": audio,
        "verified": len(errors) == 0,
        "errors": errors,
    }


def create_synthetic_transition() -> TransitionData:
    """Create a synthetic transition for testing."""
    return TransitionData(
        index=1,
        from_artist="Demo Artist A",
        from_title="Track One",
        to_artist="Demo Artist B",
        to_title="Track Two",
        technique="standard_blend",
        transition_beats=16,
        from_bpm=95.0,
        to_bpm=98.0,
        from_cue_seconds=0.0,
        to_cue_seconds=0.0,
        ride_beats=64,
        reasoning="Smooth BPM transition with EQ swap and 16-beat crossfade",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate vertical short-form clips from claw-dj transitions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--plan", type=Path, help="Path to mix plan JSON or plan slug")
    parser.add_argument("--transition", type=int, default=1, help="Transition number (1-indexed)")
    parser.add_argument("--template", choices=["same_beat", "watch_ai_mix"], default="same_beat",
                        help="Clip template to use")
    parser.add_argument("--audio", type=Path, help="Source audio file for the clip")
    parser.add_argument("--start-offset", type=float, default=0.0,
                        help="Start offset in audio (seconds)")
    parser.add_argument("--duration", type=float, default=20.0,
                        help="Clip duration (15-30 seconds recommended)")
    parser.add_argument("--hook-text", help="Override hook text on screen")
    parser.add_argument("--brand-image", type=Path, help="Optional brand/mascot image")
    parser.add_argument("--output", type=Path, required=True, help="Output MP4 path")
    parser.add_argument("--seed", type=int, help="Random seed for variation")
    parser.add_argument("--synthetic", action="store_true",
                        help="Use synthetic test data instead of a plan")
    
    args = parser.parse_args(argv)
    
    if args.synthetic:
        transition = create_synthetic_transition()
    elif args.plan:
        plan_path = args.plan.expanduser().resolve()
        if not plan_path.exists():
            from brain import plan_paths
            try:
                paths = plan_paths.resolve(str(args.plan))
                plan_path = paths.mix_plan
            except Exception as e:
                print(f"Error: Could not find plan: {e}", file=sys.stderr)
                return 1
        transition = load_transition_from_plan(plan_path, args.transition)
    else:
        print("Error: Either --plan or --synthetic is required", file=sys.stderr)
        return 1
    
    config = ClipConfig(
        template=args.template,
        start_offset=args.start_offset,
        duration=args.duration,
        hook_text=args.hook_text,
        brand_image=str(args.brand_image) if args.brand_image else None,
        output_path=str(args.output),
        seed=args.seed,
    )
    
    print(f"Generating {config.template} clip for transition #{transition.index}")
    print(f"  {transition.from_artist} — {transition.from_title}")
    print(f"  → {transition.to_artist} — {transition.to_title}")
    print(f"  Duration: {config.duration}s, Output: {config.output_path}")
    
    try:
        output_path, sidecar = generate_clip(
            transition,
            config,
            audio_path=args.audio,
        )
        
        verification = verify_output(output_path, config.duration)
        
        print("\nOutput:")
        print(f"  Video: {output_path}")
        print(f"  Sidecar: {output_path.with_suffix('.json')}")
        print(f"  Size: {verification['size_bytes'] / 1024:.1f} KB")
        print(f"  Duration: {verification['duration']:.1f}s")
        print(f"  Verified: {verification['verified']}")
        
        if verification["errors"]:
            print("\nVerification errors:")
            for error in verification["errors"]:
                print(f"  - {error}")
            return 1
        
        print("\nSuggested metadata:")
        print(f"  Title: {sidecar['suggested_title']}")
        print(f"  Hashtags: {' '.join(sidecar['suggested_hashtags'])}")
        
        return 0
        
    except Exception as e:
        print(f"Error generating clip: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
