#!/usr/bin/env python3
"""clip-factory: long video -> short vertical clips.

Steps (files on disk between them, all under work/<id>/ and out/<id>/):
  fetch URL --id ID   -> work/ID/src.*, meta.json
  transcribe ID       -> work/ID/transcript.json   (faster-whisper, word timestamps)
  highlights ID       -> work/ID/highlights.json   (LLM: hermes/codex profile if CLIP_HERMES_HOME, else claude -p)
  edit ID             -> out/ID/clip_N.mp4 (+ .ass)  (cut + 9:16 face reframe + burned captions)
  qa ID               -> out/ID/qa.json (+ 2 PNG frames per clip)
"""
import argparse, json, os, re, shutil, statistics, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NODE = Path.home() / ".nvm/versions/node/v22.23.2/bin/node"
YTDLP = shutil.which("yt-dlp") or str(Path.home() / ".local/bin/yt-dlp")
FACE_MODEL = ROOT / "tools/blaze_face_short_range.tflite"
HOOKS = ROOT / "hooks.json"  # [{hook_type, template, example, evidence}], written by the trends profile
MIN_LEN, MAX_LEN, N_CLIPS = 20.0, 45.0, 3
OUT_W, OUT_H = 1080, 1920


def wdir(vid): return ROOT / "work" / vid
def odir(vid): return ROOT / "out" / vid
def src(vid): return next(p for p in wdir(vid).glob("src.*") if p.suffix != ".part")
def load(p): return json.loads(Path(p).read_text())
def save(p, obj): Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
def all_words(tr): return [w for s in tr["segments"] for w in s["words"]]
def norm_words(t): return re.findall(r"[a-z0-9']+", t.lower())


# ---------------- fetch ----------------
def fetch(a):
    d = wdir(a.id); d.mkdir(parents=True, exist_ok=True)
    base = [YTDLP, "--js-runtimes", f"node:{NODE}", "--no-playlist", "-o", str(d / "src.%(ext)s"),
            "--print-json", "--no-simulate"] + (["--cookies", a.cookies] if a.cookies else
                                                ["--cookies-from-browser", a.browser] if a.browser else [])
    # up to 4K: a 9:16 crop of 1080p is 608x1080 and gets upscaled 1.78x; of 2160p it is downscaled
    for res in ("2160", "1080"):
        r = subprocess.run(base + ["-S", f"res:{res},vcodec:vp9", a.url], capture_output=True, text=True)
        if r.returncode == 0: break
        print(f"res:{res} failed: {r.stderr.strip()[-400:]}", file=sys.stderr)
    else:
        sys.exit("fetch failed")
    info = json.loads(r.stdout.splitlines()[-1])
    keep = ("webpage_url", "title", "license", "duration", "width", "height", "uploader", "heatmap")  # heatmap: YouTube "Most replayed"
    save(d / "meta.json", {k: info.get(k) for k in keep} | {"url": a.url})
    print(src(a.id))


# ---------------- transcribe ----------------
def _preload_cuda():
    """ctranslate2 dlopen()s cuBLAS/cuDNN by soname; preload the pip wheels' copies so no LD_LIBRARY_PATH is needed."""
    import ctypes, nvidia
    base = Path(list(nvidia.__path__)[0])
    for pat in ("cublas/lib/libcublasLt.so.*", "cublas/lib/libcublas.so.*", "cudnn/lib/libcudnn*.so.*"):
        for so in sorted(base.glob(pat)):
            ctypes.CDLL(str(so), mode=ctypes.RTLD_GLOBAL)


def transcribe(a):
    from faster_whisper import WhisperModel
    import ctranslate2
    device = a.device
    if device == "auto":
        device = "cuda" if ctranslate2.get_cuda_device_count() else "cpu"
    if device == "cuda":
        try: _preload_cuda()
        except Exception as e: print("cuda libs not loadable, using cpu:", e); device = "cpu"
    model_name = a.model or ("medium" if device == "cuda" else "small")
    ctype = "int8_float16" if device == "cuda" else "int8"
    t0 = time.time()
    model = WhisperModel(model_name, device=device, compute_type=ctype, cpu_threads=4)
    # decode via ffmpeg (16 kHz mono float32, ~64 MB per 17 min); faster-whisper's PyAV path breaks with av>=17
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src(a.id)), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, info = model.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, vad_filter=True, beam_size=1)
    out = []
    for s in segs:  # generator: streams segment by segment
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "words": [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for w in s.words]})
        print(f"\r{s.end:7.1f}s / {info.duration:.0f}s", end="", file=sys.stderr)
    save(wdir(a.id) / "transcript.json", {"language": info.language, "duration": info.duration,
         "model": model_name, "device": device, "secs": round(time.time() - t0, 1), "segments": out})
    print(f"\n{len(out)} segments, {model_name}/{device}, {time.time() - t0:.0f}s")


