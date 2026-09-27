# Authoring a same-beat continuous mix

For a set where every record shares one instrumental (the Who Shot Ya
variations: album, Club Mix, the VLS instrumental, and freestyles over the same
beat), the goal is one continuous beat with the backbeat locked: snares on the
same 2 and 4, never one count off. Any agent harness can do this with the tools
below; the plan format and live runner are in [SHARED_PERFORMANCE.md](SHARED_PERFORMANCE.md).

Measurements are evidence for placement. Ernest's listening pass decides.

## 1. Spec (outside the checkout)

List each source once, with a rough BPM and musical spans that avoid mandatory
exclusions, skits and DJ talk. Pick the cleanest instrumental as `reference`.

```json
{"reference": "inst", "tempo_bpm": 91.68,
 "sources": {"inst":  {"track_id": "/Volumes/.../03-who_shot_ya_(instrumental)-nuc.mp3", "bpm": 94.66, "spans": [[20, 180]]},
             "album": {"track_id": "/Volumes/.../18. Who Shot Ya.mp3", "bpm": 91.67, "spans": [[4, 203.5], [224.5, 300]]}}}
```

Choose `tempo_bpm` near the records you want untouched (91.68 kept the album,
Ja Rule, Jim Jones and K-Dot at rate ~1.0).

## 2. Measure

```sh
M="uv run python -m brain.performance_measure"
$M fit    --spec spec.json --out ev/measure.json            # tempo, pattern zero, drift, loudness
$M pitch  --spec spec.json --measure ev/measure.json --anchor album --out ev/pitch.json
$M lags   --spec spec.json --measure ev/measure.json --out ev/lags.json
$M vocals --spec spec.json --measure ev/measure.json --out ev/vocals.json
```

Read them this way:

- **fit**: `drift_ms_p5_p95` within about ±10 ms means one fixed rate holds the
  record against the bed. `jumps_over_100ms` marks splices and rewinds (Jadakiss
  jumps 2 beats at 2:39): end the clip before them. Every `zero` names the same
  point of the shared pattern, because all sources fold against one reference.
- **pitch**: `residual_cents` near 0 means turntable rate (keylock off) puts the
  record in tune with the anchor. The Who Shot Ya pressings differ by 3–5% in
  speed and land within ±2 cents once rate-matched, so layering stays in tune.
- **lags**: `backbeat_ok` means lag 0 beats beats ±1 beat, the off-by-one
  failure. `bar_aligned` also rules out a 2- or 4-beat shift.
- **vocals**: one character per bar. `#` is voice, `.` is beat only, `_` is a
  beat drop. Use it to find verse ends, gaps, and clean handoff bars when the
  lyric timelines are wrong or missing.

For a vocal double-up, first prove the two copies are the same take:

```sh
$M hooks --spec spec.json --measure ev/measure.json --query album:224.3 --out ev/hooks.json
$M align --spec spec.json --measure ev/measure.json --a album:224.5 --b club:223.7 --out ev/align.json
```

`same_take_likely: true` (album vs Club Mix: correlation 0.67 at 0 ms) means a
real double. A different rapper's hook (Ja Rule vs Club Mix: 0.27 at +52 ms)
is two vocals on top of each other, not a double.

## 3. Author with `brain.performance_author.Grid`

```python
from brain.performance_author import Grid
g = Grid(91.68, measure, anchor="album")            # album plays source 0:00 at mix 0:00
a = g.clip("album", "album", 0.0, 203.5, 0.0, fade_in=0, fade_out=0.12, gain_db=-5.8)
loop = g.loop("inst", 8, beats=32)                  # clean 32 beats on a pattern point
dmx_at = g.aligned_start("dmx", g.pattern_point("dmx", 0), g.end(a) + 20)
```

- Place every start with `aligned_start`, or with `mix_time` of a clip that is
  already placed. `shared.performance.validate` rejects anything off the
  pattern phase, so a correctly measured clip cannot land one count off.
- Enter and leave on pattern points (`pattern_point`) or beats (`beat_point`).
  Re-entries after a mandatory skip use `side="after"`. The gap is then
  covered by the bed.
- Set gains from `lufs` (target ≈ −15 LUFS per foreground), not by ear guesses.

### Decks and EQ

Mixxx EQ gains run 0–4, where 1 is centre. Crossovers are 246 Hz and 2484 Hz.

| Control | Use |
|---|---|
| `live_eq` `[low, mid, high]` | A clip's fixed EQ. A vocal foreground over a bed: low 0.3–0.45. |
| `eq_automation` `[{at, scale:[l,m,h]}]` | Timed scaling of the clip's EQ (clip-local seconds, eased between points, held outside). Lets one clip change EQ mid-song without splitting it. |
| bed `support` `low_gain` / `mid_gain` / `high_gain` | Settled bed EQ after `transition_seconds`. `mid_gain` defaults to `high_gain`. |
| bed `pulse_times` | A number (default `pulse_gain` and width), or `{at, gain, width_seconds}`: triangles that lift the bed's mid and high. Good for skip gaps and last bars. |

A bed is one support clip looping an instrumental loop on the common clock, from
a pattern point (`Grid.bed`). One bed for the whole set keeps the bass timbre
identical across every handoff. Pass 2 of the Opus 5.5 Who Shot Ya mix ran the
bed with mids and highs at 0.95 under DMX and 50 Cent (thin rips) and at 0.45
elsewhere.

Up to four decks can play at once. A deck is reused only 2 s after its last
clip ends. The compiler assigns decks and rejects an overcommitted timeline.

## 4. Compile, render, verify, listen

```sh
uv run python -m brain.performance_cli --plan <slug-or-mix_plan.json>
uv run python -m hands.offline_mix --plan <mix_plan.json> --out ev/render --stem pass1
$M verify --measure ev/measure.json --plan <mix_plan.json> --render ev/render/pass1.wav --reference inst --out ev/verify.json
./scripts/run_mix.sh --plan <mix_plan.json> --dry-run
```

`verify` folds the 5–10 kHz snare/hat band on the plan's own clock. Every window
should report `margin_one_beat > 0`. `by_clip` gives the median offset per clip:
a clip several ms away from the others is the one to re-measure. The offline
render approximates live EQ with the same `clip_eq` curve and zero-phase band
split, but not Mixxx's exact filters. The live run is the real check.

## Known limits

- **Deck-to-deck timing live.** The Rust runner corrects a clip's position
  only when it starts. After that it checks every 0.5 s and stops at 80 ms of
  drift. Two decks can wander roughly 15–80 ms apart. That is fine for a bed
  under a rapper. A same-take vocal double will sound doubled or phased rather
  than one voice.
- **Measurement resolution.** Pattern zeros are sub-bin interpolated (well
  under 10 ms). Weak-backbeat records (50 Cent's 24 Shots cut) have low
  `backbeat_margin`, so check them with `lags` and `verify`.
- **Lyric timelines can be for a different edit.** 50 Cent's was 213 s for a
  111 s file. Trust the `vocals` map and Ernest's notes over LRC timestamps.
