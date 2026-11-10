"""Ask a local vision-language model (Qwen3-VL, 4-bit on the GPU) a question about video frames.
  .venv/bin/python scripts/vlm_ask.py "question" clip.mp4@12.5 clip.mp4@14 ...   -> one answer per frame
Frames are read with OpenCV; HDR sources are fine for yes/no questions."""
import sys, cv2, torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

MODEL = "Qwen/Qwen3-VL-4B-Instruct"


def frame(spec, max_side=1280):
    path, t = spec.rsplit("@", 1)
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
    ok, f = cap.read()
    if not ok:
        raise SystemExit(f"no frame: {spec}")
    h, w = f.shape[:2]
    s = max_side / max(h, w)
    f = cv2.resize(f, (int(w * s), int(h * s))) if s < 1 else f
    return Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))


def load():
    q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")
    model = AutoModelForImageTextToText.from_pretrained(MODEL, quantization_config=q, device_map="cuda")
    return model, AutoProcessor.from_pretrained(MODEL)


def ask(model, proc, img, question, max_new_tokens=64):
    msgs = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": question}]}]
    inp = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_dict=True,
                                   return_tensors="pt").to(model.device)
    out = model.generate(**inp, max_new_tokens=max_new_tokens, do_sample=False)
    return proc.batch_decode(out[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()


if __name__ == "__main__":
    question, specs = sys.argv[1], sys.argv[2:]
    model, proc = load()
    for s in specs:
        print(f"{s}\t{ask(model, proc, frame(s), question)}", flush=True)
