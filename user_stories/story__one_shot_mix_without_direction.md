# Build a first mix without writing direction

As a casual listener, I want to select songs, a mix feel and an available DJ
brain, then press Build mix plan without writing instructions, so I get the
best listening experience the system can produce from its available analysis.

Accepted by Ernest on 2026-10-06 in
docs/intents/intent__one-shot-mixes-and-agent-refinement-of-the-curre-3dc013eb.md.

Acceptance:

- Direction is optional. A selected provider reviews the optimized order for
  every supported set (two or more songs), including an empty/whitespace brief.
  It receives the effective mix feel and full effective DJ notes. A blank brief
  skips only the brief-to-constraints call, not the DJ review.
- The model can retain an already good order. Reordering must preserve all
  finalized songs exactly once and pass the existing ordering/backbeat rules.
  Model failure or an invalid proposal keeps the optimized order and explains why.
- Build uses existing phrase, verse, tempo/key, stem, source-boundary and gentle
  fader protections. DJ showcase also requests validated model transition moves.
- Approved measured techniques are applied automatically when the current plan's
  recording-specific evidence supports them. No extra listener configuration is
  required for each build. Missing/stale/incompatible evidence keeps ordinary
  planning; a model cannot invent evidence or approvals. Producing that evidence
  automatically for arbitrary libraries remains future work.
- Preview shows the candidate order, model outcome and unverified blends before
  the separate Start action. Build never starts audio. One shot means a strong
  first pass, not a guarantee of subjective taste or an audible approval.

<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt prompts/brain/mix_llm_refine_Python.prompt prompts/brain/dj_brain_workflow_Python.prompt prompts/brain/advanced_mix_Python.prompt -->
