# Anthology visuals — Flux image prompt library

Companion to `ANTHOLOGY_AND_SHORT_FORM_PROGRAM.md`. That document owns the
campaign strategy, clip selection, and approval gates. This document owns the
still-image half: prompts, negatives, parameters, and formats for the art that
backs short-form clips and YouTube beds.

**Generation target:** a local desktop on the LAN (around `192.168.86.91`) with
an RTX 3060, nunchaku-quantized **FLUX.1-dev**, and LoRAs — including a
**retro-anime** LoRA. Copy or email this file to that box as-is; nothing here
needs network access from the DJ machine.

---

## 1. Creative freedom (not hard rules)

These are **starting points**, not strict brand law. Rewrite freely on the
generation box.

**People and likenesses are allowed.** You may name artists, describe faces,
or reimagine iconic looks (e.g. a *Doggystyle*-adjacent Snoop pose, a *2001*
studio-era vibe, a Reasonable Doubt skyline mood). With a retro-anime LoRA,
stylized portraiture and era mascots often read better than pure empty rooms.

**Album-cover recreation and reimagining are allowed.** Homage, parody
layout, “as if drawn for a bootleg anime sleeve,” or a fresh spin on a known
cover language is fine for this private pipeline. Prefer *reimagine / homage /
in the visual language of* over “pixel-perfect counterfeit” when you care about
originality — but the prompts below do not forbid cover-adjacent composition.

**Text in-image is optional.** Flux lettering is unreliable. If you need clean
titles later, keep lettering out of the render and composite. If the retro-anime
LoRA produces cool stylized titles, keep them. Negatives include text
suppression as a *default*; drop those tokens when you want lettering.

**Series intent (soft):** short-form on phones (9:16) and YouTube (16:9). Aim
for strong, readable centers; let detail live in the outer thirds when possible.

---

## 2. Formats (short-form + YouTube)

Generate masters near ~1 MP for Flux coherence; upscale later if needed.

| Use | Dimensions | Aspect | Notes |
|---|---|---|---|
| **Primary short-form / phone** | **768 × 1344** | 9:16 | Reels, Shorts, TikTok, X vertical. Default for social. |
| **Primary YouTube / landscape** | **1344 × 768** | 16:9 | Thumbnails, video beds, end cards. |
| Higher-detail 16:9 | 1536 × 864 | 16:9 | Hero stills; slower. |
| Higher-detail 9:16 | 864 × 1536 | 9:16 | Optional hero vertical. |
| YouTube thumbnail deliverable | 1280 × 720 | 16:9 | Downscale from 1344×768; do not upscale into it. |
| Square (optional) | 1024 × 1024 | 1:1 | Feed / plan art. |

**Practical tip:** for each mix card, generate **both** 1344×768 and 768×1344
from the same seed and prompt pair when the box can afford it. Same creative
DNA, two deliverables.

Flux is happiest near 1 MP; past ~1.5 MP coherence often slips. Prefer
generate-then-upscale over huge native resolutions on a 3060.

---

## 3. Parameters

### Base settings (FLUX.1-dev, nunchaku INT4)

```
model:        FLUX.1-dev, nunchaku SVDQuant INT4
steps:        24              (usable 20–28; below 20 gets mushy)
guidance:     3.2             (2.5 filmic / soft; 4.0 punchy / graphic)
sampler:      euler
scheduler:    beta            (simple is fine)
cfg:          try 1.0 first; raise toward 1.5–2.5 if your graph supports
              true classifier-free guidance and you want negatives to bite harder
seed:         fixed per mix, recorded (see variant protocol)
resolution:   1344×768 and/or 768×1344
```

### Box notes

- **3060 is Ampere (sm_86)** → nunchaku **INT4**. FP4 is Blackwell-only.
- Use **nunchaku’s LoRA loader**, not stock ComfyUI `LoraLoader`, on a
  quantized transformer.
- **Retro-anime LoRA:** start **0.55–0.85**. At 1.0 it can erase era
  differences across the series. For portrait/cover-homage cards, 0.7–0.9 is a
  good first band; for pure atmosphere, 0.5–0.7.
- Other style LoRAs: **0.6–0.8** typical.
- 12 GB VRAM: 1344×768 / 768×1344 is comfortable at INT4. On 8 GB, stay there
  and skip 1536-class sizes.

### Negative prompts

Provide a **negative every time** (CLIP and/or T5 negative fields, depending on
your nodes). Even when effect is mild at cfg 1.0, keep them in the graph so
true-CFG / dual-conditioning paths work without retyping.

**Shared negative (baseline for every card):**

```
ugly, deformed, blurry, lowres, low quality, worst quality, jpeg artifacts,
watermark, signature, username, logo spam, caption bar, subtitles overlay,
extra fingers, fused fingers, deformed hands, malformed anatomy, extra limbs,
distorted face, asymmetric eyes, plastic skin, waxy skin, oversharpened,
oversaturated, HDR halo, blown highlights, muddy shadows, noise soup,
cluttered unreadable mess, random modern smartphone UI, anachronistic LED billboard,
broken perspective, duplicate heads
```

Per-card negatives below **append** to that baseline (or replace tokens when
noted). If you *want* on-image text or logos for a cover homage, remove
`watermark, signature, logo spam` (and any “no text” tokens) for that render.

---

## 4. Prompt format (CLIP + T5)

Flux uses two text encoders:

| Field | Encoder | Role |
|---|---|---|
| **Prompt 1** | **CLIP-L** | ~**77 tokens**. Comma-separated tags. Front-load style + subject. |
| **Prompt 2** | **T5-XXL** | Up to ~**512 tokens**. Full prose: composition, light, story, likeness cues. |

In ComfyUI: `clip_l` and `t5xxl` on `CLIPTextEncodeFlux` (plus `guidance`).

**Retro-anime LoRA tip:** put anime medium words early in CLIP
(`retro anime still, 90s anime cel, film grain anime poster`) and keep T5 as
cinematic prose so the scene stays grounded.

---

## 5. The prompts