# ---------------- highlights ----------------
PROMPT = """You are a short-form video editor. Below is a timestamped transcript of a long video.
Pick the {n} best moments to cut as standalone vertical shorts (TikTok/Shorts/Reels).
Rules:
- each clip {lo:.0f}-{hi:.0f} seconds long (end - start), boundaries on the given timestamps;
- the first 2 seconds must already be a strong hook (a surprising claim, question, punchline) - no warm-up, no greetings;
- the first spoken word must NOT be a filler: "and", "so", "but", "like", "um", "uh", "you know" - start at the next sentence;
- self-contained: understandable without the rest of the video, ends on a finished thought;
- clips must not overlap.
Return ONLY a JSON array, no prose, no code fences:
[{{"start": <sec>, "end": <sec>, "hook": "<the opening words>", "hook_type": "<one of: {hook_types}>", "caption": "<on-screen banner, 2-6 words>", "title": "<short catchy title>", "why": "<one line>"}}]
"caption" is burned on screen over the first seconds while the hook is spoken: it must ADD context the words don't give
(who is speaking, the stakes, the topic), never repeat or paraphrase the opening words.

{extra}TRANSCRIPT:
{transcript}
"""


def heatmap_peaks(hm, k=8):
    """Top-k "Most replayed" buckets of a yt-dlp heatmap, touching ones merged: [(t0, t1, value)] by time."""
    # ponytail: first bucket skipped (everyone replays the start); no local-maximum detection
    top = sorted(hm[1:], key=lambda b: -b["value"])[:k]
    peaks = []
    for b in sorted(top, key=lambda b: b["start_time"]):
        if peaks and b["start_time"] <= peaks[-1][1] + 1e-6:
            peaks[-1] = (peaks[-1][0], b["end_time"], max(peaks[-1][2], b["value"]))
        else:
            peaks.append((b["start_time"], b["end_time"], b["value"]))
    return peaks


# closed taxonomy from ~/.hermes/docs/2026-10-03-trends-profile-inputs.md 1.3, so stats per class stay comparable
HOOK_TYPES = ["question", "curiosity_gap", "contrarian", "number_list", "pattern_interrupt", "in_medias_res",
              "confession_story", "pov_relatable", "proof_first", "contrast", "direct_callout", "stakes_warning",
              "reveal_countdown", "other"]


def hooks_block(hooks, max_lines=15):
    """Prompt block from hooks.json entries: a header + up to max_lines-1 patterns."""
    rows = [h for h in hooks if isinstance(h, dict) and h.get("hook_type") and h.get("template")][:max_lines - 1]
    if not rows: return ""
    return ("PROVEN HOOK PATTERNS (prefer clips whose opening fits one; set hook_type accordingly):\n"
            + "\n".join(f'- {h["hook_type"]}: "{h["template"]}"' + (f' e.g. "{h["example"]}"' if h.get("example") else "")
                         + (f' [{h["evidence"]}]' if h.get("evidence") else "") for h in rows) + "\n\n")


def peaks_block(peaks):
    if not peaks: return ""
    return ("MOST REPLAYED moments of this video (YouTube heatmap, replay=1.0 is the most replayed) - "
            "strongly prefer clips that contain one of them:\n"
            + "\n".join(f"[{a:.1f}-{b:.1f}] replay={v:.2f}" for a, b, v in peaks) + "\n\n")


def llm_codex(prompt):
    out = Path(os.environ.get("TMPDIR", "/tmp")) / f"codex-{os.getpid()}.txt"
    subprocess.run(["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only",
                    "-o", str(out), "-"], input=prompt, text=True, check=True, capture_output=True, timeout=900)
    txt = out.read_text(); out.unlink(); return txt


def llm_claude(prompt):
    claude = shutil.which("claude") or str(Path.home() / ".local/bin/claude")
    return subprocess.run([claude, "-p", "--output-format", "text"], input=prompt, text=True,
                          check=True, capture_output=True, timeout=900).stdout


HERMES_PY = Path.home() / ".hermes/hermes-agent/venv/bin/python"


def hermes_cmd(prompt):
    return [str(HERMES_PY), "-m", "hermes_cli.main", "-z", prompt,  # provider+model: the profile's config (gpt-5.4-mini: 400 on ChatGPT accounts)
            "-t", "safe", "--ignore-rules", "--cli"]


