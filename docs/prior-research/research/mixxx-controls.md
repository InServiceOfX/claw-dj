# Mixxx controls we will touch

A short, opinionated subset of [Mixxx's full Control list](https://github.com/mixxxdj/mixxx/wiki/MixxxControls)
that covers everything M0–M3 needs.

## Per deck (`[Channel1]`, `[Channel2]`, `[Channel3]`, `[Channel4]`)

| key                     | type   | range  | use                              |
|-------------------------|--------|--------|----------------------------------|
| `play`                  | bool   | 0/1    | start/stop transport             |
| `cue_default`           | bool   | 0/1    | toggle cue                       |
| `cue_set`               | bool   | press  | set cue at current position      |
| `cue_goto`              | bool   | press  | jump to cue                      |
| `loop_in` / `loop_out`  | bool   | press  | manual loop                      |
| `beatloop_4_activate`   | bool   | press  | 4-beat loop                      |
| `sync_enabled`          | bool   | 0/1    | beat-sync                        |
| `rate`                  | float  | -1..1  | pitch fader (range setting maps) |
| `bpm`                   | float  | r/o    | effective BPM                    |
| `playposition`          | float  | 0..1   | r/o                              |
| `beat_active`           | bool   | r/o    | true on a beat                   |
| `track_loaded`          | bool   | r/o    | a track is loaded                |
| `volume`                | float  | 0..1   | channel fader                    |
| `pregain`               | float  | 0..4   | trim                             |
| `pfl`                   | bool   | 0/1    | headphone cue                    |
| `LoadSelectedTrack`     | bool   | press  | load track from library to deck  |

## Per-deck EQ (`[EqualizerRack1_[Channel1]_Effect1]`)

| key            | range  | use         |
|----------------|--------|-------------|
| `parameter1`   | 0..1   | low EQ      |
| `parameter2`   | 0..1   | mid EQ      |
| `parameter3`   | 0..1   | high EQ     |
| `button_parameter1..3` | 0/1 | EQ kill (per band) |

## Master / mixer (`[Master]`)

| key              | range   | use                          |
|------------------|---------|------------------------------|
| `crossfader`     | -1..1   | A/B crossfader               |
| `headMix`        | -1..1   | head/master cue mix          |
| `headVolume`     | 0..5    | head volume                  |
| `gain`           | 0..2    | master gain                  |
| `balance`        | -1..1   | master balance               |

## Library (`[Library]`)

| key              | use                          |
|------------------|------------------------------|
| `MoveTrack`      | scroll selection             |
| `MoveFocus`      | move focus between panes     |
| `GoToItem`       | activate selection           |

For our use, **we never drive `[Library]` from the agent.** We pre-resolve a
file path and use the deck-level `LoadTrackFromDeck` mechanism via JS:

```js
engine.setValue("[Channel1]", "LoadSelectedTrackFromGroup", 0);  // not enough
// instead, JS-side helper that uses Mixxx's library DB lookup:
function loadIntoDeck(deck, fullPath) {
    engine.setValue("[Channel" + deck + "]", "stop", 1);
    // Mixxx 2.4+: there is no direct path-load; we either use the auto-DJ
    // queue, or call into the user library lookup. Easiest path:
    //   - precompute a Mixxx "playlist" containing all candidate tracks
    //   - the agent picks an index, JS does:
    //       engine.setValue("[Playlist]", "LoadTrackFromGroup", deck);
    // More reliable: use Mixxx 2.6's load-by-location (see TODO).
}
```

> **Open task:** confirm Mixxx 2.5/2.6 has a sanctioned "load by file path"
> route from JS. If not, we maintain a pre-built clawdj playlist and reference
> by row index (slower to set up, but bulletproof).