Your twelve, then more, then an A/B pair for DJ-format comparison. Every card
assumes base parameters; deviations are in **Notes**.

---

### 1. R&B — general / timeless

**CLIP-L:**
```
retro anime still, timeless R&B album art mood, warm amber lamplight, silk velvet, vinyl record, intimate close portrait optional, soft bokeh, sensual, 35mm film grain
```

**T5:**
```
A warm, intimate R&B atmosphere at night in a retro-anime still: amber lamp glow, deep burgundy and chocolate velvet, a spinning vinyl catching a soft highlight. Optional stylized figure in soft profile or silhouette — elegant, timeless, not tied to one decade — or pure still life if the face fails. Silk drapes frame the outer thirds; center stays readable. Fine film grain, gentle halation, shallow depth of field, sensual and quiet.
```

**Negative (append):**
```
cold clinical lighting, harsh daylight, cartoon chibi exaggeration, gore, horror
```

**Notes:** Series default when a mix doesn’t map cleanly. Guidance ~3.0.

---

### 2. 1990s R&B

**CLIP-L:**
```
retro anime, mid-1990s R&B music video, rain-slick city night, warm tungsten neon, satin chrome, moody teal amber, romantic 90s R&B couple silhouette optional, 35mm grain
```

**T5:**
```
Mid-1990s R&B music-video night: rain-slick street, wet asphalt reflecting tungsten and muted teal neon, steam from a grate, period sedan chrome beaded with rain. Optional retro-anime couple in satin under an umbrella or a lone singer in soft close-up — period fashion, soft glam, romantic melancholy. Outer thirds carry neon and fire escapes; center stays open and cinematic. Grainy 35mm, warm highlights, deep blue-black shadows.
```

**Negative (append):**
```
2020s fashion, LED strip lights, modern SUV, daylight beach
```

**Notes:** If storefronts invent gibberish signs you dislike, add
`illegible random signage, lorem ipsum text`.

---

### 3. 2000s R&B

**CLIP-L:**
```
retro anime Y2K, early 2000s R&B aesthetic, chrome frosted glass, blue-white club light, glossy digital sheen, silver, lens flare, futuristic minimal, stylish figure optional
```

**T5:**
```
Early-2000s Y2K R&B interior: chrome, frosted glass, brushed silver, cool blue-white light, hard specular sheen, anamorphic flare across the upper third. Optional retro-anime club figure in metallic fabric or crop silhouette — optimistic, glossy, slightly futuristic. Icy blue / silver / white with one warm accent. Crisp digital-clean gradients rather than heavy film. Center open and high-key.
```

**Negative (append):**
```
gritty documentary, heavy film damage, sepia, 1970s wood paneling
```

**Notes:** Least filmic card on purpose. Guidance ~3.5.

---

### 4. West Coast — Chronic / Doggystyle / Dogg Pound / Warren G era

**CLIP-L:**
```
retro anime, early 1990s Long Beach Los Angeles, Doggystyle album cover reimagining, Snoop Dogg inspired figure on roof or stoop optional, golden hour palms, lowrider candy paint chrome, Chronic era haze, 35mm
```

**T5:**
```
Early-1990s West Coast golden hour reimagined as a retro-anime still: tall palms against burnt-orange smog sky, candy-paint lowrider chrome, sun-bleached stucco, chainlink, dry grass. Freely reimagine a *Doggystyle*-adjacent composition — iconic rooftop or stoop energy, relaxed G-funk swagger, dog-themed or cartoon-mascot flavor welcome if it stays playful homage rather than corporate logo spam. Optional stylized Snoop-inspired character (long hair, casual early-90s LA fit) or pure vehicle-and-palms atmosphere. Warm 35mm haze, lifted blacks, laid-back and sunbaked.
```

**Negative (append):**
```
snow, New York skyline, hard industrial blue night only, modern EV car
```

**Notes:** Strongest light identity in the set. LoRA 0.7–0.9 if you want the
cover-homage face/pose to hold.

---

### 5. West Coast — Westside Connection era

**CLIP-L:**
```
retro anime, mid-1990s Los Angeles night, Westside Connection era energy, hard flash underpass, black chrome car, concrete sodium vapor, harder colder edge, group silhouette optional, high contrast
```

**T5:**
```
Mid-1990s LA night under a freeway underpass: sodium-vapor orange on bare concrete, cold near-black shadows, blacked-out car with chrome wheels, hard direct flash. Westside Connection–era attitude — confrontational, dense, colder than the sunlit G-funk cards. Optional retro-anime crew silhouettes in dark jackets and caps, or a single hard-lit portrait with tough composition. Grey, black, chrome; high contrast; 35mm grain. Center stays readable despite the grit.
```

**Negative (append):**
```
warm beach sunset, pastel candy colors, romantic soft focus only
```

**Notes:** Cold counterweight to #4.

---

### 6. West Coast — 2001 era, expanded to Eminem and 50 Cent

**CLIP-L:**
```
retro anime, 1999-2003, Chronic 2001 era, Dre studio night, red black chrome, Eminem 50 Cent era expansion optional, mixing console glow, smoke haze, cinematic album art
```

**T5:**
```
Turn-of-the-millennium studio control room at night: long mixing console with red/amber lights, glass to a dim live room, condenser mic in hard key light, smoke beams. Palette glossy black, deep red, chrome — polished, expensive, slightly menacing. Freely reimagine *2001*-adjacent album-art energy and the era’s expansion toward Eminem / 50 Cent: optional stylized figures at the board or behind glass (headphones, chains, early-2000s streetwear), or empty studio if portraits fail. Cinematic contrast, shallow DOF, subtle grain. Center is open dark air between console and glass.
```

**Negative (append):**
```
daytime exterior only, pastel pop, pure acoustic folk cabin
```

**Notes:** Studio framing bridges LA / Detroit / NYC radio dominance of that window.

---

### 7. Wu-Tang era — Staten Island / East Coast winter

**CLIP-L:**
```
retro anime, early 1990s Wu-Tang era, Staten Island New York winter, Shaolin mythic grit, weathered brick fog, martial arts film grain, muted yellow black, crew silhouette optional
```

