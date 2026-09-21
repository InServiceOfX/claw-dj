# One musical plan can render or perform live

As a DJ, I want the same saved musical decisions to work when I export a mix
and when I perform its transitions in Mixxx, so changing a cue or blend does not
require maintaining two different arrangements.

- Running my named plan performs overlapping tracks on separate decks.
- Rendering it makes a listening file without replacing the live plan.
- I can explicitly choose finished-file playback and see which mode I selected.
- Track notes and forbidden source regions apply to both executions.
- A long supporting instrumental remains underneath the selected foregrounds.
- Invalid or stale plans fail before playback; interruption stops all used decks.
- Reusable tools survive in the repository; generated audio stays outside it and
  old listening versions and temporary files are not accumulated.
- Live playback loads original music and performs rate/EQ/loop/fader changes in
  Mixxx while it plays. Rust handles the timing loop.
- Live playback MUST NOT require rendering a master or processing source copies.
- Offline export MUST NOT overwrite the executable plan or original recordings.
