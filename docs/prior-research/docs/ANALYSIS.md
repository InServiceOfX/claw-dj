# Analysis pipeline

Goal: turn a folder of audio files into a queryable corpus where every track
has BPM, musical key (Camelot), beat grid, downbeats, sections, energy curve,
and (optionally) time-aligned lyrics.

## Why offline

Live decisions must be O(microseconds). Anything that takes more than a few ms
must be precomputed. The agent reads cached metadata at planning time; the
core only sends MIDI at play time.

## Pipeline stages

```
audio file
   │
   ├─► [1] decode + resample to 22050 mono float32       (ffmpeg / symphonia)
   │
   ├─► [2] BPM + beat grid    (librosa beat_track, or aubio, or madmom DBN)
   │       → list of beat times, downbeat indices
   │
   ├─► [3] key detection       (essentia KeyExtractor → Camelot mapping)
   │       → "9A", confidence
   │
   ├─► [4] section segmentation (essentia SBic / MSAF / librosa.segment.agglomerative)
   │       → intro / verse / chorus / break / drop / outro
   │
   ├─► [5] energy curve         (RMS over 1-bar windows, normalized)
   │
   ├─► [6] lyric alignment      (LRC file → use; else whisper.cpp word-level)
   │
   └─► JSON line on stdout, schema below
```

## JSON output schema (one line per track)

```json
{
  "path": "/path/to/your/Music/track.m4a",
  "duration_s": 213.4,
  "tags": {"title":"...", "artist":"...", "album":"...", "year":1996, "genre":"Hip-Hop"},
  "bpm": 92.5,
  "bpm_confidence": 0.94,
  "key_camelot": "8A",
  "key_traditional": "Am",
  "key_confidence": 0.81,
  "downbeats": [0.34, 2.94, 5.55, ...],
  "beats":     [0.34, 0.99, 1.65, 2.30, 2.94, ...],
  "sections": [
    {"kind":"intro",     "start":0.0,   "end":15.6},
    {"kind":"verse",     "start":15.6,  "end":47.0},
    {"kind":"chorus",    "start":47.0,  "end":63.0},
    {"kind":"breakdown", "start":120.0, "end":135.5},
    {"kind":"acapella",  "start":150.0, "end":165.0}
  ],
  "energy_curve": [{"t":0,"e":0.12},{"t":1,"e":0.18}, ...],
  "lyrics": [{"t":15.8, "line":"yo, this is..."}, ...],
  "analyzed_at": "2026-04-26T03:55:00Z",
  "analyzer_version": "0.1.0"
}
```

## Tooling per stage

| Stage              | First choice    | Fallback        | Notes                       |
|--------------------|-----------------|-----------------|-----------------------------|
| Decode             | `symphonia` (Rust) | `ffmpeg` CLI | AAC/m4a needs `aac` feature |
| BPM/beat           | `aubio-rs` (Rust) | `librosa` (py) | aubio is fast, decent       |
| Downbeat / phrase  | `madmom` (py)   | librosa heuristic| madmom is the gold standard |
| Key (Camelot)      | `essentia` (py) | `keyfinder-cli` | Both exist; essentia is best|
| Sections           | `essentia` SBic | `MSAF`          |                             |
| Lyrics (sync)      | local `.lrc`    | `syncedlyrics`  | Then whisper.cpp word-level |

We tolerate both pipelines: a **fast Rust path** (symphonia + aubio) gives BPM
+ key for an entire library in minutes; the **deep Python path** runs on
demand for tracks the agent has slated for a set, adding sections + lyric
alignment.

## Camelot mapping (for harmonic mixing)

```
1A  Abm     1B  B
2A  Ebm     2B  F#
3A  Bbm     3B  Db
4A  Fm      4B  Ab
5A  Cm      5B  Eb
6A  Gm      6B  Bb
7A  Dm      7B  F
8A  Am      8B  C
9A  Em      9B  G
10A Bm     10B  D
11A F#m    11B  A
12A Dbm    12B  E
```

Compatible neighbors of `nA`: `nA`, `nB`, `(n±1)A`. (Standard wheel rule.)
The planner uses this.

## Performance targets

- **Library scan:** 1k tracks / minute on M5 Max (BPM+key only).
- **Deep analysis (per track):** ≤ 20 s with sections + downbeats.
- **Lyric alignment (whisper.cpp small model):** ≤ realtime on M5 GPU.

## Caching strategy

- One row per track in SQLite, keyed by `(path, mtime, size, sha256_first_1MB)`
  so a file moved or re-tagged is detected and re-analyzed only as needed.
- JSON blobs stored in `~/.local/share/clawdj/cache/{sha}.json`.
- Schema migrations via straight SQL files in `core-rust/migrations/`.