def llm_hermes(prompt):
    """Codex subscription via a Hermes profile. Only with an explicit profile home: the default profile is the
    owner's main Codex account and must never be used here."""
    home = os.environ.get("CLIP_HERMES_HOME")
    if not home: raise RuntimeError("CLIP_HERMES_HOME not set")
    # ponytail: prompt goes in argv (Linux caps one arg at 128 KB, ~2.5 h of transcript); stdin if that's hit
    return subprocess.run(hermes_cmd(prompt), env=os.environ | {"HERMES_HOME": home}, text=True, check=True,
                          capture_output=True, timeout=900, stdin=subprocess.DEVNULL).stdout


BACKENDS = {"hermes": llm_hermes, "codex": llm_codex, "claude": llm_claude}


def backend_order(first):
    """Backends to try: `first`, then the rest; hermes only when CLIP_HERMES_HOME is set, codex only if installed."""
    ok = {"hermes": bool(os.environ.get("CLIP_HERMES_HOME")), "codex": bool(shutil.which("codex")), "claude": True}
    return [b for b in [first] + [b for b in BACKENDS if b != first] if ok[b]]


def parse_json_list(txt):
    m = re.search(r"\[.*\]", txt, re.S)
    if not m: raise ValueError("no JSON array in LLM output: " + txt[:300])
    return json.loads(m.group(0))


FILLERS = {"and", "so", "um", "uh", "like", "but"}


def filler_start(ws):
    """True if the first spoken words (word dicts) are a filler: and/so/um/uh/like/but or "you know"."""
    t = first_tokens(ws)
    return bool(t) and (t[0] in FILLERS or t == ["you", "know"])


def first_tokens(ws, n=2): return [t for w in ws[:n] for t in norm_words(w["w"])][:n]


def skip_filler(words, i, within=1.5):
    """Index of the word a clip starting at words[i] should start at to avoid a filler opening:
    i itself if clean, else the first non-filler sentence start within `within` s, else the first word after
    the leading filler run (also within `within` s); None if neither exists."""
    if not filler_start(words[i:i + 2]): return i
    near = [j for j in range(i + 1, len(words)) if words[j]["s"] - words[i]["s"] <= within]
    for j in near:
        if re.search(r"[.!?]$", words[j - 1]["w"]) and not filler_start(words[j:j + 2]): return j
    j = i
    while j < len(words) and filler_start(words[j:j + 2]):
        j += 2 if first_tokens(words[j:j + 2]) == ["you", "know"] else 1
    return j if j < len(words) and words[j]["s"] - words[i]["s"] <= within else None


def hits_peak(c, peaks):
    try: return any(float(c["start"]) < b and a < float(c["end"]) for a, b, _ in peaks)
    except (KeyError, TypeError, ValueError): return False


def validate(cands, words, lo=MIN_LEN, hi=MAX_LEN, n=N_CLIPS, slack=3.0, peaks=()):
    """Snap LLM times to word boundaries, enforce length and no overlap. Returns <= n clips,
    candidates overlapping a heatmap peak first, otherwise in given order."""
    if not words: return []
    kept = []
    for c in sorted(cands, key=lambda c: not hits_peak(c, peaks)):  # stable
        try: s, e = float(c["start"]), float(c["end"])
        except (KeyError, TypeError, ValueError): continue
        if e <= s: continue
        # snap to the nearest word start / end (LLM sees segment times, which coincide with word times)
        i = min(range(len(words)), key=lambda k: abs(words[k]["s"] - s))
        e2 = min(words, key=lambda w: abs(w["e"] - e))["e"]
        if abs(words[i]["s"] - s) > 2: continue
        i = skip_filler(words, i)  # never open on "and"/"so"/"you know"...
        if i is None: continue
        s2 = words[i]["s"]
        if abs(e2 - e) > 2 or e2 <= s2: continue
        if e2 - s2 > hi:  # too long: trim to last word end within hi
            e2 = max(w["e"] for w in words if s2 < w["e"] <= s2 + hi)
        if e2 - s2 < lo - slack or e2 - s2 < 5: continue
        if e2 - s2 < lo:  # slightly short: extend by following words up to lo
            more = [w["e"] for w in words if e2 < w["e"] <= s2 + hi]
            e2 = next((x for x in more if x - s2 >= lo), more[-1] if more else e2)
            if e2 - s2 < lo: continue
        if any(s2 < k["end"] and k["start"] < e2 for k in kept): continue
        kept.append(c | {"start": round(s2, 2), "end": round(e2, 2), "llm_start": s, "llm_end": e,
                         "hook_type": c.get("hook_type") if c.get("hook_type") in HOOK_TYPES else "other"})
        if len(kept) == n: break
    return kept


