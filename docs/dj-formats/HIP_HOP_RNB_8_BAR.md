# Hip-hop / R&B 8-bar DJ format

Status: version 1, strict. Source: working session with a practicing
hip-hop/R&B DJ, relayed by Ernest on 2026-07-24.

**Archived 2026-07-24 → 2026-07-31.** Live A/B listening against plain
`none` + a free-text mix brief consistently sounded worse under this
format. Hidden from the GUI dropdown (`brain/dj_formats.py`, `status:
"archived"`) but still selectable via `--dj-format hiphop-rnb-8bar` on the
CLI — the grammar/planner code is intentionally kept, not deleted, in case
the underlying bug (not this spec) turns out to be fixable. See
`PROGRESS.md`.

This is a transition grammar, not a mix-feel preset. It can be combined with
`dj-showcase`, `club-set`, or `mix-to-listen`.

## Deck convention

- Song A is the outgoing deck.
- Song B is the incoming deck.
- “Left” and “right” describe that example only. When the live decks swap,
  the rule swaps with them: outgoing/incoming semantics stay the same.

## Hard rules

1. Every incoming song starts on beat 1 of a bar.
2. When Song A exits at its chorus/hook, the transition anchor is beat 1 of
   that chorus/hook.
3. The recipes target songs with an 8-bar intro and an 8-bar chorus/hook:
   four beats per bar, 32 beats per phrase.
4. If the planner cannot prove a required beat-1 cue or phrase boundary from
   the beatgrid/timeline (or from explicit human DJ annotations), it must stop
   with a validation error. It must not substitute a generic blend.

“On the 1” means the first beat of a four-beat bar, not merely the next beat
reported by Mixxx.

## Allowed recipes

### `chorus_to_intro`

On beat 1 of Song A’s chorus, start Song B on beat 1 of its 8-bar intro.
Transition across the 8-bar phrase.

This is the default recipe when the required chorus and intro structure is
available.

### `acapella_hook_swap`

As Song A’s hook with no music begins, start Song B on beat 1. The two anchors
land together on beat 1.

The current lyric timeline cannot prove that a hook has no music. Require an
explicit, human-verified `hook_acapella_seconds=<seconds>` annotation on Song
A. Optionally set `format_recipe=acapella_hook_swap`; the annotation itself
also selects this recipe.

### `intro_loop_under_entry`

As beat 1 of Song A’s chorus arrives, jump Song A to beat 1 of its intro and
loop that intro for 8 bars. Start Song B on beat 1 while the loop is active,
then complete the handoff over those 8 bars.

Require a verified Song A intro loop point, either from its analyzed intro or
`intro_loop_seconds=<seconds>`. Select with
`format_recipe=intro_loop_under_entry`.

## Human annotation vocabulary

These tokens live in a track’s persistent `dj_notes`:

- `format_recipe=chorus_to_intro`
- `format_recipe=acapella_hook_swap`
- `format_recipe=intro_loop_under_entry`
- `intro_seconds=<seconds>` — verified beat 1 of the intro
- `chorus_seconds=<seconds>` — verified beat 1 of the exit chorus
- `hook_acapella_seconds=<seconds>` — verified beat 1 of the music-free hook
- `intro_loop_seconds=<seconds>` — verified beat 1 to loop on Song A

Explicit human annotations take precedence over inferred lyric segments, but
they still must resolve to beat 1 against the analyzed beatgrid.

## Non-claims

- The three recipes are recorded as given; no claim is made that they cover
  all hip-hop/R&B mixing.
- “Hook with no music” is not inferred from lyrics alone.
- A detected “chorus” label is evidence, not ground truth. A human annotation
  is preferred when the timeline is wrong.
- Format selection does not change track order automatically. Compatibility,
  key, tempo, and narrative ordering remain separate planning concerns.
