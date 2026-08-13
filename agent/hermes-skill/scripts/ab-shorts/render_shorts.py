#!/usr/bin/env python3
"""Render three 9:16 shorts from the 2026-08-09 A/B mixes.

Noe stack: motion from frame 1, text hook, short cuts, designed comment bait.
Imagine video gen is unavailable (ZDR); Ken Burns + hard cuts are the fallback.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

FPS = 30
W, H = 1080, 1920
WORK = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09-ab-shorts")
OVER = WORK / "overlays"
IMG = Path(
    "/Users/ernestyeung/.openclaw/workspace/Data/Public/Images/ClawDJImages/CompareDJTransitionFormat"
)

NONE_AUDIO = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_19h40m43s.wav")
GUIDED_AUDIO = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_20h46m18s.wav")

NONE_STILLS = [
    IMG / "SameMixNoExpertjib-mix-svdq-Steps35Iter2-Guidance9.2cfg2Iter2-7b1974b28fb9.png",
    IMG / "SameMixNoExpertsvdq-int4_r32-flux.1-krea-dev.safetensors-Steps35Iter0-Guidance3.4cfg2Iter0-dd0bbe51baad.png",
    IMG / "SameMixNoExpertsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter1-Guidance6.3cfg2Iter1-72f98b22d1d5.png",
]
GUIDED_STILLS = [
    IMG / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter1-Guidance5.7cfg2Iter1-ff1da72d7049.png",
    IMG / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-krea-dev.safetensors-Steps35Iter1-Guidance5.7cfg2Iter1-b4dbcdd2501c.png",
    IMG / "SameMixGuidedExperimentalsvdq-int4_r32-flux.1-dev.safetensors-Steps35Iter2-Guidance7.6cfg2Iter2-b94c5d24ed29.png",
]


def crop_zoom(duration: float, mode: int) -> str:
    frames = max(1, round(duration * FPS))
    step = 0.0018
    if mode % 2 == 0:
        z = f"min(zoom+{step},1.14)"
    else:
        z = f"if(eq(on,0),1.14,max(1.001,zoom-{step}))"
    return (
        f"scale=2160:1215:flags=lanczos,"
        f"crop=684:1215:738:0,"
        f"zoompan=z='{z}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        f"d={frames}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p"
    )


def xfade_chain(n: int, durations: list[float], xf: float = 0.25) -> tuple[str, str]:
    parts = [f"[v{i}]" for i in range(n)]
    # build after zoompan labels already exist
    lines = []
    current = "v0"
    elapsed = durations[0]
    for i in range(1, n):
        offset = max(0.05, elapsed - xf)
        out = f"x{i}"
        lines.append(
            f"[{current}][v{i}]xfade=transition=fade:duration={xf}:offset={offset:.3f}[{out}]"
        )
        current = out
        elapsed += durations[i] - xf
    return ";".join(lines), current


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd[:8]), "...")
    subprocess.run(cmd, check=True)


def encode(name: str, image_specs: list[tuple[Path, float, int]], audio: Path, audio_ss: float, overlays: list[tuple[str, float, float]]) -> Path:
    """overlays: (filename, start, end)"""
    out = WORK / name
    durations = [d for _, d, _ in image_specs]
    filt = []
    for i, (_, dur, mode) in enumerate(image_specs):
        filt.append(f"[{i}:v]{crop_zoom(dur, mode)}[v{i}]")
    xf_lines, last = xfade_chain(len(image_specs), durations)
    if xf_lines:
        filt.append(xf_lines)
    audio_i = len(image_specs)
    filt.append(f"[{audio_i}:a]atrim=start={audio_ss:.3f},asetpts=PTS-STARTPTS[aout]")
    current = last
    next_i = audio_i + 1
    for fname, start, end in overlays:
        filt.append(
            f"[{next_i}:v]format=rgba,setpts=PTS-STARTPTS[ov{next_i}]"
        )
        nxt = f"o{next_i}"
        filt.append(
            f"[{current}][ov{next_i}]overlay=0:0:enable='between(t,{start:.2f},{end:.2f})'[{nxt}]"
        )
        current = nxt
        next_i += 1
    filt.append(
        f"[{current}]fade=t=in:st=0:d=0.18,fade=t=out:st={sum(durations)-0.35:.2f}:d=0.30[vout]"
    )
    script = WORK / f"{name}.filter.txt"
    script.write_text(";\n".join(filt) + "\n")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-stats"]
    for path, dur, _ in image_specs:
        cmd.extend(["-loop", "1", "-t", f"{dur:.3f}", "-i", str(path)])
    cmd.extend(["-ss", f"{audio_ss:.3f}", "-i", str(audio)])
    for fname, _, _ in overlays:
        cmd.extend(["-loop", "1", "-i", str(OVER / fname)])
    cmd.extend(
        [
            "-/filter_complex",
            str(script),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-t",
            f"{sum(durations):.3f}",
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            "8000k",
            "-pix_fmt",
            "yuv420p",
            "-tag:v",
            "avc1",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            "-shortest",
            str(out),
        ]
    )
    run(cmd)
    return out


def build_ab_audio() -> Path:
    """13s No Expert into Nas, then 14s Guided into the same song."""
    out = WORK / "ab-nas-handoff.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-ss",
            "114.0",
            "-t",
            "13.0",
            "-i",
            str(NONE_AUDIO),
            "-ss",
            "134.0",
            "-t",
            "14.0",
            "-i",
            str(GUIDED_AUDIO),
            "-filter_complex",
            "[0:a][1:a]acrossfade=d=0.08:c1=tri:c2=tri[a]",
            "-map",
            "[a]",
            str(out),
        ]
    )
    return out


def main() -> None:
    missing = [p for p in NONE_STILLS + GUIDED_STILLS + [NONE_AUDIO, GUIDED_AUDIO] if not p.is_file()]
    if missing:
        raise SystemExit("missing:\n" + "\n".join(str(p) for p in missing))

    ab_audio = build_ab_audio()

    # 1) A/B — same Nas handoff, two brains. ~27s
    encode(
        "short-01-which-mix-wins-9x16.mp4",
        [
            (GUIDED_STILLS[0], 0.80, 0),
            (NONE_STILLS[0], 0.80, 1),
            (GUIDED_STILLS[1], 0.80, 2),
            (NONE_STILLS[1], 0.70, 3),
            (NONE_STILLS[0], 10.0, 0),
            (GUIDED_STILLS[0], 10.0, 1),
            (GUIDED_STILLS[1], 4.2, 2),
        ],
        ab_audio,
        0.0,
        [
            ("badge.png", 0.0, 27.3),
            ("hook_ab.png", 0.0, 3.1),
            ("label_none.png", 3.1, 13.0),
            ("label_guided.png", 13.0, 23.0),
            ("cta_ab.png", 23.0, 27.3),
        ],
    )

    # 2) Guided crate — Bonnie & Clyde handoff. ~22s
    encode(
        "short-02-crate-shouldnt-work-9x16.mp4",
        [
            (GUIDED_STILLS[0], 1.10, 0),
            (GUIDED_STILLS[1], 1.00, 1),
            (GUIDED_STILLS[2], 8.40, 2),
            (GUIDED_STILLS[0], 8.00, 3),
            (GUIDED_STILLS[1], 4.00, 0),
        ],
        GUIDED_AUDIO,
        395.0,
        [
            ("badge.png", 0.0, 22.5),
            ("hook_crate.png", 0.0, 3.2),
            ("cta_handoff.png", 18.0, 22.5),
        ],
    )

    # 3) No expert — Nas handoff. ~22s
    encode(
        "short-03-zero-expert-rules-9x16.mp4",
        [
            (NONE_STILLS[0], 1.10, 0),
            (NONE_STILLS[1], 1.00, 1),
            (NONE_STILLS[2], 8.40, 2),
            (NONE_STILLS[0], 8.00, 3),
            (NONE_STILLS[1], 4.00, 0),
        ],
        NONE_AUDIO,
        114.0,
        [
            ("badge.png", 0.0, 22.5),
            ("hook_zero.png", 0.0, 3.2),
            ("cta_slap.png", 18.0, 22.5),
        ],
    )


if __name__ == "__main__":
    main()
