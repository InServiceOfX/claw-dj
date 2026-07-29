# Strict hip-hop / R&B pilot

Status: audition candidate, not yet human-verified.

This four-song sequence is a small proving set for
`--dj-format hiphop-rnb-8bar`. It deliberately excludes “Ten Crack
Commandments”: the selected album recording starts its count immediately and
does not provide the required conventional 8-bar incoming intro.

## Proposed order

1. The Notorious B.I.G. — Who Shot Ya (91.67 BPM)
2. Timbaland feat. Jay-Z & Justin Timberlake — Give It To Me - Remix (Clean)
   (96.50 BPM)
3. Snoop Dogg & Wiz Khalifa — Young Wild And Free (feat. Bruno Mars)
   (95.00 BPM)
4. The Notorious B.I.G. — I Love The Dough (ft. Jay-Z and Angela Winbush)
   (99.10 BPM)

The 91.67–99.10 BPM range is compact enough for a useful pilot. The opener
does not need an incoming-intro certification and the closer does not need an
outgoing-chorus certification.

## Audition points

Every time below is analyzer-derived and aligned to beat 1 of a bar. That
proves downbeat placement, not musical structure. Listen to the generated
32-beat clips before converting any row to a `dj_notes` annotation.

| Track | Role | Candidate time | Beat index | Required confirmation |
|---|---|---:|---:|---|
| Who Shot Ya | outgoing chorus | 128.714s | 196 | A chorus/hook begins on the first audible beat and holds for 8 bars |
| Give It To Me - Remix | incoming intro | 10.348s | 16 | A usable intro begins on beat 1 and holds for 8 bars |
| Give It To Me - Remix | outgoing chorus | 149.622s | 240 | A chorus/hook begins on beat 1 and holds for 8 bars |
| Young Wild And Free | incoming intro | 0.289s | 0 | A usable intro begins on beat 1 and holds for 8 bars |
| Young Wild And Free | outgoing chorus | 65.973s | 104 | A chorus/hook begins on beat 1 and holds for 8 bars |
| I Love The Dough | incoming intro | 10.058s | 16 | A usable intro begins on beat 1 and holds for 8 bars |

The audition files live in the ignored local directory
`brain/data/strict_pilot_auditions/`. Each clip starts on the proposed cue and
lasts exactly 32 beats at the track's analyzed BPM.

## After listening

Only confirmed points should be written into `dj_notes`:

```text
Who Shot Ya: chorus_seconds=128.714
Give It To Me - Remix: intro_seconds=10.348; chorus_seconds=149.622
Young Wild And Free: intro_seconds=0.289; chorus_seconds=65.973
I Love The Dough: intro_seconds=10.058
```

These lines are a review checklist, not current annotations. Once confirmed,
build the pilot with:

```bash
uv run python -m brain.build_mix_plan \
  --playlist brain/data/strict_pilot_playlist.json \
  --tracks 4 \
  --dj-format hiphop-rnb-8bar
```

If any clip fails the musical check, reject that cue and audition a different
bar or replace the song. Do not weaken strict mode to make the pilot pass.
