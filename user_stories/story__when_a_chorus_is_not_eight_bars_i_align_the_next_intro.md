<!-- pdd-story-status: drafted-2026-08-19 -->
<!-- pdd-story-areas: build_mix_plan, mix_directives -->

# User Story: When a chorus is not eight bars, align the next intro

## Story

As a DJ mixing hip-hop and open-format club records, when the outgoing
chorus is **not 8 bars**, I want claw-dj to line the next 8-bar intro up
with that chorus the way Remix Report taught it (eps 088, 093, 096, 099):

- **8-bar chorus:** start the intro on the chorus downbeat (the default).
- **10-bar chorus:** wait **2 bars**, then start the 8-bar intro
  (Drake *Over*/*Forever*, *Empire State of Mind*).
- **6-bar chorus:** skip **2 bars** of the incoming intro so 6 bars of
  intro cover the 6-bar chorus (*Magic Stick*, first *Pump It Up*).
- **12-bar chorus:** wait 4 bars (*Get Low* — mix from the start of
  “from the window to the wall,” not mid-chorus).

I do **not** want 24- or 40-bar choruses to add 16–32 bars of ride.
Remix Report said mix those out earlier.

## Acceptance

- `chorus_bars=10` on the outgoing track adds 8 beats of ride before the
  transition and notes the wait.
- `chorus_bars=6` advances the incoming cue by 2 bars of its own tempo
  and marks `chorus_intro_skip_bars=2`.
- `chorus_bars` outside 4–12 is ignored for auto-alignment.
- Human `ride_beats` is still the ride; the wait is *added* for 10/12 so
  the intro does not drop two bars early.

## Source

Whisper + analysis:

- `Data/Public/Videos/Youtube/parsed-CtA3yOULp7k/`
- `Data/Public/Videos/Youtube/parsed-MXz0B05_z0o/`
- `Data/Public/Videos/Youtube/parsed-aaRsbpfAan8/`
- `Data/Public/Videos/Youtube/parsed-H9TB81qM34s/`
