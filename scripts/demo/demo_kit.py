#!/usr/bin/env python3
"""claw-dj public demo short: stills, a voice-over, and a finished 16:9 + 9:16 cut.

Run from the claw-dj repo root (media goes to OUT, never into Git):

  uv run python scripts/demo/demo_music.py            # original, royalty-free demo music + its 2-track plan
  uv run python scripts/demo/demo_kit.py stills       # GUI screenshots (headless Chrome; --gui URL)
  uv run python scripts/demo/demo_kit.py vo-draft     # placeholder voice (macOS `say`)
  uv run python scripts/demo/demo_kit.py import-vo ~/Downloads/<Voice Memo>.m4a   # one iPhone take, split by pauses
  uv run python scripts/demo/demo_kit.py record-vo    # or: read each line at the Mac (teleprompter)
  uv run python scripts/demo/demo_kit.py assemble                 # draft: placeholder voice
  uv run python scripts/demo/demo_kit.py assemble --vo ernest --obs ~/Movies/<recording>.mkv

The script, timing and on-screen text live in scripts/demo/storyboard.json.
All music is original (scripts/demo/demo_music.py), so the cut is safe to post
publicly. The bed is an offline render of the demo plan's blend from the plan's
own numbers. With --obs, the picture of the "deck" shots and the audio from the
audition's start onward come from Ernest's OBS recording of Mixxx performing
that same demo plan (synced by cross-correlation), so what plays under
"it performs, live" is the real live performance.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SB_PATH = Path(__file__).with_name("storyboard.json")
OUT = Path.home() / ".openclaw/workspace/Data/Public/Videos/claw-dj-demo-short"
GUI = "http://127.0.0.1:8787/"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SR = 48000

INK = (9, 10, 14)
PANEL = (20, 22, 30)
MINT = (92, 224, 168)
CYAN = (80, 200, 255)
MAGENTA = (255, 84, 160)
WHITE = (245, 247, 250)
GREY = (150, 156, 170)
F_AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
F_COND = "/System/Library/Fonts/Avenir Next Condensed.ttc"
F_MONO = "/System/Library/Fonts/Menlo.ttc"
_fonts: dict = {}


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    key = (path, size, index)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size, index=index)
    return _fonts[key]


def heavy(size):
    return font(F_COND, size, 8)


def bold(size):
    return font(F_AVENIR, size, 0)


def demi(size):
    return font(F_AVENIR, size, 2)


def regular(size):
    return font(F_AVENIR, size, 7)


def mono(size, b=False):
    return font(F_MONO, size, 1 if b else 0)


def ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def load_storyboard() -> dict:
    return json.loads(SB_PATH.read_text())


# --------------------------------------------------------------------- stills
STILLS = {"curate": ("curate", 1400), "mix": ("mix", 3000), "arrange": ("arrange", 3000)}


def cmd_stills(args) -> None:
    """Screenshot the GUI's three pages for whichever plan is active there.

    The public cut uses a clean, freshly built plan (no "stale" badges): run a
    private copy of the editor on another port with a scratch copy of
    brain/data, build a plan there, and pass --gui http://127.0.0.1:8788/.
    """
    (OUT / "stills").mkdir(parents=True, exist_ok=True)
    gui = args.gui.rstrip("/") + "/"
    for name, (view, height) in STILLS.items():
        path = OUT / "stills" / f"{name}.png"
        run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size=1920,{height}",
             "--force-device-scale-factor=1", "--virtual-time-budget=9000", f"--screenshot={path}", f"{gui}#{view}"],
            stderr=subprocess.DEVNULL)
        print("still:", path)


# ------------------------------------------------------------------ the blend
def blend_numbers(sb: dict) -> dict:
    """The blend under the "perform" shot, read from its mix plan (not retyped)."""
    want = sb["blend"]
    plan_path = Path(want["plan"]).expanduser()
    plan = json.loads(plan_path.read_text())
    ev = plan["events"]
    for i, e in enumerate(ev):
        if e["op"] == "transition" and sum(1 for x in ev[:i + 1] if x["op"] == "transition") == want["transition"]:
            out_body = [x for x in ev[:i] if x["op"] == "play_body"][-1]
            in_body = next(x for x in ev[i + 1:] if x["op"] == "play_body")
            cue = [x for x in ev[:i] if x["op"] in ("load", "preload_after_transition") and x["track_id"] == in_body["track_id"]][-1]
            pa, ipa = out_body["phase_anchor"], in_body["phase_anchor"]
            out_bpm, in_bpm = pa["grid_bpm"], ipa["grid_bpm"]
            return {
                "number": sum(1 for x in ev[:i + 1] if x["op"] == "transition"),
                "out_path": out_body["track_id"], "in_path": in_body["track_id"],
                "out_label": e["from_track"], "in_label": e["to_track"],
                "out_bpm": out_bpm, "in_bpm": in_bpm,
                "fade_at": pa["first_beat_seconds"] + pa["planned_anchor_beat_index"] * 60 / out_bpm,
                "beats": int(e["transition_beats"]),
                "blend_s": int(e["transition_beats"]) * 60 / out_bpm,
                "in_cue": float(cue["cue_seconds"]),
                "nudge_s": float(e.get("incoming_nudge_ms") or 0) / 1000,
                "beat_s": 60 / out_bpm,
            }
    sys.exit(f"transition {want['transition']} not found in {plan_path} — run scripts/demo/demo_music.py first?")


def decode(path: str, start: float, dur: float, tempo: float = 1.0) -> np.ndarray:
    af = [f"atempo={tempo:.6f}"] if abs(tempo - 1) > 1e-4 else []
    # -ss after -i: sample-accurate (input seeking into an mp3 can land a frame off)
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-ss", f"{max(0.0, start):.4f}", "-t", f"{dur * tempo + 1:.3f}",
           "-ac", "2", "-ar", str(SR)] + (["-af", ",".join(af)] if af else []) + ["-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    y = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
    n = int(dur * SR)
    if len(y) < n:
        y = np.vstack([y, np.zeros((n - len(y), 2), np.float32)])
    return y[:n]


def render_bed(b: dict, blend_start: float, total: float) -> dict:
    """Two decks as Mixxx played them: synced, nudged, additive crossfade with a gradual bass swap."""
    t = np.arange(int(total * SR)) / SR
    a = decode(b["out_path"], b["fade_at"] - blend_start, total)
    tempo = b["out_bpm"] / b["in_bpm"]  # sync: incoming runs at the outgoing tempo, keylock on
    in_len = max(0.0, total - blend_start)
    raw_b = decode(b["in_path"], b["in_cue"] + b["nudge_s"], in_len, tempo)
    bb = np.zeros_like(a)
    k0 = int(blend_start * SR)
    bb[k0:k0 + len(raw_b)] = raw_b[: len(bb) - k0]
    p = np.clip((t - blend_start) / b["blend_s"], 0, 1)
    ga = np.clip(2 * (1 - p), 0, 1)  # additive crossfader: both full at centre
    gb = np.clip(2 * p, 0, 1)
    # gradual bass handover on the outgoing deck between 35% and 65% (hands/run_mix_plan.py)
    low_keep = 1 - np.array([ease(x) for x in np.clip((p - 0.35) / 0.3, 0, 1)])
    from scipy.signal import butter, sosfiltfilt
    sos = butter(2, 180, "lowpass", fs=SR, output="sos")
    a_low = sosfiltfilt(sos, a, axis=0).astype(np.float32)
    a_shaped = (a - a_low) + a_low * low_keep[:, None]
    deck_a = a_shaped * ga[:, None]
    deck_b = bb * gb[:, None]
    return {"a": deck_a, "b": deck_b, "mix": deck_a + deck_b, "ga": ga, "gb": gb, "p": p, "low_keep": low_keep}


def write_wav(path: Path, y: np.ndarray) -> None:
    run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(path)],
        input=np.ascontiguousarray(y, dtype=np.float32).tobytes())


# ----------------------------------------------------------------- voice-over
def vo_dir(kind: str) -> Path:
    return OUT / ("vo_ernest" if kind == "ernest" else "vo_draft")


def pick_voice() -> str:
    names = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    for v in ("Evan (Enhanced)", "Nathan (Enhanced)", "Tom (Enhanced)", "Alex", "Daniel", "Samantha"):
        if v.split(" (")[0] in names and (v in names or "(" not in v):
            return v
    return "Samantha"


def cmd_vo_draft(_args) -> None:
    sb = load_storyboard()
    d = vo_dir("draft")
    d.mkdir(parents=True, exist_ok=True)
    voice = pick_voice()
    for i, s in enumerate(sb["segments"], 1):
        if not s.get("vo"):
            continue
        aiff = d / f"{i:02d}_{s['id']}.aiff"
        run(["say", "-v", voice, "-r", "178", "-o", str(aiff), s["vo"].replace("claw-dj", "claw D J")])
        run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", str(SR), "-ac", "1", str(aiff.with_suffix(".wav"))])
        aiff.unlink()
    print(f"placeholder voice ({voice}) -> {d}")


def mic_device() -> str:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                         capture_output=True, text=True).stderr
    audio = out.split("audio devices:")[-1]
    devs = re.findall(r"\[(\d+)\] (.+)", audio)
    for idx, name in devs:
        if "microphone" in name.lower() or "mic" in name.lower():
            return idx
    return devs[0][0] if devs else "0"


def cmd_record_vo(args) -> None:
    sb = load_storyboard()
    d = vo_dir("ernest")
    d.mkdir(parents=True, exist_ok=True)
    dev = args.device or mic_device()
    lines = [(i, s) for i, s in enumerate(sb["segments"], 1) if s.get("vo")]
    if args.line:
        lines = [x for x in lines if x[0] == args.line]
    print(f"\nRecording from audio device {dev}. Speak naturally, a little slower than feels normal.")
    print("For each line: press Enter to START, read it, press Enter to STOP. Type r + Enter to redo.\n")
    for i, s in lines:
        while True:
            print("\033[1;32m" + f"[{i}/{len(sb['segments'])}] " + "\033[0m" + "\033[1m" + s["vo"] + "\033[0m")
            input("   Enter to start > ")
            wav = d / f"{i:02d}_{s['id']}.wav"
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "avfoundation", "-i", f":{dev}", "-ac", "1", "-ar", str(SR), str(wav)],
                                 stdin=subprocess.PIPE)
            time.sleep(0.15)
            input("   ● recording … Enter to stop > ")
            p.communicate(b"q")
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)],
                                       capture_output=True, text=True).stdout or 0)
            again = input(f"   saved {dur:.1f}s. Enter = keep, r = redo, p = play back > ").strip().lower()
            if again == "p":
                subprocess.run(["afplay", str(wav)])
                again = input("   Enter = keep, r = redo > ").strip().lower()
            if again != "r":
                break
    print(f"\nVoice saved in {d}. Next: uv run python scripts/demo/demo_kit.py assemble --vo ernest")


def cmd_import_vo(args) -> None:
    """Split one continuous take (e.g. an iPhone Voice Memo) into the storyboard's lines.

    Read every line in order with a clear pause (about two seconds) between
    lines. The longest pauses become the cuts, so a short breath inside a line
    is never mistaken for the end of it.
    """
    sb = load_storyboard()
    lines = [(i, s) for i, s in enumerate(sb["segments"], 1) if s.get("vo")]
    d = vo_dir("ernest")
    d.mkdir(parents=True, exist_ok=True)
    takes = [Path(t).expanduser() for t in args.take]
    if len(takes) > 1:  # one memo per line, in order
        if len(takes) != len(lines):
            sys.exit(f"[import-vo] got {len(takes)} files for {len(lines)} lines; pass one take, or exactly one file per line")
        for (i, s), t in zip(lines, takes):
            wav = d / f"{i:02d}_{s['id']}.wav"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(t), "-ac", "1", "-ar", str(SR), str(wav)])
            print(f"  [{i}] {t.name}  {s['vo']}")
        print(f"\nVoice saved in {d}. Next: uv run python scripts/demo/demo_kit.py assemble --vo ernest")
        return
    src = takes[0]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    hop = SR // 100  # 10 ms frames
    n = len(y) // hop
    db = 20 * np.log10(np.sqrt((y[: n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-9)
    floor = np.percentile(db, 10)
    speech = db > max(floor + 12, np.percentile(db, 60) - 25)
    # runs of silence
    gaps, k = [], 0
    while k < n:
        if not speech[k]:
            j = k
            while j < n and not speech[j]:
                j += 1
            if k > 0 and j < n:
                gaps.append((j - k, k, j))
            k = j
        else:
            k += 1
    need = len(lines) - 1
    cuts = sorted(sorted(gaps, reverse=True)[:need], key=lambda g: g[1])
    if len(cuts) < need or (cuts and cuts[0][0] < 35):
        print(f"[import-vo] WARNING: found {len(gaps)} pauses, needed {need} clear ones (≥0.35 s).")
        print("  Re-record with about two seconds of silence between lines, or use record-vo.")
        if len(cuts) < need:
            sys.exit(1)
    bounds = [0] + [(a + b) // 2 for _, a, b in cuts] + [n]
    for (i, s), a, b in zip(lines, bounds[:-1], bounds[1:]):
        wav = d / f"{i:02d}_{s['id']}.wav"
        write_mono(wav, y[a * hop: b * hop])
        print(f"  [{i}] {(b - a) / 100:5.1f}s  {s['vo']}")
    print(f"\nVoice saved in {d}. Listen to any line with: afplay '{d}/01_{lines[0][1]['id']}.wav'")
    print("Next: uv run python scripts/demo/demo_kit.py assemble --vo ernest")


def write_mono(path: Path, y: np.ndarray) -> None:
    run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", str(path)],
        input=np.ascontiguousarray(y, dtype=np.float32).tobytes())


def load_vo(kind: str, sb: dict) -> dict[int, np.ndarray]:
    d = vo_dir(kind)
    out = {}
    for i, s in enumerate(sb["segments"], 1):
        f = d / f"{i:02d}_{s['id']}.wav"
        if s.get("vo") and f.exists():
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-af",
                                  "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
                                  "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,"
                                  "highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=8:release=120,loudnorm=I=-16:TP=-1.5",
                                  "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], check=True, capture_output=True).stdout
            out[i] = np.frombuffer(raw, dtype=np.float32).copy()
    return out


# ------------------------------------------------------------------- timeline
def layout(sb: dict, vo: dict, beat_s: float) -> list[dict]:
    """Segment start/end on the beat; segments grow to fit their voice line."""
    segs, t = [], 0.0
    for i, s in enumerate(sb["segments"], 1):
        dur = s["dur"]
        if i in vo:
            dur = max(dur, s.get("vo_at", 0.3) + len(vo[i]) / SR + 0.45)
        end = round((t + dur) / beat_s) * beat_s
        if end <= t:
            end = t + beat_s
        segs.append({**s, "n": i, "start": t, "end": end})
        t = end
    return segs


def wrap(draw, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=f) <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------- deck visual
def waveform_strip(y: np.ndarray, gain: np.ndarray, px_per_s: int, h: int, colors) -> Image.Image:
    """A Mixxx-like RGB waveform: low/mid/high energy per pixel column."""
    from scipy.signal import butter, sosfilt
    mono_y = y.mean(axis=1)
    bands = []
    for lo, hi in ((None, 220), (220, 2500), (2500, None)):
        if lo is None:
            sos = butter(2, hi, "lowpass", fs=SR, output="sos")
        elif hi is None:
            sos = butter(2, lo, "highpass", fs=SR, output="sos")
        else:
            sos = butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
        bands.append(np.abs(sosfilt(sos, mono_y)))
    hop = SR // px_per_s
    n = len(mono_y) // hop
    env = np.stack([b[: n * hop].reshape(n, hop).max(axis=1) for b in bands])
    g = gain[: n * hop].reshape(n, hop).mean(axis=1) if len(gain) >= n * hop else np.ones(n)
    env = env / (np.percentile(env.sum(axis=0), 99) + 1e-9)
    img = np.zeros((h, n, 3), np.float32)
    mid = h // 2
    total = np.clip(env.sum(axis=0), 0, 1.2)
    for k in range(n):
        amp = total[k] * (h * 0.46)
        if amp < 1:
            continue
        w = env[:, k] / (env[:, k].sum() + 1e-9)
        col = sum(np.array(c, np.float32) * w[j] for j, c in enumerate(colors))
        bright = 0.25 + 0.75 * g[k]
        y0, y1 = int(mid - amp), int(mid + amp)
        img[y0:y1, k] = col * bright
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


class DeckVisual:
    """Two scrolling decks, playhead, crossfader and bass knob, drawn from the rendered bed."""

    PX = 260  # px per second

    def __init__(self, bed: dict, b: dict, total: float):
        cols_a = [(255, 70, 120), (92, 224, 168), (210, 235, 255)]
        cols_b = [(255, 120, 70), (80, 200, 255), (230, 230, 255)]
        self.strip_a = waveform_strip(bed["a"], bed["ga"], self.PX, 300, cols_a)
        self.strip_b = waveform_strip(bed["b"], bed["gb"], self.PX, 300, cols_b)
        self.bed, self.b = bed, b

    def frame(self, t: float, W: int, H: int) -> Image.Image:
        img = Image.new("RGB", (W, H), INK)
        d = ImageDraw.Draw(img)
        # subtle vignette grid
        for x in range(0, W, 120):
            d.line([(x, 0), (x, H)], fill=(16, 18, 25))
        k = int(t * SR) if int(t * SR) < len(self.bed["p"]) else len(self.bed["p"]) - 1
        lane_h = int(H * (0.21 if W > H else 0.17))
        y1, y2 = (int(H * 0.24), int(H * 0.53)) if W > H else (int(H * 0.30), int(H * 0.53))
        lanes = [(self.strip_a, self.b["out_label"], self.bed["ga"][k], 1, y1),
                 (self.strip_b, self.b["in_label"], self.bed["gb"][k], 2, y2)]
        cx = W // 2
        for strip, label, g, deck, y0 in lanes:
            x_px = int(t * self.PX)
            left = x_px - cx
            crop = Image.new("RGB", (W, strip.height), INK)
            src_l, src_r = max(0, left), min(strip.width, left + W)
            if src_r > src_l:
                crop.paste(strip.crop((src_l, 0, src_r, strip.height)), (src_l - left, 0))
            crop = crop.resize((W, lane_h))
            img.paste(crop, (0, y0))
            d.rectangle([0, y0, W, y0 + lane_h], outline=(34, 38, 50), width=2)
            on = g > 0.02
            tag = f"DECK {deck}"
            d.rounded_rectangle([40, y0 - 52, 40 + 130, y0 - 12], 10, fill=MINT if on else (50, 54, 66))
            d.text((58, y0 - 49), tag, font=bold(26), fill=INK if on else GREY)
            d.text((190, y0 - 50), label, font=demi(30), fill=WHITE if on else GREY)
            bpm = self.b["out_bpm"]
            if W > H:
                d.text((W - 300, y0 - 50), f"{bpm:6.2f} BPM", font=mono(28, True), fill=MINT if on else GREY)
            if not on:
                d.text((cx + 40, y0 + lane_h / 2 - 20), "CUED · SYNCED" if W < H else "CUED · SYNCED · WAITING FOR THE PHRASE", font=bold(28), fill=(70, 76, 92))
        d.line([(cx, y1 - 8), (cx, y2 + lane_h + 8)], fill=WHITE, width=3)
        # crossfader
        p = self.bed["p"][k]
        fx0, fx1, fy = (int(W * 0.34), int(W * 0.66), int(H * 0.81)) if W > H else (int(W * 0.22), int(W * 0.78), int(H * 0.75))
        d.rounded_rectangle([fx0, fy - 6, fx1, fy + 6], 6, fill=(40, 44, 56))
        kx = int(fx0 + (fx1 - fx0) * p)
        d.rounded_rectangle([kx - 26, fy - 30, kx + 26, fy + 30], 8, fill=WHITE)
        d.line([(kx, fy - 22), (kx, fy + 22)], fill=INK, width=4)
        if W > H:
            d.text((fx0 - 120, fy - 18), "DECK 1", font=bold(24), fill=GREY)
            d.text((fx1 + 24, fy - 18), "DECK 2", font=bold(24), fill=GREY)
        # deck-1 bass knob
        lk = self.bed["low_keep"][k]
        kx0, ky0 = (int(W * 0.13), fy) if W > H else (int(W * 0.10), fy)
        d.ellipse([kx0 - 34, ky0 - 34, kx0 + 34, ky0 + 34], outline=(70, 76, 92), width=4)
        ang = math.radians(-225 + 270 * (0.5 + 0.5 * lk))
        d.line([(kx0, ky0), (kx0 + 28 * math.cos(ang), ky0 + 28 * math.sin(ang))], fill=MAGENTA if lk < 0.98 else WHITE, width=5)
        if W > H:
            d.text((kx0 + 50, ky0 - 16), "DECK 1 BASS", font=bold(22), fill=GREY)
        return img


# ------------------------------------------------------------------ visuals
def obs_reader(path: Path, start: float, W: int, H: int, fps: int):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-i", str(path), "-an",
           "-vf", f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = W * H * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield Image.frombytes("RGB", (W, H), buf)
    p.wait()


def view_box(v: dict, u: float, W: int, H: int, im_size, vertical: bool = False):
    x, y, w, h = v["crop"]
    z = v["zoom"][0] + (v["zoom"][1] - v["zoom"][0]) * ease(u)
    if vertical:
        z *= v.get("vertical_zoom", 1.9)
    vw = w / z
    vh = vw * H / W
    f0 = v.get("vertical_focus", v.get("focus", [0.5, 0.5])) if vertical else v.get("focus", [0.5, 0.5])
    f1 = (v.get("vertical_focus_end") if vertical else None) or v.get("focus_end") or f0
    fx, fy = (f0[i] + (f1[i] - f0[i]) * ease(u) for i in range(2))  # optional slow pan
    cx, cy = x + fx * w, y + fy * h
    if v.get("clamp") == "roi":
        lo_x, hi_x, lo_y, hi_y = x, x + w, y, y + h
    else:
        lo_x, hi_x, lo_y, hi_y = 0, im_size[0], 0, im_size[1]
    cx = (lo_x + hi_x) / 2 if vw > hi_x - lo_x else min(max(cx, lo_x + vw / 2), hi_x - vw / 2)
    cy = (lo_y + hi_y) / 2 if vh > hi_y - lo_y else min(max(cy, lo_y + vh / 2), hi_y - vh / 2)
    return cx - vw / 2, cy - vh / 2, vw, vh


def ken_burns(im: Image.Image, v: dict, u: float, W: int, H: int, vertical: bool = False) -> Image.Image:
    ox, oy, vw, vh = view_box(v, u, W, H, im.size, vertical)
    sx = vw / W
    return im.transform((W, H), Image.AFFINE, (sx, 0, ox, 0, sx, oy), resample=Image.BICUBIC)


def to_screen(v: dict, box, u: float, W: int, H: int, im_size, vertical: bool = False):
    """Map a still's pixel box to output coordinates under the same Ken Burns view."""
    ox, oy, vw, vh = view_box(v, u, W, H, im_size, vertical)
    s = W / vw
    return [(box[0] - ox) * s, (box[1] - oy) * s, (box[2] - ox) * s, (box[3] - oy) * s]


