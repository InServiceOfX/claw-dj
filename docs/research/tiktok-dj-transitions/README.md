# TikTok DJ-transition research (ingested 2026-10-30)

Three short DJ tutorials, each with a `README.md` (metadata, summary,
takeaways, verbatim text, on-screen text, screenshots, mapping to claw-dj), a
timestamped `transcript.md`, and `screenshots/` (720px JPGs). Raw videos are
not committed. This is outside-world reference material. It cites
[`docs/DJ_TRANSITIONS_PLAYBOOK.md`](../../DJ_TRANSITIONS_PLAYBOOK.md) and
[`docs/MIXXX_CONTROL_SURFACE.md`](../../MIXXX_CONTROL_SURFACE.md) and does not
change any behavior.

| Video | Technique | Closest claw-dj concept | Proposed addition |
|---|---|---|---|
| [tayxsounds-7701063954830839053](tayxsounds-7701063954830839053/README.md) | **Drop swap / drop switch**: blend in during the build, then swap MID and LOW EQs so the incoming drop lands where the outgoing drop would | `entry_style=beat_drop`, `bass_swap`, the playbook's "drop-to-drop" gap | `drop_swap` technique: cue = `D_in - N bars`, start at `D_out - N bars`, LOW killed / MID at about 10 o'clock / volume 50% -> volume up -> MID swap -> LOW swap -> outgoing down at the drop |
| [lilianbilottaa-7682170614508965128](lilianbilottaa-7682170614508965128/README.md) | **Crossfader rhythm on a 1-beat acapella loop with reverb** | `transformer_cut` flourish | `loop_chop_rhythm` flourish: `beatloop_1` under `slip_enabled`, reserved Reverb slot, patterned crossfader cuts for 1-2 bars before a phrase boundary |
| [djaystayhigh-7692047131015777550](djaystayhigh-7692047131015777550/README.md) | **5-level scratch drill**: baby scratch, catch and drop, hot-cue scratch, crossfader (forward) scratch, speed up; "every release lands on the beat" | `scratch2` brakes and spinbacks, hotcue juggling, `snare_align` timing discipline | Grid-quantized *release* scheduling for scratch gestures; a "catch-and-drop" entry; a graded scratch test ladder for the Rust hands |

## Complementary evidence

The same three videos also have [caption-backed notes and media hashes](../tiktok/README.md) from `docs/tiktok-learning-intake`. Preserve both research passes; they are not six distinct sources. Each pass states its own transcription and visual-inspection limits. No implementation or human audition is implied by combining them.

Cross-cutting lessons:

1. **Timing is defined by where the sound lands, not where the gesture
   starts:** drops land on drops, scratch releases land on beats. Schedule
   the landing point in the hands engine.
2. **Phrasing first:** every technique begins N bars (a phrase multiple)
   before the target moment. This is the existing `phrase_beats=32` math.
3. **Gradual EQ trades beat instant kills:** the drop swap trades MID, then
   LOW, over the build, which supports turning `bass_swap` into a ramp.
4. **Flourishes stay sparing:** loop chops and scratches are showcase moves.
   They stay under `flourish_every` and `no_flourish`, and never become an
   abrupt song ending.

Method: yt-dlp, faster-whisper `small`, transcript cue points plus ffmpeg
scene detection, frames reviewed by eye (OCR was unavailable). Marketing and
short-form videos from the same batch are in the private Monoclaw repo
(`docs/shortform/tiktok/`).
