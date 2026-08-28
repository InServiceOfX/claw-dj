<!-- pdd-story-status: enforced-2026-08-28; Get Up over Outta Control Instrumental is the canonical keep-bed layer -->
<!-- pdd-story-areas: catalog, mix_order_brief, build_mix_plan, plan_mix_build, mix_directives, stems -->
<!-- pdd-story-prompts: order_constraints_Python.prompt, plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: order_constraints_Python.prompt, plan_mix_build_Python.prompt -->

# User Story: Vocals-only and instrumental-only tracks are layered, not sequenced as full songs

## Story

As a DJ curating a hip-hop / G-Unit set, I can **choose vocals-only and
instrumental-only tracks** and claw-dj **identifies them accurately**. Those
stems are **parts to layer**, not songs to play end-to-end.

When a vocals-only track is in the set I want it mixed **at the same time**
as an instrumental bed, **beat-matched**:

1. **Acapella break** — a short, chosen slice of the vocal over another
   song’s interesting beat or instrumental break; or
2. **Stem mash** — the vocal-only track over another **interesting**
   instrumental-only track.

The instrumental does **not** have to be the one that came with that vocal.
Pairing an acapella with its own instrumental is just the original record;
we already have that.

A vocals-only track is **not** placed as its own sequential slot
(empty bed, then the next title) — **including a 32-beat "short break."**
32 live beats of dry vocal is still the vocal alone. This is **not** a DJ
blend or mix transition: two decks play **at the same time**, because
otherwise all you hear are vocals.

The only exception is a **deliberate showcase** of a slice as an acapella
break (`showcase_acapella`). That is **very rare**. Dry acapella as its
own song is not a default, not a short-break fallback, and not something
the planner may invent. If you can hear only vocals, the mix is wrong.

The agent **chooses an initial pair** from any vocals-only / acapella and
any instrumental-only (or a cued, looped instrumental section of a full
song) already in the set. Later we may swap either stem to improve the
mash. `clawdj stems pair` (Rust) and `brain.stems.pair_vocals` (planner)
are that choice.

**No Banks exception.** I heard *On Fire (Acapella)*, *Warrior (Acapella)*,
and *Baby By Me (Acapella)* play on their own and they sounded bad. Dry
acapella is **very rare** — not a default for a strong rapper, not a
short-break fallback. Those three must layer over an instrumental-only
bed (or a looped cued section of a full mix), two decks at once.

## Acceptance criteria (observable)