def banner_text(c):
    """On-screen banner: the LLM `caption`, unless it just repeats the spoken hook; then the title. Never the hook."""
    cap, hook = norm_words(c.get("caption") or ""), set(norm_words(c.get("hook") or ""))
    if cap and sum(w in hook for w in cap) / len(cap) < 0.6: return c["caption"]
    return c.get("title") or ""


def highlights(a):
    tr = load(wdir(a.id) / "transcript.json")
    lines = "\n".join(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in tr["segments"])
    meta = wdir(a.id) / "meta.json"
    peaks = heatmap_peaks(load(meta).get("heatmap") or []) if meta.exists() else []
    hooks = load(HOOKS) if HOOKS.exists() else []
    prompt = PROMPT.format(n=N_CLIPS + 3, lo=MIN_LEN, hi=MAX_LEN, transcript=lines,  # ask extra, some fail validation
                           hook_types="|".join(HOOK_TYPES), extra=hooks_block(hooks) + peaks_block(peaks))
    for b in backend_order(a.backend or ("hermes" if os.environ.get("CLIP_HERMES_HOME") else "claude")):
        t0 = time.time()
        try:
            raw = BACKENDS[b](prompt)
            clips = validate(parse_json_list(raw), all_words(tr), peaks=peaks)
        except Exception as e:
            print(f"{b} failed: {e} {(getattr(e, 'stderr', '') or '')[-300:]}", file=sys.stderr); continue
        if clips:
            save(wdir(a.id) / "highlights.json", {"backend": b, "secs": round(time.time() - t0, 1), "raw": raw, "clips": clips})
            for c in clips: print(f"{c['start']:7.1f}-{c['end']:7.1f} ({c['end']-c['start']:.0f}s) {c['title']}")
            return
    sys.exit("no backend produced valid highlights")


# ---------------- edit ----------------
def crop_x(cx, W, H, out_ar=9 / 16):
    """Left edge of a full-height out_ar crop centred on normalised face x `cx`, clamped to frame."""
    cw = int(H * out_ar) // 2 * 2
    if cw >= W: return 0, W
    return int(min(max(cx * W - cw / 2, 0), W - cw)), cw


def ass_time(t):
    t = max(t, 0); cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def caption_events(words, start, end, max_words=3, gap=0.6, hold=1.2):
    """Word-level karaoke: chunks of <=max_words; one event per word, current word highlighted.
    A chunk's last word stays on screen until the next chunk starts if that pause is < hold s (no flicker in pauses).
    Returns [(t0, t1, text)] relative to clip start."""
    ws = [w for w in words if w["s"] >= start - 0.05 and w["e"] <= end + 0.05 and w["w"]]
    chunks, cur = [], []
    for w in ws:
        if cur and (len(cur) == max_words or w["s"] - cur[-1]["e"] > gap or re.search(r"[.!?,]$", cur[-1]["w"])):
            chunks.append(cur); cur = []
        cur.append(w)
    if cur: chunks.append(cur)
    ev = []
    for ci, ch in enumerate(chunks):
        nxt = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else None
        for i, w in enumerate(ch):
            t0 = w["s"]
            t1 = ch[i + 1]["s"] if i + 1 < len(ch) else (nxt if nxt is not None and nxt - w["e"] < hold else w["e"])
            txt = " ".join(("{\\c&H00E5FF&}" + x["w"].upper() + "{\\c&HFFFFFF&}") if j == i else x["w"].upper()
                           for j, x in enumerate(ch))
            ev.append((round(max(t0 - start, 0), 2), round(min(t1, end) - start, 2), txt))
    return ev


ASS_HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {OUT_W}
PlayResY: {OUT_H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,60,60,560,1
Style: Hook,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC0000000,-1,0,0,0,100,100,0,0,3,18,0,8,80,80,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(path, events, hook, seam=()):
    """seam: (t0, t1) spans with the stacked layout; captions there sit on the seam between the two halves."""
    on_seam = lambda t: any(a <= t < b for a, b in seam)
    tag = "{\\pos(%d,%d)}" % (OUT_W // 2, OUT_H // 2 + 50)  # bottom-centre anchor: text straddles the seam
    lines = [f"Dialogue: 0,{ass_time(t0)},{ass_time(t1)},Cap,,0,0,0,,{tag if on_seam(t0) else ''}{t}" for t0, t1, t in events]
    if hook: lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(2.5)},Hook,,0,0,0,,{hook}")
    Path(path).write_text(ASS_HEAD + "\n".join(lines) + "\n")


def face_detector():
    from mediapipe.tasks.python import vision, BaseOptions
    return vision.FaceDetector.create_from_options(vision.FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=str(FACE_MODEL)), min_detection_confidence=0.5))


