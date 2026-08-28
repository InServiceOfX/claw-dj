<!-- pdd-story-status: drafted-2026-08-19; vocal_over_bed planner+runner 2026-08-19 -->
<!-- pdd-story-areas: catalog, mix_order_brief, build_mix_plan, plan_mix_build, mix_directives -->
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

A vocals-only track is **not** placed in full as its own sequential slot
(empty bed, then the next title). The only exception is a **deliberate
showcase** of a slice as an acapella break.

**Lloyd Banks exception (not the rule):** I heard *On Fire* / *Warrior*
acapellas ride more than a stab and it still worked, because Banks is a
strong enough rapper that the dry vocal holds attention. That is an
ear-certified exception for a specific MC/performance, recorded in
dj_notes. It does **not** license every acapella in the crate to play as a
full song.

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
   - Preferred beds, in order:
     1. an **interesting** instrumental-only track already in the set
        (same-song instrumental is allowed but **not required**);
     2. an interesting beat / instrumental break in another full song.
   - The plan records that pairing (vocal track_id + bed track_id) so
     Arrange / dry-run can show it as a layer, not as “next song.”

3. **Do not play the acapella in full**
   - Default ride on a vocals-only track is a **short break** (a hook,
     a verse slice, or a verified lyric window) — not `full_track` and
     not a profile-length solo body.
   - Playing more of a dry vocal requires an explicit human note
     (`showcase_acapella` / trusted ride on that track) naming why
     (the Banks exception). Without that note, a long solo acapella
     body is a plan error.

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
(Instrumental)* → *Warrior (Instrumental)* as five consecutive full
slots. The Banks acapellas sounding good dry is the **exception** named
above, not acceptance of that sequence as the product.

**2026-08-19 cut:** first layer used the radio *Still Will (Acapella)*
(clean CDS stem). Ernest: it sounded bad mostly because it is the
**clean** version. Replaced with Promo VLS *I'll Still Kill (Acappella)*
over the same instrumental; clean *Still Will* acapella is excluded.

**2026-08-20 regression:** the live plan emitted `play_body` for 50 Cent
*Get Up (Acapella)* for 129 beats. This is now an executable build failure,
not merely discouraged prose. In this tribute, the selected *Outta Control
- Instrumental* is the compatible preceding bed; *Get Up (Acapella)* uses
`entry_style=vocal_over_bed` for a 64-beat layer and then fades while the
instrumental remains live.

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