1. **Accurate identification**
   - A track is vocals-only when the title/path (or a later human mark)
     means a dry vocal / acapella stem: `(Acapella)`, `(A Cappella)`,
     `Acappella`, `vocals only`, and obvious spelling variants.
   - A track is instrumental-only when it is an instrumental **version**:
     `(Instrumental)`, `[Instrumental]`, `Instrumental` as a version tag.
   - False friends stay **full mixes**:
     - “Vocal Remix” / “Vocal Version” of a produced record
       (e.g. *Jimmy Crack Corn (Vocal Remix)*).
     - A different song whose title merely contains a word like
       *Soldiers* or a folder named `Instrumentals` for a whole album of
       beats that are themselves the records.
     - Genre tag “Instrumental Hip-Hop” alone does not make a vocal
       record an instrumental stem.
     - **Clean vs Dirty:** a radio retitle or a CDS acapella that sits
       next to `(Clean)` is the clean vocal (e.g. *Still Will* for
       *I'll Still Kill*). Prefer the Dirty / Album / Promo VLS
       acappella, or the Dirty mix. Do not showcase the clean stem in a
       hip-hop set unless the human asked for radio.
   - The user can still **include or exclude** those stems in the set.
     Identification does not auto-drop them.

2. **Layered, beat-matched use (the default)**
   - A vocals-only track in a built mix plan is **overlapped** with an
     instrumental bed (instrumental-only track, or a verified instrumental
     stretch / break in a full mix). Both decks share a beat; the vocal is
     not a solo sequential ride through the whole file.
   - The instrumental bed **stays live** (`keep_outgoing_live`). After the
     layer, fade the vocal out and keep the bed; do not stop the
     instrumental when the acapella ends.
   - Canonical pattern (accepted 2026-08-28, 50centgunitera): *Outta
     Control - Instrumental* rides a short intro, then *Get Up (Acapella)*
     layers 96 beats on the other deck, xfader center, bed still playing,
     next song loads onto the freed vocal deck.
   - Preferred beds, in order:
     1. an **interesting** instrumental-only track already in the set
        (same-song instrumental is allowed but **not required**);
     2. an interesting beat / instrumental break in another full song.
   - The plan records that pairing (vocal track_id + bed track_id) so
     Arrange / dry-run can show it as a layer, not as “next song.”
   - Pairing a vocal that already has `entry_style=vocal_over_bed` still
     **moves the bed immediately before it**. A note is not enough if the
     previous track is a full mix with vocals.

3. **Do not play the acapella on its own**
   - Any solo `play_body` on a vocals-only track is a plan error,
     including a 32-beat or 64-beat "short break."
   - Playing a dry vocal sequentially requires an explicit human note
     (`showcase_acapella`) naming why. Banks On Fire/Warrior is **not**
     that exception — those dry rides sounded bad.
   - Default: `entry_style=vocal_over_bed` over an instrumental-only
     bed already in the set. If the only usable bed is a full mix,
     cue an instrumental stretch and loop it (`bed_loop_beats=32`).

4. **Same-song instrumental is not the interesting default**
   - If both the acapella and its matching instrumental are in the set,
     stacking them is legal but **not preferred** over a more interesting
     bed. The original mixed record in the set already is that stack.

5. **Out of scope / must not**
   - Do not invent `landing_seconds` / `chorus_seconds` for a stem.
   - Do not treat this as `acapella_hook_swap` (that recipe is a
     **music-free hook inside a full song**, verified by
     `hook_acapella_seconds` — a different object).
   - Do not auto-include every acapella/instrumental in the crate; the
     user chooses.
   - Do not start Mixxx to “prove” identification.

## Evidence (current anti-pattern this story forbids)

In `50centgunitera` the planner sequenced Lloyd Banks *On Fire (Feat.
50 Cent)* → *On Fire (Acapella)* → *Warrior (Acapella)* → *On Fire
(Instrumental)* as consecutive full slots, then *Baby By Me (Acapella)*
as a smooth_blend off that instrumental. Playing those acapellas on their
own sounded really bad. They must layer over the instrumental (or a
looped cued section) at the same time. The earlier "Banks exception"
is revoked.

**2026-08-19 cut:** first layer used the radio *Still Will (Acapella)*
(clean CDS stem). Ernest: it sounded bad mostly because it is the
**clean** version. Replaced with Promo VLS *I'll Still Kill (Acappella)*
over the same instrumental; clean *Still Will* acapella is excluded.

**2026-08-20 regression:** the live plan emitted `play_body` for 50 Cent
*Get Up (Acapella)* for 129 beats. Treated as a build failure.

**2026-08-28 regression:** Get Up (Acapella) still rode **32 dry beats**
(`ride_beats=32; trust_ride_beats`) after Best Friend. The 64-beat ceiling
had been treating a short solo as legal. It is not — you still only hear
vocals. Pairer now prefers the adjacent different-song *Outta Control -
Instrumental* (92 Ebm, relative to Get Up's F# / double-time 186) over
same-song *Get Up (Instrumental)*. Layer is `vocal_over_bed` 96 beats;
the instrumental stays live. Any remaining dry acapella without
`showcase_acapella` fails the build.

**2026-08-28 accepted first attempt:** the Get Up / Outta Control layer
is the pattern to keep. Ernest: no further mix-craft ideas on that pair;
enforce the story. Build fails if an acapella has a solo `play_body`, is
not `vocal_over_bed`, the bed is not kept live, or the bed is a full mix
with vocals and no `bed_loop`. Already-noted `vocal_over_bed` vocals still
get their instrumental moved in front of them.

## Source

Ernest, 2026-08-19, after listening to the 50centgunitera mix:

> The user should be able to choose vocals only and instrument only
> tracks which are accurately identified as such. The vocals only
> tracks are meant to be mixed at the same time, matching beat with an
> instrumental only track. In no way should a vocal only track be
> placed in full, unless we are showcasing a certain part of it as an
> acapella break, we usually want to either blend it into another song
> with an interesting beat or instrumental break, or play the vocal
> only track over another interesting instrumental only track, not
> necessary the same track that it came from (because we could just
> play the original song anyway). I just heard the Lloyd Banks tracks
> and how you mixed it even with the vocal only, it's pretty good,
> since Lloyd Banks is a good rapper even just with acapella. But
> that's more of an exception than the norm.
