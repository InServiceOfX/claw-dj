# The Mixxx control surface — what the board can do, and how we drive it

Researched 2026-07-13 against the fork at `repos/mixxxes/mixxx` (2.7-dev).
Full official list: https://manual.mixxx.org/2.6/en/chapters/appendix/mixxx_controls
(hundreds of controls; this doc curates the ones that matter for transitions
and live effects, verified in `src/engine/controls/` and `src/effects/`).

## The one fact that changes everything

Our control API patch (`src/network/controlapiserver.cpp`) routes `get`/`set`
straight into `ControlObject::get/set` for **any (group, key) that exists**,
plus `subscribe` (pushed change events) and `load`. There is no allowlist:
**every knob, button, and fader in Mixxx is already remote-controllable over
TCP port 9995.** The Python client (`hands/mixxx_control.py`) and the plan
runner use maybe a dozen controls; the rest of the board is untapped.

## Deck controls — `[ChannelN]` (N = 1..4)

### Transport & cues (`cuecontrol.cpp`)
| Control | What it does |
| --- | --- |
| `play`, `cue_default`, `cue_gotoandplay`, `cue_gotoandstop`, `cue_set`, `cue_point`, `cue_preview` | CDJ-style cue vocabulary |
| `hotcue_X_activate` / `_set` / `_goto` / `_gotoandplay` / `_clear` (X = 1..36) | hotcue drumming / juggling; set them from code at lyric-timeline verse starts |
| `intro_start_*`, `intro_end_*`, `outro_start_*`, `outro_end_*` | Mixxx's own silence-detected intro/outro markers — free cue candidates alongside our lyric/phrase cues |

### Rate, scratch, direction (`ratecontrol.cpp`)
| Control | What it does |
| --- | --- |
| `rate`, `rate_ratio` | pitch fader (we use this for settle_rate) |
| `rate_temp_up/down(_small)` | **pitch bend** — momentary nudge, the human way to phase-align |
| `scratch2` + `scratch2_enable` | direct platter velocity — **spinbacks, brakes, scratches** from code (ramp velocity 1→0 for a brake, 1→-6 for a spinback) |
| `reverse`, `reverseroll` | `reverseroll` = **censor**: slip-reverse while held, playback position keeps advancing underneath |
| `jog`, `wheel`, `back`, `fwd` | jog semantics |

### Loops, slip, beatjump (`loopingcontrol.cpp`)
| Control | What it does |
| --- | --- |
| `beatloop_N_activate`, `beatloop_size`, `loop_double/halve`, `reloop_toggle`, `reloop_andstop` | beat loops |
| `beatlooproll_N_activate` | **loop roll** — slip-based stutter, position keeps advancing |
| `slip_enabled` | master slip switch: any loop/scratch/reverse under slip snaps back seamlessly on release |
| `beatjump_N_forward/backward`, `beatjump_size`, `loop_move` | grid-quantized jumps (chorus skips without a second deck) |

### Sync & beatgrid surgery (`bpmcontrol.cpp`)
| Control | What it does |
| --- | --- |
| `beatsync`, `sync_enabled`, `sync_leader` | tempo+phase sync (verse cuts deliberately avoid it) |
| `beatsync_phase` | **phase-only align** — snap phase without touching tempo; the missing precision tool before an on-beat cut |
| `beats_set_halve` / `_double` / `_twothirds` … | **rewrite the beatgrid ratio from code** — fixes double-time BPM detections (the old "Don Doggy 149 BPM" problem) programmatically |
| `beats_translate_curpos`, `beats_translate_earlier/later` | nudge the grid to the current position |

### Musical key (`keycontrol.cpp`)
| Control | What it does |
| --- | --- |
| `keylock` | tempo changes don't chipmunk (we set this) |
| `pitch`, `pitch_adjust` | **shift musical key in semitones independent of tempo** — soften key-clash blends by moving the incoming track ±1–2 semitones, release after landing |
| `sync_key`, `reset_key` | match/reset key to the other deck |

