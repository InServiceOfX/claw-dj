# Proposal: a more dependable one-shot Build mix plan (lessons from Grokicad)

Status: proposal, 2026-10-08. Not accepted yet. Serves the existing story
`user_stories/story__one_shot_mix_without_direction.md`.
Grokicad analysis: `repos/Grokicads/grokicad-local/docs/LLM_CALL_PATTERNS.md`
(local branch `docs/llm-call-lessons`).

## Where we are

- The baseline Ernest likes (tag `mix-to-listen-baseline-v1`) used **no model**:
  optimizer order + Mix to listen rides + DJ notes + snare checks.
- Every model review on the R&B set so far did not change that order:
  xAI timed out; Grok CLI hit "Max turns reached"; one earlier Claude review
  was rejected by the rules for adding unverified blends.
- So the model is not yet adding value to Build. The goal is to make it add
  value without ever making the baseline worse.

## What claw-dj does today vs Grokicad

| | Grokicad (explain parts) | claw-dj Build review today |
|---|---|---|
| Input | distilled JSON, sliced to the selection + top-10 scored neighbours | whole catalog (78 songs) + only the *current* neighbour edges |
| Size | small | ~2.6k tokens (brief call) + ~7.7k tokens (review), 78 songs |
| Calls | 1, no tools | 2; CLI providers run as agents with tools, up to 10 turns (uncommitted) |
| Output | short prose, unvalidated | the full 78-id order, validated |
| Prompt | versioned file with data model | inline Python strings |

Two mismatches matter most:

1. **The model must rewrite a 78-item permutation.** One missing or duplicate
   id and the whole answer is discarded. Grokicad never asks for that.
2. **The model cannot see the compatibility of the moves it proposes.** It gets
   scores only for the pairs that are already adjacent, so any swap is a guess,
   and the rules then reject it (blend score, backbeat).

## Proposed changes, smallest first

1. **One bounded call, no tools.** Build-review calls run single-answer, no tool
   use, for every provider (CLI or API), with a timeout that fits Build (e.g.
   180 s). Agentic, multi-turn work belongs to "refine the current mix", not
   to the Build button. *(Reverses the uncommitted 10-turn change for Build only.)*
2. **Distilled "mix sheet" input (the Grokicad distiller analogue).** Per song:
   id, artist/title, BPM, key, duration, intro length, verse/chorus outline
   (counts and where the last verse ends), snare read, DJ-note summary. Per song,
   the **top-K best next songs** from `MixGraph` with score, reasons and backbeat
   label (Grokicad's scored proximities). The model chooses among scored options
   instead of guessing.
3. **Ask for edits, not a rewrite.** Output a short list of operations against
   stable ids, e.g. `{"edits":[{"op":"move","id":"t031","after":"t012","why":"…"}]}`
   with a cap (e.g. ≤ 8 edits). The validator applies them one by one and drops
   only the illegal ones, so one bad edit no longer throws away the good ones.
   "No edits" is a valid, cheap answer.
4. **Schema-constrained output where the provider supports it**, with the same
   JSON validated in Python for all providers.
5. **Prompt as a versioned file** (`brain/llm_prompts/build_review.md`) with a
   data-model section, the reasoning steps, the edit format, and "say 'likely'
   when unsure" for the notes.
6. **Offline eval against the baseline.** Gates per build: share of each song
   played, fades ending inside a verse, fades starting inside a verse, mean
   blend score, snare-matched count. A model review is accepted only if it does
   not lower these vs the optimizer order. Record the raw model reply in the
   plan folder for audit.

## How to test, one variable at a time

Same 68-song set as the baseline, Mix to listen, same direction text:
1. Optimizer only (baseline numbers known).
2. Change only the DJ brain (e.g. Claude) with change 1 in place. Compare gates
   and order notes; listen only if gates pass.
3. Add changes 2–3 and repeat.

## Open decisions for Ernest

- Should the Build review be allowed to change only order (today), or also
  choose per-song "full body vs highlight" within a small budget
  (the "a few highlights per mix" idea)?
- Which provider to use as the reference for experiments.
