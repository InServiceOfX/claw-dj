# Media renderers

Canonical procedure: `../references/media-export.md`.

These scripts are the Git copies of campaign renderers that used to live only
under `~/Music/Mixxx/Recordings/`. **Outputs stay there.** Do not commit WAV/MP4.

| Script | Campaign |
|---|---|
| `render_transition_teaser.py` | Generic 9:16 before/after teaser |
| `full-mix/render_noexpert_mix.py` | 2026-08-09 Format None YouTube master |
| `full-mix/render_guided_experimental_mix.py` | 2026-08-09 Guided Experimental master |
| `ab-shorts/render_shorts.py` | 9:16 A/B shorts from those two mixes |
| `ab-shorts/POSTING.md` | Captions |
| `recruit/render_attention_short.py` | 9:16 recruit short (not-a-playlist hook + DJ/customer CTA) |

The full-mix / shorts scripts still point at absolute Mixxx + image paths from
that night. Treat them as the working recipe; parameterize on the next reuse.

Recruit campaign brief:
`docs/marketing/PRODUCT_DEMO_AND_RECRUIT_CAMPAIGN.md`.