def logo_card(W, H, u, sb, lift=0.0):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    glow = Image.new("RGB", (W, H), INK)
    gd = ImageDraw.Draw(glow)
    r = int(min(W, H) * (0.30 + 0.05 * ease(u)))
    gd.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r], fill=(18, 60, 48))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120)), 0.9)
    d = ImageDraw.Draw(img)
    size = int(W * (0.16 if W > H else 0.24))
    f = heavy(size)
    text = "claw-dj"
    a = ease(u / 0.25)
    tw = d.textlength(text, font=f)
    x = (W - tw) / 2
    y = H / 2 - size * 0.72 - lift * H
    col = tuple(int(INK[i] + (MINT[i] - INK[i]) * a) for i in range(3))
    d.text((x, y + (1 - a) * 30), text, font=f, fill=col)
    b = ease((u - 0.25) / 0.25)
    sub = sb["tagline"].upper()
    fs = demi(int(size * 0.20))
    sw = d.textlength(sub, font=fs)
    colb = tuple(int(INK[i] + (WHITE[i] - INK[i]) * b) for i in range(3))
    d.text(((W - sw) / 2, y + size * 1.12), sub, font=fs, fill=colb)
    lw = int(sw * ease((u - 0.15) / 0.4))
    d.rectangle([(W - sw) / 2, y + size * 1.12 + fs.size * 1.45, (W - sw) / 2 + lw, y + size * 1.12 + fs.size * 1.45 + 6], fill=MINT)
    return img


