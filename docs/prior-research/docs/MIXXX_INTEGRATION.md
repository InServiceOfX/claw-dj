# Mixxx integration: research + decision

## What Mixxx exposes today

Updated check: 2026-07-03, against:

- Installed `/Applications/Mixxx.app`: **2.5.6 arm64**.
- Upstream stable docs: **2.5.6** is the current stable release; 2.6 beta and
  2.7 alpha/nightly builds exist but are not recommended for live use.
- Local source checkout: Mixxx `main` at `4ae413dbe8`, matching a 2.7-alpha
  development snapshot.

Mixxx has a unified internal API called the **Control system** — every knob,
button, slider, deck, EQ, effect is a `(group, key)` pair you can read and
write. Examples:

| Group        | Key            | Type | Description              |
|--------------|----------------|------|--------------------------|
| `[Channel1]` | `play`         | bool | Deck 1 play/pause        |
| `[Channel1]` | `rate`         | -1..1| Pitch fader              |
| `[Channel1]` | `bpm`          | float| Current effective BPM    |
| `[Channel1]` | `playposition` | 0..1 | Relative play position   |
| `[Channel1]` | `beat_active`  | bool | True on a beat           |
| `[EqualizerRack1_[Channel1]_Effect1]` | `parameter1` | 0..1 | Low EQ |
| `[Master]`   | `crossfader`   | -1..1| Crossfader position      |
| `[Library]`  | `MoveTrack`    | rel  | Browse library           |

Source: <https://github.com/mixxxdj/mixxx/wiki/MixxxControls>

The Control system is reachable from:

1. **GUI** (the user clicking).
2. **MIDI / HID controller mappings** — XML mapping + accompanying JavaScript
   that runs inside Mixxx's `QJSEngine` (Qt's JS sandbox, ES7-ish, sample-rate
   timers via `engine.beginTimer`). This is the **primary scriptable surface**.
3. **OSC client (output only, unmerged branch)** — see "OSC" below.
4. **Keyboard mappings** (limited).

There is **no built-in TCP/HTTP/WebSocket/REST/OSC input API** in stable Mixxx.
There is no "headless" Python or JavaScript runner that talks to the Control
system from outside Mixxx. You can launch Mixxx with command-line flags
(`--developer`, `--debug-assertions`, `--settings-path`, etc.) and with startup
audio files, but those don't provide a live command channel.

Source check notes:

- The legacy controller scripting API exposes `engine.getValue`,
  `engine.setValue`, `engine.makeConnection` / `engine.connectControl`, timers,
  scratch helpers, and MIDI output.
- `engine.getPlayer(group)` exists, but in legacy controller scripts it returns
  a `JavascriptPlayerProxy` exposing metadata only (`artist`, `title`, `key`,
  etc.). It does **not** expose a load-by-path method.
- Mixxx's newer QML layer has `QmlPlayerManagerProxy::loadLocationToPlayer` and
  `QmlPlayerProxy::loadTrackFromLocation`, but that proxy is for QML UI /
  controller-screen code, not the XML+JS MIDI mapping path we use today.
- The local `main` checkout still has no general-purpose command server.

## The decision: virtual-MIDI bridge

We make the OS expose a virtual MIDI input port; we point Mixxx's
"controllers" preferences at it; we ship a controller mapping
(`clawdj.midi.xml` + `clawdj.scripts.js`) that knows how to interpret messages
from clawdj-core. Then any process that can write MIDI bytes can drive Mixxx.

Pros:
- Officially supported, stable interface.
- Zero patches to Mixxx itself (works against upstream stable releases).
- Same code path on macOS and Linux.
- The JS side runs *inside Mixxx* with low-latency access to the Control
  system, so timing-critical ops (EQ-kill on the beat, scratch motions) live
  there.

Cons:
- 7-bit values for raw MIDI CC (we use 14-bit CC pairs or pre-scaled JS lookups
  where precision matters).
- We have to invent and document our own command set.

### macOS — virtual MIDI

The OS ships an "IAC Driver" virtual MIDI bus. User enables it once in
Audio MIDI Setup → MIDI Studio → IAC Driver → "Device is online". We name a
bus `clawdj`. Mixxx sees it as `IAC Driver clawdj`. Our Rust core uses the
`midir` crate; on macOS `midir` can also create its *own* virtual port via
CoreMIDI without IAC, which is even cleaner.

### Linux — virtual MIDI

Two equivalent options:

- `snd-virmidi` kernel module (modprobe) → `hw:Virtual,0` etc.
- ALSA sequencer client created by `midir` directly — preferred (no root).

JACK users get `a2jmidid` for free.

## The OSC story (read-only state)

There is an old PR / fork that adds an OSC *client* to Mixxx. It only sends
state outward (which deck is playing, position, title, duration, volume). It
does **not** accept inbound OSC. It's not in mainline.

