"""Find beat-aligned, energetic cue points for a small demo playlist.

Mixxx remains the beat authority: this decodes its BeatGrid-2.0 protobuf to
recover the exact first-beat phase. ffmpeg supplies a low-rate mono waveform
used only to rank 16-beat phrase candidates by energy and energy rise.

Usage:
    uv run python -m brain.phrase_analysis --tracks 8
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
import sys
from array import array
from pathlib import Path

from shared.mixxx_db import connect_readonly

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_PLAYLIST = DATA_DIR / "playlist.json"
DEFAULT_OUT = DATA_DIR / "phrase_analysis.json"


def _varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift < 70:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ValueError("invalid protobuf varint")


def _fields(data: bytes):
    offset = 0
    while offset < len(data):
        tag, offset = _varint(data, offset)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, offset = _varint(data, offset)
        elif wire == 1:
            if offset + 8 > len(data):
                raise ValueError("truncated protobuf fixed64")
            value = data[offset : offset + 8]
            offset += 8
        elif wire == 2:
            length, offset = _varint(data, offset)
            value = data[offset : offset + length]
            if len(value) != length:
                raise ValueError("truncated protobuf bytes")
            offset += length
        elif wire == 5:
            if offset + 4 > len(data):
                raise ValueError("truncated protobuf fixed32")
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        yield number, wire, value


def decode_beat_grid(blob: bytes) -> tuple[float, int]:
    """Decode Mixxx BeatGrid-2.0 as (bpm, first_beat_frame)."""
    bpm = None
    first_frame = None
    for number, wire, value in _fields(blob):
        if number == 1 and wire == 2:
            for inner_number, inner_wire, inner_value in _fields(value):
                if inner_number == 1 and inner_wire == 1:
                    bpm = struct.unpack("<d", inner_value)[0]
        elif number == 2 and wire == 2:
            for inner_number, inner_wire, inner_value in _fields(value):
                if inner_number == 1 and inner_wire == 0:
                    first_frame = int(inner_value)
    if not bpm or bpm <= 0 or first_frame is None:
        raise ValueError("BeatGrid-2.0 is missing bpm or first beat")
    return bpm, first_frame


def choose_phrase(
    beat_energy: list[float],
    *,
    first_beat_seconds: float,
    bpm: float,
    phrase_beats: int = 16,
    max_cue_seconds: float = 90.0,
    duration_seconds: float | None = None,
) -> dict:
    """Choose an energetic phrase start, preferring a clear rise and earlier cue."""
    if not beat_energy:
        return {"beat_index": 0, "cue_seconds": max(0.0, first_beat_seconds), "confidence": 0.0}
    peak = max(beat_energy) or 1.0
    candidates = []
    for index in range(0, max(1, len(beat_energy) - phrase_beats), phrase_beats):
        cue = first_beat_seconds + index * 60.0 / bpm
        if cue < 0 or cue > max_cue_seconds:
            continue
        after = beat_energy[index : index + 8]
        before = beat_energy[max(0, index - 4) : index]
        if not after:
            continue
        level = sum(after) / len(after) / peak
        previous = sum(before) / len(before) / peak if before else 0.0
        rise = max(0.0, level - previous)
        # Recognizable energy matters most; mild early bias avoids jumping to a late chorus.
        score = level + 0.65 * rise - 0.0015 * cue
        candidates.append((score, index, cue, level, rise))
    if not candidates:
        return {"beat_index": 0, "cue_seconds": max(0.0, first_beat_seconds), "confidence": 0.0}

    def as_dict(candidate: tuple) -> dict:
        score, index, cue, level, rise = candidate
        return {
            "beat_index": index,
            "cue_seconds": round(cue, 4),
            "confidence": round(min(1.0, 0.7 * level + 0.3 * rise), 3),
            "energy": round(level, 3),
            "energy_rise": round(rise, 3),
            "score": round(score, 3),
        }

    # Two entry flavors: "intro" = the track's opening region (soft build,
    # interesting occasionally), "body" = a high-energy phrase past the intro
    # (chorus / first verse — where the amplitude jumps). The plan builder
    # picks between them per slot for variety.
    body_floor = max(30.0, 0.15 * (duration_seconds or 0.0))
    intro_pool = [c for c in candidates if c[2] <= 25.0]
    body_pool = [c for c in candidates if c[2] >= body_floor]
    return {
        **as_dict(max(candidates)),
        "intro": as_dict(max(intro_pool)) if intro_pool else None,
        "body": as_dict(max(body_pool)) if body_pool else None,
    }


def decode_pcm(path: str, *, sample_rate: int, seconds: float) -> array:
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            path,
            "-t",
            str(seconds),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    )
    samples = array("h")
    samples.frombytes(result.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def beat_rms(
    samples: array,
    *,
    sample_rate: int,
    first_beat_seconds: float,
    bpm: float,
) -> list[float]:
    period = 60.0 / bpm
    energies = []
    beat = 0
    while True:
        start = max(0, round((first_beat_seconds + beat * period) * sample_rate))
        end = min(len(samples), round((first_beat_seconds + (beat + 1) * period) * sample_rate))
        if end <= start:
            break
        window = samples[start:end]
        energies.append(math.sqrt(sum(value * value for value in window) / len(window)))
        beat += 1
    return energies


def analyze_track(row, *, max_seconds: float = 120.0, analysis_rate: int = 11025) -> dict:
    bpm, first_frame = decode_beat_grid(bytes(row[4]))
    source_rate = float(row[3])
    first_beat_seconds = first_frame / source_rate
    samples = decode_pcm(row[0], sample_rate=analysis_rate, seconds=max_seconds)
    energies = beat_rms(
        samples,
        sample_rate=analysis_rate,
        first_beat_seconds=first_beat_seconds,
        bpm=bpm,
    )
    phrase = choose_phrase(
        energies,
        first_beat_seconds=first_beat_seconds,
        bpm=bpm,
        # Cap at 55% of the track so every entry leaves runway; no 90s cap —
        # a chorus at 1:40 is a legitimate showcase entry point.
        max_cue_seconds=float(row[2]) * 0.55,
        duration_seconds=float(row[2]),
    )
    return {
        "track_id": row[0],
        "artist": row[5],
        "title": row[1],
        "duration": row[2],
        "bpm": bpm,
        "first_beat_seconds": round(first_beat_seconds, 6),
        "phrase_beats": 16,
        **phrase,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--tracks", type=int, default=8)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    args = parser.parse_args()

    tracks = json.loads(args.playlist.read_text())[: args.tracks]
    conn = connect_readonly()
    try:
        query = """
            SELECT track_locations.location, library.title, library.duration,
                   library.samplerate, library.beats, library.artist
            FROM library
            JOIN track_locations ON library.location = track_locations.id
            WHERE track_locations.location = ?
              AND library.beats_version = 'BeatGrid-2.0'
              AND library.beats IS NOT NULL
        """
        results = []
        for track in tracks:
            row = conn.execute(query, (track["track_id"],)).fetchone()
            if row is None:
                print(f"[skip] no Mixxx BeatGrid-2.0: {track['artist']} - {track['title']}")
                continue
            print(f"[analyze] {track['artist']} - {track['title']}")
            results.append(analyze_track(row, max_seconds=args.max_seconds))
    finally:
        conn.close()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"version": 1, "tracks": results}, indent=2) + "\n")
    print(f"phrase analysis: {len(results)}/{len(tracks)} -> {args.out}")
    for result in results:
        print(
            f"  {result['artist']} - {result['title']}: {result['cue_seconds']:.2f}s "
            f"(beat {result['beat_index']}, confidence {result['confidence']:.2f})"
        )


if __name__ == "__main__":
    main()
