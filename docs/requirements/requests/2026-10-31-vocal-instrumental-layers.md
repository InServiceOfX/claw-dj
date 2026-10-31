# Vocals-only and instrumental tracks — original user request (2026-10-31)

Intent input from Ernest, preserved verbatim below the line. Accepted story:
`user_stories/story__when_i_pick_a_vocal_and_an_instrumental_mixxx_plays_them_together_live.md`.
Action: add (extends the 2026-08-19 acapella layering story). Status: implemented on
branch `feat/vocal-instrumental-crate`, awaiting his first live listen.

---

New claw-dj user story: vocals-only and instrumental tracks (acapella-over-instrumental blends).

Inspiration: on the Soul Digger Twitch stream, André 3000's verse from UGK "Int'l Players Anthem (I Choose You)" was laid over George Michael "Careless Whisper" and it sounded great. I want claw-dj to be able to do that kind of blend.

As the claw-dj operator, I want claw-dj to know which tracks in my library are instrumentals and which are vocals-only (acapellas or vocal stems), so the LLM can plan blends that put one song's vocal over another song's instrumental, and the MIDI engine can perform them live in Mixxx.

1. Track type tagging: mark each track as full mix, instrumental, or vocals-only. Detect it from filenames/tags first (e.g. "Instrumental", "Acapella", "Vocals"), and let me override it by hand.
2. A command that lists all instrumentals and all vocals-only tracks separately, with BPM, key and length.
3. Planner support: let the LLM propose vocal-over-instrumental pairings, matching BPM and key, with the vocal's downbeats and phrases lined up on the instrumental's grid. Backbeat/snare alignment must be exact. Don't repeat the off-by-one-count bug we keep hitting.
4. Engine support: play both decks together for the length of the vocal (not a quick crossfade), with EQ/filter so the instrumental's original vocals don't clash if it's a full mix.
5. Optional later: generate stems from full mixes (e.g. Demucs) when no instrumental or acapella exists. Propose it, don't build it yet.

In the GUI and also in the backend, I want a list of all the songs that are vocals only and all the songs that are instrumental only, found from the song's metadata or the filename/title. I want to quickly scroll through and select either a vocal-only or instrumental-only song and listen to it as a preview. Then I'd like Mixxx to play them together at appropriate similar levels so I can hear how a vocal and an instrumental sound together. They can each be from any genre. No new .wav render: it's a plan that commands Mixxx to play both live together, enforcing our existing user stories and Python and Rust tools for a pleasant-sounding mix.