def faces_in(det, frame_bgr, min_score=0.8):
    """Detected faces as (cx, cy, w, h) normalised, best first.
    BlazeFace short-range sees only big faces, so also scan overlapping square tiles (2/3 of the short side)."""
    # ponytail: ~9-11 detector calls per frame; a full-range/YuNet detector would need one
    import cv2, mediapipe as mp
    H, W = frame_bgr.shape[:2]
    t = min(H, W) * 2 // 3
    boxes = [(0, 0, W, H)] + [(x, y, t, t) for x in range(0, W - t + 1, t // 2) for y in range(0, H - t + 1, t // 2)]
    rgb, out = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB), []
    for x0, y0, w, h in boxes:
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb[y0:y0 + h, x0:x0 + w].copy())
        for d in det.detect(img).detections:
            if d.categories[0].score < min_score: continue
            b = d.bounding_box
            out.append((d.categories[0].score, ((x0 + b.origin_x + b.width / 2) / W, (y0 + b.origin_y + b.height / 2) / H, b.width / W, b.height / H)))
    return dedupe([f for _, f in sorted(out, key=lambda o: -o[0])])


def iou(a, b):
    """IoU of two (cx, cy, w, h) boxes."""
    ix = max(0, min(a[0] + a[2] / 2, b[0] + b[2] / 2) - max(a[0] - a[2] / 2, b[0] - b[2] / 2))
    iy = max(0, min(a[1] + a[3] / 2, b[1] + b[3] / 2) - max(a[1] - a[3] / 2, b[1] - b[3] / 2))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter or 1)


def dedupe(faces, thr=0.3):
    """Drop repeated detections of one face (overlapping tiles), keeping the first (best-scored)."""
    kept = []
    for f in faces:
        if all(iou(f, k) <= thr for k in kept): kept.append(f)
    return kept


def sample_faces(det, path, start, end, fps_sample=2.0):
    """[(t_rel, faces)] sampled at fps_sample (faces as from faces_in); reads frames sequentially (one in RAM at a time)."""
    import cv2
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step, i, res = max(int(fps / fps_sample), 1), 0, []
    while True:
        ok = cap.grab()
        if not ok: break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t > end: break
        if i % step == 0:
            ok, fr = cap.retrieve()
            f = faces_in(det, fr) if ok else []
            res.append((t - start, f))
        i += 1
    cap.release()
    return res


def scene_cuts(path, start, end):
    from scenedetect import detect, ContentDetector
    sc = detect(str(path), ContentDetector(threshold=27), start_time=start, end_time=end)
    return [s[0].get_seconds() - start for s in sc[1:]]


# ---- active speaker / stacked layout ----
# Ported from mutonby/openshorts active_speaker.py and split_layout.py, MIT License, Copyright (c) 2024 OpenShorts
# (https://github.com/mutonby/openshorts). Thresholds are theirs; code condensed to this pipeline's face tuples.
WIN, AUDIO_FLOOR, MIN_MARGIN, MIN_SHARE = 0.4, 0.18, 0.15, 0.2


def two_shot(frames, min_coexist=0.5, min_sep=0.2, min_w=0.045):
    """(left, right) median (cx, cy, w, h) if two separated faces share >= min_coexist of the sampled frames, else None.
    Coexistence tells a real two-shot from shot/reverse-shot cutting between two cameras."""
    pairs = []
    for faces in frames:
        big = [f for f in faces if f[2] >= min_w][:2]
        if len(big) == 2:
            l, r = sorted(big)
            if r[0] - l[0] >= min_sep: pairs.append((l, r))
    if not pairs or len(pairs) < min_coexist * len(frames): return None
    return tuple(tuple(statistics.median(p[k][i] for p in pairs) for i in range(4)) for k in (0, 1))


