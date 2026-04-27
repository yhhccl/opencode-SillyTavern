#!/usr/bin/env python3
"""handler.py — 聊天记录与状态管理 (adapted from AIRP_ClaudeCode).

用法:
    python handler.py append user "消息"
    python handler.py append ai "回复" [--summary "摘要"] [--options "选项"]
    python handler.py done               — 调用 /api/done 清除 pending
    python handler.py update-state <json> — 更新 state.js
    python handler.py rebuild            — 从 chat_log.json 重建 content.js

由 server.py 或 OpenCode 调用。
"""

import json, re, sys, urllib.parse, urllib.request
from datetime import datetime
from uuid import uuid4
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAT_LOG = ROOT / "chat_log.json"
CONTENT_JS = ROOT / "content.js"
STATE_JS = ROOT / "state.js"
BRIDGE = "http://localhost:8765"

IMG_RE = re.compile(r'\[img:\s*(.+?)\]')


def load_log():
    try:
        raw = json.loads(CHAT_LOG.read_text(encoding="utf-8"))
    except Exception:
        return []
    return _normalize_entries(raw)


def save_log(entries):
    normalized = _normalize_entries(entries)
    CHAT_LOG.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def append_message(role: str, content: str) -> dict:
    """Append one message with stable metadata."""
    log = load_log()
    entry = _make_entry(role, content)
    log.append(entry)
    save_log(log)
    return entry


def build_content_js(chat_log_path=None, output_path=None):
    """重建 content.js — 微信风格: 头像 + 气泡 + 生图按钮 + 已生成图片。"""
    log_path = chat_log_path or CHAT_LOG
    out_path = output_path or CONTENT_JS

    try:
        log = _normalize_entries(json.loads(log_path.read_text(encoding="utf-8")))
    except Exception:
        log = []

    parts = []
    all_gen_prompts = []
    all_generated = {}

    # 读取已有的生成图片映射
    try:
        existing = json.loads((ROOT / "img_generated.json").read_text(encoding="utf-8"))
    except Exception:
        existing = {}

    for i, entry in enumerate(log):
        role = entry.get("role", "")
        content = entry.get("content", "")
        timestamp = _format_timestamp(entry.get("timestamp", ""))

        if role == "user":
            # 用户消息: 右对齐, 绿色气泡 + 头像
            safe_content = _esc(content)
            parts.append(
                f'<div class="msg-row self">'
                f'<div class="msg-wrap self"><div class="msg self">{safe_content}</div>'
                f'<div class="msg-time self">{timestamp}</div></div>'
                f'<div class="avatar self">我</div>'
                f'</div>'
            )
        else:
            # AI 消息: 左对齐, 白色气泡 + 头像 + 生图按钮
            safe_content = _esc(content)
            # 提取 [img:...] 并移除原标签
            gen_btns = []
            current_generated = {}
            seg = [0]

            def replace_img(m):
                idx = seg[0]; seg[0] += 1
                tags = m.group(1).strip()
                key = f"{i}_{idx}"
                all_gen_prompts.append({"key": key, "tags": tags, "turn": i})
                # 检查是否已生成
                img_url = existing.get(key, "")
                if img_url:
                    all_generated[key] = img_url
                    current_generated[key] = img_url
                    return ""  # 移除标签，图片将在气泡下方显示
                else:
                    gen_btns.append(key)
                    return ""  # 移除标签，替换为按钮

            display = IMG_RE.sub(replace_img, safe_content)

            # 构建气泡
            bubble = display
            for key in gen_btns:
                prompt = next((p for p in all_gen_prompts if p["key"] == key), None)
                tags_esc = _esc_attr(prompt["tags"]) if prompt else ""
                bubble += (
                    f'<div class="gen-btn" data-key="{key}" data-tags="{tags_esc}" '
                    f'onclick="genImgPrompt(this)">🎨 生成插图</div>'
                    f'<div class="gen-img-wrap" id="img-{key}"></div>'
                )
            # 已有图片直接渲染
            for key, url in current_generated.items():
                bubble += (
                    f'<div class="gen-img-wrap" id="img-{key}">'
                    f'<img src="{_image_src(url)}" class="gen-img" loading="lazy">'
                    f'</div>'
                )

            parts.append(
                f'<div class="msg-row other">'
                f'<div class="avatar other">A</div>'
                f'<div class="msg-wrap other"><div class="msg other">{bubble}</div>'
                f'<div class="msg-time other">{timestamp}</div></div>'
                f'</div>'
            )

    html = "".join(parts)
    options = _extract_options(log[-1]["content"]) if log and log[-1].get("role") == "assistant" else []

    js = (
        f"var CONTENT_HTML = {json.dumps(html, ensure_ascii=False)};\n"
        f"var TURN_OPTIONS = {json.dumps(options, ensure_ascii=False)};\n"
        f"var IMG_GENERATED = {json.dumps(all_generated, ensure_ascii=False)};\n"
    )
    out_path.write_text(js, encoding="utf-8")