**T5:**
```
Early-1990s New York winter block in Wu-Tang / Shaolin mythic register: cold fog between brick buildings, rusted fire escapes, dirty snow, one pale yellow streetlight bloom. Heavy grain like a dubbed martial-arts VHS. Optional retro-anime crew in dark winter gear, masks or hoods as *stylized homage* to the clan’s mythic look — not a clean corporate logo sheet. Desaturated greys, cold browns, black, one muted yellow accent. Stark, cold, legendary. Center recedes into fog.
```

**Negative (append):**
```
tropical palms, bright Y2K chrome club, soft glam R&B pastels
```

**Notes:** If you have a VHS/analog LoRA, use it here at ~0.5–0.6 stacked under
retro-anime.

---

### 8. Conscious rap — Public Enemy / Arrested Development era

**CLIP-L:**
```
retro anime, early 1990s conscious rap, Public Enemy energy, Arrested Development earth tones, high contrast photojournalism, raised fist, red black green, documentary 35mm, stage silhouette optional
```

**T5:**
```
Early-1990s conscious-rap still: high-contrast documentary light, weathered wood platform, dust in sun shafts, West African–inspired textile patterns and earth tones at the edges, selective red / black / green accents. Public Enemy confrontational urgency can share the frame with Arrested Development’s grounded pastoral warmth — split the mood with light and fabric rather than clutter. Optional stylized performers or raised-fist silhouettes in retro-anime line work. Serious, communal, defiant. Center is open lit air.
```

**Negative (append):**
```
luxury champagne party, pure club neon, glamorous shiny suit excess
```

**Notes:** If you want PE and AD fully split, duplicate this card into two
renders: one hard B&W protest stage, one warm Afrocentric daylight porch.

---

### 9. East Coast golden age — Mobb Deep / Nas / Reasonable Doubt era

**CLIP-L:**
```
retro anime, mid-1990s Queensbridge rooftop, Nas Illmatic mood, Reasonable Doubt skyline, Mobb Deep winter cold, cognac smoke, Manhattan dusk, melancholy 35mm
```

**T5:**
```
Mid-1990s East Coast golden-age rooftop at blue hour: tar paper, parapet, water towers, antennae; Manhattan skyline hazy across the river as windows light. Cold blue-grey slate palette with one amber window and a cigarette ember on the ledge. Freely reimagine *Illmatic* / *Reasonable Doubt* / Mobb Deep winter energy — optional stylized young MC silhouette in period puffer or leather, contemplative, watchful. Grainy underexposed 35mm, muted, cinematic. Center is open sky and skyline.
```

**Negative (append):**
```
palm trees, candy lowrider daytime, bright fisheye club flash
```

**Notes:** Guidance ~2.8 for soft dusk gradients. Excellent 16:9 YouTube bed.

---

### 10. East Coast jazz-informed — Gang Starr / Premier / Tribe / De La

**CLIP-L:**
```
retro anime, boom bap jazz club, Gang Starr Premier era, A Tribe Called Quest, De La Soul warmth, upright bass dusty vinyl, sepia amber, mid-century jazz LP design
```

**T5:**
```
After-hours jazz club corner: upright bass, crates of worn vinyl, warm practice lamp, scuffed parquet, brass cymbal highlight, dust in the beam. Palette sepia, amber, cream, deep brown — mid-century jazz LP geometry meets boom-bap scholarship. Optional retro-anime DJ or MC half-lit at the crates (Guru/Premier *energy*, Tribe/De La warmth) or pure instruments-and-vinyl still life. Soft grain, gentle contrast, unhurried. Center is quiet warm air.
```

**Negative (append):**
```
hard gangsta underpass flash, icy Y2K chrome, pure trap 2018 aesthetic
```

**Notes:** Readable spine text on sleeves is optional; if messy, negative
`random gibberish on album spines`.

---

### 11. Shiny Suit era — Puff Daddy & the Family / Mase

**CLIP-L:**
```
retro anime, 1997-1999 shiny suit era, Puff Daddy and the Family, Mase, high gloss luxury, silver white metallic, champagne mirrors, hard flash fisheye, celebratory excess
```

**T5:**
```
Late-1990s shiny-suit excess as retro-anime glamour: ultra-wide fisheye, hard on-camera flash, mirrored silver surfaces, champagne flutes, ice bucket, white lacquer, liquid metallic fabric. Optional stylized party figures in shiny suits, platinum jewelry, high-key smiles — Puff & the Family / Mase *era energy*, loud and expensive. Barrel distortion, almost overexposed edges. Bright silver, white, pale gold. Center is bright open space.
```

**Negative (append):**
```
dark moody desaturated noir, gritty winter projects only, documentary black and white
```

**Notes:** Guidance ~4.0 for harder flash. Brightest card by design vs #9.

---

### 12. Sade / smooth funk and jazz

**CLIP-L:**
```
retro anime, Sade inspired elegant portrait optional, smooth jazz funk, tropical dusk ocean, linen gold, generous negative space, soft diffused light, muted terracotta deep teal
```

**T5:**
```
Spare tropical dusk: calm ocean horizon, sky from muted terracotta to deep teal, linen curtain in warm air, low table with a single brass object. Optional elegant retro-anime portrait in the spirit of Sade — understated glam, close crop or three-quarter, restrained expression — or pure landscape still life. Generous negative space, sand / warm white / brass gold / deep teal, soft diffused light, matte finish, sensual through restraint. Center stays open and quiet.
```

**Negative (append):**
```
busy club crowd, hard flash, graffiti, cluttered maximalism
```

**Notes:** Guidance ~2.5. Best base for later composited long titles.

---

## 6. More cards worth having

---

### 13. New Jack Swing — Teddy Riley / Guy / late-80s–early-90s

**CLIP-L:**
```
retro anime, late 1980s new jack swing, Teddy Riley era, bold color blocking, neon magenta cyan, polished floor, geometric studio set, hard studio lights, energetic dancers optional
```

