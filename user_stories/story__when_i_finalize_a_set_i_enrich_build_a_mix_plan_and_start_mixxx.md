<!-- pdd-story-status: product-flow-observed-2026-08-09 -->
<!-- pdd-story-areas: playlist_editor, enrich_set, build_mix_plan, run_mix_plan, mixxx_control -->

# User Story: Finalize a set, enrich analysis, build a mix plan, start Mixxx

## Story

As a DJ, once I have an **unordered set** of songs I want in the mix (order of
selection does not matter — the system or an LLM may reorder for the best
blend), I can Finalize for Mixxx, Analyze & enrich missing analysis, choose
mix feel and DJ transition format, Build mix plan, then Start mix (or
`scripts/run_mix.sh`) so Mixxx performs a continuous mix of that set.

## Acceptance criteria (observable)

1. **Unordered set on Curate**
   - Enabling tracks builds a working set; selection order is not the final
     mix order.
   - Agents and `Build mix plan` may reorder for blend quality unless fixed
     bunches / order constraints say otherwise.

2. **Finalize for Mixxx**
   - Locks a **finalized snapshot** of the current set for the Create-the-mix
     page (and active named plan storage when multi-plan is in use).
   - Opening Create the mix always reflects that finalized snapshot, not an
     accidental older global file.

3. **Analyze & enrich missing**
   - Analyzes tracks that still lack BPM/key (and optional lyrics/phrases/
     related enrichment) for the **finalized** set only — not the whole library.
   - Progress appears in a terminal-style console (dark background, green
     text) and the action button returns from a disabled/lightened state when
     finished.
   - macOS may still prompt for Mixxx file access on some tracks (see
     “Permissions” below). Pre-granting claw-dj or scan roots does **not**
     grant Mixxx Full Disk Access.

4. **Create the mix controls**
   - Mix feel (profile) is selectable and visually highlighted when active.
   - DJ transition format defaults to **no expert format**.
   - Optional H Company / order-engine controls interpret brief text and
     whether an external engine reorders (when configured).
   - **Build mix plan** succeeds only when the finalized set has required
     analysis for included tracks.
   - After a successful build, **Start mix** is enabled (bright red) and
     drives Mixxx via the control API.

5. **CLI parity**
   - `scripts/run_mix.sh` runs the **active named plan’s** `mix_plan.json`
     (same as GUI Start mix), not a stale legacy `brain/data/mix_plan.json`
     unless that is the only layout.
   - `scripts/run_mix.sh --help` documents dry-run, plan path, port,
     max-events, and record.

## Permissions note (Mixxx / macOS)

Mixxx is a separate process. When Analyze & enrich loads a track into a deck
for BPM/key, macOS TCC may show “permission is required to access the
following location” for paths Mixxx has not been allowed to open before.
Granting access to claw-dj, or scanning roots into SQLite, does not
automatically authorize Mixxx for the whole volume. Prefer System Settings →
Privacy & Security → **Files and Folders** / **Full Disk Access** for Mixxx,
or approve prompts as they appear. This story does not require per-track UI
picking inside claw-dj when Mixxx can open the path; the OS gate is external.

## Plan storage note

- Multi-plan workspaces store the live plan under
  `brain/data/plans/<slug>/mix_plan.json` with
  `brain/data/plans/active.json` pointing at the active slug.
- Legacy `brain/data/mix_plan.json` may still exist from older sessions and
  can point at unmounted volumes (e.g. USB322FD). Runners must prefer the
  active plan path so “I just built a plan” matches what Start mix / run_mix
  execute.

## Out of scope

- Guaranteeing zero macOS permission dialogs without OS-level grants.
- Full-library Mixxx analysis of an entire volume on first collection scan.

## Related

- Curate / collection story:
  `story__when_i_mount_a_music_volume_i_can_index_it_and_curate_a_set_with_the_dj_brain.md`
- Multi-plan intent under `docs/PRODUCT_INTENT.md` / `docs/intents/`.
