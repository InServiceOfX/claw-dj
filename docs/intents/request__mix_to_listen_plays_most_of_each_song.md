# Request: Mix to listen plays most of each song, blending on chorus/instrumental

Ernest, 2026-09-30, while running the R&B cooldown mix live (Mix to listen):

```text
So far it sounds pleasant. I do notice it's cutting the length of the songs
short in general. For DJ showcase, it's fine. But would in
http://127.0.0.1:8787/#mix if we choose Mix to Listen which i now have it at,
try to follow the user stories guiding song length and play most of the song
and blend where appropriate (i think my user story says to try not to blend
during a verse of an artist, blend during a chorus or instrumental only part
of a song, etc).
```

Decision (asked, answered "Change Mix to listen"): Mix to listen itself plays
most of each song; the planned "Lounge / bar" fourth preset is dropped.

Status: accepted. Kind: correct (supersedes the "do not change Mix to listen"
rule in `user_stories/story__when_i_mix_for_a_restaurant_bar_or_lounge_i_play_most_of_each_song_with_dj_blends.md`).

## Follow-up, same session

```text
oh and make sure both "modes" or Mix feels and build mix plan button
"respects" or "follows" the DJ notes, defined by the user locally, for each
respective song, if they have any DJ notes
```

Kind: constraint. Applied as story criterion 9 of
`story__when_i_build_a_mix_plan_the_order_is_chosen_for_the_best_blend_and_every_blend_keeps_the_backbeat.md`
and rule 22 of `prompts/brain/plan_mix_build_Python.prompt`;
`tests/test_dj_notes_respected.py`.