def mouth_activity(path, start, dur, pair, W, H, fps=25, sw=480):
    """Mouth movement per WIN-second window: [[a_left, a_right], ...]. Mean abs frame-to-frame change in each face's
    mouth region divided by that region's contrast (pixel std): raw differences scale with lighting and contrast, so a
    better-lit face would win every window. (openshorts instead rescales each speaker to their own 20-80th percentile
    per scene; on a short scene where one person talks throughout that turns the talker into noise - measured.)"""
    import numpy as np
    sh = round(H * sw / W / 2) * 2
    regions = []
    for cx, cy, w, h in pair:  # mouth sits low in the brow-to-chin box; wide enough to include the jaw
        my = cy + 0.22 * h
        x0, y0 = int(max(0, (cx - 0.36 * w) * sw)), int(max(0, (my - 0.22 * h) * sh))
        regions.append((x0, y0, int(min(sw, max(x0 + 1, (cx + 0.36 * w) * sw))), int(min(sh, max(y0 + 1, (my + 0.22 * h) * sh)))))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(path), "-an",
                          "-vf", f"fps={fps},scale={sw}:{sh}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    per, act, bucket, prev = round(fps * WIN), [], [], None
    while len(buf := p.stdout.read(sw * sh)) == sw * sh:
        fr = np.frombuffer(buf, np.uint8).reshape(sh, sw).astype(np.int16)
        if prev is not None:
            bucket.append([float(np.abs(fr[y0:y1, x0:x1] - prev[y0:y1, x0:x1]).mean() / (fr[y0:y1, x0:x1].std() + 1))
                           for x0, y0, x1, y1 in regions])
        prev = fr
        if len(bucket) >= per: act.append(np.mean(bucket, 0).tolist()); bucket = []
    p.wait()
    if bucket: act.append(np.mean(bucket, 0).tolist())
    return act


def audio_envelope(path, start, dur):
    """Per-WIN RMS of the audio normalised to its own peak; [] if no audio (then every window is eligible)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(path), "-vn",
                          "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32)
    per = int(8000 * WIN); n = len(x) // per
    if n < 1: return []
    rms = np.sqrt((x[:n * per].reshape(n, per) ** 2).mean(1))
    return (rms / rms.max()).tolist() if rms.max() > 0 else [0.0] * n


def attribute_windows(act, loud):
    """Speaker index per window, None where nobody talks (audio < AUDIO_FLOOR) or the mouths are too close to call."""
    out = []
    for i, (l, r) in enumerate(act):
        if loud and i < len(loud) and loud[i] < AUDIO_FLOOR or l + r <= 0 or abs(l - r) / (l + r) < MIN_MARGIN:
            out.append(None)
        else:
            out.append(0 if l > r else 1)
    return out


def is_conversation(verdicts, min_share=MIN_SHARE):
    """Both speakers hold >= min_share of the attributed windows."""
    c = [v for v in verdicts if v is not None]
    return bool(c) and min(c.count(0), c.count(1)) / len(c) >= min_share


def hold_speaker(verdicts, min_windows=3):
    """Smoothed verdicts: unclear windows keep the current speaker, a new one must win min_windows in a row
    (the cut is then backdated to where that run began: we render offline), the lead-in is backfilled with the
    first speaker. All None if nobody was ever attributed."""
    out, cur, pend, run, since = [], None, None, 0, 0
    for i, v in enumerate(verdicts):
        out.append(cur)
        if v is not None and v != cur:
            if v != pend: pend, run, since = v, 0, i
            run += 1
            if cur is None or run >= min_windows:
                cur, pend, run = v, None, 0
                out[since:] = [v] * (i + 1 - since)
        elif v == cur:
            pend, run = None, 0
    first = next((v for v in out if v is not None), None)
    return [first if v is None else v for v in out]


def talk_verdicts(path, start, dur, pair, W, H):
    return attribute_windows(mouth_activity(path, start, dur, pair, W, H), audio_envelope(path, start, dur))


def stack_geom(pair, W, H, tight=0.8):
    """(w, h, top_x, top_y, bot_x, bot_y): one crop size, left speaker on top, right below, each scaled to OUT_W x OUT_H/2.
    tight < 1 drops the neighbour's shoulder at the cost of slight upscaling (openshorts SPLIT_TIGHTNESS)."""
    ch = int(H * tight) // 2 * 2; cw = int(ch * OUT_W / (OUT_H // 2)) // 2 * 2
    if cw > W: cw = W // 2 * 2; ch = int(cw * (OUT_H // 2) / OUT_W) // 2 * 2
    xy = lambda f: (int(min(max(f[0] * W - cw / 2, 0), W - cw)), int(min(max(f[1] * H - ch * 0.42, 0), H - ch)))
    return (cw, ch) + xy(pair[0]) + xy(pair[1])


