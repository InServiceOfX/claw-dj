# Short-form video notes — promotion format and tooling research

**Source:** public TikTok account @itstundealao (274 posts as of 2026-11-06), audited via `yt-dlp --flat-playlist` (262 listed), local Whisper transcription (90 posts), and frame inspection (22 posts). Evidence bundle archived privately; only paraphrased practical notes appear here.

## "Fact or Hype?" format — adapted for authentic claw-dj demos

Since mid-2026 the creator's posts frequently use a repeating structure:

1. **Hook claim** — a one-sentence promise (on-screen text and spoken).
2. **Source / repro setup** — the GitHub repo page visible, followed by an install command in a coding agent.
3. **Live test** — the feature running, with real output shown.
4. **Real cost / latency** — actual spend or timing displayed in that single run.
5. **Verdict** — a checkbox labeled "Fact" or "Hype," spoken aloud.

Posts with this structure often show 0.2–1.6M views, compared with 5–20K on many earlier tip videos. **Correlation only:** timing, algorithmic shifts, topic, and audience growth could explain the difference. The format did not necessarily cause growth.

### How to adapt for claw-dj

claw-dj can use the same skeleton on its actual working features, with honest constraints:

| Step | claw-dj adaptation |
|------|--------------------|
| **Claim** | State what the demo will show (e.g., "autonomous phrase-aware blend" or "live EQ swap on the incoming deck"). |
| **Setup** | Show the Mixxx window, the plan file, or a `hands/` CLI command—no repo clone if running locally. Screen share the local project if appropriate. |
| **Live test** | Run the mix or transition in Mixxx with audio. Show the waveforms moving. |
| **Real cost / latency** | Report what applies: seconds to execute the transition, CPU load, any model-call spend if one was used. No fake benchmarks. |
| **Verdict** | Honest outcome: "this worked," "this timing was off," "needs tuning." Do not fabricate a green checkbox if the demo faltered. |

**No AI influencer persona.** The demos are faceless screen recordings of the actual software. Commentary can be spoken or text overlaid; do not manufacture a synthetic talking head or AI persona.

## Candidate test ideas (labels only — not executed)

These are bounded proposals grounded in already-implemented claw-dj features. Each would be a single short-form clip, verified live before recording.

| Label | Feature demonstrated | Format fit |
|-------|----------------------|------------|
| `blend-16-counts` | gentle 16-beat crossfader ramp from one R&B track to another | live test + stopwatch timing |
| `measured-backbeat-start` | incoming deck waits for a measured snare before Play | show waveform, log output, and audible result |
| `stem-layer-vocal-over-bed` | vocals-only + instrumental layered in Mixxx in real time | cost = zero (local); show two decks + fader |
| `anthology-cue-navigation` | jump through the hip-hop anthology by cue label | fast demo of the existing GUI Arrange page |

These are labels for planning. Execution requires Ernest's approval and a verified live preview before any recording or posting.

## Creator content-file workflow (free local alternative)

The audit source describes a "content file" containing one creator's posts, transcripts, and engagement ([video 7699512057271422240](https://www.tiktok.com/@itstundealao/video/7699512057271422240)). That demo used paid BrightData scraping and Gladia transcription.

An equivalent workflow using free local tools:

1. **List posts:** `yt-dlp --flat-playlist "https://www.tiktok.com/@<handle>"` → JSON/CSV of video IDs and captions.
2. **Download (if desired):** `yt-dlp -f best "<url>"` per video.
3. **Transcribe locally:** faster-whisper `small` on CPU, or Whisper.cpp, over each audio track.
4. **Store:** plain-text or SQLite; add view counts manually from the public page or via a later metadata pull.

This keeps transcripts, captions, and metadata without subscription cost. It does not capture private analytics or live engagement rates, only public-facing numbers.

## Optional candidate: logo-design-skill

The audit flagged a repo `kaankiziltug/logo-design-skill` ([video 7699127837030157570](https://www.tiktok.com/@itstundealao/video/7699127837030157570)). The demo showed a brand-kit output for about $3.41 in model spend.

- **Source provenance:** repo name displayed on screen; owner inferred from search and commit-author line, not confirmed from the visible frame. License: MIT.
- Potentially useful for generating claw-dj promo assets if Ernest requests branding work.
- **Not adopted:** no branding change is requested in this pass.

## Source uncertainty

| Item | Status |
|------|--------|
| `FujiwaraChoki/supoclip` | Clone URL legible; video-model reported a different owner → **frame evidence favors FujiwaraChoki**. |
| `calesthio/OpenMontage` | Header + install URL legible; video-model reported a different owner → **frame evidence favors calesthio**. |
| `debpalash/VoiceStudio` | Low-resolution prompt URL → **conflict unresolved**. |
| `claude-watch` | Owner unconfirmed; commit message says "fork as taoufik/claude-watch"; candidates include `taoufik123-collab/claude-watch` and `bradautomates/claude-video` → **source unconfirmed**. |

Conflicting reads come from a video-capable model whose owner inference differed from legible frame text. Code-level verification would resolve these but is out of scope here.

## What this note does not cover

- Full account catalog or raw transcripts (kept in the private evidence bundle).
- Paid subscriptions, API calls, or tool installation.
- Marketing sends or posts (user requested findings only).
- Causal claims about view growth.
- General tools research (going to `claw-work` separately).

---

*Added 2026-11-07 from @itstundealao TikTok audit.*
