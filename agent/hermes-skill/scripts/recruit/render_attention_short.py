#!/usr/bin/env python3
"""Render 9:16 recruit attention short + overlay cards for claw-dj.

MoneyPrinter-style text cards via PIL (Homebrew ffmpeg often lacks drawtext).
Noe stack: motion/audio from frame 1, short hook text, comment token CTA.

Uses an existing verified 9:16 craft teaser as the picture/audio bed, then
burns hook → mid → CTA overlays. Outputs stay under Data/Public/Generated/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WORK = Path(
    "/Users/ernestyeung/.openclaw/workspace/Data/Public/Generated/claw-dj-recruit-2026-09"
)
OVER = WORK / "overlays"
OUT = WORK / "out"
# Prior verified ANL lineage short (9:16, 28s) — musical bed already correct.
BASE = Path(
    "/Users/ernestyeung/.openclaw/workspace/Data/Public/Generated/"
    "claw-dj-youtube-2026-08-05/shorts/01-all-night-to-smooth-operator-9x16.mp4"
)
DURATION = 18.0
W, H = 1080, 1920
WHITE = (255, 255, 255, 255)
GOLD = (244, 215, 164, 255)
SOFT = (255, 255, 255, 210)


def font(size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", size, index=index)


def shadow_text(draw, xy, text, fnt, fill, shadow=(0, 0, 0, 200)):
    x, y = xy
    for dx, dy in ((3, 3), (2, 4), (4, 2)):
        draw.text((x + dx, y + dy), text, font=fnt, fill=shadow)
    draw.text((x, y), text, font=fnt, fill=fill)


def centered(draw, y, text, fnt, fill):
    box = draw.textbbox((0, 0), text, font=fnt)
    x = (W - (box[2] - box[0])) // 2
    shadow_text(draw, (x, y), text, fnt, fill)


def card(*lines: tuple[str, int, int, tuple]) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for text, size, y, color in lines:
        centered(draw, y, text, font(size, 0 if size >= 56 else 2), color)
    return img


def write_overlays() -> None:
    OVER.mkdir(parents=True, exist_ok=True)
    badge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(badge)
    shadow_text(d, (48, 64), "claw-dj", font(30, 5), SOFT)
    badge.save(OVER / "badge.png")
    card(("NOT A PLAYLIST.", 72, 240, WHITE), ("IT'S A DJ.", 72, 340, GOLD)).save(
        OVER / "hook.png"
    )
    card(("BUILD → LIVE MIXXX", 56, 260, GOLD)).save(OVER / "mid.png")
    card(
        ("NEED 2 PEOPLE", 64, 220, WHITE),
        ("1  DJ EXPERT", 48, 320, GOLD),
        ("2  PAYING CUSTOMER", 48, 400, GOLD),
        ("COMMENT  DJ  OR  CUSTOMER", 36, 520, WHITE),
    ).save(OVER / "cta.png")


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd[:12]), "...")
    subprocess.run(cmd, check=True)


def render_short() -> Path:
    if not BASE.is_file():
        raise SystemExit(f"missing base teaser: {BASE}")
    write_overlays()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "v2-attention-recruit-9x16.mp4"
    # Scale base if needed, overlay timed cards, trim to DURATION.
    filt = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[base];"
        f"[1:v]format=rgba,scale={W}:{H}[badge];"
        f"[2:v]format=rgba,scale={W}:{H}[hook];"
        f"[3:v]format=rgba,scale={W}:{H}[mid];"
        f"[4:v]format=rgba,scale={W}:{H}[cta];"
        f"[base][badge]overlay=0:0[b1];"
        f"[b1][hook]overlay=0:0:enable='between(t,0,3.2)'[b2];"
        f"[b2][mid]overlay=0:0:enable='between(t,3.2,8.0)'[b3];"
        f"[b3][cta]overlay=0:0:enable='between(t,12.0,{DURATION})'[b4];"
        f"[b4]fade=t=in:st=0:d=0.12,fade=t=out:st={DURATION - 0.35:.2f}:d=0.3[vout];"
        f"[0:a]afade=t=in:st=0:d=0.12,afade=t=out:st={DURATION - 0.45:.2f}:d=0.4[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-stats",
        "-i",
        str(BASE),
        "-loop",
        "1",
        "-t",
        f"{DURATION:.3f}",
        "-i",
        str(OVER / "badge.png"),
        "-loop",
        "1",
        "-t",
        f"{DURATION:.3f}",
        "-i",
        str(OVER / "hook.png"),
        "-loop",
        "1",
        "-t",
        f"{DURATION:.3f}",
        "-i",
        str(OVER / "mid.png"),
        "-loop",
        "1",
        "-t",
        f"{DURATION:.3f}",
        "-i",
        str(OVER / "cta.png"),
        "-filter_complex",
        filt,
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-t",
        f"{DURATION:.3f}",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "320k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        str(out),
    ]
    run(cmd)
    return out


def verify(path: Path) -> dict:
    probe = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_name,width,height,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        text=True,
    )
    data = json.loads(probe)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        check=True,
    )
    vol = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    frame = OUT / "v2-attention-recruit-frame.jpg"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "1.0",
            "-i",
            str(path),
            "-frames:v",
            "1",
            str(frame),
        ],
        check=True,
    )
    streams = data.get("streams") or []
    v = next(s for s in streams if s.get("width"))
    a = next(s for s in streams if s.get("codec_name") in {"aac", "mp3"})
    info = {
        "path": str(path),
        "base": str(BASE),
        "duration": float(data["format"]["duration"]),
        "size": int(data["format"]["size"]),
        "width": v["width"],
        "height": v["height"],
        "vcodec": v["codec_name"],
        "acodec": a["codec_name"],
        "sample_rate": a.get("sample_rate"),
        "channels": a.get("channels"),
        "frame": str(frame),
        "volumedetect_tail": "\n".join(vol.stderr.strip().splitlines()[-8:]),
    }
    if info["width"] != W or info["height"] != H:
        raise SystemExit(f"bad dimensions: {info}")
    if abs(info["duration"] - DURATION) > 0.35:
        raise SystemExit(f"bad duration: {info}")
    (OUT / "v2-attention-recruit.manifest.json").write_text(json.dumps(info, indent=2))
    return info


def main() -> int:
    out = render_short()
    info = verify(out)
    print(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
