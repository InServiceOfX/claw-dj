# Intent: If you're able to scan and see I have a volume called "Elements". In...

<!-- pdd-intent-id: if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58 -->
<!-- pdd-intent-sha256: a1c09a581a55be0828dadc49c4dcde3ce44e22cbc2450dae6300d75c309730d0 -->

## Record

- Intent ID: `if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58`
- Kind: `add`
- Supersedes: none
- Approval ID: `if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `a1c09a581a55be0828dadc49c4dcde3ce44e22cbc2450dae6300d75c309730d0`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `sqlite`

## Original Request

> If you're able to scan and see I have a volume called "Elements". In the GUI I have, http://127.0.0.1:8787/#curate is there a way to "switch" to the new music collection and restart "the scan" of the music collection for useful metadata? Also would need to create a new sqlite on the volume if it's not there. It's ok upon start.sh or start of GUI to default to the previously used music collection. so that start up isn't asking use which music collection. But help me implement ability to start a new music collection while saving the previous music collection "settings" if any.

## Must Stay Unchanged

- None stated.

## Examples

- None stated.

## Candidate Product Areas

- THE HARNESS-FACING CONTRACT.
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Library-scoped SQLite storage appending two CREATE TABLE IF NOT EXISTS blocks (bunches, bunch_members) to brain/library_index.py's SCHEMA.
- Optimistic-concurrency primitives.
- Start orchestration with port 9995 as a preference rather than a requirement.
