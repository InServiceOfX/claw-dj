# claw-dj transition log, 2026-10-15 (rnb-cooldown-mix-vol-02, live listening notes from Ernest)

For Claude Code: these are Ernest's ear notes from today's live run. Follow docs/LIVE_MIX_LESSONS.md: audition each fix live before changing the full mix, back up before every pass, use millisecond nudges (not whole-beat shifts), keep "don't touch" transitions byte-for-byte unchanged, and write approvals into the DJ notes. Song titles marked (?) were spoken/typed from memory; verify against mix_plan.json.

## APPROVED - DON'T TOUCH (use as reference for how fixes should feel)
1. P.M. Dawn - Paper Doll -> Majid Jordan (song ?) : excellent backbeat/snare matching.
2. Jagged Edge - Promise (Remix) -> 112 - Love Me : BEST transition so far. The keeper.
3. 112 - Love Me -> Tevin Campbell - I'm Ready : good.
4. Tevin Campbell - I'm Ready -> Maxwell - Ascension (Don't Ever Wonder) : good backbeat/snare matching.
5. Maxwell - Ascension (Don't Ever Wonder) -> next Maxwell song (title ?) : good. Ernest wants MORE like this (same-artist / same-era back-to-back pairings).
6. Donell Jones - Think About It (Don't Call My) -> Robin Thicke - Magic [430/794] : OK as-is.
   Why: Think About It ends with a separate interlude with no strong beat. Starting Magic from the beginning and blending in where it did was appropriate. Rule: when the outgoing track ends in a weak-beat interlude, starting the incoming track from the top inside that interlude is fine.
   Plan log: smooth_blend; moves sync, eq_dip_out_mid, crossfade, eq_restore; anchor [Channel2] beat 108.00 BPM; gradual bass swap; 32-beat landing -> deck 1; next loaded: 05 Make U Love Me.mp3 (110.00 BPM, cue 0.10s).

## NEEDS FIX
1. Jodeci - Feenin' -> Christina Milian - Highway : off by 1 count.
2. Christina Milian - Highway -> Keith Sweat - Right and a Wrong Way (?) : off by 1 count.
3. Boyz II Men (song ?) -> Christina Milian ft. Joe Budden - Whatever U Want : off by 1 beat. Christina's intro has no snare, but KEEP blending from the very start of her song; just align her count 1 to Boyz II Men's count 1 (find her downbeat from kick/bass/first vocal phrase).
4. Joe - How Soon (?) -> Joe - Don't Wanna Be a Player : off by 1 count; backbeat (snares on 2 and 4) not matched.
5. (? song) -> Prince - I Wanna Be Your Lover : rough. Ernest thinks the prior song may start with "I"; check tracklist.
6. Majid Jordan - Places (?) -> Joe - More & More : likely poor fit. Joe's snare lands around count 4.5 of each 4-count bar (very syncopated). Great song; get creative: short echo-out or cut on the downbeat instead of a long blend, a bridge track with a closer groove, or pair with other syncopated/swung R&B.

## IDEA TO TEST: blend length
Ernest noticed most transitions are 32 or 36 beats and suggests 40 for songs with interesting intros where the snare starts late. Suggestion: keep blends phrase-aligned (multiples of 8 beats, e.g. 32 or 48) so phrases land together; for late-snare intros, start the incoming track earlier so its first snare lands as the outgoing track drops out. A/B 32 vs. longer on the Prince transition first.

## Patterns
- Several "off by 1 count" errors: check downbeat/phase detection (count 1 alignment), especially on intros without a snare.
- Weak-beat interludes at track ends are good places to start the next song from the top.
