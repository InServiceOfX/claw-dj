<!-- pdd-story-status: drafted-2026-08-31 -->
<!-- pdd-story-areas: verse, lyric_timeline, onset_analysis, enrich_set -->
<!-- pdd-story-prompts: -->
<!-- pdd-story-dev-units: -->

# User Story: Missing lyrics still get verse start/stop from the vocal in the audio

## Story

As a DJ, I usually get **timestamped lyrics** (LRCLIB / LRC) and persist
them in the library index so the mix can respect verse start and stop.
When those lyrics **are not available** — a mixtape freestyle, a
bootleg, a deep-catalog cut LRCLIB never scored — I still need verse
boundaries.

Then claw-dj should look at the **audio itself**: frequencies and
time-structure typical of a **human voice rapping or singing**, find
where that voice starts and stops, and **discriminate verses from the
chorus / hook**. Persist those timestamps in SQLite (or whatever the
library database is) the same way synced lyrics are stored, so the
planner and `clawdj verse cue` can use them.

This is a **fallback**, not a replacement for real lyrics. Lyrics that
exist and match the file stay the source of truth. Wrong LRC (a
different song's words on this file, or timestamps past the duration)
must not silently beat a later audio-derived map.

Keep thinking about how to separate vocal from instrumental in whatever
container we actually have (`.mp3`, `.flac`, `.aac`, `.wav`, …):
frequency bands, harmonic/percussive splits, a vocal stem when we
already have one, onset of voiced energy versus the beat. The method
can evolve; the observable need is **verse start/stop when lyrics are
missing**.

## Acceptance criteria (observable)

1. **Lyrics first.** If synced LRC exists and its timestamps sit inside
   the file duration, use it. Do not re-guess from audio.
2. **Fallback when lyrics are missing.** `lyrics.source=not_found`,
   empty LRC, or a mixtape/freestyle with unsynced plain text only, may
   trigger audio verse detection on **selected / finalized** tracks —
   not the whole USB crate.
3. **What it writes.** Start/stop timestamps labeled `verse` vs
   `chorus`/`hook` (and later `skit` if we can tell spoken intro from a
   rap). Stored on the track in the library database next to
   `lyric_timelines`, with `source` naming the detector, not `lrclib`.
4. **Planner can consume it.** `brain.verse` / `audit_mix_plan` treat
   those segments like lyric segments: no mid-verse cue, no mid-verse
   exit, unless a human locked the ride.
5. **Chorus ≠ verse.** Hook/chorus repeats (same melody or shouted
   title line over the beat) are not protected as “the artist’s verse.”
   Best Friend’s opening hook must not become verse 1 just because a
   voice is present.
6. **Unknown stays legal.** If the detector is not confident, leave
   placement `unknown` and **do not invent** timestamps. Playing from
   0:00 and riding most of the file is the safe mix-to-listen fallback.
7. **Example (Who Shot Ya variations, 2026-08-31).** DMX, Jim Jones,
   Ja Rule, and K-Dot *Who Shot Ya* freestyles have no usable synced
   LRC. Until this fallback exists, the mix plays those files from 0:00
   for most of their duration so verses are not clipped by
   `phrase_body`.

## Must not

- Do not run expensive vocal/verse detection across the entire library
  scan. Selected and finalized tracks only, same rule as lyrics/chroma
  enrichment.
- Do not treat any voiced energy as a verse (ad-libs, DJ drops, crowd,
  chorus).
- Do not overwrite good synced lyrics with an audio guess.
- Do not require a GPU or a new paid API to mix a set that simply has
  no LRC — duration-based “play most of the song from 0:00” remains
  legal.
- Do not claim chorus vs verse is solved by a single high-pass. The
  first implementation can be conservative and low-recall.
- Do not start Mixxx to prove a timestamp.

## Source

Ernest, 2026-08-31, while fixing `notorious-big-who-shot-ya-variations`:

> Typically we can obtain the lyrics of songs and then we could have
> the AI agent automatically determine the timestamps matching lyrics
> of a song, and to persist that in our sqlite or whatever database we
> use in the future. However, if the lyrics aren't available,
> especially for a free style in a mixtape, or any other case, then
> possibly look into the waveform, but for frequencies that would
> frequencies typical of human voice either rapping or singing, to
> determine starts and stops of verses. We'll need to discriminate that
> from the chorus part. Continue to think of ways to separate by
> frequency or other techniques, the vocal part and instrumental part,
> given a song, whatever its format, .mp3, .flac, .aac, .wav, etc.
