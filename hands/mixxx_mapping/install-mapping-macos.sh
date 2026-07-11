#!/usr/bin/env bash
# install-mapping-macos.sh
#
# Install the clawdj Mixxx mapping into the macOS App Store sandbox
# container so Mixxx can load it from Preferences → Controllers.
#
# Idempotent: safe to re-run. Use `--unlink` to remove the mapping.

set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
DST_DIR="$HOME/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/controllers"

if [[ "${1:-}" == "--unlink" ]]; then
    rm -fv "$DST_DIR/clawdj.midi.xml" "$DST_DIR/clawdj.scripts.js"
    exit 0
fi

if [[ ! -d "$DST_DIR" ]]; then
    mkdir -p "$DST_DIR"
fi

cp -v "$SRC_DIR/clawdj.midi.xml"   "$DST_DIR/"
cp -v "$SRC_DIR/clawdj.scripts.js" "$DST_DIR/"

cat <<EOF

✅ clawdj mapping installed.

Next steps inside Mixxx:
  1. Mixxx → Preferences (⌘,) → Controllers
  2. Click 'IAC Driver clawdj'
  3. Enabled ✓
  4. Load Mapping → 'clawdj'
  5. Apply → OK

If 'IAC Driver clawdj' is not listed, quit & relaunch Mixxx after
turning IAC Driver online in Audio MIDI Setup.
EOF
