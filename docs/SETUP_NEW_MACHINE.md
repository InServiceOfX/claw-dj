# Setting up claw-dj on another Mac (USB stick + same network)

The scenario this covers: the music library (plus stems) lives on the USB
stick (`USB322FD`), the MacBook Pro is the current source of truth, and you
want the Mac Mini (or any other Mac) to have the same library index —
including everything that is expensive or impossible to regenerate there:
Mixxx-analyzed bpm/key, human `dj_notes`, cached lyrics, chroma, phrases,
lyric timelines, and beat-phase analysis.

**Why this works across Macs**: a track's identity is its absolute file
path, and macOS mounts the same USB volume at the same
`/Volumes/USB322FD/...` on every Mac. Nothing path-related needs
translating. (Linux mounts differ — that is still an open item, see
PROGRESS.md.)

**Robust against any local state**: every step below is safe to run whether
the other machine has never seen claw-dj, has a stale months-old clone, or
has its own diverged edits. Imports are merges (fill-missing only), scans
are incremental (unchanged files are skipped), and re-running any step is a
no-op the second time.

## Step 0 — on the machine you are LEAVING (MacBook Pro)

Before unplugging the USB stick, copy the current library index onto it:

```sh
cd ~/.openclaw/workspace/repos/claw-dj
uv run python -m brain.portable_library export
```

This writes `/Volumes/USB322FD/clawdj/library.sqlite3` using sqlite's
backup API, so it is safe even while the playlist-editor GUI is running.
Re-export any time the index has changed since the last export — the file
on the stick is a plain snapshot, always safe to overwrite.

Then eject the stick properly (Finder → eject, or `diskutil eject
/Volumes/USB322FD`) — yanking it mid-write corrupts the copy.

## Step 1 — on the NEW machine (Mac Mini): clone + install

```sh
git clone git@github.com:InServiceOfX/claw-dj.git
cd claw-dj
uv sync
```

If the repo is already cloned there, `git pull` instead. `uv sync` installs
everything including the audio-analysis dependencies (librosa etc.).

## Step 2 — plug in the USB stick and verify the mount

```sh
ls /Volumes/
```

You must see `USB322FD`. If it shows up under a different name (rare — a
name collision appends a suffix like `USB322FD 1`), pass the real path
explicitly to every command below via `--usb-db` / scan-root arguments, or
fix the collision by ejecting whatever claimed the name first.

## Step 3 — import the index from the stick

```sh
uv run python -m brain.portable_library import
```

This MERGES the stick's snapshot into whatever local state exists:

- tracks the local index has never seen are inserted whole (with their
  bpm/key/notes/etc.)
- tracks it already has only get NULL bpm/key/energy/duration filled in
- a local non-empty `dj_notes` is **never overwritten** — conflicts are
  printed so you can resolve them by hand
- lyrics/chroma/phrases/lyric-timelines/beat-phase caches are copied only
  for tracks that have none locally
- scan roots are unioned
- `crate.json` is refreshed at the end so the GUI sees the imported rows

Running it twice changes nothing the second time.

## Step 4 — scan for anything the snapshot doesn't cover

```sh
uv run python -m brain.scan_library \
    /Volumes/USB322FD/Music/HipHop \
    /Volumes/USB322FD/Music/Pop \
    /Volumes/USB322FD/Music/RnB \
    /Volumes/USB322FD/Music/Rock \
    /Volumes/USB322FD/Music/Country \
    /Volumes/USB322FD/Music/Electronica \
    --catalog
```

The scan is incremental: files already indexed (by size + modification
time) are skipped without being reopened, so after a fresh import this
mostly just confirms availability and picks up anything added to the stick
after the export. Live progress prints to the terminal (`N/M files, rate,
ETA`) and is also visible in the GUI's curate page if you prefer running
it from there (Step 5 → "Check for new music").

Add new roots to the command as folders appear on the stick — a root only
needs to be listed once; after that it's remembered in the database.

## Step 5 — (optional) run the GUI

```sh
uv run python -m brain.playlist_editor
# then open http://127.0.0.1:8787/#curate
```

Scanning from the GUI's "Check for new music" button does exactly the same
incremental scan with the same live progress counter.

## Step 6 — (optional) enrichment for NEW tracks

bpm/key for tracks that were never analyzed anywhere requires the patched
Mixxx build running with `--control-api-port 9995` (see PROGRESS.md "How
to run everything"). Everything already analyzed on the MacBook came over
in Step 3 — only genuinely new tracks need this. Lyrics/chroma/phrases for
a finalized set:

```sh
uv run python -m brain.enrich_set --status   # report gaps, change nothing
uv run python -m brain.enrich_set            # fill what's missing
```

## Going back the other way

The flow is symmetric. Before leaving the Mac Mini, `export`; back on the
MacBook Pro, `import`. Because import never overwrites local non-empty
dj_notes and only fills missing analysis, ping-ponging the stick between
machines cannot silently destroy either machine's work — the worst case is
a printed dj_notes conflict list you resolve by hand.

## What does NOT travel via the stick

- `brain/data/playlist.json` / finalized selections (per-machine working
  state; commit-worthy decisions live in dj_notes instead, which do travel)
- `mix_plan.json` (regenerate with `brain.build_mix_plan` — seconds)
- Mixxx's own `mixxxdb.sqlite` (each machine's Mixxx analyzes
  independently; claw-dj's index carries the bpm/key results that matter)
