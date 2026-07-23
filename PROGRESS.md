# PROGRESS — current state & next steps (for any agent harness)

> For Claude Code, Codex, Grok build, or any other AI agent continuing this
> work. Deep context lives in `docs/HANDOFF.md` (read it first); control
> reference in `docs/MIXXX_CONTROL_SURFACE.md`. Keep BOTH this checklist and
> HANDOFF.md updated as you work. Git rules (`CLAUDE.md`/`AGENTS.md`): never
> commit to `master`; feature branches only; Ernest merges.

## Active cross-machine priorities (2026-07-23)

- [ ] **YouTube OAuth/API access for `@claw-dj`.** Ernest is creating the
      Google Cloud project and Desktop OAuth client. Continue from
      `agent/hermes-skill/references/youtube-channel-oauth.md`; verify
      `channels.list(mine=true)` returns `UClafA-9ft1J1iAKo1JMZmwQ` before
      any write. Start with read/upload scopes, default the first upload to
      private, and confirmation-gate all public actions.
- [x] **Lightweight Hermes reconstruction kit.** `AGENTS.md`,
      `agent/hermes-profile/SOUL.md`, `agent/hermes-skill/`, and
      `docs/HERMES_AGENT_SETUP.md` reproduce the project agent's reviewed
      identity and workflows without exporting profile databases, caches,
      histories, binaries, or credentials.
- [x] **Reusable social-teaser workflow.** The repository skill now includes
      verified 9:16 media instructions plus a Swift/AppKit card renderer and
      FFmpeg orchestration/verification script.

## How to run everything (quick reference)

