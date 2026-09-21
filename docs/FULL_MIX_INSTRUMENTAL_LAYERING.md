# Highlighting a vocal record over a continuous instrumental

Research and local audit: 2026-09-20. Accepted example: **50 Cent — WHO SHOT
YA, 24 Shots**, featuring the performances Ernest identifies as 50 Cent and
Tony Yayo, over **The_Notorious_BIG — Who_Shot_Ya (Instrumental), Promo VLS**.
This document specifies the reusable live feature and audits the existing
Astra render. It does not claim the general live feature is implemented.

## Musical approach

Use a sustained **EQ blend**: the vocal record remains the foreground while
a second deck supplies a complementary instrumental bed throughout its body.
DJ TechTools describes precisely this situation: an instrumental's midrange
can mask a singer, so reduce the competing instrumental frequencies while
retaining enough musical content. EQ cannot cleanly extract vocals from a
finished mix because instruments and voices share frequencies. This approach
therefore accepts a foreground record that already contains drums and bass.
[DJ TechTools, EQ Mixing: Critical Techniques and Theory](https://djtechtools.com/2012/03/11/eq-critical-dj-techniques-theory/).

Long overlaps are established DJ practice. Digital DJ Tips describes combining
one record's vocal/melodic material with another's rhythm section, using level
balance and compatible musical content. For this specific repair, my choice
is the matching Who Shot Ya instrumental: preserve the recognizable backing
and improve its weight, rather than introduce a new harmonic arrangement.
That preference belongs to this full-mix reinforcement feature; the existing
acapella story still prefers an interesting alternate bed when appropriate.
[Digital DJ Tips, mixing guide](https://www.digitaldjtips.com/the-ultimate-guide-to-mixing-house-music/).

Three checks have different jobs:

1. **Tempo and beat timing:** corresponding beats stay together over time.
2. **Backbeat and musical pattern:** kick/backbeat identity and the repeating
   phrase agree. Syncing ticks alone does not prove these identities match.
3. **Waveform phase:** shared audio does not cancel or acquire a hollow tone.

Mixxx explains that a weakening kick can precede an audible double kick as
records drift. Its automatic matching depends on accurate grids; prolonged
blends still need monitoring. My added requirement here is an explicit
backbeat check at entry, through the body, and after loop wraps.
[Mixxx: beatmatching and Sync Lock](https://manual.mixxx.org/2.5/en/chapters/djing_with_mixxx.html#beatmatching-and-mixing).

Near-identical backing tracks are especially sensitive to small timing errors.
Comb filtering occurs when correlated signals combine with a short delay.
Unequal levels, complementary frequency content, and careful alignment can
reduce the problem; more bass gain alone does not solve it. A polarity flip
also cannot fix every frequency of a delayed copy. Check stereo and mono,
and compare at matched loudness before deciding which version sounds better.
[iZotope: What Is Comb Filtering?](https://www.izotope.com/community/blog/what-is-comb-filtering).

## Proposed sound treatment for the Who Shot Ya pair

These are engineering choices for an audition, not universal knob settings:

- Keep 50 Cent/Tony Yayo's phrasing and vocal presence in front. Do not label
  their full recording an acapella or require stem extraction to use it.
- Let the supplied instrumental provide most of the clean low end. Reduce
  overlapping low frequencies in the foreground only as far as its vocal
  weight and the combined sound permit. Avoid two equally loud bass copies.
- Start the bed's upper frequencies quietly. Add enough percussion to define
  the groove, reducing the bed's midrange if it masks words. A permanent high
  pass on the vocal record may thin the rappers; do not assume it is harmless.
- Establish a stable balance for the body. Use smooth entrance/exit ramps;
  avoid repeated filter sweeps or automatic pumping under every syllable.
- A clean 32-beat bed loop is suitable for this measured example. Verify the
  loop contains the complete repeating musical figure and a clean wrap. Other
  songs may need another length or their full instrumental arrangement.
- Keep the approved 91.68 BPM clock for Astra. Source tempo measurements differ
  between these recordings; equal tags or equal speed-slider positions would
  not align them. Decide keylock by listening to the actual recordings:
  preserving vocal pitch and correcting a speed-shifted instrumental transfer
  can require different choices. Do not blindly key-match guessed key tags.
- The 24 Shots source must end **before 92 seconds**, including fades and
  residual layers. The instrumental can continue after the voice ends; it
  cannot excuse retaining the forbidden 50 Cent tail.

Mixxx offers configurable per-deck EQs and Quick Effects. Its documented
default EQ crossover points are 246 Hz and 2.5 kHz, so an aggressive default
bass cut can affect more than sub-bass. EQ models also differ in phase
response. The Astra offline filter below is not equivalent to a particular
Mixxx EQ knob setting.
[Mixxx: Mixer preferences](https://manual.mixxx.org/2.5/en/chapters/preferences/mixer.html).

## How to perform it in Mixxx

For an isolated body, use two decks: the foreground full mix and the clean
instrumental. For the continuous Astra sequence, reserve deck 3 for the bed
and alternate foreground records on decks 1 and 2. During a vocal handoff,
the outgoing vocal, incoming vocal, and bed may all be active. This allocation
is my proposed workflow; Mixxx supplies four decks, loop controls, headphone
cueing, and independent channel faders.
[Mixxx: interface and loops](https://manual.mixxx.org/2.5/en/chapters/user_interface.html#loop-controls).

1. Verify grids and the actual shared pattern before opening the foreground
   channel. Correct a bad grid during preparation; do not translate a playing
   library grid merely to disguise a wrong backbeat. Mixxx provides beatgrid
   correction and constant/variable-tempo analysis.
   [Mixxx: Beat Detection](https://manual.mixxx.org/2.5/en/chapters/preferences/beat_detection.html).
2. Cue the bed's clean loop; choose a stable tempo leader. For this constant
   instrumental, followers should not chase unreliable bootleg tempo analysis.
   Read back tempo and sync state rather than assume a one-shot sync button
   maintains a whole-body lock.
3. Route deck 3 independently of the crossfader. Balance its channel fader
   and EQ against the foreground while cueing. Bring it in on the matched
   pattern and retain it across the complete approved foreground interval.
4. Monitor pattern alignment, sustained level, and vocal clarity. Any needed
   one-beat identity correction happens before an audible foreground entry.
   A tiny timing drift calls for a small nudge, not a whole-beat jump.
5. Fade the foreground out before its source limit. Keep the bed sounding
   while the freed vocal deck loads the next recording. Fade the bed away
   only when the next backing has taken over smoothly.
6. Restore every control owned by this layer on exit; an abort must silence
   all decks used by this performance, including the support deck.

Useful controls, verified against the official control table and local fork:

| Purpose | Mixxx control |
| --- | --- |
| Bed bypasses crossfader | `[Channel3],orientation=1` (center); 0/2 assign left/right |
| Independent bed balance | `[Channel3],volume`, `pregain` |
| Tempo/phase preparation | `beatsync`, `beatsync_phase`, `sync_enabled`, `sync_leader`, `quantize` |
| Inspect sync role | `sync_mode`: 0 disabled, 1 follower, 2 leader |
| Repeat approved phrase | `beatloop_32_activate`, `loop_enabled`; explicit loop positions when needed |
| Correct small drift | `rate_temp_up_small`, `rate_temp_down_small` |
| Tone balance | `[EqualizerRack1_[ChannelN]_Effect1],parameter1/2/3` |
| Optional verified filter | `[QuickEffectRack1_[ChannelN]],super1` |

`orientation=1` is essential here: a centered crossfader position alone does
not protect the bed when the foreground crossfader subsequently moves.
Use an ordinary beatloop, not a rolling/slip effect that resumes elsewhere.
[Mixxx: Controls](https://manual.mixxx.org/2.5/en/chapters/appendix/mixxx_controls.html).

Quick Effect mappings are configurable. Inspect the loaded effect rather than
assuming that moving its knob always means a low-pass or high-pass filter.
Additional effects are optional; clean synchronization and complementary EQ
are the first tools for this task.
[Mixxx: Effects](https://manual.mixxx.org/2.5/en/chapters/effects.html).

Native stem playback is an optional later path, not a prerequisite. The 2.6
development changelog lists STEM-file support; that is not proof that a given
installed build separates arbitrary MP3s in real time. Confirm capabilities
before proposing stem-specific controls. The local checkout identifies itself
as 2.7.0-alpha; the broadly applicable workflow above uses documented 2.5
controls.
[Mixxx development changelog](https://manual.mixxx.org/2.6/en/chapters/appendix/changelog.html).

## Local control audit and implementation gaps

Read-only inspection found four accessible decks on port 9995, all stopped.
Orientation, sync mode, quantize, keylock, loop state, and all three EQ
parameters could be read. No playback, routing, EQ, or preferences were changed.

One important implementation trap: the local TCP API calls
`ControlObject::set`, which accepts the control's raw value. The built-in EQ
manifest defines neutral gain **1.0**; **0.5** is its normalized knob position,
not the raw neutral gain. `EffectKnobParameterSlot` transfers raw control values
to the effect. The existing runner uses raw 0.5 in several EQ resets/restores.
The read-only snapshot showed 0.5 on decks 1/2 and 1.0 on decks 3/4. A new live
layer must handle this distinction; do not copy the existing reset constants
as calibrated unity. Fixing the runner's existing EQ calibration is separate
pending runtime work, not a completed change in this research task.

Local evidence: `../mixxxes/mixxx/src/network/controlapiserver.cpp` (`handleSet`),
`src/effects/backends/builtin/equalizer_util.h` (`createCommonParameters`),
`src/effects/effectknobparameterslot.cpp` (`loadParameter`), and
`src/effects/effectparameterslotbase.cpp` (`slotValueChanged`) in that fork.

The existing `vocal_over_bed` branch in `hands/run_mix_plan.py` is a useful
starting point: it keeps the bed live and frees the vocal deck afterward.
It does not yet supply this feature's full contract:

- Its center-crossfader routine lacks separately specified foreground/bed EQ
  and gain envelopes; its hold is wall-clock based with one-shot sync.
- That branch returns before the ordinary branch's `snare_align` handling.
  Do not assume writing the flag already fixes its backbeat.
- Planner allocation, reset, cancellation, and stop-all paths primarily use
  decks 1/2. Adding a persistent deck-3 bed requires ownership-aware lifecycle
  handling and tests; sending a single extra `load` event is insufficient.
- Current stem pairing targets vocals-only files. The new foreground stays
  classified as a full mix and needs a distinct explicit layer relationship.

For general implementation, record foreground and bed identities, approved
source spans, body coverage, pattern anchors, loop bounds, gains/EQ envelopes,
deck ownership, and exit behavior in a layer object. Show simultaneous roles
in preview. These are design fields, not newly supported CLI directives.
Preserve current acapella pairing and short instrumental bridge behavior.

## Audit of the delivered Astra mix

The current **23:34.351 offline render** already carries this matching
instrumental throughout 50 Cent's allowed body. It is played as one finished
master in Mixxx, not as live independent decks.

| Item | Verified value |
| --- | --- |
| Foreground source interval | 0.000–91.950 seconds; hard limit remains 92 |
| Foreground mix interval | 391.504–483.863 seconds (6:31.50–8:03.86) |
| Instrumental mix interval | 218.975–487.003 seconds |
| Instrumental loop | 32 beats; source 20.334–40.618 seconds |
| Independent PCM comparison | Mix 405–475 seconds; maximum reconstruction error **0.0** |

The audit rebuilt the existing bed and foreground processing independently
and compared their sum with the saved premaster, without changing the audio.
The bed supplies predominantly low frequencies, with quiet upper frequencies
through the body and extra percussion near the handoffs.

For this 70-second window, 35–145 Hz RMS measured -25.57 dBFS for the original
foreground at the same gain and -21.09 dBFS for the combined layer: about
4.48 dB more bass-band energy. This is **not a loudness-matched preference test**
or proof of better intelligibility. The foreground's current subtraction of a
causal low-pass signal is also not a textbook low-shelf cut: its measured band
energy rose 0.42 dB. Future tuning should compare a calibrated EQ treatment by
ear rather than interpret the subtraction coefficient as uniform attenuation.

Audit script and JSON belong beside the external production package, under
`~/Music/claw-dj/exports/notorious-big-who-shot-ya-variations-gpt-6-astra/astra-pass-1/`.
No new listening pass or master replacement was needed to establish coverage.
Human approval of the vocal clarity, bass tone, and corrected handoff remains
the acceptance criterion.

## Acceptance evidence for the future live feature

Automated checks must cover full-mix identity; continuous bed coverage;
whole-phrase loop bounds; no forbidden source tail even during a layer;
backbeat identity at start/middle/end and loop wraps; three-deck occupancy;
no loading over a live bed; correct raw EQ unity; and complete cleanup after
normal exit, cancellation, load failure, and connection loss. Synthetic timing
and routing tests cannot establish perceived vocal clarity or bass quality.

For audio acceptance, compare the unreinforced and reinforced passage at
matched loudness, retain the original vocal level relationship, inspect true
peaks and mono compatibility, and listen for doubled backbeats, bass thinning,
masked words, loop clicks, and changes in balance. A/B samples and measurements
are local generated outputs and stay outside the source checkout.