**T5:**
```
Turn-of-the-90s graphic studio set: magenta / cyan / yellow color blocks on black, hard gels, polished reflective floor, chrome tubing, angular props. Optional retro-anime dancers or a stylish group in late-80s fashion — New Jack energy, TV-stage artificial and high-energy. Flat, symmetrical, saturated. Center is open reflective floor.
```

**Negative (append):**
```
muted earth tones only, pure acoustic jazz club brown
```

---

### 14. Neo-soul — D’Angelo / Erykah Badu / Maxwell era

**CLIP-L:**
```
retro anime, late 1990s neo-soul, DAngelo Erykah Badu Maxwell era, natural window light, incense smoke, wood earth tones, houseplants worn books, organic intimate portrait optional
```

**T5:**
```
Late-90s neo-soul room in soft window light: incense smoke, warm wood, worn books, trailing plants, ochre rust deep green textiles, dust motes. Optional intimate retro-anime portrait — natural hair, earth jewelry, unhurried gaze — channeling D’Angelo / Badu / Maxwell era softness without needing a perfect likeness. Matte low-contrast film, organic, meditative. Center is quiet lit air.
```

**Negative (append):**
```
hard club flash, icy chrome Y2K, violent imagery
```

---

### 15. Timbaland / Missy / Aaliyah futuristic R&B

**CLIP-L:**
```
retro anime, 1997-2002 futuristic R&B, Timbaland Missy Aaliyah era, black leather liquid chrome, cool blue-green glow, desert night, angular alien geometry, sleek figure optional
```

**T5:**
```
Sleek nocturnal futurism: black leather and liquid chrome, angular almost-alien shapes, cold desert night, electric blue-green glow, hard rim light, subtle motion blur. Optional stylized retro-anime figure in futuristic streetwear or dance pose — Timbaland / Missy / Aaliyah era energy, uncanny and modern for its time. Black, chrome, blue-green, no warmth. Center is dark open space.
```

**Negative (append):**
```
warm amber only, 1970s wood studio, pure boom-bap jazz club
```

---

### 16. Quiet storm / late-night slow jams

**CLIP-L:**
```
retro anime, quiet storm late night, rain on apartment window, single warm lamp, burgundy near black, soft city bokeh, intimate solitude, optional soft silhouette
```

**T5:**
```
Deep night through a rain-streaked window: city lights as soft bokeh, single warm lamp on burgundy chair and dark wood table, everything else near-black. Optional soft retro-anime silhouette inside the room — solitude, not spectacle. Low-key, warm against cold, fine grain, hushed. Center is the soft-focus window glow.
```

**Negative (append):**
```
bright daylight beach, party crowd, hard fisheye flash
```

---

### 17. Chronic 2001 sample lineage — two eras, one room

**CLIP-L:**
```
retro anime, sample lineage diptych mood, 1970s soul studio warmth meeting 1999 digital studio cool, reel to reel and modern console, continuous single room, warm amber to cold blue
```

**T5:**
```
One continuous recording room where two eras meet: left side 1970s soul warmth — reel-to-reel, wood paneling, tungsten amber; right side late-90s / 2001 digital cool — black console, rack gear, blue light. Lighting crossfades across the middle; photographically one space, not a collage or split-screen graphic. Optional small retro-anime engineer figure bridging both sides. Grainy 35mm, deliberate, thesis image for “the record it came from and the record it became.”
```

**Negative (append):**
```
split screen, collage, comic panel borders, two disconnected photos side by side
```

**Notes:** If the model hard-splits the frame, strengthen T5 “continuous single
room / same floorboards” and keep the negative split-screen tokens.

---

### 18. Drake season — modern nocturnal

**CLIP-L:**
```
retro anime, modern nocturnal R&B rap, cold fog dark water, distant tower lights, minimal composition, desaturated blue grey, single warm accent, moody contemporary
```

**T5:**
```
Cold minimal nocturnal city: fog over dark still water, distant towers as soft vertical light, desaturated blue-grey and black, one warm amber accent on the horizon. Optional solitary retro-anime figure in contemporary outerwear at the railing — isolated, expensive, emotionally cool. Clean modern capture, little grain, restrained contrast. Center is open water and fog.
```

**Negative (append):**
```
1990s boombox primary colors, heavy VHS tracking lines
```

---

### 19. Brooklyn tribute — memorial register

**CLIP-L:**
```
retro anime, Brooklyn brownstone night, memorial candles on stoop, red gold accents, gentle snow, reverent quiet, warm against cold, optional respectful silhouette
```

**T5:**
```
Brooklyn brownstone stoop at night in winter: glass memorial candles in warm red and gold on stone steps, fine snow, bare branches, iron railings. Quiet reverence, mournful without gore. Optional distant respectful silhouette or stylized tribute energy — keep it human and soft, not exploitative. Deep blue-black and candle gold, soft grain. Center is the softly lit stoop.
```

**Negative (append):**
```
gore, violence, sensational crime scene, disrespectful party mood
```

---

### 20. Harlem 2000s — Dipset register

**CLIP-L:**
```
retro anime, mid-2000s Harlem, Dipset era energy, hot pink chrome, fur texture, brownstone stoop, hard direct flash, bold saturated color, confident excess
```

**T5:**
```
Mid-2000s Harlem night with hard flash: hot pink and chrome, fur texture catching light, brownstone stoop falling into darkness. Optional flashy retro-anime crew or single confident figure — Dipset-era swagger, loud color, unapologetic. Saturated pink, silver, black; hard flash shadows; slightly overexposed near highlights. Center is open sidewalk.
```

**Negative (append):**
```
muted documentary brown only, quiet storm solitude
```

---

## 7. A/B pair — same mix, two DJ transition formats

Use these for the **mix-to-listen** plan you dry-ran: **18 tracks**, **17
transitions**, order engine **none**, profile **mix-to-listen**. One card for
**No expert format (`none`)**, one for **Hip-hop / R&B · guided
(experimental)** — same mix DNA, different transition philosophy, so short-form
thumbs can label A vs B without reading the log.

Shared mix DNA for both:

```
18-track R&B / hip-hop listening mix, smooth continuous flow, late-night
headphones energy, mix-to-listen (not club peak-time), modern crate with
classic and contemporary picks
```