### Per-deck mixer
`volume`, `pregain`, `mute`, `VuMeter` (read — level-aware automation!),
`orientation` (0/1/2 = which side of the crossfader the deck sits on —
reassignable mid-set).

## EQ + kill switches

Group: `[EqualizerRack1_[ChannelN]_Effect1]`
- `parameter1/2/3` = low/mid/high knobs (we ramp these today)
- `button_parameter1/2/3` = **kill switches** (verified in
  `threebandbiquadeqeffect.cpp`: killLow/killMid/killHigh) — instant on/off,
  crisper bass swaps than ramping, and the classic kill-combo stutter.

## QuickEffect (the filter knob) — `[QuickEffectRack1_[ChannelN]]`
`super1` (the knob; default Moog ladder filter), `enabled`,
`loaded_chain_preset` / `next_chain_preset` — the knob can drive **any chain
preset** (echo, reverb wash…), not just filter.

## Effect units — `[EffectRack1_EffectUnitN]` (N = 1..4)
- Unit: `mix` (dry/wet), `super1` (metaknob), `group_[ChannelX]_enable`
  (route any deck through any unit), `focused_effect`
- Effect slot `[EffectRack1_EffectUnitN_EffectM]`: `enabled`, `meta`,
  `parameterK`, `effect_selector`
- **26 built-in effects** (verified `src/effects/backends/builtin/`): Echo,
  Reverb, Flanger, Phaser, Filter, Moog Ladder, Bitcrusher, Distortion,
  Glitch, Tremolo, Autopan, Balance, WhiteNoise, Pitch Shift, Compressor,
  Gain, AutoGain, Loudness Contour, Metronome, Graphic/Parametric EQ, Key
  Comparison, plus EQ variants.

## Master section
- `[Master]`: `crossfader`, `gain`, `balance`, `headGain`, `headMix`,
  `VuMeterL/R` (read)
- `[Mixer Profile]` (verified `enginemixer.cpp`): `xFaderMode`,
  **`xFaderCurve`**, `xFaderCalibration`, `xFaderReverse` — the crossfader's
  *shape*. Sharp cut curve for verse cuts and juggles, smooth constant-power
  for long blends — switchable per technique from code.

## Samplers — `[SamplerN]`
Full deck control set on lightweight sample slots: air horns, drops,
acapella stabs layered over the mix.

## New transition vocabulary this unlocks (build order suggestion)

1. **echo_out_exit** — enable Echo on the outgoing deck, cut its volume on
   the phrase; the tail rings into the incoming track. The classic clean
   exit. **Built 2026-07-14** (`hands/run_mix_plan.py: echo_out_exit`) —
   see "Loading effects deterministically" below for why it's
   convention-based rather than a runtime lookup, and the one-time setup
   step required before it's active.
2. **brake_stop / spinback** — `scratch2` velocity ramps; dramatic verse-cut
   variant and set-ender.
3. **censor fill** — `reverseroll` for a half-bar before a cut.
4. **slip stutter** — `beatlooproll_1/2` chains under `slip_enabled` as the
   fill before a landing.
5. **kill-switch bass swap** — `button_parameter1` toggles instead of ramps.
6. **key_blend** — `pitch_adjust` the incoming deck to a compatible key for
   the blend, then curve back to native through the second half of the
   overlap. **Built 2026-07-14**: `pick_technique` computes the smallest
   deterministic ±1–2-semitone bridge; `run_mix_plan` applies and restores it.
7. **phase-align cuts** — `beatsync_phase` before ordinary hard cuts. Still
   needs an audible pre-roll/cue-semantics experiment; verse tour deliberately
   remains native-tempo + quantized because phase-pull can move lyric cues.
8. **curve switching** — sharp `xFaderCurve` for cuts, smooth for blends.
9. **grid repair** — `beats_set_halve/double` driven by enrichment when
   detected BPM is 2x/0.5x the median of its genre neighbors.
10. **sampler drops** on transition landings.

## Loading effects deterministically (researched 2026-07-14)

