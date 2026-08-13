#!/usr/bin/env python3
"""Render the 2026-08-09 Guided Experimental claw-dj mix as a 16:9 video.

Falls back to Ken Burns / hard-cut stills because Imagine video generation
is unavailable (ZDR requires an upload URL). Visual plan follows Noe Murillo
pt1/pt2 as adapted for a full-length mix:

- Motion from frame 1 (never a frozen still)
- Fast opening cuts as the visual hook
- Artwork changes with the mix, not one static cover
- Character / over-shoulder / empty-room contrast
- Restrained gold waveform so the audio is visible
- On-screen text hook + format badge + track lower-thirds
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

FPS = 30
WIDTH = 1920
HEIGHT = 1080
AUDIO_DURATION = 816.533333
TRANSITION = 0.80
TEASER_DURATION = 1.70

AUDIO = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_20h46m18s.wav")
OUTPUT = Path(
    "/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_20h46m18s_GuidedExperimental_FullMix.mp4"
)
WORK = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_20h46m18s-video-work")
IMAGE_DIR = Path(
    "/Users/ernestyeung/.openclaw/workspace/Data/Public/Images/ClawDJImages/CompareDJTransitionFormat"
)
OVERLAY_DIR = WORK / "overlays"

# Named stills — only GuidedExperimental files requested by the human.
STILLS = {
    "pink_front": IMAGE_DIR
    / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter1-Guidance5.7cfg2Iter1-ff1da72d7049.png",
    "man_splash": IMAGE_DIR
    / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-krea-dev.safetensors-Steps35Iter1-Guidance5.7cfg2Iter1-b4dbcdd2501c.png",
    "sunset_city": IMAGE_DIR
    / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter2-Guidance7.6cfg2Iter2-b94c5d24ed29.png",
    "empty_deck": IMAGE_DIR
    / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev-colossusv12.safetensors-Steps35Iter1-Guidance5.7cfg2Iter1-f409182b883d.png",
    "os_grid": IMAGE_DIR
    / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter1-Guidance5.7cfg2Iter1-e7c4e671c18a.png",
    "vinyl_wave": IMAGE_DIR
    / "SameMixGuidedExperimentaljib-mix-svdq-Steps35Iter2-Guidance7.6cfg2Iter2-2af44d5a2940.png",
    "hoodie_os": IMAGE_DIR
    / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter0-Guidance3.8cfg2Iter0-69faa6ac28c4.png",
    "map_os": IMAGE_DIR
    / "SameMixGuidedExperimentaljib-mix-svdq-Steps35Iter0-Guidance3.8cfg2Iter0-dd19af28d5fe.png",
    "yellow_desk": IMAGE_DIR
    / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter2-Guidance7.6cfg2Iter2-be95ef399060.png",
}

# Seven quick opening shots: face / action / window / empty / deck / screen / face.
HOOK_KEYS = [
    "pink_front",
    "man_splash",
    "sunset_city",
    "empty_deck",
    "os_grid",
    "vinyl_wave",
    "hoodie_os",
]

# Fourteen long shots — one visual world per cue, alternating character and room.
LONG_KEYS = [
    "pink_front",
    "os_grid",
    "man_splash",
    "sunset_city",
    "vinyl_wave",
    "empty_deck",
    "hoodie_os",
    "map_os",
    "yellow_desk",
    "pink_front",
    "empty_deck",
    "man_splash",
    "sunset_city",
    "pink_front",
]

# Mixxx CUE INDEX is MM:SS:FF at 75 frames/sec.
CUE_TIMES = [
    0.000,
    56.120,
    102.200,
    139.947,
    274.987,
    339.387,
    402.720,
    448.800,
    495.413,
    568.187,
    703.227,
    740.947,
    768.160,
    795.387,
]
TRACK_HOLD = 5.5


def zoompan(index: int, duration: float) -> str:
    frames = max(1, round(duration * FPS))
    fast = duration < 3
    # Faster zoom on the hook so the first 3s are obviously moving.
    step = 0.0016 if fast else 0.000055
    mode = index % 6
    if mode == 0:
        z = f"min(zoom+{step},1.12)"
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    elif mode == 1:
        z = f"if(eq(on,0),1.12,max(1.001,zoom-{step}))"
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)*0.42"
    elif mode == 2:
        z = f"min(zoom+{step},1.10)"
        x, y = f"(iw-iw/zoom)*on/{frames}", "(ih-ih/zoom)*0.30"
    elif mode == 3:
        z = f"min(zoom+{step},1.10)"
        x, y = f"(iw-iw/zoom)*(1-on/{frames})", "(ih-ih/zoom)*0.55"
    elif mode == 4:
        z = f"min(zoom+{step},1.09)"
        x, y = "(iw-iw/zoom)*0.28", f"(ih-ih/zoom)*on/{frames}"
    else:
        z = f"min(zoom+{step},1.09)"
        x, y = "(iw-iw/zoom)*0.72", f"(ih-ih/zoom)*(1-on/{frames})"
    return (
        f"scale=3840:2160:flags=lanczos,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:"
        f"s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1,format=yuv420p"
    )


def overlay_chain(n_clips: int) -> str:
    """Badge, hook card, track lower-thirds, progress bar.

    Homebrew ffmpeg has no libfreetype, so text is pre-rendered PNG overlays.
    Input order after the stills: audio, badge, hook, track_01..track_14.
    """
    audio_i = n_clips
    badge_i = n_clips + 1
    hook_i = n_clips + 2
    first_track_i = n_clips + 3

    parts: list[str] = []
    parts.append(
        f"[{badge_i}:v]format=rgba,setpts=PTS-STARTPTS[badge]"
    )
    parts.append(
        f"[{hook_i}:v]format=rgba,setpts=PTS-STARTPTS[hook]"
    )
    for i in range(14):
        parts.append(
            f"[{first_track_i + i}:v]format=rgba,setpts=PTS-STARTPTS[trk{i}]"
        )

    current = "base"
    nxt = "o0"
    parts.append(f"[{current}][badge]overlay=0:0:shortest=1[{nxt}]")
    current = nxt
    nxt = "o1"
    parts.append(
        f"[{current}][hook]overlay=0:0:enable='between(t,0,4.2)'[{nxt}]"
    )
    current = nxt
    for i, start in enumerate(CUE_TIMES):
        nxt = f"o{i + 2}"
        end = start + TRACK_HOLD
        parts.append(
            f"[{current}][trk{i}]overlay=0:0:"
            f"enable='between(t,{start:.3f},{end:.3f})'[{nxt}]"
        )
        current = nxt

    parts.append(
        f"[{current}]drawbox=x=0:y=h-7:w='iw*t/{AUDIO_DURATION:.6f}':h=7:"
        "color=0xE8A85A@0.88:t=fill[vout]"
    )
    return ";\n".join(parts)


def build_plan() -> tuple[list[Path], list[float]]:
    n_xfade = len(HOOK_KEYS) + len(LONG_KEYS) - 1
    teaser_sum = TEASER_DURATION * len(HOOK_KEYS)
    long_sum = AUDIO_DURATION + n_xfade * TRANSITION - teaser_sum
    long_each = long_sum / len(LONG_KEYS)
    keys = HOOK_KEYS + LONG_KEYS
    durations = [TEASER_DURATION] * len(HOOK_KEYS) + [long_each] * len(LONG_KEYS)
    paths = [STILLS[key] for key in keys]
    return paths, durations


def build_filter(durations: list[float]) -> str:
    parts: list[str] = []
    for i, duration in enumerate(durations):
        parts.append(f"[{i}:v]{zoompan(i, duration)}[v{i}]")

    current = "v0"
    elapsed = durations[0]
    for i in range(1, len(durations)):
        offset = elapsed - TRANSITION
        out = f"x{i}"
        parts.append(
            f"[{current}][v{i}]xfade=transition=fade:duration={TRANSITION}:"
            f"offset={offset:.6f}[{out}]"
        )
        current = out
        elapsed += durations[i] - TRANSITION

    audio_index = len(durations)
    parts.append(f"[{audio_index}:a]asplit=2[aout][awave]")
    parts.append(
        f"[awave]showwaves=s=1680x96:mode=cline:rate={FPS}:"
        "colors=0xF4D7A4@0.55,format=rgba,colorkey=0x000000:0.12:0.08[wave]"
    )
    fade_out_start = max(0.0, AUDIO_DURATION - 2.2)
    parts.append(
        f"[{current}][wave]overlay=x=(W-w)/2:y=H-h-28:shortest=1,"
        f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out_start:.3f}:d=2.0[base]"
    )
    parts.append(overlay_chain(len(durations)))
    return ";\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="render the first 15 seconds")
    parser.add_argument("--preview-seconds", type=float, default=15.0)
    args = parser.parse_args()

    paths, durations = build_plan()
    overlay_paths = (
        [OVERLAY_DIR / "badge.png", OVERLAY_DIR / "hook.png"]
        + [OVERLAY_DIR / f"track_{i:02d}.png" for i in range(1, 15)]
    )
    missing = [
        str(p)
        for p in [AUDIO, *STILLS.values(), *overlay_paths]
        if not p.is_file()
    ]
    if missing:
        raise SystemExit("Missing inputs:\n" + "\n".join(missing))

    WORK.mkdir(parents=True, exist_ok=True)
    filter_path = WORK / "filter_complex.txt"
    filter_path.write_text(build_filter(durations) + "\n")
    output = WORK / "preview-15s.mp4" if args.preview else OUTPUT

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-stats"]
    for image, duration in zip(paths, durations):
        command.extend(["-loop", "1", "-t", f"{duration:.6f}", "-i", str(image)])
    command.extend(["-i", str(AUDIO)])
    for overlay in overlay_paths:
        command.extend(["-loop", "1", "-i", str(overlay)])
    command.extend(["-/filter_complex", str(filter_path)])
    command.extend(["-map", "[vout]", "-map", "[aout]"])
    if args.preview:
        command.extend(["-t", f"{args.preview_seconds:.3f}"])
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
    print("clips", len(paths), "teasers", len(HOOK_KEYS), "long", durations[-1])
    subprocess.run(command, check=True)
    print(output)


if __name__ == "__main__":
    main()
