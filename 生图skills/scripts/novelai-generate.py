#!/usr/bin/env python3
"""novelai-generate.py — 调用 NovelAI API 生成图片。
独立运行，从同级目录或上级目录的 .env 加载 API Key。

用法:
    python novelai-generate.py -p "提示词"
    python novelai-generate.py --queue image-queue.txt
    python novelai-generate.py --extract story.txt
    python novelai-generate.py --list-models
"""

import os, sys, json, time, base64, io, re, zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_URL = "https://image.novelai.net/ai/generate-image"

DEFAULT_NEGATIVE = (
    "blurry, lowres, upscaled, artistic error, film grain, scan artifacts, "
    "bad anatomy, bad hands, worst quality, bad quality, jpeg artifacts, "
    "very displeasing, chromatic aberration, halftone, multiple views, logo, "
    "too many watermarks, mismatched pupils, glowing eyes, negative space, "
    "blank page, low quality, sketch, censor"
)

MODEL = "nai-diffusion-4-5-curated"

V4_MODELS = {
    "nai-diffusion-4-5-curated", "nai-diffusion-4-5-full",
    "nai-diffusion-4-curated-preview", "nai-diffusion-4-full",
}
V3_MODELS = {
    "nai-diffusion-3", "nai-diffusion-furry-3",
}

AVAILABLE_MODELS = {
    "v4.5-curated": "nai-diffusion-4-5-curated",
    "v4.5-full":    "nai-diffusion-4-5-full",
    "v4-curated":   "nai-diffusion-4-curated-preview",
    "v4-full":      "nai-diffusion-4-full",
    "v3":           "nai-diffusion-3",
    "furry":        "nai-diffusion-furry-3",
}


def is_v4(m): return m in V4_MODELS


# ============ API Key ============

def _env_paths():
    """查找 .env 的候选路径：脚本目录 → 脚本父目录 → 当前目录"""
    sd = Path(__file__).resolve().parent
    yield sd / ".env"
    yield sd.parent / ".env"
    yield Path.cwd() / ".env"


def load_api_key() -> str:
    key = os.environ.get("NOVELAI_API_KEY", "")
    if key: return key
    for fp in _env_paths():
        if fp.exists():
            for line in fp.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("NOVELAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        os.environ["NOVELAI_API_KEY"] = key
                        return key
    return ""


# ============ Params ============

def build_v4_params(prompt, neg, params, char_prompts=None):
    w, h = params.get("width", 832), params.get("height", 1216)
    return {
        "params_version": 3,
        "width": w, "height": h,
        "scale": params.get("scale", 3),
        "sampler": params.get("sampler", "k_euler_ancestral"),
        "steps": params.get("steps", 28),
        "n_samples": 1, "ucPreset": 2, "qualityToggle": True,
        "autoSmea": params.get("sm", False),
        "dynamic_thresholding": False, "controlnet_strength": 1,
        "legacy": False, "add_original_image": True,
        "cfg_rescale": params.get("cfg_rescale", 0),
        "noise_schedule": "karras",
        "legacy_v3_extend": False, "skip_cfg_above_sigma": None,
        "use_coords": True,
        "normalize_reference_strength_multiple": True,
        "inpaintImg2ImgStrength": 1,
        "v4_prompt": {
            "caption": {"base_caption": prompt, "char_captions": char_prompts or []},
            "use_coords": True, "use_order": True,
        },
        "v4_negative_prompt": {
            "caption": {"base_caption": neg, "char_captions": []},
            "legacy_uc": False,
        },
        "legacy_uc": False, "seed": params.get("seed", 0),
        "characterPrompts": char_prompts or [],
        "negative_prompt": neg,
        "deliberate_euler_ancestral_bug": False,
        "prefer_brownian": True, "image_format": "png",
    }


def build_v3_params(prompt, neg, params):
    return {
        "width": params.get("width", 832), "height": params.get("height", 1216),
        "scale": params.get("scale", 5),
        "sampler": params.get("sampler", "k_euler_ancestral"),
        "steps": params.get("steps", 28), "n_samples": 1,
        "ucPreset": params.get("ucPreset", 0), "qualityToggle": True,
        "sm": params.get("sm", False), "sm_dyn": False,
        "dynamic_thresholding": False, "controlnet_strength": 1,
        "legacy": False, "add_original_image": False,
        "cfg_rescale": params.get("cfg_rescale", 0),
        "noise_schedule": "native", "seed": params.get("seed", 0),
        "negative_prompt": neg,
    }


# ============ Generate ============

def generate_image(prompt, negative=DEFAULT_NEGATIVE, model=MODEL,
                   output_dir="generated", char_prompts=None, **overrides):
    key = load_api_key()
    if not key:
        print("[NAI] 未设置 NOVELAI_API_KEY", file=sys.stderr)
        print("  在 .env 中写入: NOVELAI_API_KEY=你的密钥", file=sys.stderr)
        return None

    up = {**overrides}
    params = build_v4_params(prompt, negative, up, char_prompts) if is_v4(model) \
        else build_v3_params(prompt, negative, up)

    body = {"input": prompt, "model": model, "parameters": params}
    ptag = "V4" if is_v4(model) else "V3"
    print(f"[NAI] [{ptag}] {model} | {params['width']}x{params['height']}")

    data = json.dumps(body).encode("utf-8")
    req = Request(API_URL, data=data, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Origin": "https://novelai.net",
        "Referer": "https://novelai.net/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
        ),
    }, method="POST")

    try:
        resp = urlopen(req, timeout=180)
    except HTTPError as e:
        print(f"[NAI] HTTP {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[NAI] 错误: {e}", file=sys.stderr)
        return None

    raw = resp.read()
    img = None
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
        for n in zf.namelist():
            if n.endswith((".png", ".jpg", ".jpeg", ".webp")):
                img = zf.read(n); break
    except:
        for line in raw.decode(errors="replace").splitlines():
            if line.startswith("data:"):
                try:
                    b = base64.b64decode(line[5:].strip())
                    if len(b) > 100: img = b; break
                except: pass
    if not img and len(raw) > 100:
        img = raw

    if not img:
        print("[NAI] 未提取到图片", file=sys.stderr)
        return None

    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r'[\\/*?:"<>|\s]', '_', prompt[:40])[:35]
    fp = Path(output_dir) / f"nai_{ts}_{safe}.png"
    fp.write_bytes(img)
    print(f"[NAI] 保存: {fp.name} ({len(img)} bytes)")
    return fp


