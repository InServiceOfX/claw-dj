# Product demo + recruit campaign (claw-dj)

**Date:** 2026-09-05  
**Owner:** Ernest + TARS  
**Channels:** YouTube Shorts / TikTok `@claw__dj` / Reels (when ready) + longer YouTube `@claw-dj`  
**Links home:** https://claw-dj-links.vercel.app  
**Repo (convenience):** this file lives in claw-dj; rendered media stays **out of Git**.

Promotion is part of the product lifecycle
(`docs/ANTHOLOGY_AND_SHORT_FORM_PROGRAM.md`). This package is the **recruiting**
layer: prove the product exists, then ask for two specific humans.

---

## Goal (one sentence)

Show claw-dj mixing finished songs in Mixxx like a DJ — not a playlist app —
then ask for (1) a domain-expert DJ collaborator and (2) a paying customer who
will tell us how they want to use and deploy it.

---

## Two videos (do not merge)

| # | Format | Length | Job |
|---|--------|--------|-----|
| **V1 Product demo** | 9:16 preferred (also 16:9 cut for YT) | **45–75 s** | GUI walkthrough → build → play → two asks |
| **V2 Attention short** | **9:16 only** | **12–22 s** | Pattern interrupt + craft payoff + one CTA |

Never post a landscape recrop of a long mix as a Short (Noe / prior campaign
rule). Use dedicated 9:16 cuts.

---

## Noe-style stack (what we follow)

From prior Noe-structured work in `agent/hermes-skill/scripts/ab-shorts/POSTING.md`
and the 2026-08-05 short-form research:

1. **Motion / audio from frame 1** — never a silent logo hold.
2. **Hook triple in 0–2 s:** visual + verbal + on-screen text (≤8 words).
3. **One job per video** — demo *or* pure attention; not both at full length.
4. **Cuts every ~0.5–1.0 s** in the open; slow only on the musical payoff.
5. **Text readable muted** — large, high contrast, safe from top ~12% / bottom ~18%.
6. **Comment token** when possible (1/2, YES/LATE, DJ or CUSTOMER).
7. **CTA last 1–3 s only** — never bury the hook under the ask.
8. **Native upload** per app; do not only paste a YouTube URL into TikTok.

### MoneyPrinterTurbo → claw-dj mapping

MoneyPrinter-style pipelines auto-caption, punch-in text, and stitch stock B-roll.
We do **not** need that stack installed for this campaign:

| MoneyPrinter idea | claw-dj equivalent |
|---|---|
| Bold auto captions | Pre-rendered PNG overlays (`PIL`, no `drawtext`) |
| Fast hard cuts | FFmpeg `concat` / short segments |
| Stock B-roll | Mixxx recording + Flux DJ art + GUI screen capture |
| Hook script | Hook templates below |
| Batch variants | Same audio window, swap text (A/B) |

Recipe home: `agent/hermes-skill/scripts/ab-shorts/` +
`references/media-export.md`.

---

## Positioning (say this, not “AI playlist”)

**claw-dj** = autonomous / semi-autonomous DJ that **plays Mixxx like an
instrument**: crate + phrase-aware transitions, cues, EQ, loops, effects,
sample lineage, lyrical structure.

**Not:** shuffle + crossfade.  
**Not:** a music-production DAW.  
**Not:** “ChatGPT picks songs.”

Competitor note (Veltria DJClaw): same *category* (agent + Mixxx), different
*thesis* — we sell Mixxx-as-instrument craft, not unattended Being. See
`docs/marketing/VELTRIA_DJCLAW.md`.

---

# V1 — Product demo (45–75 s)

## Logline

Curate → pick a DJ format → Build → Mixxx moves → two asks: expert DJ +
paying customer.

## Structure (timeboxed)

| Sec | Shot | On-screen text | You say (tight) |
|-----|------|----------------|-----------------|
| 0.0–1.5 | Face OR decks already moving | `MIXING. NOT SHUFFLING.` | “This is claw-dj.” |
| 1.5–8 | GUI **Curate** — scroll crate, add 3–5 tracks | `CURATE THE CRATE` | “I pick records. The app holds the set.” |
| 8–16 | **Create / Arrange** — order visible; format dropdown | `PICK A DJ FORMAT` | “Then I choose how it should mix — guided or free.” |
| 16–22 | Click **Build mix plan** | `BUILD THE MIX` | “One build. Real cues and transitions.” |
| 22–38 | Mixxx live: crossfader, EQ, beat lock (best transition) | `LIVE IN MIXXX` | “It drives Mixxx like a DJ — blends, not playlists.” |
| 38–48 | Face cam, calm | `I NEED TWO PEOPLE` | Script block A below |
| 48–60 | Split card or two beats | `1 DJ EXPERT` / `2 PAYING CUSTOMER` | Script block B |
| 60–end | End card | `claw-dj` + link | “Link in bio. Comment DJ or CUSTOMER.” |

If under 50 s: compress Curate+Format to 10 s total; protect the Mixxx payoff
(≥12 s) and the two asks (≥12 s).

## On-camera script (teleprompter)

**Block open (≤3 s)**  
“This is claw-dj — a DJ that plays Mixxx like an instrument.”

