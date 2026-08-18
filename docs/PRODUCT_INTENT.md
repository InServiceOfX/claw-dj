# Product Intent (PRD)

This current product-intent record is maintained by `pdd intent apply`.
Each accepted change links to an immutable intent event.

<!-- pdd-intent-entry:through-the-browser-gui-http-127-0-0-1-8787-cura-88023c99:start -->
## Preview a track quickly from the browser GUI

- Intent event: [`docs/intents/intent__preview-a-track-quickly-from-the-browser-gui-88023c99.md`](intents/intent__preview-a-track-quickly-from-the-browser-gui-88023c99.md)
- Change kind: `add`
- Scope: playlist GUI (not Mixxx hands)

> From `#curate` and `#mix`, preview a library track in the same browser tab with the native HTML5 audio element. Do not use Mixxx for this listen, do not require a browser plugin, and do not stream files that are not already in the loaded library index.
<!-- pdd-intent-entry:through-the-browser-gui-http-127-0-0-1-8787-cura-88023c99:end -->

<!-- pdd-intent-entry:portable-music-collection-no-hardcoded-volume-la-288cef1d:start -->
## Portable music collection: no hardcoded volume label, safe availability, deferred relative identity

- Intent event: [`docs/intents/intent__portable-music-collection-no-hardcoded-volume-la-288cef1d.md`](intents/intent__portable-music-collection-no-hardcoded-volume-la-288cef1d.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_project_adoption`
- Technology: `not stated`

> claw-dj must not hardcode a volume label or machine-specific mount prefix in code or configuration defaults. The user's music collection lives on an external USB stick that they specify; each machine resolves where that collection is currently mounted, and scan roots stay user-specified relative to it. Record the collection's mount base and a stable collection id in the library index so identity is re-derivable without reading code. Track identity remains the absolute file path for now; because of that, the volume label is part of the collection contract and a replacement volume must be named identically, which must be documented. A root that exists but suddenly returns no files must not mass-mark its tracks unavailable and orphan their enrichment and human dj_notes; an unmounted collection must never be read as deleted. Initial metadata population stays available three ways (command-line script, GUI Check-new-music button, and agent-run) with the same result, and must never re-read tags for already-indexed unchanged files. If track identity is ever migrated to collection-relative paths, the stored keys and the scan's identity function must change atomically, and a partial migration must fail loudly rather than silently duplicate rows or drop lookups.
<!-- pdd-intent-entry:portable-music-collection-no-hardcoded-volume-la-288cef1d:end -->

<!-- pdd-intent-entry:i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160:start -->
## I need a way to plan out multiple mix plans that can be "work in...

- Intent event: [`docs/intents/intent__i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160.md`](intents/intent__i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_project_adoption`
- Technology: `not stated`

> I need a way to plan out multiple mix plans that can be "work in progress" and easy way to switch between existing mix plans i'm still working on and then create new ones. Once I've chosen a mix plan I want to work on (of course each mix plan will be "colloqujially" named such as the "2001 expanded 25th anniversary mix" or the "Notorious BIG tribute mix" , I want to be able to easily add and remove songs and also easily work with a LLM or whatever to add dj notes on transitions, adjust transitions and effects bujt through speaking with an LLM, like we could load the mix plan, but when changes gets made by an AI agent harness or something like you hermes-agent, or cluade, codex, I can press "refresh" and see the refreshed order of the songs and transitions between each in a nice GUI way. Also, I wanna specify like 2, 3, 4, or some small n number of songs should be "bunched together", should follow an exact order, transition between them, because they sound very good with each other and be able to move them all together as a "unit". Should we have another tab for this page in http://127.0.0.1:8787/#curate because right now we only have 1 · Curate set
> 2 · Create the mix at the top of the GUI. I'm really surprised the claude session I had on my Macbook Pro right before starting up this session again didn't already implement or start to implement this feature, but now please help me. See if there was any mention of this effort in this repo: /Users/ernestyeung/.openclaw/workspace/repos/claw-dj
<!-- pdd-intent-entry:i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160:end -->

<!-- pdd-intent-entry:when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36:start -->
## When Build mix plan runs, every option — NemoClaw order, H Company...

- Intent event: [`docs/intents/intent__when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36.md`](intents/intent__when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `not stated`

> When Build mix plan runs, every option — NemoClaw order, H Company order, and Feel only — must be free to reorder the finalized playlist as necessary so the mix blends and sounds as good as possible. The order in which the user selected tracks is not a required playback order; the user is only declaring which songs are available for the mix. An LLM may be used to interpret natural-language ordering constraints, but mix-quality ordering itself must not require an LLM and must work in every mode. Preserve every available track exactly once unless the user explicitly requests a subset, and preview the resulting order before Start mix. H Company planning-only ordering must not require or start a local desktop bridge.
<!-- pdd-intent-entry:when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36:end -->

<!-- pdd-intent-entry:when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0:start -->
## When scripts/start.sh starts claw-dj, Mixxx control API port 9995 is...

- Intent event: [`docs/intents/intent__when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0.md`](intents/intent__when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `not stated`

> When scripts/start.sh starts claw-dj, Mixxx control API port 9995 is the preferred default, not a strict requirement. If a patched Mixxx instance is already running with its control API on another localhost port, discover that actual port, validate it with the Mixxx control API ping protocol rather than accepting an arbitrary open TCP port, reuse that Mixxx instance, and propagate the selected port consistently to the playlist editor, Analyze & enrich, Start mix, and command-line live mix execution. Do not tell the user to quit a usable running Mixxx merely because it is not on 9995. Preserve an explicit port override as the highest-priority choice. If Mixxx is running without any reachable control API, report that distinct condition honestly; do not connect to an unrelated service or silently start a second Mixxx instance.
<!-- pdd-intent-entry:when-scripts-start-sh-starts-claw-dj-mixxx-contr-18f454c0:end -->

<!-- pdd-intent-entry:load-a-new-music-collection-from-a-chosen-volume-1830f5e2:start -->
## Load a new music collection from a chosen volume

- Intent event: [`docs/intents/intent__load-a-new-music-collection-from-a-chosen-volume-1830f5e2.md`](intents/intent__load-a-new-music-collection-from-a-chosen-volume-1830f5e2.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `bash, python, sqlite`

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
<!-- pdd-intent-entry:load-a-new-music-collection-from-a-chosen-volume-1830f5e2:end -->

<!-- pdd-intent-entry:if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58:start -->
## If you're able to scan and see I have a volume called "Elements". In...

- Intent event: [`docs/intents/intent__if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58.md`](intents/intent__if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `sqlite`

> If you're able to scan and see I have a volume called "Elements". In the GUI I have, http://127.0.0.1:8787/#curate is there a way to "switch" to the new music collection and restart "the scan" of the music collection for useful metadata? Also would need to create a new sqlite on the volume if it's not there. It's ok upon start.sh or start of GUI to default to the previously used music collection. so that start up isn't asking use which music collection. But help me implement ability to start a new music collection while saving the previous music collection "settings" if any.
<!-- pdd-intent-entry:if-you-re-able-to-scan-and-see-i-have-a-volume-c-a1c09a58:end -->
