# Intent: When scripts/start.sh starts claw-dj, Mixxx control API port 9995 is...

<!-- pdd-intent-id: when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0 -->
<!-- pdd-intent-sha256: 18f454c0abfb5bb4a3027a9e470f7f85fd9a28aac3f997822d457a9b229eaec4 -->

## Record

- Intent ID: `when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0`
- Kind: `add`
- Supersedes: none
- Approval ID: `when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `18f454c0abfb5bb4a3027a9e470f7f85fd9a28aac3f997822d457a9b229eaec4`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> When scripts/start.sh starts claw-dj, Mixxx control API port 9995 is the preferred default, not a strict requirement. If a patched Mixxx instance is already running with its control API on another localhost port, discover that actual port, validate it with the Mixxx control API ping protocol rather than accepting an arbitrary open TCP port, reuse that Mixxx instance, and propagate the selected port consistently to the playlist editor, Analyze & enrich, Start mix, and command-line live mix execution. Do not tell the user to quit a usable running Mixxx merely because it is not on 9995. Preserve an explicit port override as the highest-priority choice. If Mixxx is running without any reachable control API, report that distinct condition honestly; do not connect to an unrelated service or silently start a second Mixxx instance.

## Must Stay Unchanged

- Do not tell the user to quit a usable running Mixxx merely because it is not on 9995.
- If Mixxx is running without any reachable control API, report that distinct condition honestly; do not connect to an unrelated service or silently start a second Mixxx instance.

## Examples

- When scripts/start.sh starts claw-dj, Mixxx control API port 9995 is the preferred default, not a strict requirement.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Serves brain/web/*.js and *.css.
- THE SINGLE READ THE ARRANGE TAB NEEDS, deliberately one call: ordered tracks, effective notes with their layer (plan|global) and diverged...