def end_card(W, H, u, sb):
    img = logo_card(W, H, 1.0, sb, lift=0.13 if W > H else 0.09)
    d = ImageDraw.Draw(img)
    a = ease((u - 0.15) / 0.3)
    col = tuple(int(INK[i] + (WHITE[i] - INK[i]) * a) for i in range(3))
    colm = tuple(int(INK[i] + (MINT[i] - INK[i]) * a) for i in range(3))
    fs = bold(int(W * (0.026 if W > H else 0.046)))
    fr = demi(int(W * (0.018 if W > H else 0.034)))
    lines = [(t, fs, colm if k == 0 else col) for k, t in enumerate(sb["end_lines"])]
    y = H * (0.60 if W > H else 0.58)
    for text, f, c in lines:
        for row in wrap(d, text, f, W * 0.9):
            tw = d.textlength(row, font=f)
            d.text(((W - tw) / 2, y), row, font=f, fill=c)
            y += f.size * 1.45
    if sb.get("presenter"):
        tw = d.textlength(sb["presenter"], font=fr)
        d.text(((W - tw) / 2, y + fr.size * 0.4), sb["presenter"], font=fr, fill=tuple(int(v * 0.7) for v in col))
    return img


def stats_card(W, H, u, lines):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    size = int(W * (0.050 if W > H else 0.082))
    f = heavy(size)
    blocks = [wrap(d, line, f, W * 0.86) for line in lines]
    gap, lead = size * 0.55, size * 1.05
    total_h = sum(len(r) for r in blocks) * lead + gap * (len(blocks) - 1)
    y = (H - total_h) / 2
    n = len(lines)
    for k, rows in enumerate(blocks):
        a = ease((u - k / n * 0.8) / 0.15)
        for row in rows:
            if a > 0:
                tw = d.textlength(row, font=f)
                col = tuple(int(INK[i] + ((MINT if k == 0 else WHITE)[i] - INK[i]) * a) for i in range(3))
                d.text(((W - tw) / 2 - (1 - a) * 40, y), row, font=f, fill=col)
            y += lead
        y += gap
    return img


