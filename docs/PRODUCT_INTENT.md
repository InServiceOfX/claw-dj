# Product Intent (PRD)

This current product-intent record is maintained by `pdd intent apply`.
Each accepted change links to an immutable intent event.

<!-- pdd-intent-entry:portable-music-collection-no-hardcoded-volume-la-288cef1d:start -->
## Portable music collection: no hardcoded volume label, safe availability, deferred relative identity

- Intent event: [`docs/intents/intent__portable-music-collection-no-hardcoded-volume-la-288cef1d.md`](intents/intent__portable-music-collection-no-hardcoded-volume-la-288cef1d.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_project_adoption`
- Technology: `not stated`

> claw-dj must not hardcode a volume label or machine-specific mount prefix in code or configuration defaults. The user's music collection lives on an external USB stick that they specify; each machine resolves where that collection is currently mounted, and scan roots stay user-specified relative to it. Record the collection's mount base and a stable collection id in the library index so identity is re-derivable without reading code. Track identity remains the absolute file path for now; because of that, the volume label is part of the collection contract and a replacement volume must be named identically, which must be documented. A root that exists but suddenly returns no files must not mass-mark its tracks unavailable and orphan their enrichment and human dj_notes; an unmounted collection must never be read as deleted. Initial metadata population stays available three ways (command-line script, GUI Check-new-music button, and agent-run) with the same result, and must never re-read tags for already-indexed unchanged files. If track identity is ever migrated to collection-relative paths, the stored keys and the scan's identity function must change atomically, and a partial migration must fail loudly rather than silently duplicate rows or drop lookups.
<!-- pdd-intent-entry:portable-music-collection-no-hardcoded-volume-la-288cef1d:end -->