def _extract_options(text):
    """Extract TURN_OPTIONS-style lines from AI content."""
    opts = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith(">") and len(line) > 2:
            opts.append(line[1:].strip())
    if not opts:
        # Try markdown list
        for m in re.finditer(r'^[\-\*]\s+(.+)$', text, re.MULTILINE):
            opts.append(m.group(1).strip())
    return opts[:4]  # max 4


def _make_entry(role: str, content: str, entry_id: str | None = None, timestamp: str | None = None) -> dict:
    return {
        "id": entry_id or uuid4().hex,
        "role": role,
        "content": content,
        "timestamp": timestamp or datetime.now().isoformat(timespec="seconds"),
    }


def _normalize_entries(entries):
    normalized = []
    changed = False
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role", "")
        if role == "ai":
            role = "assistant"
            changed = True
        content = entry.get("content", "")
        if entry.get("id") and entry.get("timestamp") and role == entry.get("role", ""):
            normalized.append(entry)
            continue
        normalized.append(
            _make_entry(
                role=role,
                content=content,
                entry_id=entry.get("id"),
                timestamp=entry.get("timestamp"),
            )
        )
        changed = True
    if changed and CHAT_LOG.exists():
        CHAT_LOG.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def _format_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%H:%M")
    except ValueError:
        return value


def _image_src(path: str) -> str:
    return "/api/image?path=" + urllib.parse.quote(path, safe="")


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("*", "<em>").replace("</em><em>", "").replace("<em>", "<em>", 1) if False else _esc2(s)


def _esc2(s):
    """Escape HTML but convert *text* to <em>text</em>."""
    # Simple approach: escape first, then restore em tags
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    return s


_esc = _esc2


def _esc_attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def bridge_done():
    try:
        urllib.request.urlopen(BRIDGE + "/api/done", data=b"", timeout=3)
    except Exception:
        pass


# ═══ CLI ═══

def main():
    if len(sys.argv) < 2:
        print("handler.py <cmd> [...]")
        return

    cmd = sys.argv[1]

    if cmd == "append":
        if len(sys.argv) < 4:
            print("用法: handler.py append <user|ai> <text>")
            return
        role = "assistant" if sys.argv[2] == "ai" else sys.argv[2]
        text = sys.argv[3]
        append_message(role, text)
        build_content_js()
        print(f"[handler] append {role} ok ({len(load_log())} turns)")

    elif cmd == "done":
        bridge_done()
        pending = ROOT / ".pending"
        pending.unlink(missing_ok=True)
        print("[handler] done: pending cleared")

    elif cmd == "update-state":
        if len(sys.argv) < 3:
            print("用法: handler.py update-state '<json>'")
            return
        try:
            state = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print("[handler] invalid json")
            return
        STATE_JS.write_text(f"var STATE = {json.dumps(state, ensure_ascii=False)};", encoding="utf-8")
        print("[handler] state updated")

    elif cmd == "rebuild":
        build_content_js()
        print(f"[handler] content.js rebuilt ({len(load_log())} turns)")

    else:
        print(f"[handler] unknown: {cmd}")


if __name__ == "__main__":
    main()
