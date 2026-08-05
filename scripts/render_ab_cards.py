#!/usr/bin/env python3
"""Render A/B comparison cards for a transition-format experiment.

Produces 16:9 cards at 1344x768, the size `render_transition_teaser.py`
expects for --before-image / --after-image. That renderer builds the
1080x1920 vertical card itself, so nothing here generates 9:16 directly.

Deterministic: same spec in, byte-identical PNG out. No model, no network.

Usage:
    python3 scripts/render_ab_cards.py                 # render all cards
    python3 scripts/render_ab_cards.py --outdir DIR
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1344, 768
PAD = 76

BG = (11, 11, 13)
FG = (242, 240, 236)
DIM = (128, 128, 136)
RULE = (44, 44, 50)

ACCENT_BASELINE = (122, 136, 153)   # cool grey-blue
ACCENT_GUIDED = (232, 163, 61)      # warm amber
ACCENT_NEUTRAL = (206, 202, 194)

DISPLAY = "/System/Library/Fonts/Avenir Next Condensed.ttc"
MONO = "/System/Library/Fonts/SFNSMono.ttf"
HEAVY, MEDIUM, REGULAR = 8, 5, 7

PENDING = "— pending dry-run —"


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size, index=index)


def tracked(draw: ImageDraw.ImageDraw, xy, text, fnt, fill, spacing: float = 0.0):
    """Draw text with manual letterspacing; PIL has no native tracking."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + spacing
    return x


def rule(draw: ImageDraw.ImageDraw, y: int, x0: int, x1: int, color, weight: int = 2):
    draw.rectangle([x0, y, x1, y + weight - 1], fill=color)


def render_card(spec: dict, out: Path) -> Path:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    accent = spec["accent"]

    f_kicker = font(DISPLAY, 21, MEDIUM)
    f_variant = font(DISPLAY, 116, HEAVY)
    f_title = font(DISPLAY, 68, HEAVY)
    f_sub = font(DISPLAY, 29, REGULAR)
    f_label = font(MONO, 17)
    f_value = font(MONO, 22)
    f_foot = font(DISPLAY, 21, REGULAR)

    # left accent spine
    d.rectangle([0, 0, 7, H], fill=accent)

    # kicker
    tracked(d, (PAD, PAD - 12), spec["kicker"].upper(), f_kicker, DIM, spacing=3.2)

    y = PAD + 34

    # variant letter + title
    if spec.get("variant"):
        d.text((PAD - 6, y), spec["variant"], font=f_variant, fill=accent)
        title_x = PAD + d.textlength(spec["variant"], font=f_variant) + 34
    else:
        title_x = PAD

    ty = y + 26
    for line in spec["title"]:
        d.text((title_x, ty), line, font=f_title, fill=FG)
        ty += 66

    sy = max(ty + 22, y + 132)
    d.text((title_x, sy), spec["subtitle"], font=f_sub, fill=DIM)

    # rule
    ry = 396
    rule(d, ry, PAD, W - PAD, RULE)

    # stat rows
    sy = ry + 40
    for label, value in spec["stats"]:
        tracked(d, (PAD, sy + 4), label.upper(), f_label, DIM, spacing=1.8)
        is_pending = value == PENDING
        d.text((PAD + 300, sy), value, font=f_value,
               fill=(DIM if is_pending else FG))
        sy += 42

    # footer
    if spec.get("footer"):
        rule(d, H - PAD - 44, PAD, W - PAD, RULE, weight=1)
        d.text((PAD, H - PAD - 30), spec["footer"], font=f_foot, fill=accent)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


PLAN_KICKER = "claw-dj · transition format a/b · mix-to-listen"

CARDS = {
    "ab-title": {
        "kicker": "claw-dj · listening test",
        "variant": None,
        "title": ["SAME 18 TRACKS.", "TWO TRANSITION ENGINES."],
        "subtitle": "Hip-hop / R&B · mix-to-listen · deterministic local ordering",
        "accent": ACCENT_NEUTRAL,
        "stats": [
            ("plan", "18 tracks · 17 transitions"),
            ("profile", "mix-to-listen"),
            ("order engine", "none — deterministic local mix-quality ordering"),
            ("what changes", "the transition format only"),
        ],
        "footer": "Everything else is held constant. One variable.",
    },
    "ab-a-none": {
        "kicker": PLAN_KICKER,
        "variant": "A",
        "title": ["NO TRANSITION", "FORMAT"],
        "subtitle": "Baseline — the setting ear tests have preferred so far",
        "accent": ACCENT_BASELINE,
        "stats": [
            ("dj format", "none"),
            ("techniques", PENDING),
            ("cues", PENDING),
            ("events", PENDING),
        ],
        "footer": "Baseline run — paste its dry-run summary to fill these in.",
    },
    "ab-b-guided": {
        "kicker": PLAN_KICKER,
        "variant": "B",
        "title": ["GUIDED", "TRANSITION FORMAT"],
        "subtitle": "Experimental — 8-bar recipes, phrase-aligned fallbacks",
        "accent": ACCENT_GUIDED,
        "stats": [
            ("dj format", "Hip-hop / R&B · guided"),
            ("techniques", "smooth ×11 · standard ×4 · key-clash ×1 · tempo-gap ×1"),
            ("cues", "phrase-intro downbeat ×16 · human ×1 · body ×1"),
            ("events", "56 events · 17 transitions · guided fallback ×17"),
        ],
        "footer": "Experimental — not yet reliable. Every entry still lands on beat 1.",
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="brain/data/media/ab-cards")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    for name, spec in CARDS.items():
        path = render_card(spec, outdir / f"{name}-16x9.png")
        print(f"  wrote {path}")


if __name__ == "__main__":
    main()
