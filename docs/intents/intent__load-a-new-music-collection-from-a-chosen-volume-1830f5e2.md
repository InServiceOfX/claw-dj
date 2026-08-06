# Intent: Load a new music collection from a chosen volume

<!-- pdd-intent-id: load-a-new-music-collection-from-a-chosen-volume-1830f5e2 -->
<!-- pdd-intent-sha256: 1830f5e2f988520e6fd66f1940a079431c9d53a09fb9e27072b07eb256952a31 -->

## Record

- Intent ID: `load-a-new-music-collection-from-a-chosen-volume-1830f5e2`
- Kind: `add`
- Supersedes: none
- Approval ID: `load-a-new-music-collection-from-a-chosen-volume-1830f5e2`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `1830f5e2f988520e6fd66f1940a079431c9d53a09fb9e27072b07eb256952a31`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `bash, python, sqlite`

## Original Request

> I want to be able to mount a new Volume if on Mac OS, or similarly on Linux, with a bunch of audio files that is a new collection of music. I want to be able to do this 2 ways but both ways must achieve the same exact outcome:
>
> 1. Through the GUI, I can choose a new "Volume" (the GUI currently knows where the music is; that has to become choosable), and then the user has the option to do an initial "scan" and "metadata" population for the music there. A new sqlite database is likely needed, since the sqlite data is carried with the music collection, so it makes sense for the sqlite database to be per-volume. The GUI asks the user whether it is OK to scan and which "root" directories to use for the music collection, gives an estimate of how long it will take, and asks the user to confirm before proceeding.
>
> 2. A command line script (bash shell or Python) to run the same thing if the user prefers that.
>
> Finally, enough markdown file(s) should be provided so an AI agent can do this for the user when asked.
>
> We cannot and should not do the Analyze-and-Enrich-song step (lyrics, chromagraph, etc.) for all songs on the drive. But for the parts of that procedure that do NOT require an API call -- so we do not hit API limits and get banned -- anything else that can be done on all the songs to add metadata without an API call should be offered to the user as an option during this initial process.
>
> Also: when we do Analyze and Enrich songs, Mixxx asks for file permission for some songs and I have to manually click, whereas for other songs it happens automatically. I want to understand why, and to fix -- or ask the user for permission to fix -- these file permission problems before starting up Mixxx to find key and BPM data via Mixxx.

## Must Stay Unchanged

- I want to be able to do this 2 ways but both ways must achieve the same exact outcome:
- But for the parts of that procedure that do NOT require an API call -- so we do not hit API limits and get banned -- anything else that can be done on all the songs to add metadata without an API call should be offered to the user as an option during this initial process.

## Examples

- Finally, enough markdown file(s) should be provided so an AI agent can do this for the user when asked.
- Also: when we do Analyze and Enrich songs, Mixxx asks for file permission for some songs and I have to manually click, whereas for other songs it happens automatically.

## Candidate Product Areas

- Pure stdlib shared types, no I/O and no imports outside the standard library.
- THE HARNESS-FACING CONTRACT.
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Registers '3 .
- Library-scoped SQLite storage appending two CREATE TABLE IF NOT EXISTS blocks (bunches, bunch_members) to brain/library_index.py's SCHEMA.
