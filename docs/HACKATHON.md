# The Computer Use Hackathon — by H Company

Reference doc for the event this project started at. Stable info goes here;
for what's actually built and what's left, see [HANDOFF.md](HANDOFF.md).

## Event

- **What:** The Computer Use Hackathon, by H Company — San Francisco. Powered
  by H Company, NVIDIA and Accel, organized by Iterate.
- **When:** Saturday, July 11 – Sunday, July 12, 2026
- **Where:** San Francisco
- **Format:** Teams of 3–5 (up to 5), 120 participants
- **Platform:** https://iterate.inc/computer-use?welcome=true (resources tab:
  `&tab=resources`, home tab: `&tab=home`)
- **Slides from kickoff:**
  https://docs.google.com/presentation/d/1A2VLWHBEGnaZNxbCLGGPODJLwYHE0r0_VZN390IDaFw/edit
- **Discord:** https://discord.gg/6pf9FD42V

## Tracks (pick one)

1. **Computer Use** — agents that see, click, and type across real desktop
   apps. **This is our track** (claw-dj drives Mixxx's GUI).
2. **Browser Use** — agents navigating the real web.
3. **Free-For-All** — any idea using H Company agents.

Side challenges (optional, stackable): **Nvidia Challenge** (via NemoClaw),
**Voice Challenge** (best use of Gradium — TTS/STT).

## Judging — 100 points, 5 × 20

Technicality · Creativity · Usefulness · Demo · Track/sponsor alignment.

See [ARCHITECTURE.md](ARCHITECTURE.md)'s "Judging-criteria mapping" section
for how claw-dj's design targets each of these.

## Submission requirements

- Must use H Company models/agents.
- **Build entirely during the event — no prior commits to the repo.** (All
  commits on this repo are dated 2026-07-11 or later; keep it that way.)
- 2–5 person team.
- Open-source libs/APIs/pre-trained models OK if credited.
- Submit: a 2-minute demo video, the GitHub repo link, a short description.
- Judging: Round 1 is 5 min/team (1:30 pitch, 1:30 live demo, 2:00 Q&A) to
  all judges. 8–10 finalists go to Round 2: 3 min/team on stage (1:30 pitch,
  1:30 demo, no Q&A).

## H Company resources used

- Docs hub: https://hub.hcompany.ai/computer-use-agents/introduction
- Local desktop control docs:
  https://hub.hcompany.ai/computer-use-agents/desktop/local-control
- API keys / account: https://platform.hcompany.ai (sidebar → API Keys →
  Create API Key; key shown once, starts `hk-...`)
- Demo repo (cloud browser-use examples, not what we ended up using):
  https://github.com/hcompai/computer-use-agents-demos
- **What we actually use for local desktop control:**
  https://github.com/hcompai/holo-desktop-cli — see HANDOFF.md for why we
  picked this over the raw `hai_agents.Client()` SDK snippet from the
  hackathon's local-control docs.

## Credentials / logistics (kept out of this repo on purpose)

Wifi SSID/password and the Gradium redemption code from the hackathon
welcome packet are **not** written into any committed file — this repo may
end up public (submission requires a GitHub link), and those aren't
project code. Keep them in your own notes/password manager instead.

H Company login: `holo login` opens a browser to `portal.hcompany.ai`. Sign
in with the same account you used to generate the `hk-...` key on
`platform.hcompany.ai`, so the hackathon's API credits are actually on the
account `holo` authenticates as. Verify with `holo whoami`.