def crop_plan(samples, cuts, dur, W, H, verdicts=None, stack=False):
    """Per scene: one static crop on the median best face; but in a two-shot (see two_shot) with
    `verdicts(a, b, pair)` given, the crop follows the active speaker (switching on WIN-s windows), or with `stack`
    and both people talking, both are stacked. Returns [(t_from, x, stack_geom or None)], cw."""
    # ponytail: static crop per scene/speaker turn, no in-shot panning; add EMA tracking if speakers move a lot
    bounds = [0.0] + [c for c in cuts if 0 < c < dur] + [dur]
    plan, last, cw = [], 0.5, crop_x(0.5, W, H)[1]
    for a, b in zip(bounds, bounds[1:]):
        frames = [f for t, f in samples if a <= t < b]
        pair = two_shot(frames) if verdicts else None
        v = verdicts(a, b, pair) if pair else []
        held = hold_speaker(v)
        if stack and b - a >= 2.5 and is_conversation(v):  # shorter stacks read as a glitch (openshorts)
            plan.append((a, crop_x(last, W, H)[0], stack_geom(pair, W, H)))
        elif held and held[0] is not None:
            plan += [(a + i * WIN, crop_x(pair[k][0], W, H)[0], None) for i, k in enumerate(held)]
            last = pair[held[-1]][0]
        else:
            xs = [f[0][0] for f in frames if f]
            last = statistics.median(xs) if xs else last
            plan.append((a, crop_x(last, W, H)[0], None))
    return [p for i, p in enumerate(plan) if i == 0 or p[1:] != plan[i - 1][1:]], cw


def stack_spans(plan, dur):
    return [(t, (plan[i + 1][0] if i + 1 < len(plan) else dur)) for i, (t, _, g) in enumerate(plan) if g]


def x_expr(plan, k=1):
    """ffmpeg expression switching per plan entry on value plan[i][k]: if(lt(t,t1),x0,if(lt(t,t2),x1,x2))."""
    e = str(plan[-1][k])
    for i in range(len(plan) - 2, -1, -1):
        e = f"if(lt(t,{plan[i + 1][0]:.3f}),{plan[i][k]},{e})"
    return e


def encoder():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "nullsrc=s=256x256:d=0.1", "-c:v", "h264_nvenc",
                        "-f", "null", "-"], capture_output=True)
    return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "21"] if r.returncode == 0 else ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]


def probe(path):
    return json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                                     capture_output=True, text=True, check=True).stdout)


def edit(a):
    hl = load(wdir(a.id) / "highlights.json")["clips"]
    words = all_words(load(wdir(a.id) / "transcript.json"))
    path = src(a.id); out = odir(a.id); out.mkdir(parents=True, exist_ok=True)
    v = next(s for s in probe(path)["streams"] if s["codec_type"] == "video")
    W, H = int(v["width"]), int(v["height"])
    det, enc, plans = face_detector(), encoder(), []
    for n, c in enumerate(hl, 1):
        s, e = c["start"], c["end"]; dur = e - s
        t0 = time.time()
        samples = sample_faces(det, path, s, e)
        cuts = scene_cuts(path, s, e)
        verd = (lambda a_, b_, pair: talk_verdicts(path, s + a_, b_ - a_, pair, W, H)) if a.speakers else None
        plan, cw = crop_plan(samples, cuts, dur, W, H, verd, a.stack)
        spans, ass = stack_spans(plan, dur), out / f"clip_{n}.ass"
        write_ass(ass, caption_events(words, s, e), banner_text(c).upper()[:60] if a.hook_overlay else "", spans)
        base = f"crop={cw}:{H}:'{x_expr(plan)}':0,scale={OUT_W}:{OUT_H}:flags=lanczos"
        if spans:  # stacked two-shot overlaid on the single crop where both speakers talk
            st = [p for p in plan if p[2]]; gw, gh = st[0][2][:2]
            half = lambda j: f"crop={gw}:{gh}:'{x_expr([(t, g[j]) for t, _, g in st])}':'{x_expr([(t, g[j + 1]) for t, _, g in st])}',scale={OUT_W}:{OUT_H // 2}:flags=lanczos"
            en = "+".join(f"between(t,{t0:.3f},{t1:.3f})" for t0, t1 in spans)
            vfa = ["-filter_complex", f"[0:v]split=3[c][t][b];[c]{base}[base];[t]{half(2)}[top];[b]{half(4)}[bot];"
                   f"[top][bot]vstack[st];[base][st]overlay=0:0:enable='{en}',fps=30,ass={ass}[v]", "-map", "[v]", "-map", "0:a"]
        else:
            vfa = ["-vf", f"{base},fps=30,ass={ass}"]
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s:.3f}", "-i", str(path), "-t", f"{dur:.3f}",
               *vfa, *enc, "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out / f"clip_{n}.mp4")]
        subprocess.run(cmd, check=True)
        plans.append({"clip": n, "start": s, "end": e, "title": c.get("title"), "scene_cuts": cuts, "crop_plan": plan,
                      "stacked": spans, "face_samples": len(samples), "face_hits": sum(bool(f) for _, f in samples), "secs": round(time.time() - t0, 1)})
        print(f"clip_{n}.mp4 {dur:.1f}s scenes={len(cuts) + 1} crops={len(plan)} stacked={len(spans)} faces={plans[-1]['face_hits']}/{len(samples)} {time.time()-t0:.0f}s")
    det.close()
    save(out / "edit.json", plans)


