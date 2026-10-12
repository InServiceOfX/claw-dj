<!-- pdd-story-prompts: prompts/brain/popups_Python.prompt, prompts/hands/popup_obs_Python.prompt, prompts/hands/popup_overlay_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-12 -->
<!-- pdd-story-intent: docs/intents/intent__pop-up-music-facts-and-ernest-s-commentary-over--71fbe377.md -->
<!-- pdd-story-intent: docs/intents/intent__native-obs-pop-ups-with-automatic-and-manual-mod-40842147.md -->

# User Story: While the mix plays, pop-ups show music facts and my commentary

## Story

While claw-dj plays a mix (on the Twitch stream, or in a short or long video
made from a mix), large pop-up cards appear now and then over the picture,
like VH1's Pop-Up Video:

- **music facts** about the song and artist playing, written by the agent;
- **snippets of Ernest's own writing** about music, pop culture, and the
  development of hip hop and R&B, either quoted directly or distilled, and
  always marked as his with a small **EY** mark.

It is its own mini-application inside claw-dj. It runs beside the music and
never changes what plays.

## Acceptance criteria (observable)

1. **Pop-ups on a cadence.** One card shows at a time, for a few seconds,
   every so often (both adjustable). The text is large enough to read on
   stream, in a VH1-style bubble that pops in and out.
2. **About what's playing.** When a song is identified, the card is a fact
   about that song or artist, or commentary tagged with that artist, era or
   genre, whenever one exists. Otherwise a general fact or untagged
   commentary is shown. A card does not repeat until the others have had a
   turn.
3. **Knows what's playing on its own.** On the stream machine it works out
   the audible song from Mixxx: the playing deck whose channel fader and
   crossfader side are up. It identifies the song without any change to the
   mix runner. A manual "now playing" input works when Mixxx isn't used.
4. **Ernest's words are always marked EY; the agent's facts never are.**
   - Every card from Ernest's writing carries a small, subtle EY mark.
   - A direct quote is shown in quotation marks.
   - A distillation is labeled as one (not shown as a quote) and only comes
     from distillations Ernest has kept.
   - Agent-written facts carry no EY mark.
5. **A progression of thoughts.** Commentary can run as a short sequence from
   one piece of writing (1/3, 2/3, 3/3) over successive pop-ups, in the
   author's order.
6. **Writing lives in the repo, one folder per author.** Ernest writes
   ordinary Markdown in `commentary/ernest-yeung/`. Another person can add
   `commentary/<their-name>/` with their own initials, and their snippets are
   marked with their initials, not EY. Optional tags tie a piece to artists,
   eras or genres. Lines starting with `>` are preferred pull quotes. Template
   or draft files (names starting with `_`) are never shown.
7. **Facts are sourced and reviewable.** Each fact names its source and
   records whether a human has checked it. The overlay can be limited to
   checked facts.
8. **Also for videos.** For a recorded mix, the same cards come out as a
   timeline from the Mixxx cue sheet: each card inside the song it is about,
   none overlapping. They also come out as text overlays the video builders
   can burn in.
9. **Stream-ready, lowest footprint first (2026-10-12).**
   - The default stream mode drives OBS's own text sources (no browser source,
     so no embedded Chromium) through the authenticated OBS control.
   - Text is sized to the actual canvas, which may be smaller than 1920x1080 to
     save video bandwidth for audio.
   - A transparent web page (browser source) remains as an optional fancier
     mode.
10. **Automatic and manual.**
   - Automatic mode pops cards on its own for unattended streams.
   - Manual mode lets Ernest flip forward and back, show, hide, pause and
     resume, from the command line or a small control page on his phone or
     laptop.
11. **Preview without OBS.** The same cards, with the same timing and manual
   controls, can be previewed in the terminal.

## Examples

1. **Stream, 2026-10-12.** claw-dj plays *chill-afternoon-rnb-vol-01* on the
   Mac mini; OBS shows `http://<mac-mini>:8765/overlay`. While Joe's *Sweeter
   Than Sugar* plays, a bubble pops up with a fact about Joe. Two minutes
   later, a snippet of Ernest's essay tagged `R&B, 2000s` pops up in quotation
   marks with a small EY in the corner.
2. **Long-form video.** The Mo Money segment's cue sheet produces a timeline:
   facts about Diana Ross during *I'm Coming Out*, about Biggie during *Mo
   Money Mo Problems*, and an EY snippet about sampling. The video builder
   burns them in.

## Must not

- Do not show the agent's facts with an EY mark, or Ernest's words without
  one.
- Do not present a distillation as a direct quote, or show a distillation
  Ernest hasn't kept.
- Do not show template or draft files (`_` prefix).
- Do not change what the mix plays, or block it, if the overlay fails.
- Do not invent sources for facts.

## Source

Ernest, 2026-10-12, streaming at https://www.twitch.tv/clawdj with claw-dj
running autonomously on the Mac mini: "an application that will periodically
show in large text either interesting music facts about the songs and artists
we're playing, much like how VH1 used to have pop ups … snippets of [my
writing], or a progression of text about my commentary, either quoting me
directly or a distillation of my thoughts … mark with EY my initials when I'm
saying something … otherwise the music factoids you surface is all yours."
On location: "since it's me then the subdirectory to place it should name me,
as others in the future could possibly add their own."
