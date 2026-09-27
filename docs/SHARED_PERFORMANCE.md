# One musical plan, live first

`mix_plan.json.performance` is the source of musical decisions: original track
identities, allowed source spans, measured rate, eight-beat/backbeat anchors,
clip placement, fades, instrumental support and source exclusions. Compiled
`events` are a reviewable schedule derived from it. No rendered file is needed
for live playback, and an export never replaces these events.

```sh
# Once per setup, or after changing Rust:
(cd core-rust && cargo build --release -p clawdj-cli)

# After editing the performance:
uv run python -m brain.performance_cli --plan path/to/mix_plan.json

# Inspect / perform the same named plan:
./scripts/run_mix.sh --plan path/to/mix_plan.json --dry-run
./scripts/run_mix.sh --plan path/to/mix_plan.json

# Optional listening export, outside the repository:
uv run python -m hands.offline_mix --plan path/to/mix_plan.json --out /external/current
```

Python validates source hashes, current hard DJ notes, source revisions, pattern
phase (including skips), source regions, deck occupancy and compiled events.
Rust then loads the original songs, sets their native playback rates, schedules
seeks/loops, and changes Mixxx EQ and channel volume while the audio plays.
Mixxx's audio engine performs the DSP. No FFmpeg decode, prepared-track cache,
vocal extraction or source rewriting is in this live execution path. During
playback the executor prints one block per deck start: the song, whether the
channel fader is opening, the low/mid/high EQ being written to that Mixxx
deck, and which other decks are already playing. A later line marks when a
supporting instrumental settles into its bass-bed EQ.

The source identity can be mapped to another machine's files with
`--source-map paths.json` on either runner/export command. That file is a JSON
object mapping each saved `track_id` to its local original file. Hash checks
still apply. Code and synthetic tests belong in Git; personal plans, mappings,
analysis reports and audio do not.

## Native execution

The current compiler assigns up to four decks, with at least two seconds free
before a replacement's start. Persistent supporting instrumentals and brief
source-skip covers are independent decks. Foregrounds remain full mixes; their
low EQ can be reduced to leave room for the instrumental bass. `live_eq` holds
raw low/mid/high gain controls, with 1.0 neutral. Playback rate changes use
turntable-style speed/pitch changes, with keylock disabled.

Every active source span has an engine loop bounded to its permitted region.
This prevents a stalled scheduler from running onward into an excluded section;
it may repeat allowed audio instead. The source-skip cover fades over that
boundary while the foreground pauses and resumes at the approved landing.
The executor checks observed source position and stops if drift exceeds 80 ms
or playback unexpectedly stops. This is a fail-fast controller, not a hard
real-time or sample-identical guarantee. Initial alignment uses waveform-derived
pattern anchors rather than trusting an arbitrary beatgrid parity.

Before playback or a new recording, the runner loads every original into stopped
Mixxx decks for native source preflight. A bad endpoint is reported before the
set starts. Independently measured EOF positions can differ slightly: at most
5 ms is accepted, with the actual source guard clamped to Mixxx's EOF. Declared
source exclusions never move later, and rhythmic loop lengths are never shortened
under this tolerance. Larger overruns report clip/path, planned span and native
duration. Stored cue recall settles before source guards are installed.

The runner refuses to take over playing decks. It temporarily disables automatic
ReplayGain and competing effect routing, centers deck crossfader assignment,
uses conservative master gain, and restores controls after stopping every owned
deck. Ctrl-C terminates and joins the Rust child before final mixer cleanup.
`--max-events` is intentionally rejected for simultaneous timelines; use an
explicit short test performance. Mixxx recording remains available with
`--record` and an existing recording is never stopped by this runner.

## Optional export and analysis

`hands/offline_mix.py` renders the same source spans, musical placements, loops
and fades. Its low-band filter and final loudness normalization differ from
Mixxx's native EQ/mastering, so the files are not an exact prediction of live
sound. Temporary decoded audio is scoped to the export and removed. A verified
current WAV/MP3 replaces the same filenames, never an original recording or the
live plan. Playback of an exported file is a separate player action.

`brain/audio_patterns.py` preserves the reusable local drum-pattern measurement
from the original experiment. Run `--help` for explicit reference/source paths,
windows, reference tempo/phase and output location. It measures bass and backbeat
onsets and fits the shared multi-beat pattern. Analysis is optional preparation
of musical metadata, not generation of music files required to perform.

Generic GUI Build refuses to overwrite an explicit performance. Edit and compile
that timeline instead. Automatic translation of arbitrary generic plans into
this richer schema is not implemented yet.

Primary control references: [Mixxx controls](https://manual.mixxx.org/2.4/en_gb/chapters/appendix/mixxx_controls),
[EQ and gain](https://manual.mixxx.org/2.4/en_gb/chapters/user_interface).
The installed patched Mixxx source confirms writable `rate_ratio` and stereo
engine-sample loop positions; the native integration checks exercise both.