There is **no load-by-name control**. `EffectSlot`'s `loaded_effect`
(`src/effects/effectslot.cpp`) takes a **1-indexed position in the visible
effects list** — manifest string IDs (`EchoEffect::getId()`) exist
internally but are never exposed to `ControlObject`, so the control API
can only load by numeric position. That position comes from
`BuiltInBackend::BuiltInBackend()` registration order in
`builtinbackend.cpp` (Echo is the 8th `registerEffect<>()` call as of this
fork) — fixed per build, but not something to hard-code: a different
machine with LV2/VST backends installed would shift every index.

**Resolution: convention over runtime lookup.** One unit+slot is reserved
for Echo, loaded **once by hand** via the GUI. On this machine that ended
up being `[EffectRack1_EffectUnit2_Effect3]` — the compact 4-DECKS skin's
effects strips don't label which unit is which (the "EFFECTS" tab in this
skin is a visibility toggle for that same row, not a separate labeled
rack — a dedicated multi-unit view may exist in other skins but not this
one), so the pragmatic move was matching the code to wherever Echo
actually landed rather than fighting the GUI for a specific slot number.
After that one-time load, every control needed is name-stable and
requires no further GUI interaction or index guessing:
- `[EffectRack1_EffectUnit2_Effect3],loaded` — readback to confirm it's
  there (code checks this and no-ops with a one-time note if not)
- `[EffectRack1_EffectUnit2_Effect3],enabled`
- `[EffectRack1_EffectUnit2_Effect3],parameter1..4` — Echo Time,
  Feedback, Ping Pong, and Send, in manifest order
- `[EffectRack1_EffectUnit2_Effect3],button_parameter1` — beat quantize
- `[EffectRack1_EffectUnit2],mix` (dry/wet)
- `[EffectRack1_EffectUnit2],group_[Channel1]_enable` (route a deck through it)

Implemented in `hands/run_mix_plan.py` (`echo_out_exit`, `echo_ready`,
`ECHO_UNIT`/`ECHO_SLOT`): explicitly configures a quantized half-beat Echo,
feeds it for one beat, cuts the dry deck as the incoming track starts, and
keeps the post-fader effect routed for four beats so the buffer can decay.
Only then does it unroute the deck and reset the wet mix. The earlier
implementation unrouted immediately after its one-second volume ramp,
which killed the delay buffer and sounded like a plain cut despite the
nominal Echo move. Same pattern would extend to Reverb in a second reserved
slot for a wash-out variant.

## Rust: controlling the whole board (`core-rust` plan)

Today `core-rust` (`clawdj` lib: `midi.rs`, `live.rs`, `command.rs`,
`queue.rs`, `chroma.rs`) speaks **MIDI only** — no TCP. The control API is a
line-delimited JSON protocol over TCP, trivial in Rust with `std::net` +
`serde_json`, no async needed:

1. **`control_api.rs`** — blocking JSON-lines client: `get/set/subscribe/
   load`, correlation ids, a `subscribe`-driven event stream. Mirror of
   `hands/mixxx_control.py`.
2. **Typed control namespace** — a small codegen script scrapes this doc +
   the manual appendix into `controls.rs` (enums for groups, consts for
   keys) so "the whole board in Rust" is compile-time-checked, not stringly.
3. **Gesture executor** — port `run_mix_plan.perform_transition`'s inner
   timing loops (smoothstep crossfade, transformer cuts, filter sweeps) plus
   the new vocabulary above as `clawdj gesture <name> [--beats N …]`. This is
   where Rust actually earns its keep: sub-beat (1/16-note ≈ 40 ms) timing
   for stutters/juggles/scratch ramps, where Python jitter starts to matter.
   `BeatClock` (live.rs) gains a TCP `subscribe beat_active` source next to
   its MIDI one.
4. **Runner integration** — Python `run_mix_plan` stays the orchestrator and
   shells out per gesture (later: a long-running `clawdj serve` fed plan
   events). The plan format does not change — same principle as mix
   profiles: judgment upstream, execution declarative.

Python remains the right home for everything in `brain/` (planning,
enrichment, agents — I/O-bound). Port the hands' inner loops, not the brain.
