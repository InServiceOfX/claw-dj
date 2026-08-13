#!/usr/bin/env python3
"""Transparent 1920x1080 text overlays. Homebrew ffmpeg has no drawtext."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WORK = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09_20h46m18s-video-work")
OUT = WORK / "overlays"
W, H = 1920, 1080
GOLD = (244, 215, 164, 255)
WHITE = (255, 255, 255, 255)
WHITE_SOFT = (255, 255, 255, 200)

TRACKS = [
    "YOU'RE THE ONE  ·  SPECIAL MIX",
    "STAND BY YOUR MAN",
    "YOU'RE THE ONE  ·  PUFF DADDY",
    "NAS  ·  IF I RULED THE WORLD",
    "50 CENT  ·  OUT OF CONTROL",
    "STAKES IS HIGH",
    "'03 BONNIE & CLYDE",
    "HEY LOVER",
    "BONNIE & SHYNE",
    "GIVE IT TO ME",
    "BROOKLYN'S FINEST",
    "GET THAT MONEY MAN",
    "LOVERS AND FRIENDS",
    "CONFESSIONS PT. II REMIX",
]


def font(path: str, size: int, index: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=index)


def shadow_text(draw, xy, text, fnt, fill, shadow=(0, 0, 0, 170)):
    x, y = xy
    for dx, dy in ((2, 2), (1, 3), (3, 1)):
        draw.text((x + dx, y + dy), text, font=fnt, fill=shadow)
    draw.text((x, y), text, font=fnt, fill=fill)


def badge() -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    f_label = font("/System/Library/Fonts/Avenir Next.ttc", 30, 2)
    f_brand = font("/System/Library/Fonts/Avenir Next.ttc", 22, 5)
    shadow_text(draw, (48, 34), "GUIDED  ·  EXPERIMENTAL", f_label, GOLD)
    shadow_text(draw, (48, 72), "claw-dj", f_brand, WHITE_SOFT)
    img.save(OUT / "badge.png")


def hook() -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    f_main = font("/System/Library/Fonts/Avenir Next.ttc", 58, 0)
    f_sub = font("/System/Library/Fonts/Avenir Next.ttc", 30, 5)
    line1 = "THIS CRATE SHOULDN'T WORK"
    line2 = "14 TRANSITIONS  ·  13:36"
    b1 = draw.textbbox((0, 0), line1, font=f_main)
    b2 = draw.textbbox((0, 0), line2, font=f_sub)
    x1 = (W - (b1[2] - b1[0])) // 2
    x2 = (W - (b2[2] - b2[0])) // 2
    y1 = int(H * 0.12)
    shadow_text(draw, (x1, y1), line1, f_main, WHITE)
    shadow_text(draw, (x2, y1 + 68), line2, f_sub, GOLD)
    img.save(OUT / "hook.png")


def tracks() -> None:
    f_track = font("/System/Library/Fonts/HelveticaNeue.ttc", 30, 10)
    for i, title in enumerate(TRACKS, start=1):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Slim gold rule above the title so it reads as a lower-third.
        draw.rectangle((48, H - 128, 220, H - 124), fill=GOLD)
        shadow_text(draw, (48, H - 118), title, f_track, WHITE)
        img.save(OUT / f"track_{i:02d}.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    badge()
    hook()
    tracks()
    print(OUT)


if __name__ == "__main__":
    main()
