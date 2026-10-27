# Do not turn uncertain backbeats into guessed count shifts

As Ernest, when I hear a mix enter on the wrong count, I want the DJ to
identify the musical downbeat and backbeat rather than guess a one-beat fix
from a beatgrid, so another alignment repair does not repeat the same mistake.

## What I need

- Keep approved transitions unchanged, including their starts and fade points.
- Keep the requested Maxwell-into-Maxwell pairing. Preserve the full opening
  of an iconic or late-snare intro instead of cutting it off to make timing easy.
- If the evidence does not establish the right count, say that it is unresolved.
  Do not pretend that matching grid ticks or alternating transients proves
  downbeat1 and snares2/4. Do not automatically choose a whole-beat correction.
- If I request an accurately verified start, a whole-count position error must
  not pass as verified. A verification failure must not launch the wrong cue.
- Never pair SWV with Sorry; do not force a percussive groove into a ballad or
  keep forcing a pair I reject as jumbled.
- I can explicitly choose implementation/building before an audition. That
  permission is not a claim that I heard or approved the new sound.
- If I start the current mix while the agent works, leave that run alone.
  Prepare the new version separately and let me test later.

## Source

Ernest's live listening logs, October17/20/22, and explicit October23 approval
to back up, skip the audition, implement Python changes, and test after returning.
Implementation status and executable evidence belong in
`docs/requirements/backbeat-start-safety.md`, not in this acceptance story.
