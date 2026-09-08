# Zero automatic short handoffs

## Ernest's correction (2026-09-04, verbatim)

> or could we require that we get rid of almost all short handoffs? you almost never want to use it, as it breaks the energy and consistency of the beat, and only rarely, at most once if at all in a mix. We want to avoid as much as possible that's why I almost think we should require it to be not used at all or at most once in a mix

> it was a really poor decision to make it like this with the short handoff for weak or inconsistent local snare/clap evidence, please don't do it again

## Scoped interpretation announced to Ernest

Default to **zero automatic evidence-triggered short handoffs** in a mix,
not a budget of one for the runner to spend. This supersedes even the
eight-beat confirmed-mismatch recovery proposed in
`request__implement_gradual_blend_recovery.md` earlier in this implementation.
No automatic quota, opt-in setting, or UI feature is inferred from “at most
once”; a rare deliberate short handoff would require an explicit request.

- Keep the planned gradual fade for weak, missing, noisy or lost evidence
  AND measured mismatch. Preserve best-effort cue-preserving alignment and
  repeated verification; report mismatch honestly, without claiming success.
- Do not blindly jump audible decks or invent tempo changes to hide errors.
  Deliberately requested DJ cuts remain separate performance choices.
- A corroborated stopped/exhausted outgoing track is a physical constraint,
  not routine evidence recovery. Report it; do not promise a full overlap
  after audio runs out. Preserve existing body reservation for transitions.
- Build, previews and live execution share this policy. Older two-/eight-beat
  recovery metadata must not reinstate the retired policy. Add whole-chain
  regressions so the default is zero evidence-triggered short handoffs.
- No live Mixxx controls, active-plan rewrites or automatic playback restart.
- Update story, prompt, agent instructions and tests; independent review and
  live listening are separate validation gates.
