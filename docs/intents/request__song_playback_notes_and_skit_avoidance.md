# Song playback notes, skit avoidance, and listening feedback

Received 2026-09-05. Add/clarify playback-note editing and extend the existing
skit story; record audible backbeat regression separately. No live mix changes.

## Original request (verbatim)

I wanted a feature that would at least let us add notes specifically for how a song is played. Specifically for this song, [11/110] play_body
  riding The Notorious B.I.G. — Who Shot Ya for 312 live beats
  hints: ['Optional: tweak [ChannelN] filterHighEq mid-phrase', 'Optional: beatjump_1_forward to skip to chorus', 'Optional: beatloop_4_toggle for a loop-roll fill']
  trusted body: observed grid beat 43; keeping ride duration, resolving backbeat at live entrance
 for this song, we want to either skip the skit starting at aroujnd 3:30 and ending at about 3:50 (you could try to load the same song on the other deck and then cross fade blend into 3:50 time on the same song, but on the other deck, from 3:30 on the former deck, or jujst start blending into the next song before the start of the skit. There should be a user story where we're trying to identify skits within or at the end of a song that we want to either skip if it's in the middle (one can try the method I described above) or start blending into the next song. Also the transitions are better, but for this one, it's off by one count, the beat parity or backbeat matching was off by 1 count: [10/110] transition
  smooth_blend: Lloyd Banks — On Fire (Feat. 50 Cent) → The Notorious B.I.G. — Who Shot Ya
  moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
  notes: Near-identical tempo + friendly key — long crossfade with light EQ.
  anchoring on [Channel2] beat (95.00 BPM)
  backbeat: positions verified (-41 ms median); opening gradual blend
  crossfade: planned 32 beats (20.2s); scheduled 32.0 beats (20.2s)
  backbeat: local verification unavailable; keeping the gradual blend
  bass swap (gradual)
  backbeat: local verification unavailable; keeping the gradual blend
  backbeat: local verification unavailable; keeping the gradual blend
  crossfade landed -> deck 1: 32.0 beats / 20.2s executed (planned 32 beats)
  rate settled to native tempo on deck 1
  preload next into freed deck 2
[load] deck 2: 06. WHO SHOT YA.mp3  (111s, 93.00 BPM, cue 0.44s verified at 0.44s)

## Bounded interpretation announced to Ernest

- Expose the existing track-scoped plan-note API in Arrange with an editable
  playback note, Save/Cancel and explicit return to the library default.
  Link from Mix so notes are discoverable. Preserve revision checks,
  exact recording identity, existing notes, other plans and library defaults.
- Saving text records intent; it does not interpret arbitrary prose, rebuild
  the artifact or change playback. Make that distinction explicit in the UI.
- Extend the existing skit story to opening, middle and ending skits, including
  source-time ranges, reviewed versus approximate timing, same-song two-deck
  continuation, and finishing a normal next-song blend before the skit starts.
  Do not silently treat a direct beatjump as the requested seamless splice.
- Keep the gradual-v3 policy and current playback code/artifact untouched.
  Investigate/report the logged one-count complaint; no blind parity flip.
- Current rough 210–230-second range differs from historical 203.5–224.5;
  exact bounds and a playable skip/early-exit plan remain to be validated.
  No automatic DSP skit detector or two-deck splice is claimed implemented.
