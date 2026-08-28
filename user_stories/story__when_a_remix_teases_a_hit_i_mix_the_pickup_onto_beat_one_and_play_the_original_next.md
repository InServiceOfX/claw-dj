<!-- pdd-story-status: drafted-2026-08-19 -->
<!-- pdd-story-areas: mix_order_brief, build_mix_plan, mix_directives -->

# User Story: Mix a teased hit the way Remix Report mixes In Da Club

## Story

As a DJ mixing hip-hop and party breaks, when a remix or mashup **teases**
another song that is also in the set (Holla Boyz *Show Me Love In Da Club*
teasing 50 Cent *In Da Club*), I want claw-dj to:

1. start the remix so its **real downbeat** lands on 1 — not so the
   opening brake / “put your hands up” pickup *is* beat 1;
2. play the **original immediately after**, unless I already played the
   original before the tease.

I learned this from Remix Report Episode 0012 (DJ JD & DJ Jay Spring,
2010-02-08, https://youtu.be/hu_Y3dt2JWU). On-screen: “Wrong way —
starting as if the brake sound was on 1” vs “Right way — starting the
brake sound early so the beat comes in on 1.” Then: if the room is amped
on that beat, “you pretty much have to play In Da Club after this.”

## Acceptance criteria (observable)

1. **Pickup on 1**
   - `pickup_beats=4` on an incoming track is a valid dj_note.
   - The incoming cue is **0.00s** (the audible pickup).
   - The plan records a landing at beat 4 (4 × 60 / BPM seconds).
   - The transition into that track is `pickup_on_one_blend` and lasts at
     least those pickup beats, so the real downbeat can sit on 1.
   - Treating the pickup as beat 1 is documented as the wrong mix.

2. **Mashup payoff**
   - A title like “Show Me Love In Da Club (Hollaboyz Remix)” next to
     “In Da Club” in the same finalized set becomes an ordered pair:
     remix → original.
   - Same-song versions do **not** fire this rule (P.I.M.P. Remix vs
     P.I.M.P., In Da Club Instrumental vs In Da Club).
   - If the original already appears *before* the remix, do not drag it
     later. That is the exception Remix Report named.

3. **Out of scope**
   - Do not invent `landing_seconds` for “Go shorty” from memory. Use
     synced lyrics + `entry_style=verse_landing` when a human verifies it.
   - Do not require the Holla Boyz file to exist in the crate. The rule
     is general.

## Evidence

- Transcript + stills:
  `Data/Public/Videos/Youtube/parsed-hu_Y3dt2JWU/`
- Canonical transcript:
  `Data/Public/youtube-transcripts/remixreport_Episode_0012_Show_Me_Love_In_Da_Club_hu_Y3dt2JWU.json`
