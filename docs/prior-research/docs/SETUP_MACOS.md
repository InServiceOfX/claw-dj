# Setup — macOS

Tested against macOS 15.x on Apple Silicon, Mixxx (App Store, sandboxed build).

## 1. Confirm IAC Driver `clawdj` port is online

Already done by Ernest 2026-04-25:

- Open **Audio MIDI Setup** (`/System/Applications/Utilities/Audio MIDI Setup.app`).
- **Window → Show MIDI Studio**.
- Double-click **IAC Driver**.
- Tick **"Device is online"**.
- Add a port named **`clawdj`** (default Bus 1 can stay; we don't use it).

Verify from terminal:

```bash
swift - <<'EOF'
import CoreMIDI
let n = MIDIGetNumberOfSources()
for i in 0..<n {
  let s = MIDIGetSource(i)
  var dn: Unmanaged<CFString>?
  MIDIObjectGetStringProperty(s, kMIDIPropertyDisplayName, &dn)
  print("src", i, dn?.takeRetainedValue() as String? ?? "?")
}
EOF
```

Expected to include: `IAC Driver clawdj`.

## 2. Install the clawdj Mixxx mapping

The App Store build of Mixxx uses a sandboxed Application Support directory:

```
~/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/controllers/
```

Copy our two mapping files there:

```bash
SRC="$HOME/.openclaw/workspace/repos/Monoclaw/Projects/clawdj/mixxx-mapping"
DST="$HOME/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/controllers"
mkdir -p "$DST"
cp -v "$SRC/clawdj.midi.xml"     "$DST/"
cp -v "$SRC/clawdj.scripts.js"   "$DST/"
```

## 3. Wire the mapping in Mixxx

1. Mixxx → **Preferences** (⌘,) → **Controllers**.
2. In the left pane, find **IAC Driver clawdj**. Click it.
3. **Enabled** ✓.
4. **Load Mapping** → pick **clawdj** (it should now appear in the dropdown
   because we put the XML in the controllers folder).
5. Apply → OK.

## 4. Smoke test

After clawdj-core is built (M0), run:

```bash
clawdj setup    # prints detected ports, exits 0 if all good
clawdj load 1 <track_id>
clawdj cmd '{"op":"play","deck":1}'
```

You should see deck 1 in Mixxx light up with the track and start playing.

## 5. Sandbox file access

Mixxx is sandboxed but already holds Document-Access tokens for `~/Music`
(it reads your library fine). clawdj-core never touches Mixxx's process and
runs unsandboxed; it just sends MIDI and writes to its own SQLite. Mixxx's
own SQLite is *also* readable from outside (it's a regular file in the
container). Writes to Mixxx's DB are limited to the `__clawdj_queue` playlist.

## Troubleshooting

- **No `IAC Driver clawdj` in Mixxx Preferences** → quit & reopen Mixxx after
  enabling IAC; Mixxx scans MIDI on launch.
- **Mapping not in dropdown** → confirm the XML's `<info><name>clawdj` matches
  the dropdown entry; check that file is in the sandbox-container path, not
  the unsandboxed `~/Library/Application Support/Mixxx/`.
- **"Failed to start MIDI device"** in Mixxx log → another app is holding the
  port. Close other DAWs/MIDI tools or restart CoreMIDI:
  `sudo killall -9 coreaudiod`.
