#!/usr/bin/env python3
"""Render the 2026-08-09 NoExpert claw-dj mix as an animated 16:9 video."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

FPS = 30
WIDTH = 1920
HEIGHT = 1080
AUDIO_DURATION = 539.925333
TRANSITION = 1.0

AUDIO = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_19h40m43s.wav")
OUTPUT = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_19h40m43s_NoExpert_FullMix.mp4")
WORK = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_19h40m43s-video-work")
IMAGE_DIR = Path("/Users/ernestyeung/.openclaw/workspace/Data/Public/Images/ClawDJImages/CompareDJTransitionFormat")

# Strong character/action frame first, then alternate environment and character views.
IMAGES = [
    IMAGE_DIR / "SameMixNoExpertsvdq-int4_r32-flux.1-krea-dev.safetensors-Steps35Iter0-Guidance3.4cfg2Iter0-dd0bbe51baad.png",
    IMAGE_DIR / "SameMixNoExpertsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter0-Guidance3.4cfg2Iter0-8b32ad5ae48a.png",
    IMAGE_DIR / "SameMixNoExpertjib-mix-svdq-Steps35Iter2-Guidance9.2cfg2Iter2-7b1974b28fb9.png",
    IMAGE_DIR / "SameMixNoExpertsvdq-int4_r32-flux.1-dev-colossusv12.safetensors-Steps35Iter1-Guidance6.3cfg2Iter1-10d452ce3a48.png",
    IMAGE_DIR / "SameMixNoExpertsvdq-int4_r32-flux.1-dev-colossusv12.safetensors-Steps35Iter2-Guidance9.2cfg2Iter2-e7996cc9723f.png",
    IMAGE_DIR / "SameMixNoExpertsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter1-Guidance6.3cfg2Iter1-72f98b22d1d5.png",
    IMAGE_DIR / "SameMixNoExpertjib-mix-svdq-Steps35Iter0-Guidance3.4cfg2Iter0-bb5431a3582a.png",
]

# Seven quick opening shots provide a visual hook; fourteen long shots breathe with the mix.
TEASER_DURATION = 1.8
LONG_DURATION = (AUDIO_DURATION + 20 * TRANSITION - 7 * TEASER_DURATION) / 14
DURATIONS = [TEASER_DURATION] * 7 + [LONG_DURATION] * 14
SEQUENCE = IMAGES + IMAGES + list(reversed(IMAGES))


def zoompan(index: int, duration: float) -> str:
    frames = round(duration * FPS)
    fast = duration < 3
    step = 0.0011 if fast else 0.000075
    mode = index % 6
    if mode == 0:
        z = f"min(zoom+{step},1.10)"
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    elif mode == 1:
        z = f"if(eq(on,0),1.10,max(1.001,zoom-{step}))"
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    elif mode == 2:
        z = f"min(zoom+{step},1.09)"
        x, y = f"(iw-iw/zoom)*on/{frames}", "(ih-ih/zoom)*0.35"
    elif mode == 3:
        z = f"min(zoom+{step},1.09)"
        x, y = f"(iw-iw/zoom)*(1-on/{frames})", "(ih-ih/zoom)*0.60"
    elif mode == 4:
        z = f"min(zoom+{step},1.08)"
        x, y = "(iw-iw/zoom)*0.30", f"(ih-ih/zoom)*on/{frames}"
    else:
        z = f"min(zoom+{step},1.08)"
        x, y = "(iw-iw/zoom)*0.70", f"(ih-ih/zoom)*(1-on/{frames})"
    return (
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:"
        f"s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1,format=yuv420p"
    )


def build_filter() -> str:
    parts: list[str] = []
    for i, duration in enumerate(DURATIONS):
        parts.append(f"[{i}:v]{zoompan(i, duration)}[v{i}]")

    current = "v0"
    elapsed = DURATIONS[0]
    for i in range(1, len(DURATIONS)):
        offset = elapsed - TRANSITION
        out = f"x{i}"
        parts.append(
            f"[{current}][v{i}]xfade=transition=fade:duration={TRANSITION}:"
            f"offset={offset:.6f}[{out}]"
        )
        current = out
        elapsed += DURATIONS[i] - TRANSITION

    # A restrained, audio-derived line adds continuous motion without importing other art.
    audio_index = len(DURATIONS)
    parts.append(f"[{audio_index}:a]asplit=2[aout][awave]")
    parts.append(
        f"[awave]showwaves=s=1600x110:mode=cline:rate={FPS}:"
        "colors=0xFFB15A@0.58,format=rgba,colorkey=0x000000:0.12:0.08[wave]"
    )
    parts.append(
        f"[{current}][wave]overlay=x=(W-w)/2:y=H-h-46:shortest=1,"
        "fade=t=in:st=0:d=1.6,fade=t=out:st=537.9:d=2.0[vout]"
    )
    return ";\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="render the first 15 seconds")
    args = parser.parse_args()

    missing = [str(path) for path in [AUDIO, *IMAGES] if not path.is_file()]
    if missing:
        raise SystemExit("Missing inputs:\n" + "\n".join(missing))

    WORK.mkdir(parents=True, exist_ok=True)
    filter_path = WORK / "filter_complex.txt"
    filter_path.write_text(build_filter())
    output = WORK / "preview-15s.mp4" if args.preview else OUTPUT

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]
    for image, duration in zip(SEQUENCE, DURATIONS):
        command.extend(["-loop", "1", "-t", f"{duration:.6f}", "-i", str(image)])
    command.extend(["-i", str(AUDIO), "-filter_complex_script", str(filter_path)])
    command.extend(["-map", "[vout]", "-map", "[aout]"])
    if args.preview:
        command.extend(["-t", "15"])
    command.extend(
        [
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            "12000k",
            "-maxrate",
            "16000k",
            "-bufsize",
            "24000k",
            "-tag:v",
            "avc1",
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
    subprocess.run(command, check=True)
    print(output)


if __name__ == "__main__":
    main()
