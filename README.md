# clip-factory

Local prototype: long video -> 3 short vertical (1080x1920) clips with face reframe and word-level burned captions.
Based on section 4.4 of `~/.hermes/docs/2026-10-03-clipping-business-research.md`. Nothing is uploaded anywhere.

## Setup

Supported baseline: Linux or WSL2, Python 3.11+, `uv`, Node.js 22+, npm, and
FFmpeg/ffprobe with libass. NVIDIA CUDA is optional; transcription has a CPU
fallback. On a fresh clone install system tools first, then reproduce the locked
Python and JavaScript environments:

```
uv sync
cd remotion && npm ci && cd ..
cd hyperframes && npm ci && cd ..
mkdir -p tools && curl -sSfL -o tools/blaze_face_short_range.tflite \
  https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite
```

To install the project's pinned agent skills:

```
git clone https://github.com/VasilijEpishkin/clip-factory-agent-tool-stack /tmp/clip-factory-agent-tool-stack
python3 /tmp/clip-factory-agent-tool-stack/install.py .
```

Account login, MCP configuration, and browser cookies are per-device and must
be configured locally; never copy `.mcp.json`, OAuth files, or cookies from
another machine.

For Windows, run the project inside WSL2 so FFmpeg, Python, Node, and skill
symlinks share the same filesystem.

```
ffmpeg -version && ffprobe -version        # confirm the system runtime
node --version && uv --version
```
Needs system `ffmpeg` with libass (`h264_nvenc` used when available, else libx264), `yt-dlp`, and an LLM CLI:

- `hermes` (default when configured): `export CLIP_HERMES_HOME=~/.hermes/profiles/<clip profile>` - a profile logged into
  a **separate** Codex subscription. Runs `hermes -z <prompt> -t safe --ignore-rules --cli`
  with `HERMES_HOME=$CLIP_HERMES_HOME`; provider and model are that profile's `model:` config (`gpt-5.4-mini` is rejected for ChatGPT-account Codex). Without the variable the backend is skipped (never the default profile: that is
  the owner's main Codex account) and `claude -p` is used.
- `codex` (`codex exec`, if installed and logged in), `claude` (`claude -p`).

### YouTube bot check ("Sign in to confirm you're not a bot")

Two layers, neither guaranteed. Prefer the rights holder's source file from the campaign brief.
1. PO tokens via [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) (GPL-3.0; we only run it,
   no code copied). The plugin is a pip package and is installed into the yt-dlp uv tool (2026-10-03):
   `uv pip install --python ~/.local/share/uv/tools/yt-dlp/bin/python bgutil-ytdlp-pot-provider==2.0.1`.
   It also needs a token provider; script mode works without Docker (Node >= 22, already present), **built 2026-11-03** (`~/bgutil-ytdlp-pot-provider`, script-node provider detected by yt-dlp):
   ```
   git clone --single-branch --branch 2.0.1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git ~/bgutil-ytdlp-pot-provider
   cd ~/bgutil-ytdlp-pot-provider/server && npm ci && npx tsc     # -> build/generate_once.js, found by the plugin by default
   ```
   (or the HTTP server: `node build/main.js`, or `docker run -d --init -p 127.0.0.1:4416:4416 brainicism/bgutil-ytdlp-pot-provider`).
   Check: `yt-dlp -v URL 2>&1 | grep pot` should show `Generating a gvs PO Token ... via bgutil script`.
2. `--cookies cookies.txt` exported from a **separate** throwaway account, never the owner's main one (it can get banned).

Metadata (incl. `heatmap`) already works from this IP without either; format downloads are what get blocked.

## Run

```
P="nice -n 10 .venv/bin/python clip.py"
$P fetch URL --id ID       # work/ID/src.* (best <=2160p, retry capped at 1080p), meta.json (+ YouTube heatmap); --cookies FILE
$P transcribe ID           # work/ID/transcript.json  (CUDA medium int8_float16, or CPU small int8; --device/--model)
$P highlights ID           # work/ID/highlights.json  (--backend hermes|codex|claude; falls back to the others)
$P edit ID                 # out/ID/clip_N.mp4 + clip_N.ass + edit.json  (--stack, --no-speakers)
$P qa ID                   # out/ID/qa.json + clip_N_f1.png / clip_N_f2.png
.venv/bin/python -m pytest -q
```

### MoneyPrinterTurbo WebUI

The optional standalone generator can be installed at the reviewed revision in
`vendor/MoneyPrinterTurbo`:

```
mkdir -p vendor/MoneyPrinterTurbo
git -C vendor/MoneyPrinterTurbo init
git -C vendor/MoneyPrinterTurbo remote add origin https://github.com/harry0703/MoneyPrinterTurbo.git
git -C vendor/MoneyPrinterTurbo fetch --depth 1 origin bbe7eb9ae3e7a44f4553070b82d4a126aad62a33
git -C vendor/MoneyPrinterTurbo checkout --detach FETCH_HEAD
```

