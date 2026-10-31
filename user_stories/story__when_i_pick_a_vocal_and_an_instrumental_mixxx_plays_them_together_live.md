<!-- pdd-story-status: implemented-2026-10-31; awaiting Ernest's first live listen -->
<!-- pdd-story-areas: stems, stem_crate, stem_layer_plan, stem_layer, api_stems, playlist_editor, web/stem_crate, mix_llm_refine, run_mix_plan -->
<!-- pdd-story-prompts: brain/stem_crate_Python.prompt, brain/stem_layer_plan_Python.prompt, hands/stem_layer_Python.prompt, brain/api/api_stems_Python.prompt, brain/mix_llm_refine_Python.prompt, brain/plan_notes_Python.prompt -->

# User Story: I pick a vocal and an instrumental, and Mixxx plays them together live

Extends [vocals-only and instrumental-only tracks are layered, not sequenced](story__when_i_add_vocals_only_and_instrumental_only_tracks_i_layer_them_i_do_not_play_the_acapella_in_full.md).
Its rules still hold: never a dry acapella, the bed stays live, and Get Up
over Outta Control Instrumental is the canonical layer.

## Story

As the claw-dj operator, I want claw-dj to know which tracks in my library
are **instrumentals** and which are **vocals only** (acapellas or vocal stems).
Then the LLM can plan blends that put one song's vocal over another song's
instrumental, and Mixxx can perform them live.

Inspiration: on the Soul Digger Twitch stream, André 3000's verse from UGK
*Int'l Players Anthem (I Choose You)* was laid over George Michael *Careless
Whisper*, and it sounded great. The library has both pieces: *Int'l Players
Anthem (I Choose You) (Explicit Acappella)* and Wham! *Careless Whisper
(Instrumental)*.

## Acceptance criteria (observable)

1. **Track type.** Every library track is a full mix, an instrumental, or
   vocals only.
   - The type is found from the title tag first, then the filename. The tags
     are version tags: `(Acapella)`, `(A Cappella)`, `(Accapella)`, `(A
     Capella)`, `(Acappela)`, `[Vocal Stem]`, `(Vocals Only)`, `(Instrumental)`,
     `(Remix Instrumental)`, `(Instrumental Version)`, `(Inst.)`, `-Inst`,
     `(Karaoke Version)`, and so on.
   - False friends stay full mixes: a song *named* Accapella (Kelis) or
     Acapella (Karmin), "L.A. Cappella", "(Vocal Remix)", the 12-inch
     single's "(Vocal)" version, "Instrumental Hip-Hop", "TV Track" and "Dub".
   - I can override any track by hand ("vocals only", "instrumental", "full
     mix", or "auto" to undo). The override is stored as `track_kind=` in the
     track's global DJ note, so a rescan or a plan note overlay keeps it.
   - Python (`brain/stems.py`) and Rust (`clawdj stems classify --notes`) give
     the same answer on every shared case (`tests/fixtures/stem_kinds.json`).

2. **Two lists, backend and GUI.**
   - `python -m brain.stem_crate list` prints vocals only and instrumentals
     separately, with BPM, key and length. Mixxx's analysis comes first, then
     tags; "—" means not analyzed yet, and Mixxx analyzes a track when it loads.
   - The GUI's **Stems** page shows both lists, each scrollable and
     searchable. Every row has ▶ browser preview (not Mixxx), its BPM, key and
     length, why it was classified, a "hand" or "clean" flag, and a type menu
     for the override.
   - The Curate list badge uses the same classifier.

3. **Play them together, live.**
   - I pick one vocal and one instrumental (any genre each). "Plan (dry run)"
     shows exactly what will happen. "Play together in Mixxx" needs a tick
     first, and then plays both on decks 1 and 2 **at the same time for the
     vocal's whole length**, not as a quick crossfade.
   - It is a plan that commands Mixxx; it never renders a .wav.
   - I can choose where the vocal starts (for example André's verse): preview
     the acapella, pause, and click "Use preview position".
   - The vocal plays at its own speed (no stretched voice). The instrumental
     follows its tempo with keylock on. Tempos more than 8% apart are refused,
     with a request to pick a closer instrumental.
   - Levels are similar, with the voice slightly in front. Mixxx ReplayGain is
     trusted when both tracks have it; otherwise claw-dj equalizes measured
     loudness by turning the louder one down. A full-mix bed dips its mids and
     highs so its own singer steps back.
   - The instrumental plays alone for 8 bars (or 4 or 16), then the vocal
     enters on a bar. After the last word the instrumental fades over 16
     beats. It is never cut off.
   - Stop works at any time (a short fade). It refuses to start while a mix or
     an audition is playing.

4. **Backbeat exact, no off-by-one count.**
   - An acapella has no drums. Its timing is borrowed from the analyzed full
     mix of the same song, which has the same vocal take: the two are lined up
     by cross-correlating the voice, both halves must agree within 20 ms, and
     the full mix's measured snare timing then applies to the acapella.
   - The instrumental's snare is measured directly. Snares therefore land
     together on 2 and 4.
   - Count 1 vs 3 cannot be measured reliably yet, so it is labeled "count 1
     guessed". The A/B choice moves it by a whole snare cycle (2 beats) and
     **never by 1 beat**, which would put the snare on 1 and 3.
   - In the vocal's silent first bar the live timing is checked against the
     30 ms guard. It is corrected once while still silent, and never moved
     mid-word.
   - Without an analyzed full mix, the plan says the vocal's backbeat is
     unverified.

5. **The LLM plans pairings.**
   - In a mix build, the order-review sheet tags each stem's `type` and gives
     each vocal its best `layer_beds` (tempo, then key, a different song
     preferred).
   - The model chooses the pairing by placing an instrumental right before
     the vocal. The builder layers the vocal over it for the vocal's whole
     length in the instrumental's beats.
   - In the full-mix runner, a full-mix bed (`bed_loop`) gets the same mids and
     highs dip. Instrumental beds are unchanged, so the approved Get Up layer
     sounds the same.

6. **Later, proposed only:** stems from full mixes (Demucs). See
   `docs/proposals/STEM_SEPARATION_DEMUCS.md`. Not built.

## Must not

- Render audio, or start Mixxx without a button press or an explicit command.
- Play an acapella dry, or stack two vocals.
- Shift a count by one beat, or call a guessed count verified.
- Write Mixxx's database. All Mixxx DB reads are read-only.

## Source

Ernest, 2026-10-31:

> New claw-dj user story: vocals-only and instrumental tracks
> (acapella-over-instrumental blends). Inspiration: on the Soul Digger Twitch
> stream, André 3000's verse from UGK "Int'l Players Anthem (I Choose You)"
> was laid over George Michael "Careless Whisper" and it sounded great. …
> In the GUI and also in the backend, I want to be able to have a list of all
> the songs that are vocals only and all the songs that are instrumental only.
> … i want to as a user be able to quickly scroll through and select either
> vocal only or instrumental only and listen to it as a preview. Then I'd
> like to have mixxx play them together at appropriate similar levels so i
> could see how a vocal and an instrumental sound like together. They each
> respectively can be from any genre. i don't want a new .wav render that
> defeats the purpose of live mixing. It's a plan that commands mixxx to play
> both live together.
