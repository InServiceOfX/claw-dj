# PROGRESS — current state & next steps (for any agent harness)

> For Claude Code, Codex, Grok build, or any other AI agent continuing this
> work. Deep context lives in `docs/HANDOFF.md` (read it first); control
> reference in `docs/MIXXX_CONTROL_SURFACE.md`. Keep BOTH this checklist and
> HANDOFF.md updated as you work. Git rules (`CLAUDE.md`/`AGENTS.md`): never
> commit to `master`; feature branches only; Ernest merges.

## How to run everything (quick reference)

```bash
# Mixxx (patched 2.7 fork, default app) with the control API:
open -a Mixxx --args --control-api-port 9995

# Playlist editor UI (scan / ask-the-DJ-brain / suggest / finalize):
uv run python -m brain.playlist_editor --open

# Post-finalize enrichment (bpm/key, lyrics, chroma, phrases, lyric timelines):
uv run python -m brain.enrich_set            # --status to just report

# Order + plan + perform:
uv run python -m brain.curate_playlist --mode selection --planner mix-graph
uv run python -m brain.build_mix_plan --tracks N --profile dj-showcase --mix-brief "..."
uv run python -m hands.run_mix_plan          # --dry-run first

# Verse tour (one song, two decks, chorus skipped):
uv run python -m brain.build_verse_tour --track "21 Questions"
uv run python -m hands.run_mix_plan --plan brain/data/verse_tour_plan.json

# Rust gestures (build: cd core-rust && cargo build --release -p clawdj-cli):
core-rust/target/release/clawdj ctl get '[Master]' crossfader
core-rust/target/release/clawdj gesture brake --deck 1
core-rust/target/release/clawdj gesture stutter --deck 1 --rolls 4 --size 0.5

# Tests: uv run python -m unittest discover -s tests   (+ cargo test/clippy/fmt in core-rust)
```

## Done (post-hackathon arc, 2026-07-13)

- [x] Hackathon: **finalist** (no top-3/NVIDIA). Focus now: transitions & mix quality.
- [x] **Synced-lyric timelines** — `brain/lyric_timeline.py`: LRC parsing,
      chorus-by-repetition, verse onsets snapped to beatgrid bars; SQLite
      `lyric_timelines`; wired into `enrich_set`. 17/24 coverage on current set.
- [x] **Verse tour** — `brain/build_verse_tour.py`: same song on decks 1+2,
      on-beat hard cuts verse→verse, choruses skipped. Live-validated (21 Questions).
- [x] **Control-surface research** — `docs/MIXXX_CONTROL_SURFACE.md`: the
      control API reaches ANY Mixxx control; curated catalog + 10-move vocabulary.
- [x] **Rust control layer** — `core-rust/clawdj/src/control_api.rs` (TCP
      JSON-lines client + BeatWaiter) and `gesture.rs`: brake, spinback,
      kill_swap, kill_restore, censor, stutter, fade. CLI: `clawdj ctl …`,
      `clawdj gesture …`. All live-validated against running Mixxx except
      spinback/fade (validated by construction; audible test pending).

- [x] **Rust gestures wired into plans (2026-07-14)** — the flourish
      rotation now includes `stutter_fill`/`censor_fill`, extreme-tempo cuts
      became `brake_out` exits, and the runner shells out to
      `clawdj gesture …` with graceful degradation to plain blends/hard cuts
      when the binary is missing. Live-validated: stutter fill → brake exit
      → incoming track hits. Gotcha: clap parses the parent `--port` flag
      only BEFORE the gesture subcommand.
- [x] **"Create the mix" UI page** — built in the Grok session (playlist
      editor page 2: profile presets + free-text brief + analyze/enrich +
      start); was listed here as todo — corrected per Codex's 2026-07-14
      review.

