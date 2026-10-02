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

<!-- pdd-intent-entry:when-i-blend-i-match-the-snare-not-just-the-beat:start -->
## A blend matches the snare, not just Mixxx beat ticks

- Intent event: [`docs/intents/intent__when_i_blend_i_match_the_snare_not_just_the_beat.md`](intents/intent__when_i_blend_i_match_the_snare_not_just_the_beat.md)
- Change kind: `add`
- Story: [`user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md`](../user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md)
- Scope: mix planner + Mixxx runner

> Beatsync locking Mixxx beatgrid ticks is not a finished blend. The snares must hit together (usually 2 and 4 in 4/4, sometimes only 2 or only 4). After sync, jump the incoming deck one beat (`snare_align`) when the ear or high-confidence snare-phase analysis says the landing is one count off. Do not slide the incoming cue one beat later and do not treat outgoing ride length ±1 as the snare lock. If the user says a blend is still off by one, put `snare_align` on the incoming track and rebuild.
<!-- pdd-intent-entry:when-i-blend-i-match-the-snare-not-just-the-beat:end -->

<!-- pdd-intent-entry:refactor-build-mix-plan-and-preserve-the-curate--f4cf5bf3:start -->
## Refactor Build mix plan and preserve the Curate/Mix GUI

- Intent event: [`docs/intents/intent__refactor-build-mix-plan-and-preserve-the-curate--f4cf5bf3.md`](intents/intent__refactor-build-mix-plan-and-preserve-the-curate--f4cf5bf3.md)
- Change kind: `replace`
- Supersedes: `when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36`
- Scope: `existing_pdd_change`
- Technology: `python` (corrected: PDD inferred `cpp` from "llama-cpp")

> # Request: Refactor Build mix plan; preserve the Curate and Create-the-mix GUI
>
> Ernest, 2026-09-30, after the Who Shot Ya three-model continuous mix
> (Grok 4.6, Claude Opus 5.5, GPT Astra 6) passed the backbeat/snare-parity
> stories. That code is the accepted base for this refactor.
>
> Status: proposed (awaiting meaning-level approval).
>
> ```text
> Now we're going to refactor the GUI. As a user I like to start here:
> http://127.0.0.1:8787/#curate I like the drop down for the mix plan to work on
> a previous mix or press New for a new one or to duplicate. I like how to check
> for new music automatically here: "New music 18058 new · 80 changed · 83177
> unchanged · 986 need tags Scanned folders: /Volumes/Elements/Music" and with
> the Check for new music button. Also I like how I can choose which "volume"
> would have my music collection, on this same page on here: Music collection
> ElementsMusic · /Volumes/Elements Known collections Use selected Start new
> collection… As a user I like how I can search for my music in the text field
> and click on buttons to easily add from Library into Enabled set. And also the
> Archive first button to toggle or not, and to clear a set. I also like the
> audio preview player built right in. I also like Finalize for Mixxx button on
> there too. There should be user stories for all of this, because I like all of
> this and we should preserve it. If we don't have a related, even remotely
> related user story, create it. So I'll press Finalize for Mixxx right now.
>
> http://127.0.0.1:8787/#mix on here i like how I can just press Analyze &
> enrich missing and see the log to see which files had gotten lyrics, the bpm
> and key from mixxx, and how I don't have to allow permissions for each and
> every song; we just assume given the volume then recursively all the songs can
> and should be accessible to mixxx. Now once I'm finished with Analyze and
> enrich I like how Build mix plan is ready.
>
> Now here's the part I don't like with Build mix plan. Despite selecting DJ
> show case for quick transitions to showcase the mixing ability of claw-dj, it
> doesn't adhere to some of our rule such as backbeat matching. And then for Mix
> to listen I don't like how it doesn't work consistently to blend nicely. Also,
> I find that Candidate playback order it's following too closely, during the
> first time to how the user chooses it from the first page, in Library and
> Enable, instead of choosing the best order to make the best blend. Also I'm
> not using H company's model at this point much, and I don't think it's the
> right model for it. Also Nemoclaw is too difficult to deploy and keep up. We
> should refactor this build mix plan. It's got to be LLM powered and if it's
> not yet LLM powered, then just optimize its "computational graph" (we
> calculate for each song a metric of compatibility to blend with each other,
> don't we? if not, then i'm mistaken, and ignore) and create the mix without
> LLM. But at this point, allow for user to either for Claude, authorize with
> OAuth (on the browser?) with Claude, or likewise codex, or likewise Grok. Also
> for each of these 3, Claude, Grok, and OpenAI's GPT codex, be able to provide
> a .env that'll have the API keys (or the best way to do that to have this
> local application keep the API keys). OR, finally, use llama-cpp's
> llama-server, and call that for help. Keep Candidate playback order list, that
> looks nice. But yeah we gotta refactor from the step Build mix plan. Shuffle
> opener doesn't help much either in creating, a one shot or best first try mix.
> that also follows our user stories too. Help!
> ```
>
> ## Inferred actions
>
> - **Constraint (preserve):** Curate page plan picker (open / New / Duplicate),
>   New-music scan summary + Check for new music, collection chooser (Known
>   collections, Use selected, Start new collection…), search + add from Library
>   into Enabled set, Archive first toggle + Clear set, built-in audio preview,
>   Finalize for Mixxx; Create-the-mix Analyze & enrich missing with a per-file
>   log, Candidate playback order list.
> - **Correct:** Analyze & enrich must not depend on per-song file permission
>   prompts; access is granted per volume (recursively). Supersedes the
>   "macOS may still prompt per track" acceptance note in
>   `story__when_i_finalize_a_set_i_enrich_build_a_mix_plan_and_start_mixxx.md`.
> - **Correct:** Build mix plan ordering must not echo selection order; it must
>   optimize blend quality over the whole set, with backbeat (snare) matching as
>   a hard rule in every profile, including DJ showcase and Mix to listen.
> - **Remove:** NemoClaw and H Company as Build-mix-plan order engines; Shuffle
>   opener.
> - **Add:** model providers for Build mix plan — Claude, OpenAI Codex/GPT, Grok
>   (each by browser sign-in or by locally stored API key) and a local
>   llama.cpp `llama-server`; with no provider, a deterministic graph optimizer
>   builds the mix.
<!-- pdd-intent-entry:refactor-build-mix-plan-and-preserve-the-curate--f4cf5bf3:end -->