---

### 21. Same mix — **No expert format** (`none`)

**Intent:** continuous feel, free blend, no rigid 8-bar recipe grammar — ear
and mix graph only. Visually: seamless river of sound, organic crossfades.

**CLIP-L:**
```
retro anime, continuous DJ mix atmosphere, seamless blend, liquid audio waveform river, two decks soft crossfade, warm headphones night, organic freeform transitions, no grid overlay, smooth R&B hip-hop listening mix, soft bokeh
```

**T5:**
```
A retro-anime night scene for a long listening mix built with **no expert DJ transition format** — free, ear-led blends only. Two turntables or CDJs dissolve into each other with a soft, liquid crossfader glow; sound is visualized as a smooth continuous river or silk ribbon of music with no hard bar-grid, no metronome lattice, no 8-bar recipe diagrams. Warm amber desk lamp, comfortable headphones, late-night “mix-to-listen” calm rather than club strobes. Optional stylized DJ hands riding a slow blend, relaxed posture. Palette: warm burgundy, soft gold, deep navy. Center stays calm and readable for an A/B label like “FORMAT: NONE”. Feels continuous, forgiving, human.
```

**Negative (append):**
```
hard beat grid overlay, 8-bar ruler graphics, laboratory HUD, aggressive strobe club, broken jump cuts collage
```

**Suggested params:** guidance 3.0; retro-anime LoRA 0.6–0.75; seed family A
(record it). Generate **1344×768** and **768×1344**.

---

### 22. Same mix — **Hip-hop / R&B · guided (experimental)**

**Intent:** every entry aims at beat 1; verified 8-bar recipes when possible;
otherwise **guided fallbacks** (your dry-run: `guided fallback×17`, cues like
`guided_phrase_intro_downbeat`). Visually: phrase grid + experimental recipe
energy — structured but still a bit raw / not fully trusted.

**CLIP-L:**
```
retro anime, experimental guided DJ format, 8-bar phrase grid, beat one downbeat markers, hip-hop R&B transition recipes, waveform locked to bars, cyan amber HUD light, two decks phrase aligned, laboratory craft meets street, listening mix
```

**T5:**
```
A retro-anime craft-table scene for the **same** 18-track mix-to-listen set, but planned with **Hip-hop / R&B guided (experimental)** transition format: every handoff wants **beat 1**, phrase-aware intros, and practicing-DJ 8-bar recipes when verified — with other joins labeled as **guided fallbacks**. Visualize a translucent 8-bar / 32-beat grid floating above the decks, soft downbeat ticks, phrase brackets, and a few handwritten recipe tags (chorus→intro, phrase-aligned fallback) as stylized anime UI — experimental, slightly unfinished, honest about not being fully reliable yet. Cool cyan grid light mixing with warm desk amber. Optional focused DJ figure aligning a cue point. Same late-night listening mood as the NONE card, but more structured and technical. Leave calm center space for a label like “FORMAT: GUIDED · EXPERIMENTAL”.
```

**Negative (append):**
```
totally empty atmosphere only, pure nature landscape, no decks, chaotic unreadable HUD spam, stock corporate powerpoint chart
```

**Suggested params:** guidance 3.4–3.8 (crisper grid); retro-anime LoRA 0.65–0.8;
**reuse seed family A** from card 21 if you want a true A/B pair, then only
change the prompt (and optionally +0.2 LoRA). Same dual resolutions.

**A/B checklist when you publish:**

| | Card 21 NONE | Card 22 GUIDED |
|---|---|---|
| Mix | same 18-track dry-run | same |
| Profile | mix-to-listen | mix-to-listen |
| Format | none | hiphop-rnb-guided |
| Visual tell | liquid seamless blend | phrase grid + recipe tags |
| Seed | family A | family A (preferred) |

---

## 7b. Featured track — Mary Jane Girls · *All Night Long* (1983)

For mixes that feature **Mary Jane Girls — “All Night Long”** (Rick James /
Motown, 1983; from the debut *Mary Jane Girls*). Celebrate **that** early-80s
funk-R&B girl-group era: beauty, fashion, swagger, and the song’s all-night
party invitation — not a random modern club still.

### Research notes (for the prompter, not for on-image text)

**Lyrics / mood (high level):** A come-on to **party all night long** — funky,
playful, confident, social. Invitation energy (“come on baby… party all night
long”), dancing until morning, desire and fun rather than quiet-storm solitude.
The record is midtempo funk with a long groove; the visual should feel
**endless night**, not a 10-second drop.

**Cover / visual language (homage allowed):** The era and single presentation
read as **glamorous early-80s group imagery** — multiple beautiful Black women
styled as a unit, bold makeup, big soft-volume hair, lingerie-adjacent or
body-conscious glam, tropical or lush studio fantasy for some press/cover
treatments, Motown/Rick James funk-family polish. Reimagine freely (retro-anime
LoRA welcome); you may lean cover-homage or pure fashion fantasy. Prefer
*celebration of the group’s era* over a sterile empty room.

**Fashion & style keywords for this era:** early 1980s R&B/funk glam; big soft
curls or feathered volume; dramatic eyes and glossy lips; gold jewelry;
metallic or satin fabrics; high-cut leotard/bodysuit language of the period
(tasteful, glamorous); shoulder emphasis; bold color against deep night or lush
green; confident group posing; “party girls” as power, not parody.

Two **distinct** cards below — different composition and story. Same brand DNA
(retro-anime, amber/night possible) but **not** interchangeable.

---

### 23. *All Night Long* — cover-homage glam (group fashion still)

**Intent:** Beauty and **group fashion** first — a square-friendly or 16:9
hero that could sit under the track in a short or YouTube bed. Echoes debut /
single-era **glamour**: four stylized women, coordinated but individual, lush
or tropical-studio fantasy, Motown funk polish. Celebrate how the Mary Jane
Girls *looked* and *posed* in that moment.

