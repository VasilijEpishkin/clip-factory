# Gemini <-> clip-factory bridge

Gemini (Tasks, Google AI Pro) generates images/video. Any project agent (Claude Code, Codex, Hermes) assembles them into a reel here.
The only channel is the Google Drive folder `ClipFactory` (owner `umoxinacuve54@gmail.com`, root id `1F1r-AC85TorBWuFZXXlSyUSPDtYqnGbE`).
Nothing talks directly: every side polls the folder. Each writer owns its own files, so there are no write conflicts.

## Verified (2026-11-03)
- A Gemini Task created `projects/test.txt` (as a Google Doc, content `ok`) and `projects/clipfactory_project_studio.jpg` (928 KB). So Tasks **can write text and images to Drive**.
- Gemini turns text files into **Google Docs**. Agents must read results as Docs (`read_file_content`), never rely on `.json`/`.md` extensions from Gemini.
- Not yet verified: video (Veo) saved to Drive, Gmail-monitor trigger, minimum schedule interval, daily generation quotas.
- Triggers available in Tasks ([help](https://support.google.com/gemini/answer/17094710)): time schedules (once/hourly/daily/weekly), Gmail monitors (email matching a filter), topic monitors.
  **No Drive-event trigger.** Manual creation in the Scheduled page is time-only; a Gmail trigger must be created in chat. Limits: 50 schedules, 15 concurrent; run times are approximate.

## Layout
```
ClipFactory/
  _README.md  _templates/  _styles/
  projects/<YYYY-MM-DD>_<slug>/
    brief.md            agent writes
    requests/<id>.md    agent writes   (one per asset; id = S03_img)
    01_to_gemini/       agent writes   (reference images)
    02_from_gemini/{images,video,audio}/<id>_v<N>.<ext>   Gemini writes
    results/<id>_v<N>   Gemini writes  (Doc; first line STATUS: in_progress|done|failed)
    reviews/<id>_v<N>   agent writes   (Doc/md; first line VERDICT: approved|rejected, then feedback)
    03_final/           agent writes   (finished reel)
    _archive/
```
A file is edited only by its owner. Never overwrite: a new attempt is `v<N+1>`.

## State machine (derived from files, no shared status field)
| Condition for asset `<id>` | Meaning | Next actor |
|---|---|---|
| `requests/<id>` exists, no `results/<id>_v1` | pending | Gemini |
| `results/<id>_vN` STATUS in_progress, older than 3 h | stale claim | Gemini retries as v(N) again |
| `results/<id>_vN` STATUS done + media file | ready for review | agent |
| `reviews/<id>_vN` rejected | needs redo, feedback inside | Gemini makes v(N+1) |
| `reviews/<id>_vN` approved | final asset | agent assembles |
| all requests approved, no `03_final/*` | project ready to cut | agent |

`request` fields (plain `key: value` lines): `id, kind (img|vid|aud), prompt, aspect (9:16), duration_s, refs (files in 01_to_gemini), style (file in _styles), source_frame (img id; a vid waits until that still is approved), version (1)`.
Per Gemini run: up to 4 images OR 1 video (limits are compute-based, ~5 h windows; Veo/image model names in the app change, so the task says "best available" and `results` records the exact model).

## Gemini side
Task text to paste into Gemini "Task" mode: `docs/gemini-task-prompt.md` (also stored as `_templates/gemini_task.md` on Drive).
Trigger: hourly schedule (time-based, can be created manually on the Scheduled page). For urgency, say "go" in the task thread.
Optional faster trigger: Gmail monitor on a subject like `[ClipFactory] new request` (needs an email sent to that account; not set up).

## Agent side (any agent)
Poll loop, run on a timer, idempotent:
1. List `projects/*/results/` and `reviews/`; find assets with a `done` result and no review.
2. Download the media, look at it (frames/ffprobe), write `reviews/<id>_vN` (approved or rejected + concrete feedback).
3. For projects where every request is approved and `03_final/` is empty: assemble with clip-factory tools (ffmpeg, Remotion, `clip.py edit`, captions), upload the reel to `03_final/`, write `03_final/README` with what was used.
4. Create new work: write `brief.md` and `requests/*.md` for a new reel (the only step that starts a cycle).
Never write into `02_from_gemini/` or `results/`. Never delete; move to `_archive/`.

Access per agent:
- **Claude Code**: the Google Drive connector (create/read/search/download; can upload files). Timer: `/loop 30m <poll prompt>` or `/schedule`.
- **Codex / Hermes**: no connector. Drive is mirrored to `gemini-bridge/` in this repo (gitignored) by `scripts/bridge_poll.sh` (rclone remote `gdrive:`, rooted at `ClipFactory`, token in `~/.config/rclone/rclone.conf`). Docs arrive as `.txt`. The script pulls, pushes agent-owned dirs, and launches `BRIDGE_AGENT=claude|codex|hermes|none` only when `results/` or `02_from_gemini/` changed. Cron entry not installed yet.
Poll prompt (same for every agent): `Follow docs/gemini-bridge.md "Agent side": run one poll on Drive folder ClipFactory, report what changed in one line.`

## Rules of thumb
- Videos: 9:16, 1080x1920, MP4, 5-8 s per shot, one shot per request. Longer = several requests.
- Max 3 assets per Gemini run (compute limit); the rest wait for the next run.
- No real people, no third-party branding, no secrets in the folder.
