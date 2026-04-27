#!/usr/bin/env python3
"""extract-img.py — 从 RP 输出中提取 [img: ...] 提示词。

用法:
    python extract-img.py story.txt
    python extract-img.py story.txt --output queue.txt
    python extract-img.py story.txt -g                # 提取后直接生成
    python extract-img.py story.txt -g --latest-only  # 只生成最新一张
    echo "..." | python extract-img.py -
"""

import re, sys, os, subprocess
from pathlib import Path

IMG_PATTERN = re.compile(r'\[img:\s*(.+?)\]')


def extract_prompts(text):
    return [(i, m.group(1).strip())
            for i, line in enumerate(text.splitlines(), 1)
            for m in [IMG_PATTERN.search(line)] if m]


def main():
    import argparse
    p = argparse.ArgumentParser(description="提取 [img:...] 并可选生成")
    p.add_argument("input")
    p.add_argument("-o", "--output", default="image-queue.txt")
    p.add_argument("-l", "--latest", action="store_true")
    p.add_argument("-n", "--line-numbers", action="store_true")
    p.add_argument("-c", "--count", action="store_true")
    p.add_argument("-g", "--generate", action="store_true")
    p.add_argument("-s", "--size", default="832x1216")
    p.add_argument("-m", "--model", default="nai-diffusion-4-5-curated")
    p.add_argument("--steps", type=int, default=28)
    p.add_argument("--scale", type=float, default=5)
    p.add_argument("--latest-only", action="store_true")

    args = p.parse_args()

    text = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    prompts = extract_prompts(text)

    if args.count:
        print(f"{len(prompts)} 条"); return
    if not prompts:
        print("无 [img:...]", file=sys.stderr); sys.exit(0)

    if args.latest_only and args.generate:
        prompts = [prompts[-1]]
    elif args.latest:
        prompts = [prompts[-1]]

    out_path = Path(args.output)
    lines = [f"[行{ln}] {t}" if args.line_numbers else t for ln, t in prompts]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"提取 {len(prompts)} 条 → {out_path.resolve()}")

    if not args.generate:
        for line in lines: print(f"  {line}")
        return

    sd = Path(__file__).resolve().parent
    gs = sd / "novelai-generate.py"
    if not gs.exists():
        print(f"未找到 novelai-generate.py", file=sys.stderr); sys.exit(1)

    print("生成中...")
    r = subprocess.run([
        sys.executable, str(gs), "-q", str(out_path.resolve()),
        "-s", args.size, "-m", args.model, "-o", str(sd.parent / "generated"),
        "--steps", str(args.steps), "--scale", str(args.scale),
    ], cwd=str(sd.parent))
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
