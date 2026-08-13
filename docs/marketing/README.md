# Marketing and media (part of the product)

Promotion is already in `AGENTS.md` and
`docs/ANTHOLOGY_AND_SHORT_FORM_PROGRAM.md`. This folder is the operational
home: what we publish, which scripts render it, and how that relates to
adjacent AI-DJ projects.

## What lives in Git vs what does not

| In this repo | Stays on disk (not Git) |
|---|---|
| Renderers, overlay helpers, posting copy | Mixxx WAVs, full mix MP4s, 9:16 exports |
| Channel URLs, caption templates | OAuth tokens, cookies |
| Competitive notes | Personal library / Mixxx DB |

Recordings still come from `~/Music/Mixxx/Recordings/`. Scripts may hardcode
those paths for a given campaign; generalize when the same renderer is reused
a third time.

## Scripts

Checked in under `agent/hermes-skill/scripts/`:

| Path | Job |
|---|---|
| `render_transition_teaser.py` | Original 9:16 before/after card teaser (verified) |
| `full-mix/render_*_mix.py` | 16:9 YouTube masters (Ken Burns + waveform + titles) |
| `full-mix/make_overlays.py` | PNG titles (Homebrew ffmpeg has no `drawtext`) |
| `ab-shorts/render_shorts.py` | 9:16 A/B shorts from the two 2026-08-09 mixes |
| `ab-shorts/POSTING.md` | Noe-structured captions |

Procedure and verification gates:
`agent/hermes-skill/references/media-export.md`

## Live channels (canonical)

- YouTube: https://www.youtube.com/@claw-dj
- TikTok: https://www.tiktok.com/@claw__dj
- Links: https://claw-dj-links.vercel.app
- GitHub: https://github.com/InServiceOfX/claw-dj

## Competitor notes

See [`VELTRIA_DJCLAW.md`](VELTRIA_DJCLAW.md). Short version: VeltriaAI’s
DJClaw/DJ Treta is the same *category* (agent + Mixxx), a different *thesis*
(unattended Being vs Mixxx-as-instrument), and not a reason to dilute hip-hop
transition craft.