**CLIP-L:**
```
retro anime, early 1980s, Mary Jane Girls era, All Night Long single cover homage, four beautiful Black women group portrait, big soft volume hair, glamorous makeup, satin metallic bodysuits, gold jewelry, lush tropical studio fantasy, Motown funk glam, confident fashion pose, cinematic
```

**T5:**
```
A celebratory retro-anime fashion still for Mary Jane Girls’ early-1980s era and the spirit of “All Night Long”: four beautiful Black women as a stylized girl-group unit, each distinct but coordinated — big soft-volume 80s hair, dramatic eyes, glossy lips, gold chains and earrings, body-conscious satin or metallic leotard/bodysuit glamour of the period (tasteful, high-fashion, not crude). They pose with Motown funk confidence, close together, owning the frame like an album or single cover reimagined. Background: lush tropical-studio fantasy or deep green foliage with warm studio key light and soft amber rim — the kind of glamorous early-80s R&B packaging that sold desire and party invitation. Rich color, slight film grain, center-readable for a track title composite later if needed. Celebrate beauty, sisterhood styling, and that era’s fashion language.
```

**Negative (append):**
```
modern athleisure, 2020s streetwear, y2k chrome club only, gritty documentary B&W,
four identical cloned faces, childlike proportions, gore, parody ugly caricature,
crowded unreadable collage, pure empty landscape no people, male-dominated group
```

**Suggested params:** guidance **3.4–3.8** (hold faces and fashion); retro-anime
LoRA **0.7–0.9**; steps 24–28. Generate **1024×1024** (avatar/thumb) and
**1344×768** / **768×1344**. Seed family **MJG-A**.

---

### 24. *All Night Long* — all-night party / dancefloor era night

**Intent:** The **lyric and groove** — party all night long. Early-80s funk club
or house-party night: beautiful women in that era’s fashion **dancing**,
movement, sweat-glam, endless night. Distinct from #23’s posed cover still —
this one is **kinetic nightlife**, not a static group portrait.

**CLIP-L:**
```
retro anime, early 1980s funk R&B club, All Night Long Mary Jane Girls energy, beautiful women dancing all night, big 80s hair, gold jewelry, satin dresses and jumpsuits, disco funk floor lights, amber and magenta night, joyful confident party, motion blur accents, cinematic
```

**T5:**
```
A kinetic retro-anime night scene celebrating “All Night Long” as a **party that never ends**: early-1980s funk / R&B club or packed house-party energy. Beautiful women in period fashion — big soft volume hair, bold glam makeup, gold jewelry, satin minis, metallic jumpsuits, body-conscious 80s silhouettes — dancing close, laughing, owning the floor until morning. Warm amber and magenta club light, soft lens bloom, a little motion blur on hands and hems, vinyl or band energy suggested at the edge (not a modern EDM laser cage). Mood: invitation, desire, fun, confidence — “come on… party all night long” without needing readable lyrics on the image. Composition more open and cinematic than a tight cover crop; outer thirds hold dancers and light, center stays alive but not chaotic. Celebrate that Mary Jane Girls / Rick James Motown funk era’s nightlife glamour.
```

**Negative (append):**
```
static mannequin poses only, corporate office party, 2010s LED wall festival,
trap 2018 aesthetic, pure portrait headshot no environment, empty abandoned club,
horror red rooms, text-heavy flyer spam, sports bar screens
```

