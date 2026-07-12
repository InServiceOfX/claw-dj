# Quick sample-lineage mix demo

This is the shortest path to a two-minute mix that tells a sample story
instead of playing complete songs serially.

## Roles

- The H Company agent is the optional Brain. With `--planner h-agent`, it
  orders the six-song subset using BPM and sample-lineage context.
- Deterministic Hands load files, seek past selected intros, wait on Mixxx's
  beat clock, and alternate decks. Model latency never touches beat timing.
- Patched Mixxx supplies the analyzed BPM and beatgrid. Tracks more than 6%
  apart use a one-beat cut instead of an unnatural tempo sync.

Full lyrics are intentionally not copied into the project. The planner gets a
short hook phrase, sample source, sample element, and research URL. Add licensed
or user-supplied lyric data later only if section-level sentiment is genuinely
needed.

## Run

Start patched Mixxx with its local control API:

```bash
cd ../mixxxes/mixxx/BuildGcc
./mixxx --developer --controller-debug --control-api-port 9995
```

Preview the story without touching Mixxx:

```bash
uv run python -m brain.quick_mix --dry-run
```

Run the deterministic fallback order:

```bash
uv run python -m brain.quick_mix --seconds 20 --beats 4
```

Have the H Company agent order the set first:

```bash
uv run python -m brain.quick_mix --planner h-agent --seconds 20 --beats 4
```

The default six tracks take roughly two minutes. Each track rides for about 20
seconds, transitions overlap, and the final deck stops automatically.

## Live validation

Validated on Linux/X11 on 2026-07-11 against the patched Mixxx control API.
The H Company planner returned a valid six-track order. Mixxx analyzed the
tracks on load, the opening 85.95 -> 95.25 BPM gap used an unsynced one-beat
cut, and the remaining tracks completed four beat-synced blends near 95 BPM.
Both decks were stopped at completion. The Mixxx database then contained all
six tracks and twelve generated cue records.

The separate H-agent GUI inspection timed out after 90 seconds. Do not make a
screenshot-loop action a prerequisite for audible playback. If judges need a
visible Computer Use moment, run it before or after the deterministic mix and
keep the mix command available as the fallback.

## Waveforms

Waveform-derived features are useful; a waveform screenshot by itself is not a
mix plan. For a stronger second pass, extract onset strength, downbeats,
low-energy intro/outro regions, phrase boundaries, and loudness. Store only
timestamps/features, then seek Mixxx to those cue points. Mixxx's analyzed
beatgrid remains the timing authority during playback.

The first-45-second waveform overviews were generated locally during
validation and intentionally not committed because they derive from private
audio. They confirmed the six-second cues for `Warning` and `G Thang` and the
later transient development in `The Next Episode`.

## NemoClaw decision

NemoClaw is optional for this demo, not part of the beat-critical path. The
current `my-assistant` sandbox is registered but disconnected and its gateway
is down. Recover it with `nemoclaw onboard --resume` only when a working model
endpoint is ready.

This laptop has an 8 GiB RTX 3070. Holo's self-hosting guide targets the 35B
Holo3 model and says Q4 fits on recent Apple Silicon; it does not claim an 8
GiB NVIDIA configuration. Treat local Holo3-35B on this laptop as impractical.
For a NemoClaw-specific judging leg, use a remote OpenAI-compatible Holo3
endpoint, a larger GPU host, or NemoClaw's documented generic-Linux 4B model
while keeping the H Company planner as the separate sponsor integration.