def terminal_card(W, H, u, lines, hl):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    mx, my = int(W * 0.07), int(H * (0.20 if W > H else 0.30))
    win = [mx, my, W - mx, H - int(H * (0.08 if W > H else 0.24))]
    d.rounded_rectangle(win, 22, fill=(16, 18, 24), outline=(44, 48, 60), width=2)
    for k, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([win[0] + 26 + k * 34, win[1] + 22, win[0] + 46 + k * 34, win[1] + 42], fill=c)
    d.text((win[0] + 150, win[1] + 16), "claw-dj — audition", font=demi(24), fill=GREY)
    fs = mono(int(W * (0.0128 if W > H else 0.019)))
    shown = int(len(lines) * ease(u / 0.55)) + 1
    y = win[1] + 70
    for k, line in enumerate(lines[:shown]):
        for row in wrap(d, line, fs, win[2] - win[0] - 60):
            hi = k in hl
            if hi:
                d.rectangle([win[0] + 20, y - 4, win[2] - 20, y + fs.size + 6], fill=(18, 54, 42))
            col = MINT if hi else (WHITE if line.startswith("%") else (190, 196, 210))
            d.text((win[0] + 34, y), row, font=mono(fs.size, hi), fill=col)
            y += int(fs.size * 1.5)
    return img


