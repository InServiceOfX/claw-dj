# Pop-ups: music facts and commentary over the stream and videos

VH1 Pop-Up Video for claw-dj. While a mix plays, large bubbles pop up:

- **Music facts** about the song and artist playing. They're written by the
  agent, carry no mark, and each names its source.
- **Snippets of an author's writing** from `commentary/<author-slug>/`. Each
  carries the author's initials (Ernest: a small **EY** badge).
  - A direct quote is in quotation marks.
  - A distillation shows "in brief" and only comes from the author's own
    `distilled.md`.
  - Long passages run as a progression (1/3, 2/3, 3/3).

Story: `user_stories/story__while_the_mix_plays_pop_ups_show_music_facts_and_my_commentary.md`.
Code: `brain/popups.py` (cards, choice, video timelines), `hands/popup_obs.py`
(native OBS text sources, auto and manual) and `hands/popup_overlay.py`
(browser-source overlay). Prompts: `prompts/brain/popups_Python.prompt`,
`prompts/hands/popup_obs_Python.prompt`, `prompts/hands/popup_overlay_Python.prompt`.

## On stream: native OBS (recommended, lowest footprint)

OBS renders the pop-ups with its own text sources, so there's no browser
source and no embedded Chromium (about 100-300 MB saved). A small Python
process (about 30-40 MB) sets the text and shows or hides the sources through
the authenticated OBS control (`docs/OBS_AGENT_CONTROL.md`).

**One-time OBS setup (about 2 minutes).** The OBS control deliberately can't
create or move sources, so you add them once:

1. OBS's WebSocket server must be on with a password saved (once):
   `uv sync --extra obs`, then in your own terminal
   `.venv/bin/python -m hands.obs_cli setup-password`.
2. In your stream scene, add:
   - **Text source named `claw-dj pop-up`**: the card. Pick a bold font sized
     for your canvas (for example 28-36 px at 854x480, 40-52 px at 1280x720),
     white with an outline or drop shadow, and place it where the bubble goes.
   - Optional **Text source `claw-dj pop-up EY`**: the small initials badge,
     placed at the card's corner. Without it, commentary ends with "— EY" in
     the card text instead.
   - Optional **backdrop `claw-dj pop-up bubble`**: a Color source (dark, about
     60% opacity) or an Image source sized behind the text.
   - Optional: a fade or slide show/hide transition on each source
     (right-click → Show Transition / Hide Transition) for the pop.
3. Start, in a terminal on the stream machine, next to the mix:
   ```
   cd repos/claw-dj
   caffeinate -dimsu uv run python -m hands.popup_obs run --scene "Your Scene" --allow-write
   ```
   `--allow-write` is required: it's your go-ahead for this process to change
   OBS text and visibility.

**Automatic mode** is the default: a card every `--interval` seconds (75),
shown `--show` seconds (12), matched to the song playing. The song comes from
Mixxx, read-only, as described below.

**Manual mode**, any time, from another terminal:
```
uv run python -m hands.popup_obs next      # next card (or forward through ones you went back over)
uv run python -m hands.popup_obs back      # previous card
uv run python -m hands.popup_obs show      # show the current card again
uv run python -m hands.popup_obs hide
uv run python -m hands.popup_obs pause     # stop automatic cards; a manual card stays up until hide/next/back
uv run python -m hands.popup_obs resume
uv run python -m hands.popup_obs status
```
Or open the control page at `http://127.0.0.1:8766/`. To use it from your
phone, start with `--control-host 0.0.0.0` and open `http://<mac-mini>:8766/`.

**Preview without OBS:** `uv run python -m hands.popup_obs dry-run` prints each
card in the terminal when it would pop up. The same manual commands work.

## On stream: browser source (optional, fancier bubbles)

1. Start the mix as usual, for example
   `caffeinate -dimsu scripts/run_mix.sh` (`caffeinate` keeps the Mac awake;
   see the 2026-10-11 sleep stall in `PROGRESS.md`).
2. In another terminal on the same machine:
   ```
   cd repos/claw-dj
   uv run python -m hands.popup_overlay
   ```
   It prints, for example, `OBS Browser Source URL: http://192.168.x.x:8765/overlay`.
3. In OBS: **Sources → + → Browser**, paste the URL, and set **Width and Height
   to your canvas size** (for example 1280x720 or 854x480; the page scales to
   whatever size it's given). On small canvases add `?scale=1.4` to the URL.
   To cut its cost, set the source to 10-15 fps and turn on "Shutdown source
   when not visible".

### How it knows what's playing (both modes)

It reads Mixxx without changing anything:
- **Audible deck:** the playing deck with the highest channel fader × crossfader level.
- **Identification:** that deck's exact track length is matched against the
  active plan, with Mixxx's analyzed BPM breaking ties.
- **Unknown song:** if the song can't be identified with certainty, general
  facts or untagged commentary show instead.

Neither mode writes to Mixxx or affects the mix.

Options (both modes):

| Flag | Default | Meaning |
|---|---|---|
| `--interval S` | 75 | seconds between pop-ups |
| `--show S` | 12 | seconds each pop-up stays up |
| `--commentary-every N` | 3 | every Nth pop-up is commentary (when any exists) |
| `--verified-only` | off | only facts marked `"verified": true` |
| `--now-file now.json` | — | `{"artist": "...", "title": "..."}` instead of Mixxx |
| `--wrap N` (native) | 30 | characters per line |

Preview the cards for a song in the terminal:
```
uv run python -m brain.popups preview --artist "Joe" --title "I Wanna Know"
```

## In videos (shorts and full mixes)

From a recorded mix's Mixxx cue sheet:
```
uv run python -m brain.popups timeline --cue ~/Music/Mixxx/Recordings/<mix>.cue \
    --duration <seconds> --interval 45 --show 10 --out popups.json
```
Each card sits inside the song it's about, and cards never overlap. In a
Python video builder, `brain.popups.drawtext_filters(items, out_dir, fontfile)`
returns an ffmpeg drawtext chain to burn them in.

## Writing commentary

See `commentary/README.md` and `commentary/ernest-yeung/_template.md`.
- One folder per author, named for them, with `author.json` giving their
  initials.
- Pieces are Markdown files. Optional `tags` (artists, eras, genres) make a
  piece pop up when a tagged artist is playing.
- Lines starting with `>` are the exact pull quotes to use.
- Files starting with `_` are never shown.

## Facts

`brain/popup_facts.json` is a list of facts. Each entry has:
- `id` and `text`;
- `artists` (empty means a general fact) and optional `titles`;
- `source`: required, where it can be checked;
- `verified`: whether a human checked it.

The starter set (2026-10-12) covers the artists in `chill-afternoon-rnb-vol-01`
and the Mo Money segment. The agent wrote it from well-documented facts with
Wikipedia sources, and every entry is `"verified": false` until checked. Use
`--verified-only` on stream once you've reviewed some.