Its local `config.toml` and API keys are not stored here; configure those on
each device before using the WebUI. From WSL, start it with the upstream
instructions in `vendor/MoneyPrinterTurbo`:

```
./scripts/start_moneyprinterturbo.sh
```

Then open `http://localhost:8501` in Windows. If WSL localhost forwarding is
disabled, use the current WSL address from `hostname -I`, for example
`http://172.29.54.130:8501`. Windows users can run `start-moneyprinterturbo.bat`
from Explorer; it starts the WSL service and opens the browser.

The project-local `.agents/skills/` directory connects the imported YouTube,
video-shotcraft, brag, prompt-master, Seedance, and YouMind workflows.

## How it works

- **highlights**: transcript segments `[start-end] text` go to the LLM, which returns `[{start,end,hook,caption,title,why}]`.
  If `meta.json` has a YouTube `heatmap` ("Most replayed", saved by `fetch`), the top 8 buckets (merged, first bucket
  skipped) go into the prompt and `validate()` keeps candidates overlapping a peak first.
  If `hooks.json` exists (`[{hook_type, template, example, evidence}]`, written by the trends profile), up to 15 lines
  of it go into the prompt; every clip gets a `hook_type` from a closed taxonomy (unknown -> `other`), copied to `qa.json`.
  The committed `hooks.json` holds 5 generic PLACEHOLDER patterns, not measured data.
  `caption` is the on-screen banner: it must add context, not repeat the spoken hook (falls back to `title` if it does).
  `validate()` snaps times to word boundaries, trims to <=45 s, extends slightly-short picks to >=20 s, drops overlaps/garbage, keeps 3.
- **edit**: faces sampled 3x/s with MediaPipe on the clip range (one frame in RAM at a time), scene cuts via PySceneDetect,
  one static 9:16 crop per scene centred on the median face x; in a two-shot (two faces >=0.2 frame-width apart in >=half the
  samples) the crop follows the active speaker: mouth-region frame difference / region contrast per 0.4 s window, counted
  only where audio RMS >= 0.18 of the scene peak, a new speaker must win 3 windows in a row (cut backdated to the run start).
  `--stack`: when both talk (each >= 20% of windows, scene >= 2.5 s) both are stacked 1080x960 each, captions on the seam.
  Speaker logic ported from [mutonby/openshorts](https://github.com/mutonby/openshorts) (MIT, (c) 2024 OpenShorts);
  their per-speaker percentile normalisation was replaced (it hid a continuous talker on short scenes); ffmpeg `crop` with a per-scene `if(lt(t,..))` expression,
  ASS karaoke captions (<=3 words, current word yellow, held through pauses < 1.2 s) + banner (`caption`, never the spoken hook) for the first 2.5 s, loudnorm to -14 LUFS.
- **qa**: duration 20-45 s, 1080x1920, audio mean volume > -40 dB, caption events, face fully inside frame on >=60% of
  samples (2/s), >=3 words spoken in the first 2 s, first word not a filler (and/so/but/like/um/uh/you know).
  `validate()` moves a filler opening to the next sentence start within 1.5 s (else past the filler run, else drops the pick).

## Test input

- Source: "NASA Astronaut Discusses Life In Space With KHQ-TV, Spokane's Lowedown On Life Podcast – July 18, 2025 (jsc2025m000132)"
  https://commons.wikimedia.org/wiki/File:NASA_Astronaut_Discusses_Life_In_Space_With_KHQ-TV,_Spokane%E2%80%99s_Lowedown_On_Life_Podcast_%E2%80%93_July_18,_2025_(jsc2025m000132).webm
- License: **Public domain** (NASA work, per the Wikimedia Commons file page). ~16.7 min, 1920x1080.
- YouTube was tried first (CC-BY search filter) but yt-dlp gets "Sign in to confirm you're not a bot" from this IP for every client.

## First run (2026-10-03, nasa-khq, all steps under `nice -n 10`, a heavy rebuild running in parallel)

| step | wall | peak RSS | notes |
|---|---|---|---|
| fetch | 13 min | 66 MB | 508 MB VP9 1080p from Commons at ~0.6 MB/s |
| transcribe GPU (medium, int8_float16) | 71 s | 1.98 GB | 16.7 min audio, ~14x realtime |
| transcribe CPU (small, int8, 4 threads) | 191 s | 1.52 GB | ~5x realtime |
| highlights (claude -p) | 81 s | 0.33 GB | codex CLI not logged in (401) -> fallback |
| edit (3 clips, h264_nvenc) | 78 s | 0.70 GB | ~18-30 s per clip, face sampling dominates |
| qa | 63 s | 0.35 GB | |

All 3 clips pass QA (20-45 s, 1080x1920, audio ~-18 dB mean, captions, face in frame 100%, speech in first 2 s).
