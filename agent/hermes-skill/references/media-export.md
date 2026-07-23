# Publishing Mixxx recordings as static-image videos

Use this workflow when turning a Mixxx WAV recording into a YouTube upload master or short promotional clips.

## Inputs and defaults

1. Locate the exact WAV and images; do not infer a malformed path from prose. Mixxx normally writes recordings under `~/Music/Mixxx/Recordings/`.
2. Probe every input with `ffprobe`. Confirm duration, sample format, channels, sample rate, and image dimensions.
3. If cadence is unspecified, use hard cuts every 30 seconds and cycle through images in the supplied order. Do not add fades, zooms, or motion unless requested.
4. For a high-quality YouTube source, prefer H.264 1280x720 `yuv420p` in MOV with the original PCM stream copied. Create AAC MP4 only as a separate smaller derivative.

## Lossless-audio upload master

Create an `ffconcat version 1.0` list that repeats images until it exceeds the audio duration. Repeat the final file entry because the concat demuxer needs a following entry for the final duration.

```bash
ffmpeg -y \
  -f concat -safe 0 -i sequence.ffconcat \
  -i recording.wav \
  -map 0:v:0 -map 1:a:0 \
  -vf 'format=yuv420p' -r 30 \
  -c:v libx264 -preset medium -crf 18 \
  -c:a copy -movflags +faststart -shortest \
  output-youtube-pcm.mov
```

### Master verification

Do not report completion until all pass:

```bash
ffprobe -v error \
  -show_entries format=duration,size,format_name:stream=index,codec_name,codec_type,width,height,pix_fmt,r_frame_rate,sample_rate,channels,bit_rate \
  -of json output-youtube-pcm.mov

ffmpeg -v error -i output-youtube-pcm.mov -map 0:v:0 -map 0:a:0 -f null -

ffmpeg -v error -i recording.wav -map 0:a:0 -f md5 -
ffmpeg -v error -i output-youtube-pcm.mov -map 0:a:0 -f md5 -

ffmpeg -hide_banner -i output-youtube-pcm.mov \
  -map 0:v:0 -vf "select='gt(scene,0.10)',showinfo" \
  -an -f null - 2>&1
```

The decoded audio MD5 values must match. These are integrity checks, not security hashes. Inspect scene `pts_time` values and confirm changes occur only at intended boundaries.

## Vertical social teasers

Use 9:16 derivatives for Reels, Shorts, and X.

1. Pick a musical transition and create a 20–30 second excerpt beginning about 10–12 seconds before it.
2. Preserve the full 16:9 artwork. Do not center-crop away turntables, skyline, hands, or another important subject.
3. Build a 1080x1920 card with a darkened aspect-fill background, the complete artwork centered, and static branding in safe areas.
4. When a clip crosses a track boundary, render before/after cards and hard-cut exactly at the musical transition.
5. Encode H.264 High Profile, `yuv420p`, 30 fps, and stereo AAC at 48 kHz. A 0.15-second fade-in and 0.5-second fade-out prevent edge clicks.

Use the checked-in renderer:

```bash
python3 agent/hermes-skill/scripts/render_transition_teaser.py \
  --audio /absolute/path/recording.wav \
  --before-image /absolute/path/before.png \
  --after-image /absolute/path/after.png \
  --source-start 225 \
  --cut-offset 11 \
  --label 'CASSIE → JAGGED EDGE' \
  --series 'QUICK MIX 001' \
  --output /absolute/path/teaser-9x16.mp4
```

The script uses Swift/AppKit for cards and FFmpeg for media. It verifies required codecs, dimensions, duration, full decode, scene timing, and audio levels before reporting success.

### Manual FFmpeg equivalent

```bash
ffmpeg -y \
  -loop 1 -framerate 30 -t "$BEFORE_SECONDS" -i before-card.png \
  -loop 1 -framerate 30 -t "$AFTER_SECONDS" -i after-card.png \
  -ss "$SOURCE_START" -t 30 -i recording.wav \
  -filter_complex \
  "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p[v]; \
   [2:a]afade=t=in:st=0:d=0.15,afade=t=out:st=29.5:d=0.5[a]" \
  -map '[v]' -map '[a]' \
  -c:v libx264 -preset medium -crf 18 -profile:v high -level:v 4.2 \
  -c:a aac -b:a 320k -ar 48000 -movflags +faststart -shortest \
  teaser-9x16.mp4
```

## Verification gates for every teaser

- `ffprobe`: 1080x1920, H.264, 30 fps, stereo AAC 48 kHz, intended duration.
- Full decode: `ffmpeg -v error -i teaser.mp4 -f null -` exits zero.
- Scene detection: the only content change occurs at the intended musical transition. Similar cards may require a threshold near `0.005` instead of `0.10`.
- `volumedetect`: excerpt is neither silent nor unexpectedly clipped.
- Visual inspection: complete artwork, readable text, sensible safe areas.

## Editor versus batch renderer

Re-read editor repositories before building. In July 2026, the active OpenCut rewrite explicitly described itself as unfinished and directed users to `opencut-classic` for real editing. That status can change.

- Use FFmpeg for deterministic batch exports and exact timing.
- Use the currently recommended stable OpenCut version for interactive refinements.
- Do not put an optional editor build in the critical path when existing tools can produce and verify the output.
- If installation approval is declined, do not retry through another installer.

## Delivery

Report exact paths, durations, dimensions, codecs, file sizes, decode results, audio verification, and scene timing. Save source windows and posting order in a README beside teaser batches. Keep generated media out of Git by default. Warn that commercial tracks may trigger YouTube Content ID claims or restrictions.