def agent_card(W, H, ts, v, sb):
    """A coding-agent session driving claw-dj, revealed on the session clock ts."""
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    wide = W > H
    mx = int(W * (0.06 if wide else 0.05))
    win = [mx, int(H * (0.19 if wide else 0.24)), W - mx, H - int(H * (0.17 if wide else 0.27))]
    d.rounded_rectangle(win, 22, fill=(14, 15, 20), outline=(44, 48, 60), width=2)
    for k, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([win[0] + 26 + k * 34, win[1] + 22, win[0] + 46 + k * 34, win[1] + 42], fill=c)
    d.text((win[0] + 150, win[1] + 16), sb["agent"]["title"], font=demi(24 if wide else 26), fill=GREY)
    fs = mono(int(W * (0.0150 if wide else 0.0255)))
    lh = int(fs.size * 1.55)
    rows = []
    for ln in sb["agent"]["lines"]:
        if ts < ln["at"]:
            continue
        text, kind = ln["text"], ln["kind"]
        if kind == "prompt":
            text = text[: int((ts - ln["at"]) * ln.get("cps", 34))]
        rows.append((kind, text, ln))
    body_w = win[2] - win[0] - 70
    out = []
    for kind, text, ln in rows:
        for r, row in enumerate(wrap(d, text, fs, body_w - (40 if kind in ("tool", "out") else 0)) or [""]):
            out.append((kind, row, r, ln))
        if kind in ("prompt", "say"):
            out.append(("gap", "", 0, ln))
    max_rows = int((win[3] - win[1] - 90) / lh)
    out = out[-max_rows:]
    y = win[1] + 74
    for kind, row, r, ln in out:
        x = win[0] + 34
        if kind == "prompt":
            if r == 0:
                d.text((x, y), ">", font=mono(fs.size, True), fill=GREY)
            d.text((x + 34, y), row, font=mono(fs.size, True), fill=WHITE)
        elif kind == "say":
            if r == 0:
                d.text((x, y), "●", font=fs, fill=WHITE)
            d.text((x + 34, y), row, font=fs, fill=(214, 220, 232))
        elif kind == "tool":
            if r == 0:
                d.text((x, y), "●", font=fs, fill=MINT)
            d.text((x + 34, y), row, font=mono(fs.size, True) if r == 0 else fs, fill=MINT if r == 0 else (190, 196, 210))
        elif kind == "out":
            hi = ln.get("hl")
            if r == 0:
                d.text((x + 34, y), "└", font=fs, fill=GREY)
            if hi:
                d.rectangle([x + 66, y - 4, win[2] - 24, y + fs.size + 6], fill=(18, 54, 42))
            d.text((x + 74, y), row, font=mono(fs.size, bool(hi)), fill=MINT if hi else (165, 172, 188))
        y += lh if kind != "gap" else lh // 2
    return img


def note_card(W, H, u, v):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    mx = int(W * 0.09)
    top = int(H * (0.18 if W > H else 0.26))
    a = ease(u / 0.2)
    card = [mx, top + (1 - a) * 40, W - mx, H - int(H * (0.12 if W > H else 0.26))]
    d.rounded_rectangle(card, 26, fill=PANEL, outline=(52, 58, 72), width=2)
    pad = 54
    x0, y = card[0] + pad, card[1] + pad
    d.text((x0, y), v["title"], font=bold(int(W * (0.024 if W > H else 0.042))), fill=WHITE)
    y += int(W * (0.045 if W > H else 0.08))
    if v.get("quote"):
        fq = heavy(int(W * (0.046 if W > H else 0.075)))
        d.text((x0, y), v["quote"], font=fq, fill=MINT)
        y += int(fq.size * 1.35)
    b = ease((u - 0.2) / 0.2)
    if b > 0:
        fb = bold(int(W * (0.016 if W > H else 0.03)))
        tw = d.textlength(v["badge"], font=fb)
        d.rounded_rectangle([x0, y, x0 + tw + 44, y + fb.size + 26], 14, fill=MINT)
        d.text((x0 + 22, y + 11), v["badge"], font=fb, fill=INK)
        y += fb.size + 60
    fr = regular(int(W * (0.020 if W > H else 0.036)))
    for row in wrap(d, v["body"], fr, card[2] - card[0] - 2 * pad):
        d.text((x0, y), row, font=fr, fill=(214, 220, 232))
        y += int(fr.size * 1.45)
    d.text((x0, card[3] - pad - 20), v["meta"], font=regular(int(W * (0.012 if W > H else 0.022))), fill=GREY)
    return img