For state feedback we will:

1. Try the OSC fork **if** the user has built that branch locally.
2. Otherwise: poll Mixxx's running state via a **back-channel MIDI feedback
   mapping**. In Mixxx's JS we register `engine.connectControl("[Channel1]",
   "playposition", emitOurMidi)` which sends MIDI back out (to a second virtual
   port) so clawdj-core hears every position update without polling.

Decision: **MIDI feedback bus is the path of least resistance.** We avoid
custom Mixxx builds.

## Lyrics / transitions

Mixxx's library can store and display LRC files. We will:

- Look for `track.lrc` next to the audio file first.
- Fall back to scraping (`syncedlyrics` Python pkg, or LRCLIB API).
- Last resort: run whisper.cpp locally to time-align.

We store the synchronized lines in our own SQLite (`lyrics` table) — Mixxx
doesn't need to render them; the agent reads them to find a-cappella gaps,
hooks, and transition opportunities ("transition on the line `'one-two...'`
which falls on bar 32 beat 1").

## Why not other DJ apps?

| App                 | Scriptable? | FOSS? | Cross-plat? | Verdict |
|---------------------|-------------|-------|-------------|---------|
| Mixxx               | Yes (MIDI/JS) | GPL  | Mac+Lin+Win | ✅ |
| Rekordbox           | No (closed)   | No   | Mac/Win     | ❌ |
| Serato              | No (DVS only) | No   | Mac/Win     | ❌ |
| Traktor Pro         | Limited       | No   | Mac/Win     | ❌ |
| VirtualDJ           | Some scripts  | No   | Mac/Win     | ❌ |
| `nodejs-mix-tools`  | not a DJ app  | -    | -           | n/a |

There is no standalone "mlxxx" CLI/JS DJ tool that I can find — the user
likely meant Mixxx.

## What about MLX (Apple's `mlx` ML framework)?

The user's message says "powered using mlxxx". On second read this almost
certainly means **Mixxx**. MLX (Apple's `ml-explore/mlx`) is unrelated to DJing,
though it could later power local lyric/embedding analysis on Apple Silicon.
**Decision:** confirm with Ernest if he meant something else, but proceed with
Mixxx as the working assumption (matches the "live mix mp3/aac" story
perfectly).

## Confirmed environment (Ernest's machine, 2026-04-25)

- ✅ Mixxx is the target (PID 47256 was running while planning).
- ✅ macOS, App Store sandboxed build (`org.mixxx.mixxx` container).
- ✅ IAC Driver enabled with port `clawdj` online — visible to CoreMIDI as both source and destination. Bus 1 left untouched (default, harmless).
- ✅ Library: 1,033 tracks in `mixxxdb.sqlite`, only 8 with BPM/key. We will run a full analysis pass in M1.
- ✅ Audio files: DRM-free `.m4a` + mp3.
- ✅ v1 = classic 2-deck, 100% software, no hardware controller.

## Loading tracks: the catch and the fix

There is **no legacy controller-script JS API to load a track by file path**.
The available stock-Mixxx routes are:

1. `LoadSelectedTrackFromGroup` — acts on whatever is highlighted in the GUI library.
2. Auto-DJ queue.
3. GUI drag-and-drop (not scriptable).

**Our solution:** clawdj-core maintains a Mixxx playlist called `__clawdj_queue` by writing directly to Mixxx's `Playlists` / `PlaylistTracks` SQLite tables (read-only access to `library` / `track_locations` for ID resolution). To load:

1. Rust: `INSERT OR REPLACE` the desired `track_id` at row 0 of `__clawdj_queue`.
2. Rust: send MIDI "load deck N from queue row 0" to mapping.
3. JS in Mixxx: focus the library on our playlist, set selection to row 0, fire `LoadSelectedTrackFromGroup` against `[Channel<N>]`.

This stays inside Mixxx's sanctioned API. We never modify the real `library` table.

## Patch option: first-class `clawdj` command API

We do **not** need a custom Mixxx build for M0/M1 transport control, EQ, fader,
looping, cueing, beat feedback, or most live recipes. Virtual MIDI is enough.

The only compelling reason to fork/patch Mixxx is deterministic track loading
without GUI library focus. The smallest useful patch is **not** a broad HTTP
server; it is one of:

1. Expose a legacy controller-script method like
   `engine.loadTrackFromLocation(group, path, play)` by routing through
   `PlayerManager::slotLoadLocationToPlayer`.
2. Add a narrow local IPC command server that accepts JSON commands and calls
   existing `ControlObject` and `PlayerManager` APIs on the GUI thread.

Recommendation: keep stock Mixxx 2.5.6 for live use and finish validating the
current virtual-MIDI mapping first. If track loading proves too brittle because
of library-focus behavior, fork Mixxx and implement option (1). It is small,
upstream-friendly, and reuses already-existing Mixxx internals.