**Suggested params:** guidance **3.0–3.4** (more atmosphere/motion); LoRA
**0.65–0.8**; same dual resolutions. Seed family **MJG-B** (different from
#23 so the two images stay distinct).

**Pairing tip:** Use **#23** when the clip is a clean drop-in of the track or a
title card; use **#24** when the mix moment is the long groove / party stretch.
Both can sit on the same short-form carousel as “cover glam” vs “all night
floor.”

---

## 8. Variant protocol

Change **one** variable at a time; always record the seed.

1. Fix prompt pair + negative. Generate **6–8 seeds** at base params; keep two
   strongest compositions.
2. Sweep **guidance**: 2.5 / 3.2 / 4.0 on survivors.
3. Sweep **retro-anime LoRA strength**: 0.55 / 0.7 / 0.85.
4. Only then edit prose.

**Record with every keeper:** CLIP, T5, negative, seed, steps, guidance, cfg,
sampler, scheduler, resolution(s), LoRA names + strengths, model build.

Keep generated PNGs out of Git unless you explicitly want a small reviewed
asset committed. A local parameter manifest next to the renders is the durable
artifact.

---

## 9. Open questions (soft)

- **House look vs pure era variety:** one low-strength grade LoRA across all
  cards vs letting each era diverge hard. Decide before a hundred-image batch.
- **Card 8:** keep PE + AD as one still, or split into two prompts.
- **LoRA inventory:** send the actual list on the 3060 box (names + trigger
  words) and this file can map specific strengths per card.
- **A/B publish order:** short-form pair with on-screen labels NONE vs GUIDED
  before/after the same musical excerpt is the clearest experiment.

---

## 10. Brand identity assets — profile + links page

These are **not** mix era cards. They are the fixed face of the project across:

| Surface | URL / place |
|---|---|
| YouTube | https://www.youtube.com/@claw-dj |
| TikTok | https://www.tiktok.com/@clawdj6 |
| Links page (self-hosted) | `repos/links` example `examples/claw-dj/` → deploy as its own site |

Generate once, reuse everywhere. Prefer **one master square avatar** and crop
exports rather than three unrelated faces.

### Shared brand DNA (use in every brand prompt)

```
project: claw-dj
vibe: hip-hop & R&B first (open to other genres) · real DJ craft · code + AI in the loop
look: retro-anime still + night studio / vinyl / decks · warm amber + deep navy
tone: serious craft, not party-bro meme; elegant, cinematic, slightly mythic
```

**Shared brand negative (append to baseline negative from §3):**

```
corporate stock photo smile, LinkedIn headshot lighting, generic EDM laser rave,
meme Wojak, low-effort clipart, busy unreadable collage, random watermarks,
misspelled claw-dj text, claw dj wrong hyphenation spam, pure white void,
daytime beach vacation, sports jersey sponsor logos
```

---

### 10A. Master profile avatar (TikTok + YouTube + links)

**Use as:** TikTok profile photo, YouTube channel icon, links-page `avatar.jpg`.

| Export | Size | Notes |
|---|---|---|
| Master generate | **1024 × 1024** | Square. |
| Platform upload | 800×800 or 1024×1024 | Platforms re-encode; keep source. |
| Links page | ≥512×512, square, ideally &lt;150 KB | `public/avatar.jpg` |

**Face/center rule:** put the subject in the **center 70%**. Platforms crop
circles; corners die.

#### Variant A — icon mascot (recommended default)

**CLIP-L:**
```
retro anime, claw-dj brand avatar, circular-friendly centered composition, anthropomorphic sleek panther or claw emblem fused with vinyl record and DJ mixer, amber rim light, deep navy background, glossy black chrome, single strong icon, clean silhouette, profile picture
```

**T5:**
```
A square brand avatar for claw-dj, designed to read at tiny circular crop: centered retro-anime icon of a sleek dark panther or abstract claw mark integrated with a vinyl record and small DJ mixer faders, warm amber rim light against deep navy void, high contrast, glossy black and chrome accents, no tiny details at the edges. Looks like a premium music-channel mark — mythic West Coast / East Coast crate energy without copying a real label logo. Minimal, bold, immediately recognizable. Optional tiny subtle “claw” motif, not busy lettering. Center-weighted for TikTok and YouTube profile circles.
```

**Negative (append):**
```
full body crowded scene, tiny unreadable UI, multiple faces, photoreal celebrity,
random brand logos, Instagram filter selfie, text-heavy poster
```

**Params:** guidance 3.5–4.0; retro-anime LoRA 0.7–0.9; steps 24–28.

#### Variant B — stylized DJ portrait (if you want a “person”)

**CLIP-L:**
```
retro anime, original character DJ portrait, headphones, warm amber key light, deep navy, centered bust, calm focused expression, claw-dj channel avatar, clean shoulders-up crop
```

**T5:**
```
Square retro-anime portrait of an original character (not a real celebrity): young adult DJ, headphones around neck or on one ear, calm focused eyes, soft amber key light, deep navy backdrop, subtle vinyl bokeh. Shoulders-up, large face, center crop-safe for circular avatars. Stylish street-meets-studio wardrobe, timeless rather than meme fashion. Brand feeling of claw-dj: craft, anthologies, hip-hop and R&B history — not a party influencer face. No celebrity likeness required.
```

**Negative (append):**
```
celebrity lookalike, known musician face, selfie arm, cigarette close-up,
extreme beauty filter plastic skin, group photo
```

**Recommendation:** ship **Variant A** as the stable brand mark; keep B as an
alternate if you want a more human channel face later.

---

### 10B. YouTube channel banner (desktop + TV + mobile safe)

YouTube banner upload target is large; design for **safe areas**.

| | |
|---|---|
| Generate | **1536 × 614** (approx 2.5:1) or **1344 × 768** then crop/letterbox carefully |
| Upload target | **2560 × 1440** after upscale if needed |
| Safe center | Keep logo + title idea in the **center ~1546×423** region (TV/desktop) |
| Corners | Assume mobile crops left/right — no critical detail at far edges |

**CLIP-L:**
```
retro anime, YouTube channel banner wide, claw-dj, dual turntables Mixxx energy, vinyl crates skyline night, amber and navy cinematic grade, wide empty center for title safe zone, hip hop R&B DJ channel art
```

**T5:**
```
Wide cinematic channel banner for claw-dj: retro-anime night studio with two decks and a mixer in soft silhouette left and right, vinyl crates and a hazy city skyline suggestion in the outer thirds, deep navy and warm amber. The horizontal center stays relatively calm and open so a future wordmark “claw-dj” could sit there (generate without text first if lettering fails). Mood: DJ craft and crate energy — hip-hop and R&B first, open to more — elegant, not festival EDM chaos. Seamless wide composition, film grain, high quality.
```

**Negative (append):**
```
vertical phone frame, square only, busy center clutter, laser rave rainbow,
huge unreadable wall of tracklists, watermark corner spam
```

**Params:** guidance 3.2; LoRA 0.6–0.8 (don’t melt the wide scene).

---

### 10C. Links-page avatar

Same file as **10A**. After picking a seed:

1. Export square JPEG/PNG → `public/avatar.jpg` in the links project.
2. Optional: slight dark vignette so it sits well on `dark-space` theme.

No separate prompt required unless you want a **links-only** softer crop:

**CLIP-L (optional softer links crop):**
```
same as 10A variant A, slightly softer contrast, dark navy background matching dark-space theme, circular avatar friendly
```

**T5:** Reuse 10A T5; add “matte finish, lower specular blowouts for web UI.”

**Negative:** same as 10A.

---

### 10D. Links-page Open Graph / share image (`og.png`)

When someone pastes your links URL in Slack/X/iMessage.

| | |
|---|---|
| Size | **1200 × 630** (generate **1344 × 768**, center-crop/pad to 1200×630) |
| Path | `public/og.png` |
| Config | `social_meta.og_image` = full `https://…/og.png` |

**CLIP-L:**
```
retro anime, open graph banner 1.91:1, claw-dj link in bio card, vinyl and decks, amber navy, elegant music brand, wide cinematic still, clean center
```

**T5:**
```
A wide social preview image for the claw-dj links page: retro-anime night crate-digging energy, vinyl, soft deck silhouettes, amber rim light, deep navy paper-like negative space in the center for an optional later title. Feels like a premium music project link-in-bio, not a tech startup landing page. Cinematic, simple, high contrast, no tiny text.
```

**Negative (append):**
```
screenshot of a website, browser chrome, QR code spam, app store badges,
stock handshake business photo
```

---

### 10E. Optional favicon concept (if you draw vector later)

Flux is weak at tiny favicons. Prefer hand-vector or simplify the **10A** mark
to a **single claw + arc of vinyl** at 32×32. If you still want a Flux study:

**CLIP-L:**
```
minimal icon only, single claw mark over vinyl arc, black and amber, flat, centered, no detail, logo study
```

**T5:**
```
Extremely simple logo study: one abstract claw stroke intersecting a partial vinyl circle, amber on black, flat design, huge clear shape, no gradients required, no text.
```

**Negative:**
```
photoreal, complex scene, multiple objects, fine line noise
```

---

## 11. What to put on each profile (copy + checklist)

### Voice principles (for bios, not for internal docs)

1. **Succinct wins.** TikTok and YouTube mobile cut you off. One clear line beats
   a paragraph. Put the rest on the links page or in video captions.
2. **Lead with sound:** hip-hop and R&B first — leave the door open to other
   genres without listing everything.
3. **Skip “anthology” in public copy.** That’s internal program language. Out
   loud: mixes, sets, transitions, eras, crates.
4. **AI + code: soft, not a pitch deck.** One short clause is enough
   (“software- and AI-assisted” / “built with code + AI”). Don’t open with
   “AI DJ” or bury the music under the stack.
5. **Same display name + avatar + vibe** on every platform even if @handles differ.

### Naming consistency

| Place | Current | Advice |
|---|---|---|
| YouTube | `@claw-dj` | Keep as **canonical** brand spelling. |
| TikTok | `@clawdj6` | Fine if that handle was available; **display name** = **claw-dj**. |
| Links | handle `claw-dj` | Matches YouTube. |
| Bio / About | — | Always write **claw-dj**, not “Claw DJ” inconsistently. |

### Recommended copy (succinct — use these)

**TikTok bio (paste as-is, ~70–90 chars):**
```
Hip-hop & R&B mixes · other genres too · software + AI · full sets → YT @claw-dj
```

Alternate if you want even shorter:
```
Hip-hop & R&B (and more) · mixes with code + AI · YT @claw-dj
```

**Links page tagline / YouTube channel keywords line:**
```
Hip-hop & R&B mixes · open to more · built with code + AI
```

**YouTube About (short — preferred):**
```
claw-dj — hip-hop and R&B mixes, plus whatever else fits the night.
Real decks and transitions; software and generative AI in the loop.

Shorts: blends and moments. Full mixes on this channel.

TikTok: @clawdj6
Links: [your links page URL]
```

**YouTube About (slightly longer — only if you want more room):**
```
claw-dj plays hip-hop and R&B first, and leaves the door open to other genres
when the set needs it. Selection, order, and transitions are the craft — with
code and generative AI helping build and run the mixes.

Clips show the handoffs. YouTube holds the longer sets.

TikTok: @clawdj6
Links: [your links page URL]
```

**Channel keywords (YouTube Studio, comma-separated ideas):**
```
hip hop mix, R&B mix, DJ mix, transitions, boom bap, west coast, east coast, funk, soul, AI assisted DJ, open source
```

### YouTube — what to edit

1. **Channel name:** `claw-dj`
2. **Handle:** keep `@claw-dj`
3. **Icon:** upload 10A master (square)
4. **Banner:** upload 10B (watch mobile crop)
5. **Description:** use the **short** About above
6. **Links / website:** primary → links page; secondary → TikTok
7. **Channel trailer (optional later):** 30–60s best transition + “full mix on channel”
8. **Keywords:** as above (no “anthology”)
9. **Featured sections:** “Full mixes”, “Shorts”, era/genre shelves once you have enough uploads
10. **Branding color:** deep navy / amber if available

### TikTok — what to edit

1. **Name (display):** `claw-dj` (not only clawdj6)
2. **Username:** keep `@clawdj6` unless a cleaner handle becomes available
3. **Photo:** same 10A avatar
4. **Bio:** short TikTok line above
5. **Website link:** links page (or YouTube if links not live yet)
6. **Category:** Music / DJ if available
7. **Pin 1–3 videos:** strongest transitions or clearest era moments
8. **Captions:** name the **era / vibe / lead track**, not internal project jargon; point to full mix on YT when it exists

### Links page (`repos/links` example `claw-dj`) — what to edit

Already scaffolded under:

```
repos/links/examples/claw-dj/
  site.config.json
  links.json
  archive.json
  README.md
```

**Suggested `site.description` / `profile.tagline`:** use the links tagline
above (hip-hop & R&B · open to more · code + AI).

**Buttons shipping in the example:**

1. YouTube — full mixes & Shorts → `https://www.youtube.com/@claw-dj` (highlight)
2. TikTok — transition clips → `https://www.tiktok.com/@clawdj6` (highlight)
3. GitHub — open project → `https://github.com/InServiceOfX/claw-dj`

**Theme:** `dark-space` + `color_scheme: dark` (matches night studio brand).

**After you generate images:**

1. Deploy a **separate** Vercel project (do not clobber `ernestyalumni-links`).
2. `python3 scripts/apply-example.py --name claw-dj`
3. Copy `avatar.jpg` + `og.png` into `public/`
4. Set real `site.url` and absolute `social_meta.og_image`
5. `python3 scripts/validate.py && npm run build`
6. Put the live URL on TikTok + YouTube

**Later adds (keep list short):**

- “★ Latest mix” (YouTube video URL) at **position 1**, highlight true
- One featured era or set when you have a hero upload

### Cross-platform “do this in order”

1. Generate **10A avatar** + **10B banner** + **10D og** on the 3060 box.  
2. Upload avatar to TikTok + YouTube; banner to YouTube.  
3. Paste the **short** bios above.  
4. Build links page from `examples/claw-dj`.  
5. Set Website/Link fields on both platforms to the links URL.  
6. Pin one strong clip on TikTok; add channel trailer when you have a hero mix.  
7. Captions: era / vibe / track — link home for the full set.

### What not to do

- Different random avatars per platform (breaks recognition).  
- Bio that only says “music” with no genre hook.  
- Leading with “AI DJ agent platform…” — music first, tech one quiet clause.  
- Public use of internal words like “anthology,” “plan slug,” “guided format.”  
- Linktree of 20 dead buttons — three strong links beat twelve weak ones.  
- Implying official affiliation with labels/artists you don’t have.