# ------------------------------------------------------------------ overlays
def draw_texts(img, seg, tt, W, H):
    d = ImageDraw.Draw(img, "RGBA")
    wide = W > H
    for tx in seg.get("texts", []):
        lt = tt - tx["at"]
        if lt < 0:
            continue
        a = ease(lt / 0.22)
        style, text = tx["style"], tx["text"]
        if not seg.get("_obs") and tx.get("text_no_obs"):
            text = tx["text_no_obs"]
        if style == "kinetic":
            f = heavy(int(W * tx.get("size", 0.062) * (1 if wide else 1.25)))
            rows = wrap(d, text, f, W * (0.86 if wide else 0.9))
            x = int(W * (0.06 if wide else 0.05))
            y = int(H * (0.06 if wide else 0.07))
            if seg["visual"]["kind"] == "still":
                pw = max(d.textlength(r, font=f) for r in rows)
                d.rounded_rectangle([x - 30, y - 18, x + pw + 30, y + len(rows) * f.size * 1.08 + 44], 22, fill=(9, 10, 14, int(225 * a)))
            band = Image.new("RGBA", (W, int(f.size * (1.25 * len(rows) + 0.7))), (0, 0, 0, 0))
            bd = ImageDraw.Draw(band)
            for k in range(band.height):
                bd.line([(0, k), (W, k)], fill=(0, 0, 0, int(150 * (1 - k / band.height) * a)))
            img.paste(band, (0, 0), band)
            for r, row in enumerate(rows):
                d.text((x + (1 - a) * -30, y + r * f.size * 1.08), row, font=f, fill=WHITE + (int(255 * a),))
            lw = int(d.textlength(rows[0], font=f) * ease((lt - 0.1) / 0.35))
            yb = y + len(rows) * f.size * 1.08 + 14
            d.rectangle([x, yb, x + lw, yb + 8], fill=MINT + (int(255 * a),))
        elif style == "stat":
            f = bold(int(W * (0.024 if wide else 0.042)))
            tw = d.textlength(text, font=f)
            x, y = int(W * 0.06), int(H * (0.70 if wide else 0.62))
            d.rounded_rectangle([x, y + (1 - a) * 20, x + tw + 56, y + f.size + 38 + (1 - a) * 20], 18, fill=MINT + (int(240 * a),))
            d.text((x + 28, y + 15 + (1 - a) * 20), text, font=f, fill=INK + (int(255 * a),))
        elif style == "tag":
            f = bold(int(W * (0.018 if wide else 0.032)))
            x, y = int(W * 0.035), int(H * (0.045 if wide else 0.06))
            tw = d.textlength(text, font=f)
            d.rounded_rectangle([x, y, x + tw + 84, y + f.size + 28], 14, fill=(0, 0, 0, int(170 * a)))
            pulse = 0.6 + 0.4 * math.sin(tt * 6)
            d.ellipse([x + 22, y + f.size / 2 + 4, x + 44, y + f.size / 2 + 26], fill=(255, 60, 70, int(255 * a * pulse)))
            d.text((x + 58, y + 13), text, font=f, fill=WHITE + (int(255 * a),))
        elif style == "chips":
            f = bold(int(W * (0.017 if wide else 0.031)))
            items = text.split(" | ")
            widths = [d.textlength(c, font=f) + 48 for c in items]
            gap = 16
            rows_, cur, cw = [], [], 0
            for c, w in zip(items, widths):
                if cur and cw + w > W * 0.88:
                    rows_.append(cur)
                    cur, cw = [], 0
                cur.append((c, w))
                cw += w + gap
            rows_.append(cur)
            y = int(H * tx.get("y", 0.85 if wide else 0.775)) - (0 if "y" in tx else (len(rows_) - 1) * (f.size + 36))
            for r, row in enumerate(rows_):
                tot = sum(w for _, w in row) + gap * (len(row) - 1)
                x = (W - tot) / 2
                for k, (c, w) in enumerate(row):
                    ak = ease((lt - 0.12 * (k + r * 3)) / 0.22)
                    if ak <= 0:
                        x += w + gap
                        continue
                    yy = y + r * (f.size + 36) + (1 - ak) * 16
                    d.rounded_rectangle([x, yy, x + w, yy + f.size + 26], 30, fill=(22, 26, 34, int(235 * ak)),
                                        outline=MINT + (int(255 * ak),), width=2)
                    d.text((x + 24, yy + 10), c, font=f, fill=WHITE + (int(255 * ak),))
                    x += w + gap
        elif style == "callout":
            f = heavy(int(W * (0.040 if wide else 0.062)))
            tw = d.textlength(text, font=f)
            idx = [x for x in seg["texts"] if x["style"] == "callout"].index(tx)
            nxt = [x["at"] for x in seg["texts"] if x["style"] == "callout"]
            until = nxt[idx + 1] if idx + 1 < len(nxt) else 99
            fade = 1 - ease((tt - until + 0.25) / 0.25)
            al = a * fade
            if al <= 0:
                continue
            x = W - tw - int(W * 0.06)
            y = int(H * (0.04 if wide else 0.08))
            d.text((x + (1 - a) * 40, y), text, font=f, fill=MINT + (int(255 * al),))


