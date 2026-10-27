#!/usr/bin/env python3
"""Two original, royalty-free demo tracks plus a two-track mix plan that plays them in Mixxx.

The public demo video can't carry commercial recordings, so this writes two
instrumentals of our own (numpy synthesis: drums, bass, Rhodes, pad, pluck),
built the way a DJ wants them:

  * "Night Drive"  90 BPM, A minor. Full groove, then a DJ outro (drums + bass).
  * "Velvet Hour"  92 BPM, C major (relative key). A DJ intro (drums, then bass)
                   before the full arrangement, so the blend has room.

Both start with a kick on beat 1 at exactly 0.000 s, so the beat grid is known.

  uv run python scripts/demo/demo_music.py            # writes MUSIC_DIR/*.flac + mix_plan.json

Then Mixxx can perform the blend for real (for the OBS take):

  uv run python -m hands.audition_transition --plan MUSIC_DIR/mix_plan.json --transition 1
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
MUSIC_DIR = Path.home() / ".openclaw/workspace/Data/Public/Music/claw-dj-demo"
ARTIST = "claw-dj demo"

RNG = np.random.default_rng(7)


# ---------------------------------------------------------------- utilities
def bp(lo, hi, order=2):
    if lo is None:
        return butter(order, hi, "lowpass", fs=SR, output="sos")
    if hi is None:
        return butter(order, lo, "highpass", fs=SR, output="sos")
    return butter(order, [lo, hi], "bandpass", fs=SR, output="sos")


def midi(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def add(buf: np.ndarray, at_s: float, sig: np.ndarray, gain=1.0, pan=0.0) -> None:
    """Mix a mono signal into a stereo buffer at at_s with equal-power pan."""
    k = int(round(at_s * SR))
    if k >= len(buf):
        return
    n = min(len(sig), len(buf) - k)
    left = np.cos((pan + 1) * np.pi / 4) * gain
    right = np.sin((pan + 1) * np.pi / 4) * gain
    buf[k:k + n, 0] += sig[:n] * left
    buf[k:k + n, 1] += sig[:n] * right


def env_t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def reverb_ir(seconds=1.8, tone=5000, seed=3) -> np.ndarray:
    r = np.random.default_rng(seed)
    t = env_t(seconds)
    ir = r.standard_normal((len(t), 2)) * np.exp(-t / (seconds / 6.5))[:, None]
    ir = sosfilt(bp(None, tone), ir, axis=0)
    ir[: int(0.012 * SR)] = 0  # pre-delay
    return ir / np.sqrt((ir ** 2).sum(axis=0, keepdims=True))


def reverb(dry: np.ndarray, ir: np.ndarray) -> np.ndarray:
    out = np.stack([fftconvolve(dry[:, c], ir[:, c])[: len(dry)] for c in range(2)], axis=1)
    return out


# ---------------------------------------------------------------- voices
def kick(vel=1.0) -> np.ndarray:
    t = env_t(0.6)
    f = 52 + 78 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.2)
    click = RNG.standard_normal(len(t)) * np.exp(-t / 0.0025) * 0.35
    return np.tanh(1.3 * (body + sosfilt(bp(1500, 6000), click))) * vel


def snare(vel=1.0) -> np.ndarray:
    t = env_t(0.45)
    noise = sosfilt(bp(1700, 8000), RNG.standard_normal(len(t))) * np.exp(-t / 0.13)
    tone = np.sin(2 * np.pi * 186 * t) * np.exp(-t / 0.06) + 0.5 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.04)
    return (noise * 0.9 + tone * 0.55) * vel


def clap(vel=1.0) -> np.ndarray:
    t = env_t(0.5)
    out = np.zeros(len(t))
    for k, d in enumerate((0.0, 0.011, 0.023)):
        tt = np.clip(t - d, 0, None)
        out += (t >= d) * np.exp(-tt / (0.009 if k < 2 else 0.16))
    return sosfilt(bp(900, 6000), RNG.standard_normal(len(t))) * out * vel * 0.9


def hat(vel=1.0, open_=False) -> np.ndarray:
    t = env_t(0.4 if open_ else 0.09)
    n = sosfilt(bp(7500, None, 3), RNG.standard_normal(len(t)))
    return n * np.exp(-t / (0.16 if open_ else 0.026)) * vel


def shaker(vel=1.0) -> np.ndarray:
    t = env_t(0.12)
    a = np.minimum(1, t / 0.02) * np.exp(-t / 0.04)
    return sosfilt(bp(4000, 11000), RNG.standard_normal(len(t))) * a * vel


def bass(note: float, dur: float, vel=1.0) -> np.ndarray:
    t = env_t(dur + 0.08)
    f = midi(note)
    a = np.minimum(1, t / 0.006) * np.exp(-t / 1.1) * np.clip((dur + 0.08 - t) / 0.08, 0, 1)
    s = np.sin(2 * np.pi * f * t) + 0.55 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t) + 0.1 * np.sin(8 * np.pi * f * t)
    return np.tanh(1.4 * s * a) * vel


def rhodes(note: float, dur: float, vel=1.0) -> np.ndarray:
    t = env_t(dur + 1.2)
    f = midi(note)
    idx = (1.6 + 1.2 * vel) * np.exp(-t / 0.45)
    car = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    bell = 0.12 * np.sin(2 * np.pi * f * 14.0 * t) * np.exp(-t / 0.05)
    a = np.minimum(1, t / 0.003) * np.exp(-t / 1.9)
    rel = np.clip((dur + 1.2 - t) / 1.2, 0, 1) ** 2
    return (car + bell) * a * rel * vel


def pad(notes, dur: float, vel=1.0) -> np.ndarray:
    t = env_t(dur + 1.0)
    out = np.zeros(len(t))
    for n in notes:
        f0 = midi(n)
        for det in (-0.09, 0.0, 0.08):
            f = f0 * 2 ** (det / 12)
            ph = RNG.uniform(0, 2 * np.pi)
            for h in range(1, 9):  # band-limited saw
                if f * h > 6000:
                    break
                out += np.sin(2 * np.pi * f * h * t + ph * h) / h
    out = sosfilt(bp(None, 1400), out)
    a = np.minimum(1, t / 0.9) * np.clip((dur + 1.0 - t) / 1.0, 0, 1)
    return out * a * vel / (len(notes) * 6)


def pluck(note: float, vel=1.0) -> np.ndarray:
    t = env_t(0.7)
    f = midi(note)
    s = sum(np.sin(2 * np.pi * f * h * t) * np.exp(-t * (6 + 5 * h)) / h for h in range(1, 7))
    return s * np.minimum(1, t / 0.002) * vel


# ---------------------------------------------------------------- tracks
def chord_tones(root: int, quality: str) -> list[int]:
    shapes = {"m9": [0, 3, 7, 10, 14], "maj9": [0, 4, 7, 11, 14], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10],
              "7#9": [0, 4, 10, 15], "13": [0, 4, 10, 14, 21], "7sus": [0, 5, 7, 10], "6/9": [0, 4, 9, 14]}
    return [root + i for i in shapes[quality]]


def render_track(spec: dict) -> np.ndarray:
    bpm, bars = spec["bpm"], spec["bars"]
    beat = 60 / bpm
    total = bars * 4 * beat + 3.0
    drums = np.zeros((int(total * SR), 2))
    music = np.zeros_like(drums)
    send = np.zeros_like(drums)
    sections = spec["sections"]  # bar -> set of active parts

    def parts(bar):
        return next(p for (a, b, p) in sections if a <= bar < b)

    swing = spec.get("swing", 0.58)
    for bar in range(bars):
        on = parts(bar)
        chord = spec["progression"][bar % len(spec["progression"])]
        root, quality = chord
        t0 = bar * 4 * beat
        # --- drums
        if "kick" in on:
            for pos in spec["kick"]:
                add(drums, t0 + pos * beat, kick(0.95 if pos % 2 == 0 else 0.78), 0.55)
        if "snare" in on:
            for pos in (1, 3):
                v = 0.9 if pos == 3 else 0.85
                s = clap(v) if spec.get("clap") else snare(v)
                add(drums, t0 + pos * beat, s, 0.6, 0.06)
                add(send, t0 + pos * beat, s, 0.22)
            if spec.get("ghost") and bar % 2 == 1:
                add(drums, t0 + 3.75 * beat, snare(0.25), 0.4, 0.06)
        if "hat" in on:
            for k in range(8):  # swung 8ths: the off-beat lands at `swing` of the beat
                pos = k // 2 + (swing if k % 2 else 0)
                vel = (0.55 if k % 2 == 0 else 0.36) * RNG.uniform(0.85, 1.1)
                op = spec.get("open_hat") and k == 7
                add(drums, t0 + pos * beat + RNG.normal(0, 0.003), hat(vel, op), 0.4, 0.25)
        if "shaker" in on:
            for k in range(8):
                add(drums, t0 + (k * 0.5 + (0.25 if k % 2 else 0)) * beat, shaker(0.5 if k % 2 else 0.3), 0.25, -0.3)
        # --- bass (fundamental kept between E1 and E2)
        bass_root = root - 12
        while bass_root > 40:
            bass_root -= 12
        bass_root += 12 if bass_root < 28 else 0
        if "bass" in on:
            for pos, off, dur in spec["bass_rhythm"]:
                add(music, t0 + pos * beat, bass(bass_root + off, dur * beat), 0.24)
        # --- keys
        tones = chord_tones(root, quality)
        if "keys" in on:
            for pos, dur in spec["keys_rhythm"]:
                for j, n in enumerate(tones):
                    sig = rhodes(n, dur * beat, 0.55 + 0.1 * (j == 0))
                    add(music, t0 + pos * beat + j * 0.008, sig, 0.24, -0.25 + 0.5 * j / len(tones))
                    add(send, t0 + pos * beat, sig, 0.05)
        if "pad" in on:
            sig = pad([n + 12 for n in tones[:4]], 4 * beat, 1.0)
            add(music, t0, sig, 0.8, -0.2)
            add(music, t0 + 0.012, sig, 0.8, 0.2)
            add(send, t0, sig, 0.25)
        if "pluck" in on:
            arp = spec["arp"]
            for k in range(8):
                n = tones[arp[k % len(arp)] % len(tones)] + 12
                p = pluck(n, 0.6 if k % 2 == 0 else 0.45)
                add(music, t0 + k * 0.5 * beat, p, 0.16, 0.35 if k % 2 else -0.35)
                add(music, t0 + k * 0.5 * beat + 0.75 * beat, p, 0.06, -0.35 if k % 2 else 0.35)  # dotted-8th echo
                add(send, t0 + k * 0.5 * beat, p, 0.05)
    # side-chain pump on the music bus from the kick pattern
    pump = np.ones(len(music))
    for bar in range(bars):
        if "kick" in parts(bar):
            for pos in spec["kick"]:
                k = int((bar * 4 + pos) * beat * SR)
                n = min(int(0.28 * SR), len(pump) - k)
                if n > 0:
                    pump[k:k + n] = np.minimum(pump[k:k + n], 1 - 0.35 * np.exp(-np.arange(n) / (0.09 * SR)))
    music *= pump[:, None]
    wet = reverb(send, reverb_ir(spec.get("verb", 1.8)))
    mix = drums + music + wet * 0.35
    mix = sosfilt(bp(28, None), mix, axis=0)
    mix = np.tanh(mix / (np.max(np.abs(mix)) + 1e-9) * 1.2) * 0.9  # gentle glue, keeps the transients
    fade = np.ones(len(mix))
    tail = int(2.5 * SR)
    fade[-tail:] = np.linspace(1, 0, tail)
    return (mix * fade[:, None]).astype(np.float32)


NIGHT_DRIVE = {
    "title": "Night Drive", "bpm": 90.0, "key": "Am", "bars": 56,
    # Am9 | Fmaj7 | Dm9 | E7#9
    "progression": [(57, "m9"), (53, "maj7"), (50, "m9"), (52, "7#9")],
    "kick": [0, 1.75, 2.5],
    "bass_rhythm": [(0, 0, 1.5), (1.75, 0, 0.5), (2.5, 7, 1.0), (3.5, 12, 0.4)],
    "keys_rhythm": [(0, 1.4), (1.5, 0.4), (2.5, 1.3)],
    "ghost": True, "open_hat": True,
    "sections": [(0, 4, {"keys", "hat"}),
                 (4, 8, {"keys", "hat", "kick", "snare", "bass"}),
                 (8, 36, {"keys", "hat", "kick", "snare", "bass", "shaker"}),
                 (36, 40, {"keys", "snare"}),
                 (40, 48, {"keys", "hat", "kick", "snare", "bass", "shaker"}),
                 (48, 56, {"hat", "kick", "snare", "bass"})],  # DJ outro
}

VELVET_HOUR = {
    "title": "Velvet Hour", "bpm": 92.0, "key": "C", "bars": 60, "clap": True,
    # Cmaj9 | Am9 | Fmaj9 | G13
    "progression": [(48, "maj9"), (57, "m9"), (53, "maj9"), (55, "13")],
    "kick": [0, 0.75, 2, 2.75],
    "bass_rhythm": [(0, 0, 0.7), (0.75, 0, 0.7), (2, 0, 0.6), (2.75, 7, 0.5), (3.5, 12, 0.4)],
    "keys_rhythm": [(0.5, 0.9), (2.5, 1.2)],
    "arp": [0, 2, 1, 3, 2, 4, 1, 3],
    "verb": 2.2,
    "sections": [(0, 4, {"kick", "hat", "snare"}),  # DJ intro: drums only
                 (4, 8, {"kick", "hat", "snare", "bass", "shaker"}),
                 (8, 16, {"kick", "hat", "snare", "bass", "shaker", "pad"}),
                 (16, 52, {"kick", "hat", "snare", "bass", "shaker", "pad", "pluck", "keys"}),
                 (52, 60, {"kick", "hat", "snare", "bass", "pad"})],
}


def write_flac(path: Path, y: np.ndarray, title: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", str(SR), "-sample_fmt", "s16",
                    "-metadata", f"title={title}", "-metadata", f"artist={ARTIST}",
                    "-metadata", "comment=Original demo music for claw-dj. Royalty-free.", str(path)],
                   input=np.ascontiguousarray(y).tobytes(), check=True)


def demo_plan(a: dict, a_path: Path, b: dict, b_path: Path) -> dict:
    """A two-track plan in the runner's own event format.

    Night Drive rides into its DJ outro (bar 48 = beat 192) and fades there;
    Velvet Hour comes in on its drums-only intro (beat 0). The blend is 32 beats.
    """
    ride = 191  # anchor = cue_beat + ride + 1 = 192, the first beat of the outro
    la = f"{ARTIST} — {a['title']}"
    lb = f"{ARTIST} — {b['title']}"
    track = lambda s, p: {"artist": ARTIST, "title": s["title"], "bpm": s["bpm"], "key": s["key"], "track_id": str(p),
                          "dj_notes": "Original demo music (claw-dj). Kick on beat 1 at 0.000 s; 4/4, snare on 2 and 4.",
                          "cue_seconds": 0.0, "cue_beat_index": 0, "cue_source": "synthetic_grid"}
    load = lambda deck, s, p: {"op": "load", "deck": deck, "track_id": str(p), "artist": ARTIST, "title": s["title"],
                               "cue_seconds": 0.0, "cue_beat_index": 0, "cue_confidence": 1.0, "cue_source": "synthetic_grid",
                               "cue_grid_offset_beats": 0.0}
    events = [
        {"op": "reset_instrument", "detail": "Zero rates, open EQ, crossfader left, keylock+quantize on"},
        load(1, a, a_path),
        load(2, b, b_path),
        {"op": "start", "deck": 1, "detail": f"Open on {la}"},
        {"op": "play_body", "deck": 1, "seconds": round(ride * 60 / a["bpm"], 3), "beats": ride, "ride_phrases": 3,
         "track": la, "track_id": str(a_path),
         "backbeat": {"status": "matched", "reason": "synthetic grid: snare on 2 and 4 by construction"},
         "phase_anchor": {"grid_bpm": a["bpm"], "first_beat_seconds": 0.0, "planned_anchor_beat_index": ride + 1,
                          "target_beat_mod4": 0, "target_beat_parity": 0}},
        {"op": "transition", "from_deck": 1, "to_deck": 2, "from_track": la, "to_track": lb,
         "technique": "smooth_blend", "transition_beats": 32, "score": 0.8,
         "reasons": [f"bpm close ({a['bpm']:.0f}→{b['bpm']:.0f})", f"relative keys ({a['key']}↔{b['key']})"],
         "moves": ["sync", "eq_dip_out_mid", "crossfade", "eq_restore"],
         "notes": "Demo blend: outro drums + bass into the incoming drums-only intro.",
         "lineage_story": False, "lyric_score": 0.0, "chroma_score": 0.0, "showcase_move": "bass_swap"},
        {"op": "play_body", "deck": 2, "seconds": 60.0, "beats": 92, "ride_phrases": 2, "track": lb, "track_id": str(b_path),
         "backbeat": {"status": "matched", "reason": "synthetic grid: clap on 2 and 4 by construction"},
         "phase_anchor": {"grid_bpm": b["bpm"], "first_beat_seconds": 0.0, "planned_anchor_beat_index": 32 + 92 + 1,
                          "target_beat_mod4": 0, "target_beat_parity": 0}},
        {"op": "stop_all"},
    ]
    return {"version": 3, "track_count": 2, "seconds_per_track": 85.0, "profile": {"name": "mix-to-listen"},
            "dj_format": "none", "phrase_interval_beats": 32,
            "tracks": [track(a, a_path), track(b, b_path)], "segments": [], "events": events,
            "instrument_map": {}, "runtime": {"mixxx_control_port": 9995},
            "plan_id": "claw-dj-demo-music", "plan_slug": "claw-dj-demo-music", "source_revs": {}, "bunches": []}


def main() -> None:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for spec in (NIGHT_DRIVE, VELVET_HOUR):
        y = render_track(spec)
        p = MUSIC_DIR / f"{ARTIST} - {spec['title']}.flac"
        write_flac(p, y, spec["title"])
        paths[spec["title"]] = p
        print(f"wrote {p}  ({len(y) / SR:.1f}s, {spec['bpm']:.0f} BPM, {spec['key']})")
    plan = demo_plan(NIGHT_DRIVE, paths["Night Drive"], VELVET_HOUR, paths["Velvet Hour"])
    (MUSIC_DIR / "mix_plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {MUSIC_DIR / 'mix_plan.json'}")


if __name__ == "__main__":
    main()
