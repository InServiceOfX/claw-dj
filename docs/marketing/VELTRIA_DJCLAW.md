# VeltriaAI / DJ Treta / “DJClaw” — competitor read

Read 2026-08-12 from local clones under
`repos/VeltriaAI/{dj-treta,dj-treta-being,music-intelligence}` and the public
org https://github.com/VeltriaAI.

Per-repo notes (local branches only, not pushed to them):

- `dj-treta` → `NOTES_CLAW_DJ_READING.md`
- `dj-treta-being` → `NOTES_CLAW_DJ_READING.md`
- `music-intelligence` → `NOTES_CLAW_DJ_READING.md`

## Are they a competitor?

**Yes, same shelf: “an AI that DJs in Mixxx.”** Not the same product.

| | Veltria DJClaw | claw-dj |
|---|---|---|
| Who | Small org, no public members, ~4 stars on the main repo | Ernest’s project + published mixes |
| Job to be done | Install a *Being* that talks, downloads, and runs unattended | Play Mixxx like a hip-hop/R&B instrument |
| Proof | 30 h / $0.04 claim, TUI, intended live stream | Phrase-aware plans, A/B YouTube, Shorts |
| Genre | Techno / electronic / desi party | Hip-hop & R&B anthologies |
| Mixing truth | LLM names a technique; Python fires a 5-FX kit | Beatgrid, 8-bar / guided formats, deterministic hands |
| Library | yt-dlp + Lyria | Owned crates, Mixxx analysis, lyrics, sample lineage |

They even named the framework **DJClaw** (`djclaw` CLI). That is adjacent
branding, not proof they will eat the anthology work.

`dj-treta-live` is listed in their README and is **404** on GitHub.
`dj.treta.life` / `veltria.ai` did not respond from this machine on the
read date. Public org also has `beings-protocol` (OpenClaw-like markdown
memory — we already have that pattern) and `veltria-genmedia` (generic
image/video MCP). `music-intelligence` is one commit of Ishkur electronic
taxonomy.

## What they are ahead on

1. **Install and doctor.** One curl, Mixxx binary drop, `djclaw start`.
2. **Always-on story.** TUI + (intended) public player. Marketing as a
   24/7 radio station.
3. **HTTP Mixxx surface.** Agents like REST more than MIDI. We already
   have a control-api port; we do not need their C++ fork unless HTTP is
   the actual bottleneck.
4. **Talk-to-the-DJ UX.** `djclaw talk "go darker"` is a demo people
   understand in five seconds.

## What we are ahead on

1. **Craft in code**, not only in a knowledge markdown. Guided
   experimental vs format-none is a published A/B, not a prompt slogan.
2. **Phrase / lyric / sample lineage.** Their eval plan admits they
   score “did the model say bass_swap,” not “did the bass swap land.”
3. **Deterministic hands** (Python + Rust). Their philosophy is the
   opposite: tools stay dumb.
4. **Anthology program and short-form pipeline.** They do not appear to
   have a YouTube/TikTok craft channel.
5. **Tests that touch planning and Mixxx control**, not only LLM string
   match.

## Direction lock (Ernest, 2026-08-12)

Do **not** start MCP or a Mixxx HTTP fork because Treta has them.

- **MCP** is a wall socket. Useful if a *second* harness (Claude Code with
  no repo checkout) must drive decks. Grok/Claude already sit on the
  mix-plan CLI and the browser Arrange tab. Shipping MCP now is fashion,
  not craft.
- **HTTP Mixxx** is how *their* live “talk to the DJ” demo works. Ours is
  planned sets + deterministic hands. We already have a control-api port.
  Fork Mixxx only if that port is the actual bottleneck.
- **Do** finish claw-dj transition evals at phrase / position / audio.
  Do **not** import their string-match suite.
- Optional, later, cheap: `clawdj doctor` (Mixxx up? port? library?
  ffmpeg?). That is onboarding, not a new religion.

## What not to copy

- YouTube-as-library.
- “No deterministic DJ logic.”
- Self-writing SOUL as the mixer.
- Techno 32-bar defaults for hip-hop handoffs.
- Their product name.

## Bottom line

Watch the GitHub org. Do not build their socket layer this month.
Keep the thesis: **claw-dj is a DJ that happens to be software, not a
chatbot that happens to own two faders.**
