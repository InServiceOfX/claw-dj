<!-- pdd-story-areas: scan_library, library_index, dj_brain_workflow -->

# An interrupted scan does not leave Check for new music stuck

As Ernest, when I reopen Curate after an interrupted scan, I want the page to
tell me the scan stopped and let me check again, while leaving a genuine scan
and my existing music library alone.

- Reopening the editor after its scanner died releases stale progress and
  enables Check for new music. An interrupted scan is not labelled successful.
- This also works for an older scan record with no process identifier when
  the editor can prove that the old scanner is no longer working.
- A live scanner, a pending worker or uncertain ownership stays protected;
  being slow or paused is not evidence that a scan died.
- A new scan starting during recovery keeps its own progress. Recovery does
  not wait indefinitely behind a database writer.
- My existing tracks, notes, roots, availability and approved mix plans remain
  intact. Recovery does not automatically scan, enrich, build or play music.
- Reloading the page during a real scan continues showing its progress. A
  later successful check replaces the old interruption message.

Source: Ernest's October31 Curate0/4000 report and request to fix the behavior
in code. This is separate from redesigning the scan panel or adding a meter.
