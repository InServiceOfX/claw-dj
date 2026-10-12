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
Code: `brain/popups.py` (cards, choice, video timelines) and
`hands/popup_overlay.py` (live OBS overlay). Prompts: `prompts/brain/popups_Python.prompt`,
`prompts/hands/popup_overlay_Python.prompt`.

## On stream (Twitch via OBS, Mac mini)

1. Start the mix as usual, for example
   `caffeinate -dimsu scripts/run_mix.sh` (`caffeinate` keeps the Mac awake;
   see the 2026-10-11 sleep stall in `PROGRESS.md`).
2. In another terminal on the same machine:
   ```
   cd repos/claw-dj
   uv run python -m hands.popup_overlay
   ```
   It prints, for example, `OBS Browser Source URL: http://192.168.x.x:8765/overlay`.
3. In OBS: **Sources → + → Browser**, paste the URL, set **Width 1920, Height
   1080**, and leave the default transparent background. Put it above the
   video and visuals.

It finds the playing song by itself. It reads Mixxx without changing anything:
- **Audible deck:** the playing deck with the highest channel fader × crossfader level.
- **Identification:** that deck's exact track length is matched against the
  active plan, with Mixxx's analyzed BPM breaking ties.
- **Unknown song:** if the song can't be identified with certainty, general
  facts or untagged commentary show instead.

The overlay never writes to Mixxx and never affects the mix.

Options:

| Flag | Default | Meaning |
|---|---|---|
| `--interval S` | 75 | seconds between pop-ups |
| `--show S` | 12 | seconds each pop-up stays up |
| `--commentary-every N` | 3 | every Nth pop-up is commentary (when any exists) |
| `--verified-only` | off | only facts marked `"verified": true` |
| `--now-file now.json` | — | `{"artist": "...", "title": "..."}` instead of Mixxx |
| `--port P` / `--host H` | 8765 / all interfaces | where OBS connects |

In OBS, add `?scale=1.2` to the URL for bigger bubbles.

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
