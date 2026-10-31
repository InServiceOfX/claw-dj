# Recover interrupted scans — 2026-10-31

Accepted request: "is there a way to fix this behavior in the code???"

Context: Curate displayed Scanning Music0/4000. The scan began01:36:18;
the current editor launched01:36:57. No scan thread remained. The legacy
database record still had running=1 and scan_pid=NULL.113207 tracks were
already indexed. The older unmerged PID fix conservatively retains legacy
rows, so it would not repair this exact state by itself.

Read-only PDD intake: is-there-a-way-to-fix-this-behavior-in-the-code--399e117c.
Automatic regeneration is not used; these are narrow changes to existing
collection-aware runtime boundaries, with matching prompts and regression
tests. No model semantic certification is claimed.

Record scan ownership before discovery and clear it on completion/failure.
Recover dead processes and this editor's ended scan worker. For old records
without ownership, require a scan predating this editor, no active local scan
thread and database file-holder evidence excluding another live scanner.
Unknown evidence is not permission to clear a running scan. Use an atomic
state comparison and bounded write wait so new scans and active writers win.

Recovery changes only progress state and shows an honest interruption message.
It must preserve indexed music, availability, DJ notes, collections and mix
artifacts, and must never start a scan or touch Mixxx/OBS. Reloaded pages
resume polling genuine active scans. Successful rechecks clear the old error.

Tests cover live/dead/legacy ownership, old schema migration, a real second
process holding a temporary database, writer contention, new-scan races,
completion/failure cleanup and page initialization. Library and DJ regressions
run with temporary databases, preserving real collection-path resolution.