**Block product (while GUI + Mixxx play; keep under 20 s of speech)**  
“I curate the crate. I pick a mix format. I hit Build.  
It plans phrase-aware transitions — then runs them live in Mixxx.  
Not a playlist. Actual DJing.”

**Block A — the two asks (clear, slow)**  
“I need two people.

One: a **DJ** — domain expert — who will work with me so claw-dj gets real
booth knowledge, not just BPM math.

Two: a **paying customer** who already sees a use — and will tell me how
you’d actually use it, what features matter, and how you want it deployed.”

**Block B — close (≤5 s)**  
“Comment **DJ** or **CUSTOMER**. Link in bio. Let’s build this with you.”

### Alternate 40-second cut (if attention dies)

Open on Mixxx blend only (8 s) → “That was claw-dj.” → 10 s GUI speed-ramp
(Curate→Build) → two asks (15 s) → end card.

## Screen-record checklist (Ernest)

1. Active plan with a **short, impressive** set (Who Shot Ya variations is
   fine if USB is mounted; otherwise All Night Long lineage or imported
   working mix).
2. Music volume mounted; dry-run once:
   `./scripts/run_mix.sh --dry-run`
3. Capture **browser GUI** at 1080p+ and **Mixxx** window (or full desktop).
4. Face cam optional but strong for trust on the asks.
5. Do **not** show private library paths, passwords, or OAuth screens.
6. Prefer **Format: none** or **guided** — say the name on screen once.

## Captions (V1)

```
claw-dj mixes in Mixxx like a DJ — not a playlist.

I need 2 people:
1) DJ domain expert
2) Paying customer who’ll tell me how they’d use + deploy it

Comment DJ or CUSTOMER
Link in bio
```

**Pinned comment:**  
`DJ = booth knowledge collab. CUSTOMER = paid pilot + product interviews. Serious only.`

**Self-score target:** Hook 4 / Retention 4 / Engagement 5

---

# V2 — Attention short (12–22 s)

## Logline

Same second: mix already flying + impossible-sounding claim + one comment token.

## Hook triple (pick one)

| ID | Visual | Verbal (T6-style) | Text (≤8 words) |
|----|--------|-------------------|------------------|
| H1 | Hard cuts of decks / blend | “This isn’t a playlist.” | `NOT A PLAYLIST` |
| H2 | Sample lineage handoff | “Same groove. New record.” | `SAME GROOVE. NEW RECORD.` |
| H3 | Build button → Mixxx moves | “I hit Build. Mixxx DJs.” | `BUILD → LIVE MIX` |

**Primary for recruit wave:** **H1** or **H3**.  
**Primary for craft wave:** **H2** (reuse All Night Long teasers).

## Beat sheet (18 s default)

| Sec | Action |
|-----|--------|
| 0–2 | Audio already mid-blend; text hook |
| 2–8 | 4–6 hard cuts: GUI flash, Mixxx fader, art, waveform |
| 8–14 | Hold one clean transition (payoff) |
| 14–18 | CTA: `NEED A DJ + A CUSTOMER` / `COMMENT DJ OR CUSTOMER` |

No face required. No long explanation.

## Captions (V2)

```
Not a playlist.
claw-dj drives Mixxx like a DJ.

Need a DJ expert + a paying customer.
Comment DJ or CUSTOMER.
```

**Pinned:** `Serious DJs and buyers only — how would you use this?`

**Self-score target:** Hook 5 / Retention 4 / Engagement 5

---

## Post order

1. **V2 attention short** first (reach).  
2. **V1 demo** 1–2 days later (convert comments → DMs).  
3. Optional: existing craft teasers (All Night Long A1–A3) as proof posts
   without the recruit CTA mixed in.

Same files → YouTube Shorts `@claw-dj` and TikTok `@claw__dj`.

---

## Production status (machine)

| Asset | Status | Path |
|-------|--------|------|
| Campaign brief (this file) | **In Git** | `docs/marketing/PRODUCT_DEMO_AND_RECRUIT_CAMPAIGN.md` |
| Overlay + short renderer | **In Git** | `agent/hermes-skill/scripts/recruit/` |
| Rendered 9:16 short(s) | **Disk only** | `Data/Public/Generated/claw-dj-recruit-2026-09/out/` |
| Prior craft teasers | Disk | iCloud `Documents/claw-dj/*teaser*9x16.mp4` + ANL shorts |
| Full GUI demo capture | **Ernest films** | needs screen + optional face |
| MoneyPrinterTurbo install | **Not required** | mapped to FFmpeg + PIL overlays |

---

## Rights / safety

- Commercial audio may mute or claim Shorts — report honestly; no evasion.
- Default YouTube API uploads **private**; publish only with Ernest approval.
- Do not commit WAV/MP4, cookies, or library paths.

---

## Success metrics (first 7 days)

| Signal | Good enough |
|--------|-------------|
| V2 3-s hold | ≥50% of views |
| Comments containing DJ or CUSTOMER | ≥5 serious |
| Profile taps / link clicks | measurable vs prior craft-only posts |
| DM quality | one real DJ **or** one buyer conversation |

Views alone are not success. **Qualified comments and conversations are.**