# ---------------- qa ----------------
def mean_volume(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def qa(a):
    import cv2
    out = odir(a.id); words = all_words(load(wdir(a.id) / "transcript.json"))
    hl = load(wdir(a.id) / "highlights.json")["clips"]
    det, report = face_detector(), []
    for n, c in enumerate(hl, 1):
        p = out / f"clip_{n}.mp4"
        if not p.exists(): report.append({"clip": n, "ok": False, "error": "missing"}); continue
        info = probe(p); st = info["streams"]
        v = next((s for s in st if s["codec_type"] == "video"), {})
        dur = float(info["format"]["duration"])
        vol = mean_volume(p) if any(s["codec_type"] == "audio" for s in st) else None
        n_caps = sum(l.startswith("Dialogue") and ",Cap," in l for l in (out / f"clip_{n}.ass").read_text().splitlines())
        # face fully inside the vertical frame, sampled 2x/s on the rendered clip
        cap, hits, tot, t = cv2.VideoCapture(str(p)), 0, 0, 0.0
        while t < dur:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, fr = cap.read()
            if not ok: break
            f = faces_in(det, fr); tot += 1
            hits += bool(f and f[0][0] - f[0][2] / 2 >= 0 and f[0][0] + f[0][2] / 2 <= 1)
            t += 0.5
        for k, frac in ((1, 0.25), (2, 0.75)):
            cap.set(cv2.CAP_PROP_POS_MSEC, dur * frac * 1000); ok, fr = cap.read()
            if ok: cv2.imwrite(str(out / f"clip_{n}_f{k}.png"), fr)
        cap.release()
        first = [w for w in words if c["start"] - 0.05 <= w["s"] < c["start"] + 2]
        first2 = [w["w"] for w in first]
        r = {"clip": n, "file": str(p), "title": c.get("title"), "hook_type": c.get("hook_type"), "duration": round(dur, 2),
             "resolution": f"{v.get('width')}x{v.get('height')}", "audio_mean_db": vol, "caption_events": n_caps,
             "face_in_frame_ratio": round(hits / tot, 2) if tot else 0, "first_2s_words": " ".join(first2)}
        r["checks"] = {"duration": MIN_LEN - 0.5 <= dur <= MAX_LEN + 0.5, "resolution": r["resolution"] == f"{OUT_W}x{OUT_H}",
                       "audio": vol is not None and vol > -40, "captions": n_caps > 0,
                       "face_in_frame": r["face_in_frame_ratio"] >= 0.6, "hook_speech_2s": len(first2) >= 3,
                       "no_filler_start": not filler_start(first)}
        r["ok"] = all(r["checks"].values())
        report.append(r)
        print(f"clip_{n}: {'PASS' if r['ok'] else 'FAIL'} {r['checks']}")
    det.close()
    save(out / "qa.json", report)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("fetch"); p.add_argument("url"); p.add_argument("--id", required=True)
    p.add_argument("--cookies", help="Netscape cookies.txt of a SEPARATE account (YouTube bot check)")
    # the VPN exit IP is bot-flagged: without a logged-in session every client gets "confirm you're not a bot"
    p.add_argument("--browser", default="chrome", help="browser to read YouTube cookies from ('' to disable)")
    p.set_defaults(f=fetch)
    p = sp.add_parser("transcribe"); p.add_argument("id"); p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--model"); p.set_defaults(f=transcribe)
    p = sp.add_parser("highlights"); p.add_argument("id"); p.add_argument("--backend", choices=list(BACKENDS),
                   help="default: hermes if CLIP_HERMES_HOME is set, else claude")
    p.set_defaults(f=highlights)
    p = sp.add_parser("edit"); p.add_argument("id"); p.add_argument("--no-hook-overlay", dest="hook_overlay", action="store_false")
    p.add_argument("--no-speakers", dest="speakers", action="store_false", help="no active-speaker crop in two-shots")
    p.add_argument("--stack", action="store_true", help="stack both speakers when both talk in a two-shot")
    p.set_defaults(f=edit)
    p = sp.add_parser("qa"); p.add_argument("id"); p.set_defaults(f=qa)
    a = ap.parse_args(argv); a.f(a)


if __name__ == "__main__":
    main()
