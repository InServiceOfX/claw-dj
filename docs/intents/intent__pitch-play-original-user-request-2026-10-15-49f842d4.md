# Intent: Pitch play — original user request (2026-10-15)

<!-- pdd-intent-id: pitch-play-original-user-request-2026-10-15-49f842d4 -->
<!-- pdd-intent-sha256: 49f842d44de0b0465030b9d42a76dfbe06aee655803a14a6deca995a7003dedb -->

## Record

- Intent ID: `pitch-play-original-user-request-2026-10-15-49f842d4`
- Kind: `add`
- Supersedes: none
- Approval ID: `pitch-play-original-user-request-2026-10-15-49f842d4`
- Source kind: `file`
- Source reference: `docs/requirements/requests/2026-10-15-pitch-play.md`
- Request SHA-256: `49f842d44de0b0465030b9d42a76dfbe06aee655803a14a6deca995a7003dedb`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `rust`

## Original Request

> # Pitch play — original user request (2026-10-15)
>
> The same request was sent twice; preserve it once. This is intent input, not an approved implementation contract.
>
> Working in this repo: /Users/ernestyeung/.openclaw/workspace/repos/claw-dj
>  and take note of this tik tok: https://www.tiktok.com/@numark_dj/video/7671346273600998686?is_from_webapp=1&sender_device=pc i.e. https://www.tiktok.com/@numark_dj/video/7671346273600998686?is_from_webapp=1&sender_device=pc here: /Users/ernestyeung/Downloads
>  i already downloaded as -rw-r--r--@  1 ernestyeung  staff   10059378 Oct 15 22:04 Download.mp4
>  can you appropriately rename it, here's some "metadata" that might be useful : "/Users/ernestyeung/.openclaw/workspace/Data/Public/Images tiktokNumarkQuickBitOfPitchPlay.jpg just parse that image file for the text caption (tik tok is weird it doesn't let me cmd-c and copy on MAc Mini the text of a video), ok take this video, rename it so it's not generate Download.mp4 (keep it mp4 format of course) then move it to somewhere appropriate,y maybe like /Users/ernestyeung/.openclaw/workspace/Data/Public/Videos/TikTok
>  and parse out the audio, the video (screenshots at appropriate places could be effective to help you and other AI agents understand and grasp this video), (there's really no spoken vocals or speech to text). And analyze what the DJ is doing with "pitch play". So this could be part of a user story, or an epic, if you will, because this will be a capability for claw-dj that we'll work on and iterate as we gain more knowledge, skill, and sophistication, and trial and error: we want to be able to create in our mix the "pitch play" that results in the pitch play in this video and any other examples we surface. Because we are software based and software defined, and have mixxx and can modify mixxx and build our own binary as we want (we've already done it opening up the ports), we want to be able to do pitch play in mixxx. Let's iterative build this up, with good testing, and starting simple to something like shown in this video and any other examples we surface. So we already know more or less how to repeat a cue, in fact we have a user story for repeating for instance 4 bars (but it sounded like he repeated 8 bars or something?), and then he repeated that arpeggio (downward arpeggio) multiple times, and then somehow cued different pitches of Alicia Key's You Don't Know My Name, so that he could play the main "melody" (characteristic melody?) of Upgrade U by Beyonce. So ccheck if mixxx has this ability (I don't see any pitch buttons like on that controller tbh?) or if we need to implement it outside in Rust of mixxx or modify mixxx itself (and of course rebuild mixxx). Don't be afraid to go online to do deep research and use rea skill if necessary to see how other controllers work that do this "pitch play" (what is stems control?) , oh also, as a general note; that vocal DJ tag at least to me is annoying, and we don't have to implement that at all and just ignore that DJ tag DJ shoutout, DJ signature vocally, out of the parsing and any parsing in the future.

## Must Stay Unchanged

- So we already know more or less how to repeat a cue, in fact we have a user story for repeating for instance 4 bars (but it sounded like he repeated 8 bars or something?), and then he repeated that arpeggio (downward arpeggio) multiple times, and then somehow cued different pitches of Alicia Key's You Don't Know My Name, so that he could play the main "melody" (characteristic melody?) of Upgrade U by Beyonce.
- So ccheck if mixxx has this ability (I don't see any pitch buttons like on that controller tbh?) or if we need to implement it outside in Rust of mixxx or modify mixxx itself (and of course rebuild mixxx).
- Don't be afraid to go online to do deep research and use rea skill if necessary to see how other controllers work that do this "pitch play" (what is stems control?) , oh also, as a general note; that vocal DJ tag at least to me is annoying, and we don't have to implement that at all and just ignore that DJ tag DJ shoutout, DJ signature vocally, out of the parsing and any parsing in the future.

## Examples

- None stated.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Live audition of one built transition: lead-in placed from the ride's phase_anchor on the outgoing grid (previous fade, skips and...
- THE HARNESS-FACING CONTRACT.
- Pop-up card content and choice: agent-written sourced facts (brain/popup_facts.json, no attribution mark) and authors' commentary from...
- Reusable live Mixxx moves for live mini-experiments and hand-built live mixes: library lookup by artist/title (folder hint for duplicate...