- [x] **Spinback + Rust fade audibly-adjacent validated (2026-07-14)** —
      live-ran both against a real playing deck; end states confirmed
      correct (spinback: deck stopped, scratch2_enable cleaned up to 0;
      fade: crossfader -1.0→+1.0, deck1 stopped, deck2 landed playing).
      Human ear confirmation still pending — Ernest, give these a listen
      next time you're at the board (`clawdj gesture --port 9995 spinback
      --deck 1` / `fade --from 1 --to 2 --beats 8` with a track loaded and
      playing on deck 1). `kill_swap` gesture still not a plan move —
      Python EQ ramps handle bass swaps inside fades today.
- [x] **Echo-out exit built AND live AND audibly confirmed (2026-07-14)** —
      `hands/run_mix_plan.py: echo_out_exit`. Root cause of the original
      blocker: Mixxx has NO load-by-name effect control, only
      load-by-list-position, which isn't portable across machines/plugin
      sets. Resolved with a fixed convention instead of runtime lookup —
      full writeup in `docs/MIXXX_CONTROL_SURFACE.md` § "Loading effects
      deterministically". Echo loaded, gesture fired against a real
      playing deck, **Ernest confirmed by ear** — volume fade + rising
      echo tail sounded right. **Gotcha for future setup on other
      machines**: this skin's compact 4-DECKS effects strips don't label
      which unit is which, and the "EFFECTS" tab toggles that row's
      visibility rather than opening a separate labeled rack — so match
      `ECHO_UNIT`/`ECHO_SLOT` in `run_mix_plan.py` to wherever Echo
      actually lands, don't assume a specific unit number. Currently
      `EffectUnit2`/slot 3.
- [x] **Key-adjusted blends planned and executed (2026-07-14)** — close-BPM
      key clashes now become `key_adjusted_blend` when a deterministic
      ±1–2-semitone bridge reaches the same/relative/Camelot-neighbor key.
      Plans persist the shift and target key; the runner applies
      `pitch_adjust` for the overlap and curves it back to native through
      the second half of the fade. Unknown/unfixable keys retain the old
      filtered masking blend. Loads and instrument reset defensively zero
      stale pitch adjustment. Unit-covered; live audible validation pending.
- [x] **dj_notes: persistent human DJ knowledge → plan directives, and the
      showcase mix recorded (2026-07-14, Codex session).** `Track.dj_notes`
      (new SQLite column, additive migration) holds free-text per-track
      notes that automated enrichment never touches;
      `build_mix_plan.track_directives` parses small `key=value` hints out
      of it — `cue_seconds`/`ride_phrases`/`ride_beats`/`play_bpm` pin exact
      plan values, `entry_style` (`beat_drop`/`gentle_blend`/`verse_landing`)
      swaps in a purpose-built transition technique with a verified landing
      tolerance, `opener_style` adds a tease/echo/rewind/clean-drop opener
      (new `opener_effect`+`recue` events), `full_track` lets the finale
      ride the actual remaining runtime. `mix_profiles` gained
      `smooth_opening_transitions` (brief: "smooth opening transitions" →
      first N transitions forced into long, trick-free blends). Three
      runner robustness fixes came out of actually finishing a full live
      set: `load_deck` now waits for the plan's *expected* BPM as a load
      identity barrier (a freed deck's stale bpm/position could otherwise
      pass as the newly loaded track's), `wait_for_beats`/
      `wait_for_next_beat` fall back to sleeping out the remaining musical
      time at the deck's analyzed BPM instead of raising when Mixxx's
      `beat_active` push subscription drops mid-run, and
      `ensure_deck_playing` recovers a deck that silently lost its play
      state during a preload. `brain/archive_mix_plan.py` snapshots a
      known-good plan + playlist + exact runtime source with a git-commit
      manifest; the archive labeled
      `successful-full-playback-before-obs-capture` is the exact config in
      Ernest's recorded showcase video. Playlist editor also now shows
      album + acapella/instrumental badges (useful for dj_notes picking a
      specific version deliberately).

## Next steps (roughly in order of value)

1. **Human audible confirmation for spinback/fade** — echo-out is
   confirmed (above); spinback and fade are still only technically
   validated (correct end states via readback), never confirmed by ear.
   Quick listen next time Ernest is at the board.
2. **Transition preview rendering** — ffmpeg-stitch each planned transition
   into a ~30s snippet for offline audition (`brain/preview_transitions.py`).
   The tightest iteration loop on mix quality; no Mixxx needed.
3. **Phase-align hard-cut experiment** — A/B `beatsync_phase` on ordinary
   hard cuts. Do not silently add it to verse tour: that path was already
   live-validated with native-tempo, quantized cuts because phase-pull can
   move a lyric cue. Promote only after an audible test proves the pre-roll
   and cue semantics.
4. **whisperX fallback for unsynced lyrics** — 7/24 tracks lack synced
   lyrics; forced alignment against the plain lyrics fills the gap offline.
5. **Generic OpenAI-compatible engine** in `brain/pick_candidates.py` —
   covers xAI (Ernest has a key), local Ollama/LM Studio, and hermes with one
   client + base-URL/model config. NemoClaw/H engines stay while credits last.
6. **Typed Rust control namespace** — codegen `controls.rs` from
   MIXXX_CONTROL_SURFACE.md so the board is compile-time-checked.
7. **Cross-machine identity** — relative-path track ids + per-machine roots
   (Linux mounts differ; macOS↔macOS already works — see HANDOFF). Optionally
   keep a `library.sqlite3` copy on the USB itself.
8. **Grid repair from enrichment** — auto-fire `beats_set_halve/double`
   when detected BPM is 2x/0.5x its genre-neighborhood median.

## Known gotchas (short list; details in HANDOFF)

- Mixxx persists deck-analysis (bpm/beatgrid) to its DB **minutes** late;
  clean quit doesn't force it. Re-check later or Analyze via GUI.
- AirPlay routes die silently when idle ("zombie route") — re-pick the
  HomePod in Control Center + relaunch Mixxx before any real run.
- `hai_agents` auths via `~/.holo/.env` on this Mac; NemoClaw needs Docker
  Desktop + `openshell forward start --background 8642 hermes`.
- Verse cuts must NOT beatsync (phase-pull fights the lyric cue).
- LRCLIB lyric cache entries predating 2026-07-13 lack `synced_lyrics`;
  timeline builder force-refetches those once.