def draw_typing(img, seg, tt, W, H, im_size, vertical=False):
    ty = seg.get("typing")
    v = seg["visual"]
    u = tt / (seg["end"] - seg["start"])
    d = ImageDraw.Draw(img, "RGBA")
    if ty:
        box = to_screen(v, ty["box"], u, W, H, im_size, vertical)
        n = int(max(0, tt - ty["at"]) * ty["cps"])
        text = ty["text"][:n]
        d.rectangle([box[0] + 3, box[1] + 3, box[2] - 3, box[3] - 3], fill=(255, 255, 255, 255))
        fs = regular(max(10, int((box[3] - box[1]) * 0.46)))
        d.text((box[0] + 14, box[1] + (box[3] - box[1] - fs.size) / 2 - 2), text, font=fs, fill=(20, 20, 24))
        if int(tt * 2) % 2 == 0 or n < len(ty["text"]):
            cx = box[0] + 14 + d.textlength(text, font=fs) + 2
            d.line([(cx, box[1] + 8), (cx, box[3] - 8)], fill=(20, 20, 24), width=2)
    pu = seg.get("pulse")
    if pu and tt >= pu["at"]:
        box = to_screen(v, pu["box"], u, W, H, im_size, vertical)
        k = (tt - pu["at"]) % 1.2 / 1.2
        g = int(18 * ease(k))
        d.rounded_rectangle([box[0] - g, box[1] - g, box[2] + g, box[3] + g], 12, outline=MINT + (int(255 * (1 - k)),), width=6)


def caption_chunks(text: str, start: float, dur: float):
    words = text.split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 6 or w.endswith((".", ",", ":", "?")):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    weights = [len(c) + 6 for c in chunks]
    tot = sum(weights)
    t, out = start, []
    for c, w in zip(chunks, weights):
        out.append((t, t + dur * w / tot, c))
        t += dur * w / tot
    return out


def draw_caption(img, caps, t, W, H):
    for a, b, text in caps:
        if a <= t < b:
            d = ImageDraw.Draw(img, "RGBA")
            wide = W > H
            f = bold(int(W * (0.026 if wide else 0.05)))
            rows = wrap(d, text, f, W * 0.8)
            y = H * (0.86 if wide else 0.80) - (len(rows) - 1) * f.size * 1.2
            for r, row in enumerate(rows):
                tw = d.textlength(row, font=f)
                x = (W - tw) / 2
                yy = y + r * f.size * 1.25
                d.rounded_rectangle([x - 22, yy - 10, x + tw + 22, yy + f.size + 16], 14, fill=(0, 0, 0, 175))
                d.text((x, yy), row, font=f, fill=WHITE)
            return


