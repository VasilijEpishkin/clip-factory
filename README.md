# clip-factory

Local prototype: long video -> 3 short vertical (1080x1920) clips with face reframe and word-level burned captions.
Based on section 4.4 of `~/.hermes/docs/2026-10-03-clipping-business-research.md`. Nothing is uploaded anywhere.

## Setup

```
uv sync                                    # .venv with faster-whisper, scenedetect, mediapipe, cuBLAS/cuDNN wheels
mkdir -p tools && curl -sSfL -o tools/blaze_face_short_range.tflite \
  https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite
```
Needs system `ffmpeg` with libass (`h264_nvenc` used when available, else libx264), `yt-dlp`, and `codex` or `claude` CLI.

## Run

```
P="nice -n 10 .venv/bin/python clip.py"
$P fetch URL --id ID       # work/ID/src.*, meta.json
$P transcribe ID           # work/ID/transcript.json  (CUDA medium int8_float16, or CPU small int8; --device/--model)
$P highlights ID           # work/ID/highlights.json  (--backend codex|claude; falls back to the other)
$P edit ID                 # out/ID/clip_N.mp4 + clip_N.ass + edit.json
$P qa ID                   # out/ID/qa.json + clip_N_f1.png / clip_N_f2.png
.venv/bin/python -m pytest -q
```

## How it works

- **highlights**: transcript segments `[start-end] text` go to the LLM, which returns `[{start,end,hook,title,why}]`.
  `validate()` snaps times to word boundaries, trims to <=45 s, extends slightly-short picks to >=20 s, drops overlaps/garbage, keeps 3.
- **edit**: faces sampled 3x/s with MediaPipe on the clip range (one frame in RAM at a time), scene cuts via PySceneDetect,
  one static 9:16 crop per scene centred on the median face x; ffmpeg `crop` with a per-scene `if(lt(t,..))` expression,
  ASS karaoke captions (<=3 words, current word yellow) + hook banner for the first 2.5 s, loudnorm to -14 LUFS.
- **qa**: duration 20-45 s, 1080x1920, audio mean volume > -40 dB, caption events, face fully inside frame on >=60% of
  samples (2/s), >=3 words spoken in the first 2 s.

## Test input

- Source: "NASA Astronaut Discusses Life In Space With KHQ-TV, Spokane's Lowedown On Life Podcast – July 18, 2025 (jsc2025m000132)"
  https://commons.wikimedia.org/wiki/File:NASA_Astronaut_Discusses_Life_In_Space_With_KHQ-TV,_Spokane%E2%80%99s_Lowedown_On_Life_Podcast_%E2%80%93_July_18,_2025_(jsc2025m000132).webm
- License: **Public domain** (NASA work, per the Wikimedia Commons file page). ~16.7 min, 1920x1080.
- YouTube was tried first (CC-BY search filter) but yt-dlp gets "Sign in to confirm you're not a bot" from this IP for every client.