```bash
# One command: starts patched Mixxx with the control API if it isn't
# already running, waits for it, then opens the playlist editor.
scripts/start.sh

# Or manually:
# Mixxx (patched 2.7 fork, default app — NOT stock Mixxx, see docs/BUILD_MIXXX.md)
# with the control API:
open -a Mixxx --args --control-api-port 9995

# Playlist editor UI (scan / ask-the-DJ-brain / suggest / finalize):
uv run python -m brain.playlist_editor --open

# Post-finalize enrichment (bpm/key, lyrics, chroma, phrases, lyric timelines):
uv run python -m brain.enrich_set            # --status to just report

# Order + plan + perform:
uv run python -m brain.curate_playlist --mode selection --planner mix-graph
uv run python -m brain.build_mix_plan --tracks N --profile dj-showcase --mix-brief "..."
uv run python -m hands.run_mix_plan          # --dry-run first
uv run python -m hands.run_mix_plan --record # also records WAV via Mixxx's own recorder

# Turn a free-text DJ instruction into dj_notes edits (+ optional reorder),
# grounded in each mentioned track's real synced lyrics. Dry-run by default;
# also reachable from the web UI's "Interpret as DJ notes…" button:
uv run python -m brain.mix_directives --brief "..." --engine nemoclaw
uv run python -m brain.mix_directives --brief "..." --engine nemoclaw --apply

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
- [x] **Fixed: dj_notes cue_seconds was being silently overridden by Mixxx's
      own auto-seek-on-load (2026-07-14).** Root cause of the "Regulate
      still blends in during the monologue" bug Ernest caught by ear. The
      dj_notes cue (19.65s, verified exact against synced lyrics — Warren
      G's literal first rapped word) WAS being set correctly, but Mixxx's
      `[Controls] CueRecall=3` preference (`SeekOnLoadMode::IntroStart`,
      `src/engine/controls/cuecontrol.cpp`) auto-seeks every freshly loaded
      deck to its own detected intro-start marker (~0.24s for this track)
      — and that seek fires on a DELAY after `track_loaded`, racing our
      manual seek rather than preceding it. Confirmed by disproving the
      obvious alternative first: `cue_point`/`cue_set` looked like the
      "real" fix (that's the persisted main-cue control) but `cue_point`
      turned out to be a read-only mirror of the track's actual Cue object
      (refreshed via `loadCuesFromTrack()`), not a writable target — direct
      writes silently reverted too. The only mechanism that reliably wins
      the race: `cue_deck()` in `hands/run_mix_plan.py` now polls
      `playposition` for up to 1.5s after the initial seek, reasserting
      whenever it drifts, until it holds steady for a continuous 500ms
      window. Live-validated on the exact real seam from the recording
      (Lil' Kim → Regulate, full `perform_transition` call, not a
      simplified repro): crossfade rode continuously from 19.65s through
      the entire ~12.6s transition to 32.34s — verse to verse, monologue
      never touched. All 60 tests still pass.
- [x] **UI/workflow polish batch (2026-07-14, evening).**
  - `scripts/start.sh` — one command: starts patched Mixxx (if not already
    up) + opens the playlist editor. Answers "what do people run first."
  - **New scan roots discoverable in the UI**: "Add music folder" input on
    the Curate page (`/api/ingest/add-root`) — previously only `HipHop`/
    `RnB` were ever configured (from the very first CLI scan weeks ago);
    `Pop`/`Rock` existed on the drive but were invisible to the whole
    system since nothing ever added them as roots. Added both now
    (+1,372 tracks). "Check for new music" itself was never buggy — it
    correctly reports 0 new once a root's fully indexed; the confusion was
    two folders never being roots in the first place.
  - **Generic OpenAI-compatible engine** for Ask the DJ brain
    (`ask_generic` in `pick_candidates.py`) — env-configured
    (`CLAWDJ_LLM_BASE_URL`/`_API_KEY`/`_MODEL`), works for xAI/Grok, local
    Ollama/LM Studio, or OpenAI itself. No longer locked to NemoClaw/H
    Company.
  - **Whole-library candidate pool** for Ask the DJ brain (`--pool
    library` / UI dropdown) — root-caused why "90s West Coast G-funk"
    returned nothing: the brain only ever searched the latest scan's *new*
    tracks, and G-funk classics were indexed weeks ago. New pool does a
    keyword pre-filter over the whole 27k-track crate (top ~700 by
    relevance) before handing candidates to the LLM.
  - **Live per-track console output** for Analyze & enrich — the backend
    already buffered a log (`enrich_log`), but only bpm/lyrics/phrases'
    *phase-level* messages reached it; per-track lines existed only as
    terminal `print()`s the browser never saw. Threaded `progress`
    callbacks through `analyze_tracks`/`fill_lyrics`/`fill_phrases` so
    every track shows up in a new scrolling `<pre>` console in the UI,
    not just a single static "Enriching…" line.
  - **LRCLIB lyric fetch robustness**: one retry on transient
    network/timeout errors, and check the first 5 search results for
    lyrics (not just `results[0]`, which can be an instrumental/no-lyrics
    entry) before giving up on a title variant.
  - **Album added to library search** (was title/artist/path only).
  - **`avoid_silence` profile flag** + new **`mix-to-listen`** profile —
    club-set redefined as "beat never stops, no hard cuts, occasional
    planned drop only" (`avoid_silence=True` downgrades the rare
    extreme-tempo hard-cut fallback to a smoother always-blending
    technique); mix-to-listen is a 4th preset for a pure listening mix
    (long-ish but variable segments favoring each song's best part, no
    showcase flourishes). No single settled DJ-vernacular term found for
    "mix to listen" — closest common terms are "listening mix" / "chill
    mix"; used "mix-to-listen" as the profile name since it's unambiguous.
- [x] **Detailed DJ-craft edit pass on the West Coast G-funk set
      (2026-07-14, night).** Ernest gave extremely specific real-time
      feedback while listening to a live run; applied by hand (see below
      for the future pipeline this points at):
  - **Bass-kill timing bug, general fix**: `perform_transition` used to
    pre-kill the INCOMING deck's low EQ at progress=0, only restoring it
    at the crossfader midpoint -- for a long transition (44 beats ≈ 28s
    on Runnin' Wit No Breaks) that's ~14s of the incoming track playing
    bassless while actively growing more prominent. Now the incoming
    deck never loses bass; only the outgoing deck's bass is killed, right
    at the handoff.
  - **New `juggle_intro` opener style**: loads a second copy of the
    opener on the other deck, chops the crossfader between them over the
    first bars (classic DJ-intro flourish), lands cleanly, plays straight
    through -- nothing skipped. Live-validated (no crash, clean end
    state); audible confirmation still pending.
  - **dj_notes written from real lyric evidence, not guesses** — pulled
    raw synced LRC lines to find exact verse boundaries rather than
    trusting memory of the songs:
    - Nuthin' But A "G" Thang: now the pinned opener, `cue_seconds=0`
      (was cutting into the middle), `opener_style=juggle_intro`.
    - Stranded On Death Row: existing Kurupt-landing directive kept;
      `ride_beats=335` added so Snoop's verse (ends at 4:02.81, "Doggy
      Dogg's done") plays in full before the next transition.
    - Lil' Ghetto Boy: `entry_style=verse_landing` at 37.230s (Snoop's
      literal first rapped line, found in the raw LRC — everything
      before it is Dre's spoken community-message intro), `ride_beats=78`
      so the verse rides through to the chorus at 82.9s instead of
      cutting off after 7 beats.
    - Gz Up, Hoes Down: `cue_seconds=8` (was starting later, past more of
      the early material), `ride_phrases=3`.
    - Tha Shiznit: `play_bpm=98.5` — was blending from an 88.3bpm
      neighbor with no deliberate tempo target; nudges it toward its
      genuinely faster character per Ernest's explicit "don't be afraid
      to run it faster than default."
  - **Real bug found while doing this**: multiple FILE COPIES of the same
    song exist in the crate (different album/compilation folders), and
    dj_notes must be written to the EXACT track_id that's actually in
    `playlist.json` — writing to a same-titled-but-different copy is a
    silent no-op (confirmed: Stranded On Death Row's first dj_notes write
    landed on a compilation-disc copy, not the one actually selected;
    `ride_beats` visibly failed to apply until traced to the wrong
    file). Any future by-hand or agent-driven dj_notes edit should verify
    against `playlist.json`'s actual track_id, not just match by title.
  - **Reordered**: "213 — Groupie Luv" moved from position 2 (crowding
    the intended chronological-ish Dre/Snoop/Warren-G opening run) to
    late, adjacent to "Dollars & Sense" (closest BPM match, 97.0→98.9).
    "Eastside LB" moved next to "This DJ (Remix Version)" (91.9→91.4bpm,
    closest match of the suggested Warren G neighbors) instead of sitting
    between Deep Cover and Lil' Ghetto Boy.
  - **DONE 2026-07-15**: `brain/mix_directives.py` — the mix-brief-to-edits
    pipeline this by-hand pass motivated. Reuses `pick_candidates.py`'s
    engine functions (`ENGINES`, `ask_h_agent`); feeds the LLM the current
    ordered track list (short ids, not real paths — `t000` style, exactly
    like `pick_candidates.build_whole_library_view`'s `id_map` pattern) with
    existing dj_notes, plus each brief-referenced track's raw synced LRC
    pulled from `lyric_timelines` (token-overlap match against
    artist/title, `_mentioned_tracks()`), and asks for
    `{"notes": {short_id: new_dj_notes}, "reorder": [short_id, ...] | null}`.
    `parse_directives()` maps short ids back to real track_ids and enforces
    the two hard rules: every id must exist in the current set (the exact
    wrong-file-copy bug above, guarded structurally — a hallucinated path
    can't even be expressed, since only short ids the model was given are
    valid), and a reorder must be an exact permutation (checked as a set
    equality + length check) — never invent or drop a track. Dry-run by
    default (`print_diff`); `--apply` writes dj_notes to
    `library.sqlite3` AND patches `playlist.json`'s rows in place directly
    — **deliberately not** a `load_crate()`/`export_playlist()` round trip,
    because `crate.json` is a lazily-synced compatibility export (only
    refreshed on scan/analyze/sync) and would silently serve stale dj_notes
    back into playlist.json otherwise; a landmine this design sidesteps
    rather than hits. Wired into the web UI: `playlist_editor.py` gained
    `ask_directives`/`directives_status`/`apply_directives` (same
    background-thread-+-poll pattern as `ask_brain`) and
    `/api/directives/{ask,apply}` + `GET /api/directives`; `playlist.html`
    got an "Interpret as DJ notes…" button right before "Build mix plan"
    (reusing the same `#mix-brief` textbox) that shows the diff and
    requires an explicit "Apply these edits" click — never auto-applies.
    Tested against the live 28-track set through a real nemoclaw call: it
    correctly grounded a verse-landing-style ask in real lyrics and closed
    the loop end-to-end, but also caught a real LLM instruction-following
    miss ("don't touch this track's bpm" → it added a `play_bpm` anyway) —
    concrete evidence for why dry-run-first is load-bearing, not
    decorative. 13 unit tests in `tests/test_mix_directives.py` (id
    validation, permutation enforcement, JSON-in-prose extraction, sqlite +
    playlist.json write correctness).
  - **DONE 2026-07-15**: `--record` flag on `hands/run_mix_plan.py` —
    toggles Mixxx's `[Recording],toggle_recording`/`status` controls
    (`start_recording`/`stop_recording` in `hands/run_mix_plan.py`,
    confirmed against `RECORDING_PREF_KEY = "[Recording]"` in
    `recording/defs_recording.h` in the patched fork) around the plan run,
    inside a `try/finally` so a crash mid-set still stops the recording.
    Never touches a recording that was already running when the plan
    started (checks `status` first). Current build has no mp3 encoder (no
    `-DFFMPEG=ON` — see `docs/BUILD_MIXXX.md`), so this records WAV;
    convert with `ffmpeg` afterward, or rebuild with FFMPEG support for
    native mp3. 4 unit tests in `tests/test_mix_runner.py`
    (`RecordingControlTests`) using a fake control object.
  - **Real bug found by ear, fixed 2026-07-15**: `juggle_intro` openers
    (`hands.run_mix_plan.perform_juggle_intro`) load a second copy of the
    OPENER track onto the other deck to juggle between, and leave it
    loaded there when the juggle ends. `build_mix_plan.py` used to follow
    the `opener_effect` event with a `recue` for deck 2 — but `recue` only
    re-seeks whatever's *currently* loaded, it can't reload a different
    track. So the first transition crossfaded back into a second copy of
    the opener track instead of the real next track — audible live as
    Ernest reported: "in the middle towards the end of Snoop's first verse,
    you DO NOT need to fade in Dr. Dre's Nuthin' But a G Thing again."
    Fixed by changing that post-opener event from `recue` to an explicit
    `load` of the real second track (`brain/build_mix_plan.py`, right
    after the `opener_effect` append) — reloading deck 2 properly undoes
    the juggle's clobber before the first transition runs. Updated
    `tests/test_mix_plan.py::test_opener_effect_and_verse_landing_cue` to
    assert `load` (not `recue`) follows `opener_effect`.
  - Same request: reordered "Tha Eastsidaz — G'd Up" (2000) from position 1
    (right after the opener) to late in the set, just before "DJ Quik —
    Dollars & Sense" (97.1→98.9 bpm bridge) — chronologically it's later
    material than the early-90s Chronic/Doggystyle-era songs that should
    open the mix. "Warren G — Regulate" naturally became the new track
    right after the opener.
  - **DONE 2026-07-16, general rule (not a one-off patch)**: default cue
    points now snap forward to the nearest actual lyric-line start whenever
    synced lyrics exist, instead of trusting the beatgrid/energy
    phrase-picker blindly. Caught live on an R&B mix's opener: Cassie —
    Me&U's default "body" cue landed at 48.21s, mid-word in "...wanna see
    if it's true" (line runs 44.26–49.00s) — the phrase-picker has zero
    lyric awareness, it just finds a high-energy beatgrid phrase. Added
    `load_lyric_line_lookup()` (reads every track's raw synced LRC from
    `lyric_timelines`, once per build) and `snap_to_lyric_line()` in
    `brain/build_mix_plan.py`: nudges a raw cue point forward (never
    backward — that would replay content the energy target already meant
    to skip past) to the next line start, within a 6s cap (gives up and
    keeps the original point if the nearest line is further than that —
    likely an instrumental stretch, where forcing a snap would drift too
    far from the intended entry). Applies to both the phrase-based
    `body`/`intro` picks and the `fraction_fallback` path (converts the
    fraction to seconds via `duration_seconds` first). Explicit dj_notes
    overrides (`cue_seconds`, `entry_style=verse_landing`) are untouched —
    a human already chose those deliberately. `cue_source` gets a
    `+lyric_snap` suffix whenever it fires, so it's visible in the plan
    JSON which cues were adjusted. Verified live: Cassie's cue moved from
    48.2053s to exactly 49.0s ("They know you're the one I wanna give it
    to"). 6 new tests in `tests/test_mix_plan.py`.
  - **DONE 2026-07-16, new opener_style: `juggle_brake_intro`**. Even
    landing cleanly on a word boundary, starting the opener anywhere but
    the true beginning has no context to arrive into — Ernest's actual
    ask, for Cassie — Me&U as opener: start from true zero, juggle against
    a second copy over the instrumental intro (before the first sung line
    at 0:19.6 — just ad-lib samples over the beat), then an abrupt
    vinyl-brake stop, rewind, and replay the cue as a false-start tease
    before actually letting the song ride. New
    `hands.run_mix_plan.perform_juggle_brake_intro`: reuses
    `perform_juggle_intro`'s beat-anchored crossfader chop against a
    second copy, then calls the `brake` Rust gesture (falls back to a
    manual volume-fade + stop if the clawdj binary is missing — same
    degrade-gracefully pattern as everywhere else), rewinds `playposition`
    back to the original cue. Dispatched from `perform_opener_effect()`
    alongside the existing two styles; wired into `track_directives()`'s
    `opener_style` vocabulary (no build-side code change needed — the
    existing juggle-clobbers-deck-2 reload logic already applies to any
    `opener_style`, not just `juggle_intro` specifically).
    Two follow-up refinements from listening to it live:
    - Originally left the deck paused/"armed" (play=0) for the plan's
      *next* `start` event to resume, matching `echo_tease_drop`'s
      contract — but that event fires after a `load` (reloading deck 2
      with the real second track), which takes real wall-clock time and
      left a dead silent gap before the replay. Now resumes playback
      immediately inside the same function instead of waiting on a later
      event. The cue point is already beat-aligned (dj_notes `cue_seconds`
      or the lyric-snapped default), so resuming the instant the rewind
      lands is already "on the beat" — no separate beat-wait needed (and
      none is available anyway: `wait_for_next_beat` needs the deck
      already playing to detect beat edges, so it can't be used on a
      stopped one).
    - The brake itself defaulted to 1.4s (tuned for `perform_transition`'s
      brake_out, a mid-mix hand-off with room to breathe) — too long for a
      tease-and-replay. New `brake_seconds` event field, default lowered
      to 0.7s, for a snappier stop with less gap before Me&U resumes;
      `perform_transition`'s own brake_out is untouched (still 1.4s,
      already validated and liked on Murder Was The Case).
    2 tests in `tests/test_mix_runner.py` (updated in place as the
    behavior was refined, not duplicated).
  - **DONE 2026-07-16: Ctrl-C during a live `hands.run_mix_plan` run left
    Mixxx's decks actually still playing** (Ctrl-C only kills the Python
    orchestrator — Mixxx is a separate process, oblivious that anything
    happened) and printed a raw `KeyboardInterrupt` traceback. `run_plan()`
    now catches it around `_run_events()`, stops both decks explicitly,
    and exits cleanly instead of unwinding as a traceback. 1 new test in
    `tests/test_mix_runner.py` (mocks `MixxxControl` + a `_run_events`
    that raises, asserts both decks get `play=0`). Recording-stop-on-exit
    behavior is unaffected — it's still in the surrounding `finally`.
  - **DONE 2026-07-16: `play_bpm` had zero effect on the opener track —
    real bug, not a data problem.** It only ever applied via
    `pick_technique`'s `incoming_bpm_target`, which fires on a transition
    *into* a track. The opener (track 0) is loaded and started directly,
    no incoming transition — so a `play_bpm` directive on it silently did
    nothing. `build_plan()` now threads `play_bpm` onto the `start` event
    as `bpm_target` when set; the runner's `start` handler applies
    `set_bpm_target()` *before* `play=1` (no audible jump after the track
    is already playing). 4 new tests (2 in `test_mix_plan.py` for the
    event field, 2 in `test_mix_runner.py` for runner behavior + the
    unaffected non-opener path).
  - **DONE 2026-07-16, R&B mix tuning**: Cassie — Me&U's default ride
    (63 beats) ended at ~37.8s — right at the start of her first chorus
    (37.18s), meaning the transition into Wall to Wall began before any of
    the chorus actually played. Extended to 128 beats (exit ~77s, the
    chorus/hook block's actual end, grounded in the real synced lyrics)
    and bumped `play_bpm=103.0` (using the fix above) since it's the
    opener — room for a bit more energy. Separately: Aaliyah — Rock The
    Boat moved from 3rd to 5th (now follows Keni Burke — Risin' To The
    Top, 94.0↔93.0bpm, a near-perfect match), and Chris Brown — Wall to
    Wall's follow-up became George Michael — Fastlove (103.6bpm) instead
    of Jane Child — Don't Wanna Fall in Love (111.6bpm) — Jane Child's gap
    from Wall to Wall's 94bpm scored 0.15 ("bpm far") and produced a
    `half_time_or_cut` hard cut, the opposite of the "blend" that was
    asked for; checked `bpm_compatibility()` against every remaining track
    before picking Fastlove (0.65, "stretchy but possible", resolves to
    `standard_blend`). Jane Child relocated to sit between Janet Jackson —
    Escapade and — All for You instead (111.6bpm nestles almost exactly
    between 115.2 and 113.5 — both score 0.90+), so nothing lost a good
    neighbor by freeing up Wall to Wall's slot.
  - **DONE 2026-07-16, follow-up round on the same mix**:
    - **Reverted Cassie's `play_bpm=103.0`** — it bled into Chris Brown —
      Wall to Wall's actual playback tempo even though Wall to Wall has no
      `play_bpm` of its own. Root cause: the transition's technique
      (`key_adjusted_blend`) includes a `sync` move, and Mixxx's
      `beatsync` resyncs the *incoming* deck to whatever the *outgoing*
      deck is really playing at — which was Cassie's bumped 103bpm, not
      her native 100. A real, generalizable gotcha: any `play_bpm` bump on
      an outgoing track can bleed into the next track via `sync`, not just
      via an explicit `incoming_bpm_target`. Cassie's ride length
      (128 beats) and everything else about the opener stayed as-is —
      only the tempo bump was wrong.
    - Reordered again: Wall to Wall → Keni Burke directly (94.0↔94.0,
      exact match — "blend Keni Burke into Wall to Wall"), moved Fastlove
      out from between them to sit between Janet Jackson — Love Will
      Never Do (103.2, near-perfect 1.004 ratio) and — Escapade (115.2,
      workable 0.65) instead.
    - Aaliyah — Rock The Boat: `entry_style=verse_landing`,
      `landing_seconds=20.24` (her actual first verse line, "Boy, you know
      you make me float"), `landing_beats=28` — a long ~18s blend that
      skips only ~2s of the intro (it's iconic, wanted to preserve almost
      all of it) while still landing cleanly at the verse start rather
      than cutting into it.
    - **New profile keyword: `apply_brief()` now maps "no hard cut" /
      "avoid hard cut" / "hard cuts sparingly" / "keep it blending" /
      etc. to `avoid_silence=True`** (previously only settable by picking
      `club-set`/`mix-to-listen` outright, no way to ask for it on
      `dj-showcase` via brief). Rebuilt this mix with
      `--mix-brief "use hard cuts sparingly, avoid abrupt endings, keep
      it blending"` (no `--order-engine`, so it only changed profile
      knobs, not track order) — all 4 `half_time_or_cut` hard cuts in
      this 18-track set (all involving the Sade — Smooth Operator /
      George Michael — Amazing tempo outliers) downgraded to
      `tempo_gap_blend`. 2 new tests in `tests/test_mix_plan.py`.
  - **DONE 2026-07-16, third round on the same mix**:
    - **Janet Jackson — Love Will Never Do (Without You)** was getting
      pulled DOWN toward the slower outgoing deck's tempo (Al B. Sure! —
      Nite And Day Dawn Mix, 91.3bpm) — the same beatsync bleed-through
      as the Cassie/Wall to Wall case, just in the opposite direction.
      Fix reuses the *other* side of that same mechanism deliberately:
      set `play_bpm` to this track's own native/analyzed bpm
      (103.17676126325088, not a bump — just re-asserting its own native
      value) so `incoming_bpm_target` is set and `sync`/`beatsync` gets
      skipped entirely (per the fix two rounds back), holding it at its
      real tempo through the transition instead of being silently synced
      down. Also `cue_seconds=0.34; ride_beats=64` to protect the actual
      first verse (0:00.34–0:36.8, grounded in synced lyrics) instead of
      whatever the phrase-picker's default landed on.
    - Closer **Janet Jackson — That's the Way Love Goes**: `full_track`,
      same pattern as `Who Am I` on the G-funk mix — plays out completely.
  - **DONE 2026-07-16, fourth round**: **Chris Brown — Run It!** inserted
    into the finalized 19-track playlist between Wall to Wall and Keni
    Burke — Risin' to the Top, replacing Rise to the Top as the direct
    follow-up (Run It! stays in the set too). Live-analyzed via Mixxx
    control API (bpm=103.18, key=Ab), lyrics/timeline/chroma fetched,
    `entry_style=verse_landing` landing on the chorus per Ernest's ask
    ("just the chorus of it").
  - **DONE 2026-07-16, fifth round**: live-run crash fix —
    `hands/run_mix_plan.py`'s `load_deck()` bpm "identity barrier" wait
    (`bpm > 0` and close to the plan's expected bpm) threw a raw
    `TimeoutError` and crashed the whole live set when preloading Run
    It! onto deck 1, most likely because Run It!'s Mixxx-side analysis
    cache hadn't fully settled yet (matches the previously-observed "no
    Mixxx beatgrid yet" lag for this same newly-added track). Wrapped
    the wait in `try/except TimeoutError`: falls back to whatever bpm
    Mixxx currently reports (or the plan's expected bpm if Mixxx still
    reports 0), prints a loud warning, and keeps the set running instead
    of crashing on one track's slow/flaky analysis. New regression test
    `LoadDeckBpmTimeoutTests` in `tests/test_mix_runner.py`.
  - **DONE 2026-07-16, sixth round — reorder + beat-phase alignment**:
    - Diagnosed "Cassie into Wall to Wall doesn't match vibe" as a real
      **key clash, not a tempo problem**: G#m→Gm is a semitone apart
      (Camelot 1A→6A, ~5 steps — about as far as two keys get). Searched
      the whole 19-track pool for the best Camelot-adjacent match to
      Cassie's 1A: only **Al B. Sure! — Nite And Day (Single Edit)**
      (Ebm/2A) qualifies. Moved it from position 18 (near the end) to
      position 2, right after the opener, at its **own native tempo**
      (91.317bpm, explicitly not bumped, per Ernest — a different, third
      copy of the same song from the 1988 album also exists but wasn't
      used since it's essentially a duplicate performance, not a
      meaningfully different track).
    - First attempt inserted Sade — Sweetest Taboo as a bridge between the
      Single Edit and Wall to Wall (also real Camelot-adjacent, 3A). Ernest
      called this out as not fitting either side — reverted: Sweetest
      Taboo restored to its original, already-validated Sade-cluster slot
      (Amazing→Smooth Operator→Sweetest Taboo→Hang On To Your Love→
      Paradise, exactly as tuned in the third round), Single Edit now
      blends directly into Wall to Wall (2A→6A, a minor-third jump —
      workable, nowhere near as bad as the semitone clash that started
      this).
    - **Nite And Day (Single Edit)**: was cold-opening on the spoken intro
      ("Can you feel it, baby?"). Per Ernest: skip that, enter once the
      beat/second chorus pass kicks in (0:40.0, verified against the
      synced lyric timeline), ride most of that second chorus pass, exit
      right as the second verse begins (0:58.2). `cue_seconds=40.0;
      ride_beats=28`.
    - **Beat-phase ("snare match") fixes — Wall to Wall→Run It! and Keni
      Burke→Rock The Boat**: Mixxx's `beatsync` phase-locks to whatever
      beat the outgoing deck is *currently on*, which one of the 4
      beats-in-a-bar that is (kick vs. backbeat/snare position) is a
      deterministic function of `cue_beat_index + elapsed ride beats`.
      Made both transitions land beat-for-beat on a **bar boundary**
      (multiple of 4) from each track's own bar-aligned entry cue, so the
      sync anchor always lands on the same kind of beat the vocal/hook
      entered on, not an arbitrary offset:
      - Wall to Wall: `cue_seconds=61.97` (verse 2 start, `cue_beat_index`
        96 — a clean bar multiple), extended `ride_beats` 43→**128**
        (96+128=224, ÷4 exact) so it also finishes the third verse after
        the chorus per Ernest's ask, instead of cutting off mid-chorus.
      - Keni Burke — Risin' To The Top: shortened per Ernest ("don't have
        to play it so long") *and* re-anchored — lands right on the hook
        (`cue_seconds=102.36`) instead of mid-verse, rides just that one
        chorus, exits right as verse 2 begins. `ride_beats=36` (a multiple
        of 4 from its own bar-aligned entry).
      - This makes task #27 (Wall to Wall→Keni Burke transition quality)
        moot — Run It! now sits directly between them, so that pairing no
        longer exists.
    - **Rock The Boat → Amazing "too rushed, sounds forced"**: root cause
      was Amazing's existing `play_bpm=128.4` (native-tempo hold) forcing
      it to its full tempo *immediately* at the start of the crossfade,
      while Aaliyah (93bpm) was still playing alongside it — a 38% tempo
      jump audible for the whole ~15s overlap. Removed the `play_bpm`
      override: with none set, `perform_transition`'s plain `sync` locks
      Amazing to Rock The Boat's live ~93bpm *for the overlap itself*,
      then `hands.run_mix_plan.settle_rate` glides it back up to its own
      native 128.4bpm right after the handoff completes (a mechanism that
      already existed in the runner, previously unused here) — gentle
      match during the blend, full energy once it's the only thing
      playing.
    - 97/97 tests still passing; verified via a full dry-run rebuild that
      every cue/ride number above landed exactly as intended (not just in
      dj_notes text — the actual generated `mix_plan.json` events).
  - **DONE 2026-07-16, seventh round**: Ernest confirmed Single Edit → Wall
    to Wall as the right pairing and asked to "take our time" matching the
    beat — extended the transition from 20 to **48 beats** (~30.6s) via
    `entry_style=verse_landing`, landing right at Wall to Wall's verse-2
    start (0:61.97). Also removed the `play_bpm=94.0` hold that had been
    added alongside it: with an explicit `landing_seconds`/`entry_style`
    already pinning the cue, a play_bpm hold would have blocked the
    runner's real `sync`/beatsync from ever firing (same silent-skip
    mechanism documented all session) — the opposite of "match the beat."
    No override now: real beatsync locks phase+tempo to Single Edit's live
    ~91.3bpm for the whole 48-beat overlap, then `settle_rate` glides Wall
    to Wall back up to its own native 94bpm right after (a small, gentle
    ~3% nudge, not a jump — same mechanism as the Amazing fix above).
    Confirmed via the actual plan JSON: `incoming_bpm_target: null`,
    `transition_beats: 48`. 97/97 tests still pass.
    Also, per Ernest: Rock The Boat → Amazing still isn't the right pair
    (not a tempo/phase issue — a vibe/style mismatch, "especially
    transitioning into it with the start of the song"). Searched the wider
    library for a genuine replacement (not a duplicate copy of a song
    already in the set); no single best answer — presented Ernest 2-3 real
    candidates with tradeoffs (Usher — Yeah!, near-perfect bpm/key but a
    different production era; Marvin Gaye — "T" Plays It Cool, more
    stylistically at home but an older-school groove; Janet Jackson —
    Rhythm Nation, same key, bigger tempo jump) — awaiting his call.
  - **DONE 2026-07-16, eighth round**: two live-tested corrections plus a
    genuine new addition.
    - **Single Edit → Wall to Wall "sounds terrible" after the 48-beat
      pre-roll experiment** — reverted. Root cause (best guess, two
      compounding issues): (1) `beatsync` is a one-shot phase snap, not a
      continuous lock — over a ~30s overlap with a real ~3% tempo gap the
      decks drift audibly by the end; (2) the pre-roll started so early
      (mid-verse-1) that a whole extra chorus played out quietly
      underneath Nite And Day before "landing" — a vocal pile-up, not a
      clean reveal. Fixed by going back to a direct load at the verse-2
      landing point (no early pre-roll) + a full `play_bpm=94.0` native-
      tempo hold (no drift risk regardless of overlap length) +
      `entry_style=gentle_blend` for a modest 24-beat overlap (up from the
      original 20, nowhere near the 48 that caused the pile-up).
    - **Wall to Wall's ride "still too long"** — trimmed `ride_beats` 128→
      **112** (drops the last two lines of the third verse), still lands
      beat-for-beat on a bar boundary from the verse-2 cue (96+112=208, a
      multiple of 4) so the beat-phase fix from the sixth round still
      holds. Run It! now enters noticeably earlier.
    - **Rock The Boat → Amazing, take 2**: none of the three round-seven
      candidates fit — Ernest asked to stay in Aaliyah's own catalog
      instead. Picked **Aaliyah — Try Again** (from the same album folder
      as Rock The Boat, `.../Aaliya (Bonus Tracks)/15. Try Again.mp3`),
      live-analyzed via Mixxx control API: **93.019bpm, Dbm** — essentially
      identical native tempo to Rock The Boat's 92.983bpm (the closest bpm
      match anywhere in this set), even though the raw key is a Camelot
      outlier from Rock The Boat's Bb major. Fetched lyrics + built its
      lyric timeline fresh (was previously unanalyzed); lands on the real
      first verse ('Baby girl, oh...', 0:20.85) after skipping just the
      opening hook, rides verse+chorus, hands off to Amazing at 1:02.74.
      Amazing's existing gentle-blend/settle_rate fix (round 6) is
      artist-agnostic and needed no logic changes, just a text update.
      Set is now **20 tracks**. 97/97 tests pass; verified via a full
      dry-run rebuild.
  - **DONE 2026-07-16, ninth round**: fixed a real directive-parsing bug,
    trimmed two more rides, and built real onset/transient waveform
    analysis — a genuinely new capability, not a directive tweak.
    - **Directive-parsing bug**: `track_directives()`'s regex takes the
      *first* `key=value` match in the whole dj_notes text. Wall to
      Wall's note had mentioned its own history ("first ride_beats=128,
      then ride_beats=112...") in prose *before* the real final directive
      — the parser silently picked up the stale 128 instead of the
      intended new value. Fixed by rewriting the note to describe history
      without embedding old numeric directives in it. Audited every other
      track's dj_notes for the same pattern (none affected) and added a
      one-off audit script (not checked in) — worth remembering as a
      general rule when editing dj_notes: never repeat an old `key=value`
      pair as prose in the same note.
    - **Cassie's ride** shortened 128→**92 beats** — Ernest wants the
      blend into Nite And Day (Single Edit) to start earlier, right at the
      middle of the first chorus (0:56.23, a real lyric line) instead of
      at its end.
    - **Wall to Wall's ride** shortened again, 112→**96 beats** — still
      too much Wall to Wall on the third try; now ends right at chorus
      2's natural boundary, no third-verse tail at all.
    - **New capability: `brain/onset_analysis.py`** (+ new `librosa`/
      `scipy`/`soundfile` deps). Ernest pushed back hard on the "keep
      `cue_beat_index + ride_beats` a multiple of 4" bar-alignment fix
      from the sixth round — rightly: that was pure arithmetic, never
      verified against actual audio, and the repeated "2nd/4th beat isn't
      matching" complaints (Single Edit→Wall to Wall, Run It!→Keni Burke,
      Keni Burke→Rock The Boat) kept surviving it. Built real high-passed
      onset-strength detection (`snare_band_onset_envelope`,
      `beat_phase_energies`) that estimates which beat-in-bar carries a
      track's snare/backbeat from the actual waveform — validated against
      a synthetic click-track with a known kick/snare pattern in
      `tests/test_onset_analysis.py` (the detector correctly recovers the
      injected snare slot; not just a plausibility check).
    - **Real finding, not a guess**: ran it on the actual library files.
      Run It! (bpm 101, live Mixxx beatgrid), Keni Burke, and Rock The
      Boat all show consistent high snare-band energy on **odd** beat
      slots (1 & 3, 0-indexed) relative to their own Mixxx-analyzed
      first-beat — a normal, textbook backbeat pattern. **Wall to Wall is
      the outlier**: highest energy on **even** slots (0 & 2) — its own
      Mixxx-analyzed beatgrid is very likely phase-shifted by one full
      beat from the convention its neighbors use, meaning Mixxx's
      beatsync (which locks generic beat-tick to beat-tick, blind to
      kick/snare identity) would always land a Wall to Wall kick on a
      neighbor's snare and vice versa — a real, structural cause for "the
      beats don't match," independent of any cue_seconds/ride_beats
      choice, since the flaw lives in the beatgrid itself, not in
      directive-level timing.
    - **First attempt at a fix was based on a wrong premise, self-corrected
      before causing real harm**: tried firing `beats_translate_earlier`
      once on Wall to Wall's deck, thinking it would shift the whole grid
      by one beat. Checked the actual persisted result afterward:
      `first_beat_seconds` moved by only ~0.005s, nowhere near one beat
      period (~0.638s at 94bpm) — realized the mistake before drawing any
      false conclusion from it. The real insight: Mixxx's beatgrid is just
      an infinite series of evenly-spaced clicks anchored at
      `first_beat_seconds` — as a *set of timestamps* it's invariant under
      a shift of any whole multiple of its own period, so "translate by
      one beat" is a structural no-op on the grid itself, not a fix.
      `first_beat_seconds` is just whichever specific click Mixxx's
      detector happened to lock onto first — arbitrary per track, not a
      universal "beat 0 = kick" anchor. So there's nothing wrong with Wall
      to Wall's *grid* to repair at the Mixxx level; the fix has to live
      in **our own cue-point arithmetic**: compute each track's own
      measured `snare_beat_offset` (already what `detect_snare_phase`
      returns) and account for it when choosing `cue_seconds`/`ride_beats`
      for a transition, so the actual audio transients land together —
      not by editing Mixxx's analysis data. **Not yet wired into
      `build_mix_plan.py`** — `phase_shift_beats()` exists and is tested,
      but nothing in the plan builder calls it yet. Next concrete step if
      Ernest wants to continue this thread.
    - **Open question, not yet resolved**: Run It!, Keni Burke, and Rock
      The Boat all *already* agree with each other on odd-slot backbeat
      phase, per this same tool — meaning the Run It!→Keni Burke and Keni
      Burke→Rock The Boat mismatch complaints are **not** explained by a
      grid-shift bug the way Wall to Wall's was. Both those pairs'
      detector confidence was also low (0.168 and 0.019/0.034 — noisy
      signal, single 90-120s window analyzed). Needs more investigation:
      either the directive-level cue_beat_index math for those specific
      transitions doesn't actually preserve parity in practice the way
      the mod-4 arithmetic assumed, or the detector itself needs tuning
      (window size / highpass cutoff / longer analysis window) before its
      verdict on this specific pair can be trusted.
    - Also, per Ernest ("I really like that... great suggestion"): the
      same-artist-bridge approach (Try Again) is strongly preferred over
      cross-artist bpm/key-scored picks — saved as
      `feedback-clawdj-same-artist-bridge` in the auto-memory system.
      Live-analyzed a second same-catalog candidate for Try Again's own
      follow-up (replacing Amazing, whose forced-feeling tempo bridge
      Ernest flagged again despite the settle_rate fix): **Aaliyah — Are
      You That Somebody**, 94.0bpm/Gm — near-perfect bpm match to Try
      Again's 93.02bpm but a real Camelot-outlier key (same distance
      class as Wall to Wall/Cassie's clash, though a third apart in pitch
      rather than a semitone). Presented alongside the earlier **Alicia
      Keys — No One** candidate (90bpm/E major, a genuine Camelot-adjacent
      key match, cross-artist) — awaiting Ernest's call between
      same-artist/weaker-key vs. cross-artist/stronger-key.
    - 102/102 tests pass (97 previous + 5 new onset-analysis tests).
  - **DONE 2026-07-16, tenth round**: Ernest decided not to keep chasing a
    third same-artist option for Try Again's follow-up ("that's enough
    that we have those 2 songs from Aaliyah") and asked to try **Toni
    Braxton — He Wasn't Man Enough** instead, bumped faster. Swapped Toni
    Braxton and George Michael — Amazing's positions in the set (a clean
    two-track swap, no other reordering):
    - **Try Again → Toni Braxton**: bpm 93.02 vs Toni Braxton's native 88
      was already workable (0.9 score) without any bump, but per Ernest's
      ask bumped `play_bpm` 88.0→**93.0** anyway — more energy for its new,
      earlier position in the set (previously it sat right before the
      closer, a wind-down slot; now it's mid-set). Key clash (Dbm↔C)
      confirmed real and not cheaply pitch-bridgeable
      (`pitch_adjust_for_blend` found no candidate within ±2 semitones) —
      same tradeoff as the Try Again/Rock The Boat pairing, accepted the
      same way.
    - **Toni Braxton → Smooth Operator**: Smooth Operator's dj_notes had
      `play_bpm=128.4` baked in specifically to match its *old* predecessor
      (Amazing, a close native match) — holding that same native tempo
      against Toni Braxton's new ~93bpm would reproduce the exact "forced"
      jump Ernest already flagged twice. Removed the hold; reuses the same
      gentle-sync-then-`settle_rate` pattern as the Amazing fix.
    - **Amazing relocated** to All For You → Amazing → Closer (Toni
      Braxton's old slot). Its own gentle-blend/settle_rate entry note was
      already predecessor-agnostic — no logic change, just a text update
      naming its new neighbor. Amazing → Closer is a big native gap
      (128.4→97.7bpm) but the profile's `avoid_silence` brief already
      downgrades it to `tempo_gap_blend` rather than a hard cut, which
      looked reasonable in the rebuilt plan without further tuning.
    - Verified via a full plan rebuild + dry run (64 events, resolves
      end-to-end) and the actual transition JSON: Try Again→Toni Braxton
      `incoming_bpm_target: 93.0`; Toni Braxton→Smooth Operator and All For
      You→Amazing both `incoming_bpm_target: None` (real sync engaged, as
      intended). 102/102 tests still pass.
  - **DONE 2026-07-17, eleventh round**: pushed further on the onset-
    analysis thread per Ernest's "keep pushing." Real progress, one more
    real bug found, one root-cause theory investigated and refuted.
    - **Refactored `onset_analysis.py`'s core model**: the original 4-slot
      "which single beat wins" design gave very low, noisy confidence
      (0.02-0.17) for Keni Burke and Rock The Boat. Root cause: a standard
      backbeat puts the snare on *every other* beat (musically "2 and 4"),
      so two of the four slots legitimately tie for the top spot — ranking
      them as 4 competing options was the wrong model. Switched to
      **odd/even beat PARITY** (mod 2) as the primary signal — same raw
      energy data, much cleaner confidence (0.23-0.51) once aggregated the
      physically correct way. Added a synthetic test
      (`test_kick_on_backbeat_flips_parity_to_even`) that swaps which
      beats carry the noise burst and confirms the detector follows the
      actual audio rather than defaulting to a guess.
    - **Investigated and refuted a settle_rate-drift theory**: wondered
      whether `settle_rate`'s post-transition tempo glide (matching-tempo
      → native) might itself break phase alignment during the glide.
      Traced the actual code path: `settle_rate` only runs *after* the
      outgoing deck has already stopped (`perform_transition` stops it
      before returning), so there's nothing else playing to be out of
      phase with by the time the glide happens — not the explanation.
    - **Applied the parity math to the real, current transitions** using
      each track's actual cue/ride directives (not assumed defaults):
      - Run It! → Keni Burke: **already aligned** (`phase_shift_beats`
        returns 0) — confirms this pairing was never a phase-parity bug in
        the first place.
      - **Keni Burke → Rock The Boat: a real, confirmed 1-beat parity
        mismatch** (`phase_shift_beats` returned 1) — the first concrete,
        data-grounded fix beyond the earlier Wall to Wall finding. Fixed
        by changing Rock The Boat's `landing_beats` 28→27: since
        `cue_seconds = landing_seconds - landing_beats*60/bpm`, shifting
        `landing_beats` by exactly 1 shifts the pre-roll's start by
        exactly one beat (flips parity) without moving the actual verse-
        landing target (still lands at 0:20.24) at all. Verified with the
        real numbers: new cue beat_index 4 (was 3) against Keni Burke's
        exit anchor 196 → `phase_shift_beats` now returns 0.
      - Run It! → Keni Burke's already-good alignment plus this one real
        fix account for 2 of the 3 originally-flagged pairs. Single
        Edit → Wall to Wall wasn't re-checked with the parity model this
        round (Wall to Wall's own grid is the confirmed outlier there,
        from the tenth-round finding).
    - **Hit the exact same stale-prose-directive bug a second time** (Rock
      The Boat's note said "the previous landing_beats=28..." before the
      real `landing_beats=27` directive — the regex grabbed the stale 28
      again). This time fixed the **root cause in the parser itself**
      rather than relying on care when writing notes:
      `track_directives()`'s `number()`/`word()` helpers now take the
      **last** regex match in the text instead of the first, since the
      real directive is always the one placed at the end by convention.
      New regression test
      `test_dj_notes_last_directive_wins_over_stale_prose_mentions` in
      `tests/test_mix_plan.py` reproduces the exact failure pattern from
      both incidents.
    - 104/104 tests pass (102 previous + 1 onset-analysis parity test + 1
      parser regression test). Verified via full rebuild + dry run that
      Rock The Boat's corrected cue lands exactly as computed.
    - **Not done yet** (all three items below are now DONE — see the
      twelfth round): full sweep of the rest of the set, wiring
      `phase_shift_beats()` into the actual build loop.
  - **DONE 2026-07-17, twelfth round**: finished both open items from the
    eleventh round, plus fixed the Sade cluster ("the group isn't working").
    - **Full 18-track parity sweep**: analyzed every remaining track (real
      onset detection, not guesses) and checked every actual transition in
      the finalized set using real plan-generated cue points. Found and
      fixed 4 more real mismatches beyond the two already caught: Cassie→
      Single Edit, Dawn Mix→Love Will Never Do, All For You→Amazing, and
      (after the Sade restructure below) Paradise→Sweetest Taboo. Each
      fixed the same way — nudge whichever side's `ride_beats` isn't
      already a hard lyric-locked cue by exactly ±1 beat, verified with
      the real numbers each time (not just "should work"). **All 16
      transitions in the finalized set now confirm `shift=0`.**
    - **Hit the exact same stale-prose-directive bug a THIRD time** while
      writing Rock The Boat's note in the previous round (already fixed in
      the parser) — no new occurrence this round since the parser fix
      from round eleven caught it silently; worth noting the fix is
      holding up.
    - **Sade cluster rebuilt from data, not just genre-typical wind-down
      hoping**: Ernest said "the group of Sade songs isn't working."
      Computed pairwise bpm/key compatibility across all 4 Sade tracks plus
      both neighbors (Toni Braxton in, Al B. Sure! Dawn Mix out). Smooth
      Operator + Hang On To Your Love pair beautifully with EACH OTHER
      (0.825, same key) but both score terribly with the surrounding mix
      (0.15-0.35 in and out) — a "great couple, wrong party" problem.
      **Paradise + Sweetest Taboo** flow much better with their neighbors
      even though they're a slightly looser pair with each other, and
      Sweetest Taboo → Dawn Mix is the single best-scoring transition
      anywhere in this stretch (0.975 — near-identical bpm, relative
      major/minor key). Cut Smooth Operator and Hang On To Your Love from
      the set entirely (18 tracks now, was 20) rather than relocating them
      — no other slot in an already-tuned 90-115bpm-centered mix fits a
      120bpm/108bpm Dm-key outlier pair. Flagging honestly: this drops
      Sade's most iconic single ("Smooth Operator" itself) for the sake of
      flow — a real tradeoff, not a free win, and reversible if Ernest
      wants the iconic-value tradeoff back.
    - Paradise (Extended Mix) has **no synced lyrics at all** in LRCLIB
      (confirmed: 0 lines) — used the phrase-picker's own energy-based
      body cue instead of a lyric-grounded one, the first track in the
      whole set without a word-boundary-aware entry.
    - **Wired `phase_shift_beats()` into `build_mix_plan.py` for real**,
      not just a standalone tool run by hand:
      - New `beat_phase` SQLite table (track_id, snare_parity, confidence,
        bpm, first_beat_seconds) + `brain.enrich_set.fill_beat_phase()` to
        populate it (depends on `phrases` already being filled, same as
        the rest of the enrichment pipeline). Populated for all 18 tracks
        in the current set.
      - `build_mix_plan.py` gained `load_beat_phase_lookup()` (same
        graceful-degradation pattern as `phrase_lookup`/
        `lyric_line_lookup` — missing data just skips the check, never
        errors) and a `cue_beat_index_cache` that `cue_fields()` populates
        every time it resolves an absolute `cue_seconds`, so each track's
        own entry beat_index is available later when it becomes the
        OUTGOING side of the next transition.
      - `build_plan()`'s main loop now runs the phase-parity check
        automatically right after `ride_beats` is finalized for every
        transition, nudging by the computed shift and printing a visible
        `[beat-phase]` message when it fires. Confirmed working with two
        new tests (`test_beat_phase_mismatch_auto_corrects_ride_beats`,
        `test_beat_phase_match_leaves_ride_beats_untouched`) using
        synthetic tracks with a deliberately engineered mismatch/match —
        not just "no warnings appeared" (which could also mean the wiring
        silently isn't running).
      - Rebuilt the real 18-track plan after wiring this in: zero
        `[beat-phase]` messages fired, confirming the manual fixes above
        already left the set in a state the automated check agrees with.
    - 106/106 tests pass (104 previous + 2 new build_plan integration
      tests). Full dry-run rebuild resolves end-to-end (58 events).
  - **DONE 2026-07-17, thirteenth round**: Ernest, understandably
    frustrated, pointed out Wall to Wall's ride was still too long after
    THREE rounds of incremental trims (128→112→96/97) that each still left
    most or all of the chorus hook playing. This time a decisive cut, not
    another small one:
    - **Wall to Wall**: ride_beats 97→**49** (roughly HALVED, not trimmed)
      — rides verse 2 and just ONE pass of the chorus hook ("They packed
      up in here wall to wall and..."), landing right as the hook repeats
      a second time instead of letting it cycle 2-3 more times. Kept the
      new value odd (49, like the previous 97) specifically to preserve
      the confirmed beat-phase parity fix with Run It!'s entry from the
      eleventh round — verified the arithmetic still holds (96+49=145,
      still odd).
    - **Jane Child — Don't Wanna Fall in Love**: was getting cut brutally
      short (39 beats / ~21s from a true-intro entry at 0:00.36 — never
      even reached the chorus). No synced lyrics exist for this track
      (LRCLIB has plain text only, no timestamps) — grounded the fix in
      the plain lyrics text (found the actual chorus wording) plus the
      phrase-picker's own energy data (its highest-scored "body" moment,
      0.842 energy, at 1:26.41 — almost certainly the chorus) rather than
      exact word-boundary timing. ride_beats 39→**185**, extending well
      past that point instead of stopping during the first verse.
    - **Amazing → closer (That's the Way Love Goes)**: flagged as an
      abrupt break — a real 24% tempo drop (128.4→97.7bpm) that the
      default `tempo_gap_blend` was only softening with a mild 20-beat
      rate-nudge, not a real sync. Added `entry_style=gentle_blend` to the
      closer's own note (same established pattern as Amazing's own entry
      and Toni Braxton→Smooth Operator): forces a longer, fully SYNCED
      24-beat overlap — real sync locks the closer to Amazing's live
      ~128bpm during the blend, then `settle_rate` glides it back down to
      its own native 97.67bpm right after the handoff. Confirmed via the
      real plan JSON: `incoming_bpm_target: None`, `transition_beats: 24`
      (was 20).
    - All three verified against the actual rebuilt plan.json values (not
      just dj_notes text). 106/106 tests still pass; full dry-run
      resolves end-to-end (58 events).
  - **DONE 2026-07-17, fourteenth round**: Ernest asked why beat-matching
    was noticeably better on the West Coast G-funk mix and whether
    something used there wasn't being used here — a real, useful diagnostic
    question, answered with actual data rather than a guess.
    - **Root cause, found by comparing the two mixes' actual dj_notes**:
      the West Coast set (29 tracks) uses `play_bpm` on exactly **1**
      track (a deliberate energy bump, not a fix) and reserves
      `entry_style=beat_drop` (hard brake, drop clean, no bridging) for
      its one genuine unfixable outlier (Murder Was The Case). This R&B
      set has `play_bpm` on **9 of 18 tracks** — half the set. The catch:
      `hands/run_mix_plan.py`'s `perform_transition()` explicitly skips
      ordinary `sync`/beatsync whenever `incoming_bpm_target` (from
      `play_bpm`) is set, to protect the deliberate tempo hold from being
      silently overwritten (the Tha Shiznit bug from earlier). The
      side effect: tempo ends up numerically correct on those 9
      transitions, but the incoming deck's *phase* (kick-to-kick,
      downbeat-to-downbeat alignment) never actually gets locked at all —
      a real, previously-unnoticed cost of the play_bpm fix pattern used
      so heavily to solve the bleed-through bug this whole session.
    - **Fix: `beatsync_phase`** — a real Mixxx control that snaps phase
      *without* touching tempo (documented in
      `docs/MIXXX_CONTROL_SURFACE.md`, previously unused in this project).
      `perform_transition()` now fires it whenever a `play_bpm` hold
      blocks ordinary sync, so those 9 transitions get both a correct,
      deliberate tempo AND real phase-lock instead of tempo-accuracy
      traded away for phase-lock. Two new tests in
      `tests/test_mix_runner.py` confirm it fires exactly when expected
      (with a `play_bpm` hold) and not otherwise (plain sync case,
      `half_time_or_cut` case).
    - **Corrected a fix from the previous round**: Ernest clarified the
      closer's entry from Amazing should NOT be bridged/synced toward
      128bpm at all — he wants a hard break (brake the outgoing deck,
      drop the closer in clean at its own native 97.67bpm), the same
      `entry_style=beat_drop` pattern as Murder Was The Case. Reverted the
      `entry_style=gentle_blend` added last round; confirmed via the real
      plan JSON that no `incoming_bpm_target`/sync is attempted at all
      now (`technique: beat_drop_entry`, moves `[brake_out, hard_cut]`).
    - 108/108 tests pass (106 previous + 2 new beatsync_phase tests).
      Full rebuild + dry run resolves end-to-end (58 events).
    - **Not yet verified live** — the `beatsync_phase` fix is a genuine,
      tested code change but hasn't been confirmed by ear yet. Worth a
      live listen on one of the 9 affected transitions (e.g. Toni
      Braxton→Paradise, Try Again→Toni Braxton) next time Ernest runs the
      set.
  - **DONE 2026-07-19, fifteenth round**: big library ingest + live scan
    progress + cross-machine portability.
    - **Live scan progress (GUI + CLI)**: the curate page polls
      `scan_state` every 750ms and displays `processed/discovered`, but
      `processed` was only ever written once at the very end — a long
      ingest sat on "0/N files" in the GUI and printed nothing on the CLI
      during tag reads. `incremental_scan()` now: marks the scan running
      BEFORE discovery (rglob over a big USB tree takes real time by
      itself), prints/records discovery progress every 2000 files, jumps
      `processed` past all unchanged (skipped) files in one step with a
      line saying how many were skipped, and prints rate+ETA while
      updating the DB every 100 files during actual tag reads. One
      regression test pins the observable contract (stdout lines +
      final `discovered`/`processed` in scan_state).
    - **Ingested Ernest's big library drop**: 41,884 files discovered
      across 6 roots — including two NEW roots registered this round
      (`Country`, `Electronica`, previously not configured) — 28,114
      unchanged (skipped, the incremental check working as designed),
      **13,766 new tracks** tag-read and indexed in ~6.7 min (~35
      files/s over USB), 0 changed, 0 incomplete. crate.json + catalog
      refreshed.
    - **Cross-machine setup (MacBook Pro ↔ Mac Mini) — new
      `brain/portable_library.py` + `docs/SETUP_NEW_MACHINE.md`**:
      partially resolves the long-standing "Cross-machine identity" next-
      steps item (the macOS↔macOS half; Linux path mapping still open).
      The library index (bpm/key, dj_notes, lyrics/chroma/phrases/
      timelines/beat_phase caches — everything expensive or impossible to
      regenerate) now travels ON the USB stick itself:
      `portable_library export` snapshots the local sqlite to
      `/Volumes/USB322FD/clawdj/library.sqlite3` (sqlite backup API, safe
      while the GUI is running); `portable_library import` MERGES it into
      any local state — fill-missing only (tracks inserted if absent,
      NULL bpm/key/energy/duration filled if present, per-track caches
      copied only where absent, roots unioned), local non-empty dj_notes
      NEVER overwritten (conflicts printed instead), idempotent on
      second run, and it refreshes crate.json afterward so the GUI sees
      the imported rows (the known crate-staleness landmine). Works
      across Macs because track identity is the absolute path and macOS
      mounts the same USB volume at the same `/Volumes/USB322FD` path
      everywhere. 5 new tests cover empty-machine import, fill-missing,
      note-conflict preservation, idempotency, and the actionable
      missing-file error. The setup doc walks the whole Mac Mini flow
      (export → clone/uv sync → mount check → import → incremental scan
      → GUI → enrichment) and states what deliberately does NOT travel
      (playlist.json working state, mix_plan.json, Mixxx's own DB).
    - Exported the fresh post-ingest snapshot to the stick (21 MB) so
      it's ready to carry over as-is.
    - 114/114 tests pass (108 + 1 scan-progress + 5 portable-library).
  - **DONE 2026-07-19, sixteenth round**: beatgrid-truthfulness experiment
    (`brain/grid_quality.py`) — run honestly, hypothesis NOT confirmed,
    recorded as such rather than wired into planning.
    - **Hypothesis**: West Coast beat-matched better because drum-machine
      G-funk has mathematically rigid beatgrids, while the R&B set's live
      drummers/vinyl rips make a constant Mixxx grid wrong at any given
      moment even when right on average.
    - **Metric v1** (fraction of onsets near grid) was invalid on real
      music — legitimately off-beat onsets (hi-hats, syncopation, vocals)
      drown the signal; ear-certified-great tracks scored no better than
      the problem tracks. **Metric v2** inverts the question (for each
      GRID LINE, is there an onset near it; windowed, so drift shows as
      degrading windows) — synthetic ground-truth tests still pass
      (exact grid=1.0, 1%-off tempo fails, half-beat phase shift reads
      misaligned; `tests/test_grid_quality.py`, 3 tests).
    - **Real-data verdict: the clean genre hypothesis FAILED validation.**
      The West Coast control group (G Thang 0.64, Regulate 0.56 — the
      ear-certified best beat-matchers) scores BELOW several R&B tracks
      (Cassie 0.89, Rock The Boat 0.84, That's the Way Love Goes 0.86).
      The metric therefore must NOT drive planning decisions yet.
    - **What the data does show**: the specific tracks in Ernest's
      specific beat-match complaints score conspicuously badly —
      Nite And Day Single Edit **0.21 misaligned**, Wall to Wall 0.38
      (min-window 0.09), Keni Burke 0.49 (**min-window 0.04** — a 30s
      stretch where almost no grid line has an onset near it, 1982 live
      band), Sweetest Taboo 0.35, Love Will Never Do 0.27, All for You
      0.29. Every transition he flagged repeatedly involves at least one
      of these. Kept as a per-track ADVISORY signal (survey saved to
      `brain/data/grid_quality_survey.json`), pending validation by ear.
    - The likely true picture is compounding causes: (1) sync disabled on
      half the R&B transitions by play_bpm holds — already fixed via
      beatsync_phase, still unheard live; (2) bigger tempo gaps than the
      88-100bpm West Coast set; (3) genuinely untrustworthy grids on the
      specific tracks above.
    - Also this round: West Coast mix archives backed up to the USB stick
      (`/Volumes/USB322FD/clawdj/archives/`), and the big-library GUI
      rescan confirmed working end-to-end (41,887 discovered, 41,880
      skipped unchanged, 7 re-read — the incremental+progress work from
      the fifteenth round behaving exactly as designed in the GUI).
    - 117/117 tests pass. **Next**: the transition preview renderer
      (backlog item #2) is now clearly the highest-value build — Ernest's
      iteration loop is currently one full live run per round of feedback;
      rendering each planned transition as a ~30s audio snippet lets him
      audition all of them in minutes and gives every hypothesis
      (beatsync_phase, grid quality, cue choices) a fast ear-truth check.
  - **DONE 2026-07-19, seventeenth round**: the transition preview
    renderer is BUILT and validated on a real mix — backlog item #2
    closed. Plus the DJ-technique playbook from outside reference, and
    smarter enrichment gap messaging.
    - **`brain/preview_transitions.py`**: renders every transition in
      `mix_plan.json` as a listenable mp3 (~12s of the outgoing track
      before the anchor, the real crossfade at the planned length, ~12s
      of the incoming from its real cue) plus an `index.html` with play
      buttons — audition a whole set's transitions by ear in minutes
      instead of one full live Mixxx run per feedback round. Faithful to
      the plan's actual numbers: cue points, ride lengths, fade beats,
      play_bpm holds (atempo, pitch-preserving like keylock), sync'd
      entries rendered at the outgoing deck's live bpm, hard cuts as
      butt splices. Deliberately does NOT render EQ/filter/flourish
      seasoning — it previews beat/tempo/cue alignment, the thing that
      keeps needing ear checks. Sequencing logic is a pure function
      (`transition_specs`) with 5 unit tests (anchor math, sync-rate vs
      bpm-target precedence, play_bpm-hold window shifts, hard-cut
      handling, graceful missing-bpm errors). **Validated end-to-end on
      Ernest's brand-new 20-track mix: 19/19 transitions rendered, 0
      failures** → `brain/data/previews/index.html`.
    - **`docs/DJ_TRANSITIONS_PLAYBOOK.md`**: pulled the transcript of
      Blakey's "The Only 5 Transitions You Need as a Beginner DJ"
      (youtu.be/my9n3W3uJDE, via `uvx youtube-transcript-api` — works
      fine as a repeatable pipeline for future videos) and mapped all
      five techniques onto claw-dj's machinery with a gap scorecard.
      Three genuine gaps identified: (1) a true volume-only
      `plain_blend` (our blends always add EQ/filter seasoning), (2)
      `bass_swap` should be a gradual ramp, not an instant kill at the
      50% point, (3) **`echo_out` as a transition exit is missing
      entirely** — and it's the standard gentle answer to exactly our
      recurring large-tempo-gap pain (works with ~10bpm gaps because
      nothing rhythmic overlaps; less dramatic than the brake). The
      32-beat phrasing discipline and "clean and simple beats
      complicated" thesis both validate existing claw-dj defaults.
    - **Enrichment gap messaging** (`enrich_set.run_enrich`): incomplete
      lines now carry actionable hints — chroma on .m4a is flagged as a
      permanent Symphonia decode limitation ("swap to an mp3 copy if one
      exists") vs phrases flagged as the known lazy Mixxx DB flush
      ("re-run Analyze in a few minutes"), with a summary line saying
      how many gaps a re-run can actually fix. Notable: the big library
      ingest brought in mp3 duplicates for some m4a-only tracks (e.g.
      He Wasn't Man Enough now has a same-album mp3 at
      `Toni Braxton/Albums/(2000) The Heat/01 He Wasn't Man Enough.mp3`)
      — swapping playlist entries to mp3 copies is now a real fix path
      for chroma gaps.
    - 122/122 tests pass.
  - **DONE 2026-07-19, eighteenth round**: first full preview-driven
    feedback round on the new 20-track R&B/pop mix — Ernest auditioned
    the rendered transitions and gave per-transition feedback; everything
    below was applied and re-rendered WITHOUT a live Mixxx run.
    - **New `brain/convert_m4a.py`**: auto-converts .m4a playlist tracks
      to .mp3 siblings via ffmpeg (same folder, same basename, tags
      copied via -map_metadata; original kept for the user to delete),
      adopts ALL per-track knowledge onto the new file's DB rows
      (bpm/key/energy, dj_notes, lyrics/chroma/phrases/timelines/
      beat_phase — same audio, so analysis carries verbatim; reuses
      portable_library's column maps), and swaps the playlist entries.
      Fill-missing semantics, never overwrites, no-op on re-run. Ran it:
      3 tracks converted (He Wasn't Man Enough, Touchin Lovin, Loving
      You) — the chroma decode gap is now fixable at the source.
    - **Reorder, driven by key/tempo data**: Entourage moved from the
      wind-down slot to bridge Love Will Never Do → Escapade — all
      THREE are in Ab, and Entourage's 106.5bpm sits exactly between
      LWND's 103.2 and Escapade's 115.2 (the rough 11.6% jump Ernest
      flagged becomes 3.2% + 7.6% steps). One move answered both his
      "should we match LWND with another song?" and "Entourage is high
      tempo/high energy" placement complaints. Back half re-arced:
      ...TWLG → Best of Me → Movin' On (both kept, Ernest liked them) →
      Sisqo (beat_drop at its TRUE start per Ernest — iconic intro;
      claimed 137bpm is suspect but grid-consistent) → If (beat_drop out
      of the outlier, industrial intro as its own statement) → Touchin
      Lovin (100) → Loving You (99) → You're Makin' Me High (92) → How
      Many Ways (78) — a descending wind-down closer arc. This also
      dissolves the broken You're Makin' Me High → How Many Ways-mid-set
      and How Many Ways → Entourage pairings.
    - **Ride/tempo directives per Ernest's ear**: LWND holds native
      103.2 and finishes verse+chorus (exit 0:43.8); Escapade lands on
      verse 1 (0:50.12) at native 115.24 and sings the full verse + most
      of chorus (ride 142); Jane Child up-tempo'd to MATCH Escapade
      exactly (play_bpm 115.24, Ernest ok'd — tempo-identical blend so
      beats can genuinely lock); All For You gets a longer 32-beat
      landing right at its verse (0:48.54) and finishes verse+chorus
      (ride 98).
    - Plan rebuilt with the **mix-to-listen** profile (what the GUI's
      build actually used, per plan provenance — NOT dj-showcase).
      19/19 previews re-rendered, 0 failures. 122/122 tests pass.
    - Deferred from this round (noted, not built): `plain_blend`,
      gradual `bass_swap` ramp, `echo_out` exit (playbook gaps);
      Loving You's phrases gap (Mixxx flush lag — needs one more
      Analyze pass now that Mixxx restarted).
  - **DONE 2026-07-19, nineteenth round** (Ernest at lunch — autonomous
    pass through his reorder ask plus the deferred backlog):
    - **Reorder per Ernest**: Rock The Boat now follows Me&U directly
      (100.0→93.0, a 7.5% step inside sync range) — its entry treatment
      is certified good BY EAR ("the drop, the drop into Aaliyah's verse,
      the chorus and some of the 2nd verse") and was left byte-identical,
      with the certification recorded in its dj_notes so no future round
      touches those numbers. Wall to Wall relocated to the wind-down arc:
      Loving You (99) → Wall to Wall (94) → You're Makin' Me High (92.1)
      smooths the descending ladder and Eb→Gm is a near-key step; no
      transition Ernest marked "keep" was disturbed.
    - **Loving You's phrases gap CLOSED**: Mixxx's restart flushed the
      m4a's beatgrid; ran `fill_phrases` against the m4a and adopted the
      row onto the converted mp3 (`convert_m4a.adopt_metadata` reused for
      exactly its purpose), then `fill_beat_phase` for the mp3. Also
      filled beat_phase for the 8 other new-to-the-set tracks — **all 20
      tracks now have full beat-phase coverage**, so the planner's
      snare-parity auto-check runs on every transition (previously it
      silently skipped the new half of the set).
    - **Gradual bass swap** (playbook gap #2): `perform_transition`'s
      bass handover is now a smoothstep ramp of the outgoing deck's low
      EQ across progress 0.35→0.65 instead of an instant kill at the
      midpoint ("gradualness IS the technique"). Incoming bass still
      untouched per the 2026-07-14 hip-hop note.
    - **Echo-out exit wired end-to-end** (playbook gap #4 — the big one):
      the runner half (`echo_out_exit`, reserved Echo unit 2 slot 3,
      ramps effect mix up as deck volume drops) already existed and was
      live-validated 2026-07-14, but NO planner path ever emitted it.
      Now: new `exit_style=echo_out` dj_notes directive (parsed in
      `track_directives`) → `build_plan` overrides the technique to
      `echo_out_exit` (4 beats, single move, no sync, no tempo bridging)
      → `perform_transition` handles the move explicitly (echo ramp,
      stop outgoing, start incoming clean; plain-fade fallback when the
      Echo slot isn't loaded in the GUI) → the preview renderer renders
      it audibly (ffmpeg `aecho` + fade tail, incoming clean, splice).
      **Piloted on You're Makin' Me High → How Many Ways** (92.1→77.9,
      the 18% closer drop where every blend bridge sounded forced).
      NOTE: needs the one-time GUI step of Echo loaded in Unit 2 slot 3
      after any effects reset — `echo_ready` readback guards it.
    - Plan rebuilt (mix-to-listen), 19/19 previews re-rendered including
      the audible echo-out at #19. 125/125 tests pass (122 + 2 runner
      echo tests + 1 planner exit_style test).
  - **DONE 2026-07-19, twentieth round**: second preview-feedback pass —
    Ernest certified transitions #02–#06 "incredible, surprisingly good"
    and #15 (If→Touchin Lovin) "VERY GOOD, almost immaculate", and asked
    what made the difference (answered below); remaining complaints
    fixed.
    - **The recipe behind the good ones** (answered from the actual plan
      data, not a guess): the certified transitions all had (1) REAL
      beatsync engaged — either full sync (no play_bpm hold, e.g.
      If→Touchin) or hold+`beatsync_phase` (the round-fourteen fix,
      heard here for the first time); (2) full beat-phase parity
      coverage (only completed for the whole set this round); (3) modest
      tempo gaps from the data-driven reorder. The complained-about ones
      each broke one leg: #17 (Loving You→Wall to Wall) had a play_bpm
      hold blocking full sync — REMOVED, now mirrors the immaculate #15
      recipe exactly; #01/#07 were parity-aligned but entering on the
      wrong COUNT-in-bar.
    - **Count-aware alignment upgrade** (`count_shift_beats` in
      onset_analysis + wired into build_plan's auto-check): parity (mod
      2, measured from audio) now combines with bar position (mod 4,
      from the beatgrid, same assumption as the ear-confirmed hand fixes
      of 2026-07-16/17); measured parity wins on conflict. On rebuild it
      auto-nudged TEN transitions — including exactly the two Ernest
      flagged for count mismatch (#01 Me&U→Rock The Boat, #07
      Entourage→Escapade). 4 new tests.
    - **Sisqo's 137bpm is REAL** — librosa's independent estimate agrees
      (136), so no grid repair; it's a genuine outlier with no honest
      blend partner in-set. Per Ernest ("hard cuts sparingly... blend
      them together"), the second hard cut (Sisqo→If) became an
      **echo-out exit** — break in (kept, his call), echo tail out, If
      enters clean at its true start (its beat_drop entry directive
      removed).
    - **You're Makin' Me High extended** per Ernest: rides from 0:56.85
      to ~3:28 (most of the song, out during the final vamp, ride 200);
      echo-out pilot kept — preview's abruptness was largely the
      too-early exit.
    - **Bridge candidates found for the two hard spots** (library search,
      presented to Ernest): Aaliyah — Are You That Somebody (138.1bpm,
      0.8% from Sisqo's 137) could blend AFTER Sisqo; The-Dream —
      Rockin' That Shit (78.0bpm, 0.1% from How Many Ways) could sit
      before the closer. Both would need enrichment + his taste call.
    - 19/19 previews re-rendered; 129/129 tests pass.
  - **DONE 2026-07-19, twenty-first round**: Mya's own album version in,
    Are You That Somebody inserted (Ernest's picks), plus the first
    LIVE beatgrid repair.
    - **Mýa — It's All About Me (1998 album copy)** replaces the
      Sisqo-comp copy — IDENTICAL recording (264.9s both), so lyrics/
      timeline/chroma transferred verbatim. Crucial find: Mixxx analyzed
      this copy at **94/Gm** where the Sisqo copy read 137/D — the same
      swing groove genuinely flips Mixxx's detector between 2/3-related
      grid interpretations. Phrases/beat_phase NOT transferred (they
      were 137-grid-based and would poison the beat math).
    - **First live beatgrid repair via the control API**: Are You That
      Somebody's grid (138.05, the same 3/2-family misread) was pulled
      down with `beats_set_twothirds` → 92.04, confirmed via readback —
      putting it in the same grid family as Mya's 94 so the two decks
      genuinely sync (2.1% apart). The long-backlogged "grid repair from
      enrichment" item now has a proven manual recipe.
    - New chain: Movin' On → (Ernest's certified break) Mýa — It's All
      About Me → **real blend, 0.703 score** → Are You That Somebody
      (verse landing at 'Boy, won't you pick me up at the park', 1:24.3,
      timeline built fresh from LRCLIB) → echo-out → If. The set is 21
      tracks now.
    - **macOS Unicode landmine documented the hard way**: the Mýa path
      uses decomposed NFD ("y"+combining accent) on disk; a hand-typed
      NFC path silently created phantom cache rows and `apply_analysis`
      updated ZERO rows without erroring. Cleaned up by re-homing all
      cache rows onto the NFD track_id and patching bpm/key directly.
      Rule: always fetch track_ids from the DB/playlist, never retype
      paths with accented characters.
    - 20/20 previews re-rendered, 0 failures; 129/129 tests pass.

  - **DONE 2026-07-19, twenty-second round**: live crash on the new
    Mya→Aaliyah chain, root-caused and double-fixed.
    - **Crash**: `RuntimeError: verse landing missed (expected 84.270s,
      Mixxx reports ~76.6s)`, twice, deterministically. Root cause in the
      log's own words: `anchoring on [Channel2] beat (137.00 BPM)` — when
      Ernest's live Mixxx loaded Mýa's copy it re-analyzed it onto the
      **137 grid**, not the 94 the muted-deck read had given (the same
      swing-groove detector instability), so ride/fade beat math built
      for a 94 grid ran on a 137 deck and the pre-roll fell ~7.7s short.
    - **Fix 1 — repaired Mýa's grid live** (`beats_set_twothirds`,
      137→91.33), after first catching a stale-readback trap: an
      eject+reload cycle briefly reported 90.0 (the previous deck
      value); a 20-second settle-and-watch confirmed the real persisted
      grid was 137 before repairing. Library/playlist/dj_notes updated
      to the 91.33 grid (ride 135 beats); Mya (91.33) ↔ AYTS (92.04)
      are now 0.8%% apart — a genuine full-sync pair.
    - **Fix 2 — landing misses no longer kill the set**: the hard
      RuntimeError in `perform_transition` is now a loud warning + a
      snap of the deck to the intended landing position — one audible
      jump on one transition instead of a dead stage. Same softening
      philosophy as the load_deck bpm identity barrier. Regression test
      added.
    - 130/130 tests pass; plan rebuilt (#14 Mya→AYTS now scores 0.748);
      20/20 previews re-rendered.
  - **DONE 2026-07-19, twenty-third round**: Cassie→Al B. Sure! (album)
    →Rock The Boat chain built; a real bug in that build broke Cassie's
    opener and got fixed same-round; plus four more live-feedback fixes.
    - **Cassie → Al B. Sure! (album, 91.6bpm/Ebm) → Rock The Boat**
      chain built per Ernest's pick from the earlier bpm/key search.
      Cassie's ride extended to reach the requested exit point.
    - **Broke, then fixed, Cassie's opener in the same round**: extending
      the ride by moving `cue_seconds` from 0 to 19.57 (to skip to the
      first verse) silently dragged the ENTIRE `juggle_brake_intro`
      juggle/brake/rewind mechanism into the middle of the song with it
      — `cue_seconds` on an opener is both the load position AND the
      exact point the juggle rewinds to and resumes from, not just "where
      the ride starts counting." Ernest caught it immediately by ear
      ("the beginning sounds terrible... don't mess up Cassie's
      verses"). Fixed by reverting `cue_seconds` to 0 and reaching the
      same intended ending purely via `ride_beats` (0→207, auto-nudged
      to 208 for count parity) — same technique, computed from the
      correct baseline. Recorded as a permanent rule in
      `docs/DJ_STYLE_GUIDE.md`.
    - **Echo-out exit's real bug, found and fixed**: Ernest's complaint
      ("it just leaves silence, we want to keep the beat going") was
      correct — the original implementation rang the echo tail to full
      volume-zero, THEN stopped the outgoing deck, THEN started the
      incoming one: fully sequential, a real gap of dead air. Redesigned
      `echo_out_exit()` to take an optional `to_deck` — the incoming
      deck now starts playing and the crossfader moves DURING the same
      ~1s ramp, so something is always audible; the plain-fade fallback
      (no Echo loaded) got the identical fix. The opener-tease use
      (`echo_tease_drop`, no `to_deck`) is deliberately unchanged — that
      context wants a real brief silence before replaying the same
      track. New regression test asserts no point in the write sequence
      has both decks silent at once. Preview renderer updated to match
      (crossfade instead of splice for echo-out).
    - **Movin' On → Mya blend confirmed real** (bpm 0.9% apart) — Mya's
      `entry_style=beat_drop` removed, letting the default technique
      picker choose a genuine blend instead of a hard cut, per Ernest's
      explicit "don't use the brake/stop" ask.
    - **Mya's ride extended** to verse 1 → full chorus 1 (both internal
      repeats) → verse 2 → full chorus 2, exiting before the closing tag
      line, per Ernest's spec.
    - **Don't Wanna Fall in Love → All For You, real bug found**: All
      For You's own dj_notes literally said "beatsync_phase aligns the
      beat" as justification for holding it at its own native 113.5 —
      but Jane Child is deliberately held at Escapade's bumped 115.24,
      so the two decks sat 1.7% apart in tempo for the ENTIRE 32-beat
      overlap (phase-only sync doesn't hold tempo matched, only snaps
      phase once) — exactly Ernest's "snares not matching" complaint.
      Removed the hold; real full sync now locks both tempo and phase to
      Jane Child's live rate, `settle_rate` glides back after — the same
      recipe as the "almost immaculate" If→Touchin transition. Confirmed
      via the real plan JSON: `incoming_bpm_target: None`.
    - **Repeated the stale-prose-directive bug in a new shape** while
      writing the All For You fix note: described the OLD removed value
      as literal text ("the play_bpm=113.5 hold was wrong") with no real
      trailing directive for that key — since it was now the ONLY match
      in the text, the parser (correctly, per its own last-match rule)
      read it as live and the hold silently came back. Caught by
      re-checking the rebuilt plan's JSON rather than trusting the note
      text was right, fixed by rewording to avoid the literal
      `key=value` shape anywhere except the real trailing directives.
      Worth remembering as a durable rule: never write `key=value` in
      prose for a key being discussed but not set, in ANY dj_notes.
    - **How Many Ways researched, not moved**: fresh library-wide search
      confirms The-Dream — Rockin' That Shit (78.0bpm, 0.1% off) is the
      ONLY genuinely close-tempo match anywhere in the library — same
      track flagged for a different slot earlier and left as an open
      question pending Ernest's call, now that the echo-out fix may make
      the existing exit work without relocating anything.
    - 131/131 tests pass (130 + 1 no-silence-gap regression); plan
      rebuilt; 21/21 previews re-rendered, 0 failures.

  - **DONE 2026-07-19, twenty-fourth round**: six ear-feedback fixes plus
    a new ear-override directive.
    - **New `trust_ride_beats` directive**: locks a human-certified ride
      length against the beat-phase auto-nudge. Needed because the
      nudge's snare-parity input can be a near-coin-flip (LWND's
      confidence is 0.015) — when the ear says the count is off by one,
      the ear outranks the measurement. Parser + build_plan gate + test.
    - **LWND → Entourage count fix**: ear said "perfect beat match, wrong
      count by 1" at the auto-nudged 75 — shifted to 76 and locked with
      trust_ride_beats. Direction of a one-count error isn't knowable
      from data; if still off, the documented fallback candidate is 74.
    - **Entourage → Escapade**: removed Escapade's play_bpm hold (the
      "hit at real tempo instantly" hold left the decks 7.6% apart the
      whole overlap — the exact un-beat-matched complaint); real full
      sync now slows Escapade to Entourage's live tempo for the blend,
      settle_rate glides it back to native after, landing lengthened
      24→32 beats per "blend starting earlier". Ernest explicitly ok'd
      the slow-down-then-restore shape.
    - **AYTS → If**: echo-out exit dropped (Ernest disliked the abrupt
      end); plain synced blend instead. If now cues onto its hard
      industrial instrumental 8 beats in (4.836s, skipping the very
      beginning per Ernest) with ride reduced by the same 8 beats
      (187→179) so the ear-certified "almost immaculate" exit anchor
      into Touchin, Lovin lands on the exact same beat index; locked
      with trust_ride_beats.
    - **Al B. Sure! (album) → Rock The Boat**: ride cut 122→40 (~26s) —
      exit right after the first part of the chorus per Ernest. Flagged
      as approximate: no synced lyrics exist for this exact copy.
    - **You're Makin' Me High**: entry moved to the instrumental
      beginning, 8 beats in (5.326s), keeping the most-of-song ride
      (311 beats to ~3:28).
    - **YMMH → How Many Ways**: echo-out replaced with the explicit ask —
      HMW cues at 0:41, `entry_style=gentle_blend` forces a fully-synced
      24-beat overlap (HMW sped ~18% up to meet YMMH, Ernest's explicit
      call), then settle_rate glides it back to its native 77.9 ballad
      tempo as the closer plays out.
    - All values verified against the rebuilt plan JSON (not note text).
      132/132 tests pass; 21/21 previews re-rendered.
  - **DONE 2026-07-20**: added `full_track` to How Many Ways — it's the
    closer now (Al B. Sure! album/Rock The Boat/AYTS reorders since
    pushed it off the old closer slot), so it needed the flag explicitly
    re-added to play out completely rather than a fixed duration.
    Confirmed via the rebuilt plan's `finale` event: `play_to_end: True`,
    `seconds: 247.1` (the real remaining length). 132/132 tests pass.

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
4. **whisperX fallback for unsynced lyrics** — recurring gap (7/24, then
   8/22 in the next batch — some tracks LRCLIB just doesn't have synced
   lyrics for, mostly deep-catalog G-funk/West Coast cuts). Forced
   alignment (whisperX or similar) against the plain lyrics + the actual
   audio file generates real timestamps offline, no LRCLIB dependency.
   Real effort (new dependency, GPU/CPU cost, a new pipeline stage) —
   still backlogged, not started.
5. ~~**Generic OpenAI-compatible engine**~~ **DONE 2026-07-14** — see above.
   Original text kept for context:
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