# ------------------------------------------------------------------ assemble
def vertical_still(sq: Image.Image) -> Image.Image:
    """A square GUI view in a 9:16 frame over a blurred, darkened copy of itself."""
    W, H = 1080, 1920
    bg = sq.resize((H, H)).crop(((H - W) // 2, 0, (H - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), INK), 0.6)
    bg.paste(sq, (0, 470))
    return bg


def sync_offset(obs: Path, ref: np.ndarray, ref_t0: float) -> float:
    """Seconds into the OBS file where ref (bed time ref_t0) is heard, by cross-correlation."""
    from scipy.signal import fftconvolve
    sr = 4000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(obs), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    o = np.frombuffer(raw, dtype=np.float32)
    k0 = int(ref_t0 * SR)
    r = ref[k0:k0 + 12 * SR].mean(axis=1)[:: SR // sr]
    o = (o - o.mean()) / (o.std() + 1e-9)
    r = (r - r.mean()) / (r.std() + 1e-9)
    c = fftconvolve(o, r[::-1], mode="valid")
    best = int(np.argmax(c))
    score = c[best] / len(r)
    print(f"[obs] sync: bed {ref_t0:.2f}s found at OBS {best / sr:.2f}s (match {score:.2f})")
    if score < 0.25:
        print("[obs] WARNING: weak match. Is this the OBS recording of the demo-music audition (demo_music.py plan)?")
    return best / sr


def cmd_assemble(args) -> None:
    sb = load_storyboard()
    fps = sb["fps"]
    OUT.mkdir(parents=True, exist_ok=True)
    b = blend_numbers(sb)
    vo = load_vo(args.vo, sb)
    if not vo:
        sys.exit(f"no voice files in {vo_dir(args.vo)} — run vo-draft or record-vo first")
    segs = layout(sb, vo, b["beat_s"])
    total = segs[-1]["end"]
    agent_t0 = next((s["start"] for s in segs if s["visual"]["kind"] == "agent"), 0.0)
    for s in segs:
        s["_obs"] = bool(args.obs)
    perf = next(s for s in segs if s["id"] == "perform")
    blend_start = perf["start"] + round(perf.get("blend_at", 0.6) / b["beat_s"]) * b["beat_s"]
    print(f"[assemble] {len(segs)} shots, {total:.1f}s; blend #{b['number']} {b['out_label']} -> {b['in_label']} lands at {blend_start:.2f}s")
    bed = render_bed(b, blend_start, total)
    music = bed["mix"]
    obs_t = None
    if args.obs:
        # the audition starts its lead-in 32 beats before the fade; sync on that lead-in
        lead_in = b["beats"] * b["beat_s"]
        ref_t0 = max(0.5, blend_start - lead_in + 2.0)
        obs_t = sync_offset(Path(args.obs), music, ref_t0) - ref_t0  # OBS time = bed time + obs_t
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(args.obs), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                             check=True, capture_output=True).stdout
        live = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
        switch = max(0.0, blend_start - lead_in + 1.0)
        mixed = music.copy()
        for k in range(int(switch * SR), len(mixed)):
            j = k + int(obs_t * SR)
            if 0 <= j < len(live):
                mixed[k] = live[j]
        xf = int(0.4 * SR)
        k0 = int(switch * SR)
        w = np.linspace(0, 1, xf)[:, None]
        mixed[k0:k0 + xf] = music[k0:k0 + xf] * (1 - w) + mixed[k0:k0 + xf] * w
        live_rms = np.sqrt(np.mean(mixed[k0:] ** 2)) + 1e-9
        bed_rms = np.sqrt(np.mean(music[k0:] ** 2)) + 1e-9
        mixed[k0:] *= bed_rms / live_rms
        music = mixed
        print(f"[obs] picture + audio from {Path(args.obs).name} from {switch:.1f}s on (the real live audition)")
    # voice placement and ducking
    voice = np.zeros(len(music), np.float32)
    duck = np.ones(len(music), np.float32)
    caps = []
    for s in segs:
        if s["n"] not in vo:
            continue
        v = vo[s["n"]]
        k0 = int((s["start"] + s.get("vo_at", 0.3)) * SR)
        voice[k0:k0 + len(v)] += v[: len(voice) - k0]
        a, z = k0, k0 + len(v)
        r = int(0.25 * SR)
        level = 0.22
        duck[max(0, a - r):a] = np.minimum(duck[max(0, a - r):a], np.linspace(1, level, a - max(0, a - r)))
        duck[a:z] = np.minimum(duck[a:z], level)
        duck[z:z + r] = np.minimum(duck[z:z + r], np.linspace(level, 1, len(duck[z:z + r])))
        caps += caption_chunks(s["vo"], k0 / SR, len(v) / SR)
    fade = np.ones(len(music), np.float32)
    fade[: int(0.15 * SR)] = np.linspace(0, 1, int(0.15 * SR))
    fade[-int(1.5 * SR):] = np.linspace(1, 0, int(1.5 * SR))
    peak = np.percentile(np.abs(music), 99.9) + 1e-9
    final = music / peak * 0.55 * duck[:, None] * fade[:, None] + voice[:, None] * 0.95
    final = np.clip(final, -0.99, 0.99)
    tmp = Path(tempfile.mkdtemp(prefix="clawdj-demo-"))
    write_wav(tmp / "mix.wav", final)
    deck = DeckVisual(bed, b, total)
    stills = {}
    for s in segs:
        if s["visual"]["kind"] == "still":
            src = s["visual"]["src"]
            if src not in stills:
                p = OUT / "stills" / f"{src}.png"
                if not p.exists():
                    sys.exit(f"missing {p} — run: uv run python scripts/demo/demo_kit.py stills")
                stills[src] = Image.open(p).convert("RGB")
    formats = {"wide": (1920, 1080), "vertical": (1080, 1920)}
    want = list(formats) if args.format == "both" else [args.format]
    obs_frames = {}
    if args.obs:
        for s in segs:
            if s["visual"]["kind"] == "deck":
                obs_frames[s["id"]] = obs_reader(Path(args.obs), s["start"] + obs_t if s["visual"]["window"] == "blend"
                                                 else max(0.0, blend_start - b["beats"] * b["beat_s"] + 1.0 + obs_t), 1920, 1080, fps)
    procs = {}
    stamp = time.strftime("%Y%m%d_%H%M")
    paths = {}
    preview = set()
    if args.frames:  # contact frames only: two per shot, no video encode
        (OUT / "preview").mkdir(exist_ok=True)
        for s in segs:
            for u in (0.45, 0.92):
                preview.add(int((s["start"] + u * (s["end"] - s["start"])) * fps))
    for name in ([] if args.frames else want):
        W, H = formats[name]
        paths[name] = OUT / f"claw-dj_demo_{name}_{args.vo}_{stamp}.mp4"
        procs[name] = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                        "-r", str(fps), "-i", "-", "-i", str(tmp / "mix.wav"), "-c:v", "libx264", "-preset", "medium",
                                        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest",
                                        "-movflags", "+faststart", str(paths[name])], stdin=subprocess.PIPE)
    nframes = int(total * fps)
    for fi in range(nframes):
        if preview and fi not in preview:
            continue
        t = fi / fps
        s = next(x for x in segs if x["start"] <= t < x["end"]) if t < total else segs[-1]
        tt = t - s["start"]
        u = tt / (s["end"] - s["start"])
        v = s["visual"]
        base_wide = None
        for name in want:
            W, H = formats[name]
            kind = v["kind"]
            if kind == "still":
                im = stills[v["src"]]
                if name == "wide":
                    img = ken_burns(im, v, u, W, H)
                    draw_typing(img, s, tt, W, H, im.size)
                else:
                    sq = ken_burns(im, v, u, 1080, 1080, vertical=True)
                    draw_typing(sq, s, tt, 1080, 1080, im.size, vertical=True)
                    img = vertical_still(sq)
            elif kind == "deck":
                if s["id"] in obs_frames:
                    if base_wide is None:
                        base_wide = next(obs_frames[s["id"]], None) or deck.frame(t, 1920, 1080)
                    if name == "wide":
                        img = base_wide.copy()
                    else:
                        sq = base_wide.crop((420, 0, 1500, 1080))
                        img = vertical_still(sq)
                else:
                    img = deck.frame(t, W, H)
            elif kind == "logo":
                img = logo_card(W, H, u, sb)
            elif kind == "end":
                img = end_card(W, H, u, sb)
            elif kind == "stats":
                img = stats_card(W, H, u, v["lines"])
            elif kind == "terminal":
                img = terminal_card(W, H, u, sb["terminal_lines"], set(sb.get("terminal_highlight", [])))
            elif kind == "note":
                img = note_card(W, H, u, v)
            elif kind == "agent":
                img = agent_card(W, H, t - agent_t0, v, sb)
            else:
                img = Image.new("RGB", (W, H), INK)
            draw_texts(img, s, tt, W, H)
            if s.get("captions", True):
                draw_caption(img, caps, t, W, H)
            if t < 0.12:
                img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, t / 0.12)
            if t > total - 0.8:
                img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), min(1, (t - total + 0.8) / 0.8))
            if preview:
                img.save(OUT / "preview" / f"{name}_{t:05.1f}_{s['id']}.png")
            else:
                procs[name].stdin.write(img.tobytes())
        if fi % (fps * 5) == 0:
            print(f"  frame {fi}/{nframes}")
    for name, p in procs.items():
        p.stdin.close()
        p.wait()
        print("wrote", paths[name])
    shutil.rmtree(tmp, ignore_errors=True)
    timeline = [{"shot": s["id"], "start": round(s["start"], 2), "end": round(s["end"], 2), "vo": s.get("vo")} for s in segs]
    (OUT / "last_timeline.json").write_text(json.dumps(timeline, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("stills")
    st.add_argument("--gui", default=GUI, help="editor URL (default %(default)s)")
    sub.add_parser("vo-draft")
    iv = sub.add_parser("import-vo", help="split one continuous take (iPhone Voice Memo) into the lines")
    iv.add_argument("take", nargs="+", help="one continuous take, or one file per line in order")
    r = sub.add_parser("record-vo")
    r.add_argument("--line", type=int)
    r.add_argument("--device", help="avfoundation audio device index (default: first microphone)")
    a = sub.add_parser("assemble")
    a.add_argument("--vo", choices=["draft", "ernest"], default="draft")
    a.add_argument("--obs", help="OBS recording of Mixxx performing the demo-music audition")
    a.add_argument("--format", choices=["wide", "vertical", "both"], default="both")
    a.add_argument("--frames", action="store_true", help="write two PNG contact frames per shot to OUT/preview, no video")
    args = ap.parse_args()
    {"stills": cmd_stills, "vo-draft": cmd_vo_draft, "import-vo": cmd_import_vo, "record-vo": cmd_record_vo,
     "assemble": cmd_assemble}[args.cmd](args)


if __name__ == "__main__":
    main()
