#!/usr/bin/env python3
"""9:16 text overlays for the A/B shorts. Homebrew ffmpeg has no drawtext."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("/Users/ernestyeung/Music/Mixxx/Recordings/2026-08-09-ab-shorts/overlays")
W, H = 1080, 1920
GOLD = (244, 215, 164, 255)
WHITE = (255, 255, 255, 255)
WHITE_SOFT = (255, 255, 255, 210)


def font(size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc", size, index=index)


def shadow_text(draw, xy, text, fnt, fill, shadow=(0, 0, 0, 180)):
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


def badge() -> None:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    shadow_text(draw, (48, 56), "claw-dj", font(28, 5), WHITE_SOFT)
    img.save(OUT / "badge.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    badge()
    card(
        ("SAME CRATE.", 78, 220, WHITE),
        ("TWO BRAINS.", 78, 310, GOLD),
    ).save(OUT / "hook_ab.png")
    card(
        ("1  ·  NO EXPERT", 52, 220, GOLD),
    ).save(OUT / "label_none.png")
    card(
        ("2  ·  GUIDED", 52, 220, GOLD),
    ).save(OUT / "label_guided.png")
    card(
        ("WHICH MIX WINS?", 64, 220, WHITE),
        ("COMMENT  1  OR  2", 40, 310, GOLD),
    ).save(OUT / "cta_ab.png")
    card(
        ("THIS CRATE", 78, 220, WHITE),
        ("SHOULDN'T WORK", 72, 310, GOLD),
    ).save(OUT / "hook_crate.png")
    card(
        ("ZERO EXPERT RULES", 64, 220, WHITE),
        ("STILL MIXING", 52, 310, GOLD),
    ).save(OUT / "hook_zero.png")
    card(
        ("WHICH HANDOFF?", 60, 220, WHITE),
        ("FULL MIX ON YT", 36, 300, GOLD),
    ).save(OUT / "cta_handoff.png")
    card(
        ("DOES IT STILL SLAP?", 56, 220, WHITE),
        ("COMMENT  YES  OR  LATE", 36, 300, GOLD),
    ).save(OUT / "cta_slap.png")
    print(OUT)


if __name__ == "__main__":
    main()