<!-- pdd-intent-entry:live-mini-experiments-on-a-section-of-a-mix-48d34784:start -->
## Live mini-experiments on a section of a mix

- Intent event: [`docs/intents/intent__live-mini-experiments-on-a-section-of-a-mix-48d34784.md`](intents/intent__live-mini-experiments-on-a-section-of-a-mix-48d34784.md)
- Change kind: `add`
- Supersedes: none
- Scope: `existing_pdd_change`
- Technology: `not stated`

> i like the idea of the audition and we ought to audition more experimental things in the future. currently this audition in particular doesn't sound great and might not be a good idea. In particular backbeat sync isn't there it's off by 1 beat. I'd encourage these one off auditions in the future for things we want to experiment with. Becaue now we found out if an idea is good or not! (this specific time it might not be). So how about this, I want to try, so this won't modify the full mix with all the songs, and htis should be a user story because I've been thinkign about it a long time, while working with a LLM whether in claude code, codex, grok build, hermes agent, etc., we want to be able to "test" and "experiment" on smaller sections of a mix, whether it's a transition, or cueing a part of a song to repeat and loop over and over, or to create a new blend and new sound, whether 2 or 3 or more decks, without having for the user to listen and sit through entire mix and reconstructing netire mix. Our claw-dj "harness" should allow for this "mini" expeirmentation, work and iterative with the LLM or AI agent, AI harness on smaller parts of the mix which if successful will be incorporated into the larger mix with all the songs.
>
> Earlier in the same conversation: let's not rely on ffmpeg at all; we want to mix live. no rendered WAV. use mixxx or tools, functions using mixxx and mix live.
<!-- pdd-intent-entry:live-mini-experiments-on-a-section-of-a-mix-48d34784:end -->
