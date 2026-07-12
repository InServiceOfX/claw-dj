# claw-dj two-minute demo script

Target: under two minutes, with most of the screen time showing the live UI
and Mixxx rather than slides.

## Spoken narration with demo cues

**[Open on the claw-dj library / New Music page]**

This is claw-dj. I wanted to create an autonomous—or semi-autonomous—DJ that
can take my music and create a ready-to-play mix.

**[Click “Check for new music”; show the incremental scan result]**

First, it incrementally scans my local music drive, so after the initial
index it only needs to process new or changed tracks.

**[Enter a brief in “Ask the DJ brain”; show the engine selector and results]**

To curate a set, I describe what I want in “Ask the DJ brain.” I can use
NemoClaw, powered by NVIDIA Nemotron; an H Company agent through `hai_agents`;
or compare recommendations from both.

**[Quickly check/uncheck recommendations and search for one track]**

The agent recommends tracks that actually exist in my library. I still have
control: I can search manually, add songs, or remove recommendations from the
working set.

**[Click “Finalize for Mixxx” and move to the Create Mix page]**

When the set is ready, I finalize it for Mixxx. claw-dj analyzes only the
selected tracks—not my entire library—for BPM, key, waveform-derived phrase
cues, and tonal similarity.

**[Enter a mix brief; show profile/order controls; click “Build mix plan”]**

When I create the mix, an agent can translate a creative request—such as
putting two songs together in the first half—into structured ordering
constraints. Then the local mix graph and deterministic planner choose the
actual transitions using BPM, key, genre continuity, phrase cues, and musical
relationships.

**[Show the plan summary, then click “Start Mix”; cut to Mixxx decks moving]**

Finally, “Start Mix” hands the saved event plan to the real-time Hands engine.
It controls Mixxx directly: loading decks, waiting for live beats, syncing
tempo, moving the EQ and filters, and crossfading precisely on beat.

**[Let the transition land; end on Mixxx or the claw-dj status screen]**

AI handles taste and intent. Deterministic software handles the beat.

## Accuracy notes for the presenter

- NemoClaw and H Company are selectable Brain engines; they are not both
  required for every run.
- Agents propose track IDs and optional ordering constraints. Local code
  validates them and creates the detailed transition plan.
- “Start Mix” performs no model inference. `hands.run_mix_plan` executes the
  saved plan through Mixxx's local control API and live beat clock.
- Phrase cues are waveform-derived energy/beatgrid features. Tonal similarity
  comes from chromagram analysis; avoid calling it a generic waveform
  similarity model.
