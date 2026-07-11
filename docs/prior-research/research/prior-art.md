# Prior art

Things we should read / steal from before we write a line of code.

## DJ engines & APIs

- **Mixxx** — <https://github.com/mixxxdj/mixxx>. Our base. Read:
  - [`MixxxControls`](https://github.com/mixxxdj/mixxx/wiki/MixxxControls) wiki
  - [`MIDI Scripting`](https://github.com/mixxxdj/mixxx/wiki/midi-scripting) wiki
  - [`Components JS`](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/components-0.0.js) helper lib
  - `res/controllers/` — dozens of real-world mappings to crib from.
- **Mixxx OSC client** (unmerged) — output-only state stream.
- **TouchMixxx** — <https://github.com/VoidRatio/TouchMixxx>. Demonstrates
  controlling Mixxx from outside via TouchOSC bridge → MIDI.

## AI DJs / generative DJ work

- **Spotify "AI DJ"** (closed, but blogs describe pipeline: setlist + voiceover).
- **Music-LM / MusicGen** — generative *audio*, not mixing; orthogonal.
- **NeurIPS "DJnet" / "Mixing with style"** papers — graph-based transition
  selection. Add concrete refs in M2 work.
- **`spotify-rekordbox-bridge`-style projects** — show the analysis-pipeline
  patterns we'll reuse.

## Music analysis

- **librosa** — go-to academic toolkit; great BPM, beat tracking; slower.
- **essentia** — best key detection (Edmullen + Krumhansl profiles), Camelot
  mapping built-in via `KeyExtractor`.
- **madmom** — SOTA neural beat/downbeat tracking. Heavy install, but worth it.
- **aubio / aubio-rs** — fast C/Rust DSP; cheap BPM and onset detection.
- **`Audet`** (<https://github.com/makalin/Audet>) — opensource BPM+key with
  Camelot, batch + GUI. Useful reference impl.
- **MSAF** — section segmentation toolbox (Python).

## Lyrics / time alignment

- **LRCLIB** — free time-synced lyric API.
- **`syncedlyrics` (PyPI)** — wraps LRCLIB + Musixmatch + others.
- **whisper.cpp** — local, word-level alignment; great on Apple Silicon.
- **NUS-AutoLyricsAlign** (research) — when whisper isn't tight enough.

## DJ theory references

- **Camelot Wheel** — Mark Davis / Mixed In Key. Standard for harmonic mixing.
- **"Open Format" mixing technique notes** — phrase-aware, energy curves.
- **Hip-hop DJ canon** — Premier / Pete Rock / Clark Kent — for transition style
  vocabulary (back-spin, juggling, blends, live-edit).

## Adjacent OpenClaw skills we can reuse

- `coding-agent` (Codex / Claude Code) — for sub-agent task delegation.
- `summarize` — for digesting research into ADRs.
- `cron` — for "track ending in 30s" wakes.
- `imsg`/`wacli`/etc — irrelevant here, listed only to remind us the harness
  pattern is well-trodden.