def extract_prompts(text):
    p = re.compile(r'\[img:\s*(.+?)\]')
    return [m.group(1).strip() for l in text.splitlines() for m in [p.search(l)] if m]


# ============ CLI ============

def main():
    import argparse
    ap = argparse.ArgumentParser(description="NovelAI Image Generator")
    ap.add_argument("input", nargs="?", default=None)
    ap.add_argument("-p", "--prompt")
    ap.add_argument("-f", "--file")
    ap.add_argument("-e", "--extract")
    ap.add_argument("-q", "--queue")
    ap.add_argument("-n", "--negative", default=DEFAULT_NEGATIVE)
    ap.add_argument("-m", "--model", default=MODEL)
    ap.add_argument("-o", "--output-dir", default="generated")
    ap.add_argument("-s", "--size", default="832x1216")
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--scale", type=float, default=5)
    ap.add_argument("--sampler", default="k_euler_ancestral")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-uc", action="store_true")
    ap.add_argument("--furry", action="store_true")
    ap.add_argument("--bg", "--background", dest="background", action="store_true")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--char", dest="char_prompt", action="append", default=None)

    args = ap.parse_args()

    if args.list_models:
        for name, mid in AVAILABLE_MODELS.items():
            v = "V4" if mid in V4_MODELS else "V3"
            print(f"  {name:16s} [{v}] {mid}")
        print(f"\n默认: {MODEL}")
        return

    model = args.model
    if args.furry:
        model = AVAILABLE_MODELS["furry"]

    w, h = ((int(x) for x in args.size.split("x")) if "x" in args.size else (832, 1216))

    prompts = []
    if args.prompt:         prompts = [args.prompt]
    elif args.extract:
        fp = Path(args.extract)
        prompts = extract_prompts(fp.read_text(encoding="utf-8")) if fp.exists() else []
        print(f"提取 {len(prompts)} 条")
    elif args.queue:
        fp = Path(args.queue)
        prompts = [l.strip() for l in fp.read_text(encoding="utf-8").splitlines() if l.strip()] if fp.exists() else []
    elif args.file:
        fp = Path(args.file)
        prompts = [l.strip() for l in fp.read_text(encoding="utf-8").splitlines() if l.strip()] if fp.exists() else []
    elif args.input == "-" or args.input is None:
        prompts = [sys.stdin.read().strip()]
    else:
        prompts = [args.input]

    if not prompts:
        print("错误: 无提示词", file=sys.stderr); sys.exit(1)

    prefix = "fur dataset, " if args.furry else ("background dataset, " if args.background else "")
    neg = "" if args.no_uc else args.negative
    cps = args.char_prompt if is_v4(model) else None

    results = []
    for i, p in enumerate(prompts, 1):
        if not p: continue
        if len(prompts) > 1: print(f"\n--- [{i}/{len(prompts)}] ---")
        r = generate_image(prefix + p, neg, model, args.output_dir, cps,
                           width=w, height=h, steps=args.steps,
                           scale=args.scale, sampler=args.sampler, seed=args.seed)
        results.append((p, str(r.resolve()) if r else "FAILED"))
        if len(prompts) > 1: time.sleep(0.5)

    ok = sum(1 for _, r in results if r != "FAILED")
    print(f"\n完成: {ok}/{len(results)}")
    for prompt, path in results:
        print(f"  [{'OK' if path != 'FAILED' else 'FAIL'}] {prompt[:60]}...")


if __name__ == "__main__":
    main()
