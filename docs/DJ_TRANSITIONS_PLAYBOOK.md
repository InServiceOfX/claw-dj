# The Five Core Transitions — distilled for claw-dj

Source: "The Only 5 Transitions You Need as a Beginner DJ" by Blakey (DMC
champion), https://youtu.be/my9n3W3uJDE — transcript pulled 2026-07-19 and
mapped onto claw-dj's actual machinery. Read alongside
`docs/DJ_STYLE_GUIDE.md` (craft lessons learned by ear on our own mixes);
this file is the outside-world reference the style guide can cite.

The video's overarching thesis matches what Ernest's feedback has said all
session long: **clean and simple beats complicated, every time.** Five
techniques, each with one purpose, executed gradually and phrase-aligned,
outperform a bag of tricks.

## 0. The two fundamentals underneath everything

- **Beat matching** = tempo-match first, THEN align beats. Both decks at
  the same BPM before any blend starts. (claw-dj: `sync`/`set_bpm_target`
  handle tempo; `beatsync_phase` handles alignment when a `play_bpm` hold
  is active.)
- **Phrasing** = dance music moves in **32-beat phrases**; something
  always changes at the phrase boundary (drums in/out, vocals enter,
  percussion added). *Every* transition should begin at the end of a
  32-beat phrase — pressing play mid-phrase is the classic beginner tell.
  (claw-dj: `phrase_beats=32` is already the default, and the
  phrase-boundary math in `build_plan()` exists for exactly this; the
  onset/beat-phase parity work adds the within-bar half of the story.)

## 1. Long blend — volume only, very gradual

Nothing but the two volume faders, swapped slowly. No EQ, no effects. The
simplest and still one of the most effective transitions; done gradually
it is seamless.

- claw-dj mapping: `standard_blend`/`smooth_blend` crossfade path.
- Lesson to absorb: **gradualness IS the technique.** A long blend done
  fast is just a bad cut. When in doubt, fewer moves and more beats.
- Gap: our default recipes almost always add EQ dips/filter sweeps on
  top. A true plain volume-only blend (no `eq_dip_out_mid`, no
  `filter_sweep_out`) isn't currently a selectable technique — the
  `no_flourish` directive strips showcase moves but not the EQ/filter
  seasoning. Worth a `plain_blend` option.

## 2. Bass swap — full volumes, trade the LOW EQ

Both tracks at full volume; the incoming starts with bass fully cut, then
the bass is **gradually** traded from outgoing to incoming. Prevents the
two basslines clashing (mud, even PA distortion) while keeping both
tracks present.

- claw-dj mapping: we HAVE a `bass_swap` move — but it's an instant kill
  at the 50% point of the crossfade, not a gradual trade.
- Lesson: the video is explicit that the swap must be *gradual*, for the
  same reason the long blend must be. An instant low-EQ kill mid-fade is
  audible as a lurch. Worth migrating `bass_swap` to a ramp (e.g. swap
  over 8-16 beats centered on the midpoint) rather than a step.

## 3. Drop mix — cut the fader, play the incoming AT its drop

Play the outgoing through its build-up; at the phrase boundary right
before the outgoing would drop, kill its volume and press play on the
incoming exactly at the incoming's drop. Phrasing must be perfect or it
sounds completely wrong. Controls the crowd: they expect one drop and get
a bigger one.

- claw-dj mapping: `entry_style=beat_drop` (the brake/hard-cut entry) is
  our nearest relative, validated live on "Murder Was The Case".
- Refinement worth adopting: the video's version doesn't brake the
  outgoing — it cuts at the moment of maximum *anticipation* (end of the
  build-up), and the incoming enters at maximum *energy* (its drop). Our
  beat_drop entries currently land wherever the directive says; a
  "drop-to-drop" variant would pick the outgoing's exit at the end of a
  build and the incoming's cue at a chorus/drop onset (our
  phrase/energy analysis already finds high-energy entries).

## 4. Echo out — effect tail as the exit ramp

Apply a 1-beat echo, pull the volume fader down, let the echo tail ring,
then play the incoming clean — even into a **breakdown** rather than a
drop, for energy management. Works with tempo gaps up to ~10 BPM without
sounding wrong, because nothing rhythmic overlaps. The most-used effect
exit in DJing, but explicitly warned: **don't overuse it** — as an exit
strategy when needed, not a habit.

- claw-dj mapping: we have `echo_tease_drop` as an *opener* style and
  brake/spinback as dramatic exits, but **no echo-out transition exit** —
  this is the biggest genuinely-missing technique of the five.
- Why it matters for us specifically: our recurring pain point is
  large-tempo-gap transitions (Amazing→closer, Smooth Operator's old
  neighbors) where every blend-based approach sounded forced and the
  hard brake is the only current escape. Echo-out is the *gentler*
  standard answer for exactly that situation: clean exit, no tempo
  bridging needed at all, less dramatic than a brake. Mixxx has an Echo
  effect in its effects framework; wiring `echo_out` as a technique/move
  (effect on, fader down, tail, incoming clean at native tempo) would
  slot straight into `pick_technique()`'s large-gap branch alongside
  `tempo_gap_blend` and `half_time_or_cut`.

## 5. Crossfader cut — rapid cuts between two playing drops

Both tracks playing at full, crossfader snapped side to side to "remix"
live. High energy, creative, and — again explicitly — **use sparingly**.

- claw-dj mapping: exists as the `transformer_cut` showcase flourish
  (rapid crossfader chops). Already learned by ear on our own mixes that
  it reads badly on the wrong track (the Fastlove incident → the
  `no_flourish` directive). The video confirms the sparingly rule we
  already enforce via `flourish_every` rotation.

## Scorecard: what claw-dj has vs. what to build

| Video technique   | claw-dj today                          | Gap / action |
| ----------------- | -------------------------------------- | ------------ |
| Long blend        | standard/smooth_blend (+EQ seasoning)  | add a true volume-only `plain_blend` |
| Bass swap         | `bass_swap` move (instant, midpoint)   | make it a gradual ramp |
| Drop mix          | `entry_style=beat_drop`                | "drop-to-drop" variant: exit at build end, enter at drop |
| Echo out          | **missing as an exit**                 | build `echo_out` exit for large tempo gaps |
| Crossfader cut    | `transformer_cut` flourish             | none — sparingly rule already enforced |
| 32-beat phrasing  | `phrase_beats=32`, boundary math       | none — keep honoring it |

## For LLM-driven builds

Like `DJ_STYLE_GUIDE.md`, this file is written to be injectable into a
mix-directives prompt (`brain.mix_directives.build_prompt()`) so any
engine — Claude, NemoClaw, H-agent — constrains its transition choices to
these five patterns plus the style guide's genre notes, instead of
inventing flashier ideas the hardware executes badly.
