#!/usr/bin/env python3
"""server.py — RP Bridge Server for OpenCode (TUI injection mode).

HTTP 服务器 (端口 8765, ThreadingHTTPServer):
  POST /api/submit         — 写 web-input.txt + .pending, 立即返回
  GET  /api/pending        — 检查 .pending
  GET  /api/state          — 返回 state.js
  GET  /api/content        — 返回 content.js
  GET  /api/settings       — 返回 settings.json
  POST /api/settings       — 更新 settings.json
  POST /api/reroll         — 删除最后一轮, 恢复 pending
  POST /api/delete-turns   — 从指定轮次删除
  POST /api/done           — 清除 .pending
  POST /api/image-gen      — 调用 NAI 生成图片
  GET  /api/image?path=... — 提供生成的图片文件
  静态文件                  — 提供 index.html 等前端资源

Auto-polling (后台线程):
  检测 .pending 出现 → 读 web-input.txt → 调用 opencode_client.send_message()
  → HTTP POST /tui/clear-prompt + /tui/append-prompt + /tui/submit-prompt
  → 消息注入 opencode TUI 输入框 → AI 按 AGENTS.md 处理
  → AI Write web-response.txt → poller 返回 → handler 处理 → 重建 content.js
  → 浏览器自动刷新

启动前提: opencode --port 4096  (TUI 必须以固定端口运行)
启动: python web-frontend/server.py
停止: Ctrl+C 或 OpenCode 中 退出RP
"""

import json, os, sys, time, threading, subprocess, re, queue
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
from uuid import uuid4
from card_store import (
    ensure_card_runtime,
    get_card_payload,
    get_current_card_name,
    get_worldbook_payload,
    list_cards,
    list_worldbooks,
    preview_worldbook_activation,
    save_card_fields,
    save_worldbook_entries,
    set_current_card_name,
)
from airp_context import (
    build_turn_context,
    ensure_context_file,
    finalize_turn_context,
    get_context_payload,
    rebuild_context_snapshot,
)

PORT = 8765
ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PID_FILE = ROOT / "server.pid"
INPUT_FILE = ROOT / "web-input.txt"
RESPONSE_FILE = ROOT / "web-response.txt"
NEEDS_REPLY_FILE = ROOT / "web-needs-reply"
PENDING_FILE = ROOT / ".pending"
CHAT_LOG = ROOT / "chat_log.json"
CONTENT_JS = ROOT / "content.js"
STATE_JS = ROOT / "state.js"
SETTINGS_FILE = ROOT / "settings.json"
IMG_GENERATED_FILE = ROOT / "img_generated.json"
IMAGE_JOBS_FILE = ROOT / "image_jobs.json"

IMAGE_QUEUE = queue.Queue()
IMAGE_JOBS_LOCK = threading.Lock()

DEFAULT_SETTINGS = {
    "style": "default",
    "nsfw": "off",
    "person": "first",
    "wordCount": 600,
    "antiHijack": True,
    "imageGenEnabled": True,
}

os.chdir(str(ROOT))


def init_files():
    for f in [PENDING_FILE, NEEDS_REPLY_FILE, RESPONSE_FILE]:
        f.unlink(missing_ok=True)
    current_card = get_current_card_name()
    if current_card:
        ensure_card_runtime(current_card)
    if not CHAT_LOG.exists():
        CHAT_LOG.write_text("[]", encoding="utf-8")
    if not CONTENT_JS.exists():
        from handler import _atomic_write
        _atomic_write(CONTENT_JS, "var TURN_OPTIONS = []; var CONTENT_HTML = '';")
    if not STATE_JS.exists():
        STATE_JS.write_text(
            f'var STATE = {{"card":{json.dumps(current_card, ensure_ascii=False)},"time":"","location":"","characters":{{}},'
            '"nsfw":"off","style":"default","generatedCount":0};',
            encoding="utf-8"
        )
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
    if not IMG_GENERATED_FILE.exists():
        IMG_GENERATED_FILE.write_text("{}", encoding="utf-8")
    if not IMAGE_JOBS_FILE.exists():
        IMAGE_JOBS_FILE.write_text("{}", encoding="utf-8")
    _reset_stale_image_jobs()
    ensure_context_file()
    rebuild_context_snapshot()


# ═══ Auto-Polling Thread ═══

def response_poller():
    """后台线程: 检测 pending → 注入 opencode TUI → 等待 AI 回复 → 处理。"""
    from handler import append_message, build_content_js, load_log
    from opencode_client import send_message

    print("[poller] TUI 注入模式已启动 (opencode --port 4096)")
    while True:
        try:
            if PENDING_FILE.exists():
                user_input = INPUT_FILE.read_text(encoding="utf-8").strip()
                PENDING_FILE.unlink()
                RESPONSE_FILE.unlink(missing_ok=True)
                NEEDS_REPLY_FILE.unlink(missing_ok=True)

                if not user_input:
                    time.sleep(1.5)
                    continue

                print(f"[poller] 收到: {user_input[:60]}... → 注入 TUI")
                try:
                    ai_reply = send_message(user_input, cwd=PROJECT_ROOT)
                except Exception as e:
                    print(f"[poller] TUI 注入失败: {e}")
                    PENDING_FILE.touch()
                    time.sleep(3)
                    continue

                if not ai_reply:
                    print("[poller] 空回复, 跳过")
                    continue

                append_message("user", user_input)
                append_message("assistant", ai_reply)
                finalize_turn_context(ai_reply)
                log = load_log()
                build_content_js(CHAT_LOG, CONTENT_JS)

                try:
                    import json as _json
                    current = _json.loads(STATE_JS.read_text(encoding="utf-8").replace("var STATE = ", "").rstrip(";"))
                    current["generatedCount"] = len(log)
                    STATE_JS.write_text(f"var STATE = {_json.dumps(current, ensure_ascii=False)};", encoding="utf-8")
                except Exception:
                    pass

                print(f"[poller] 回复已处理 ({len(ai_reply)} 字, {len(log)} 轮)")

            time.sleep(1.5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[poller] error: {e}")
            time.sleep(3)


def image_worker():
    print("[image-worker] 异步生图队列已启动")
    while True:
        job_id = IMAGE_QUEUE.get()
        try:
            _run_image_job(job_id)
        except Exception as e:
            _update_image_job(job_id, status="failed", error=str(e), finishedAt=_now_iso())
            print(f"[image-worker] error: {e}")
        finally:
            IMAGE_QUEUE.task_done()


# ═══ Handler ═══

class RPHandler(SimpleHTTPRequestHandler):

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/submit":
            self._handle_submit(body)
        elif path == "/api/settings":
            self._handle_save_settings(body)
        elif path == "/api/image-gen":
            self._handle_image_gen(body)
        elif path == "/api/card":
            self._handle_save_card(body)
        elif path == "/api/worldbook":
            self._handle_save_worldbook(body)
        elif path == "/api/worldbook/preview":
            self._handle_preview_worldbook(body)
        elif path == "/api/cards/switch":
            self._handle_switch_card(body)
        elif path == "/api/reroll":
            self._handle_reroll()
        elif path == "/api/delete-turns":
            self._handle_delete_turns(body)
        elif path == "/api/done":
            PENDING_FILE.unlink(missing_ok=True)
            self._json({"ok": True})
        else:
            self.send_error(404)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/pending":
            pending = PENDING_FILE.exists()
            text = INPUT_FILE.read_text(encoding="utf-8") if INPUT_FILE.exists() else ""
            self._json({"pending": pending, "text": text})
        elif path == "/api/image":
            self._handle_serve_image()
        elif path == "/api/image-job":
            self._handle_get_image_job()
        elif path == "/api/cards":
            self._handle_list_cards()
        elif path == "/api/card":
            self._handle_get_card()
        elif path == "/api/context":
            self._handle_get_context()
        elif path == "/api/worldbooks":
            self._handle_list_worldbooks()
        elif path == "/api/worldbook":
            self._handle_get_worldbook()
        elif path == "/api/state":
            self._serve_file(STATE_JS, "application/javascript")
        elif path == "/api/content":
            self._serve_file(CONTENT_JS, "application/javascript")
        elif path == "/api/settings":
            self._serve_file(SETTINGS_FILE, "application/json")
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── handlers ──

    def _handle_image_gen(self, body):
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid json"})
            return
        tags = data.get("tags", "").strip()
        key = data.get("key", "")
        if not tags:
            self._json({"ok": False, "error": "missing tags"})
            return
        card = get_current_card_name() or "example-card"
        job_id = _create_image_job(card=card, key=key, tags=tags)
        IMAGE_QUEUE.put(job_id)
        self._json({"ok": True, "jobId": job_id, "status": "queued"})

    def _handle_serve_image(self):
        import urllib.parse as _up
        query = _up.urlparse(self.path).query
        params = _up.parse_qs(query)
        img_path = params.get("path", [None])[0]
        if not img_path:
            self.send_error(400)
            return
        p = Path(img_path)
        if not p.exists() or not p.is_file():
            self.send_error(404)
            return
        ext = p.suffix.lower()
        ct_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
        ct = ct_map.get(ext, "image/png")
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(p.stat().st_size))
        self.end_headers()
        self.wfile.write(p.read_bytes())

    def _handle_get_image_job(self):
        import urllib.parse as _up
        query = _up.urlparse(self.path).query
        params = _up.parse_qs(query)
        job_id = params.get("id", [""])[0]
        if not job_id:
            self._json({"ok": False, "error": "missing id"}, 400)
            return
        jobs = _load_image_jobs()
        job = jobs.get(job_id)
        if not job:
            self._json({"ok": False, "error": "job not found"}, 404)
            return
        self._json({"ok": True, "job": job})

    def _handle_submit(self, body):
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"text": body}
        text = data.get("text", "").strip()
        if not text:
            self._json({"ok": False, "error": "empty text"})
            return
        context = build_turn_context(text)
        INPUT_FILE.write_text(text, encoding="utf-8")
        PENDING_FILE.touch()
        print(f"[server] 收到: {text[:60]}...")
        self._json({
            "ok": True,
            "text": text,
            "context": {
                "activatedLore": context.get("activatedLore", []),
                "metadata": context.get("metadata", {}),
            },
        })

    def _handle_list_cards(self):
        self._json({
            "ok": True,
            "cards": list_cards(),
            "current": get_current_card_name(),
        })

    def _handle_get_card(self):
        try:
            payload = get_card_payload()
            self._json({
                "ok": True,
                "card": {
                    "id": payload["id"],
                    "format": payload["format"],
                    "fields": payload["fields"],
                },
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_get_context(self):
        try:
            self._json({"ok": True, "context": get_context_payload()})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_list_worldbooks(self):
        try:
            current = get_current_card_name()
            self._json({
                "ok": True,
                "current": "main",
                "cardId": current,
                "worldbooks": list_worldbooks(current),
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_get_worldbook(self):
        try:
            parsed = urlparse(self.path)
            import urllib.parse as _up
            params = _up.parse_qs(parsed.query)
            book_name = params.get("name", ["main"])[0] or "main"
            payload = get_worldbook_payload(book_name)
            self._json({
                "ok": True,
                "worldbook": {
                    "id": payload["id"],
                    "cardId": payload["cardId"],
                    "entries": payload["entries"],
                },
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_save_card(self, body):
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid json"})
            return
        card_id = data.get("id") or get_current_card_name()
        fields = data.get("fields")
        if not card_id or not isinstance(fields, dict):
            self._json({"ok": False, "error": "missing card id or fields"}, 400)
            return
        try:
            payload = save_card_fields(card_id, fields)
            self._update_state_card(card_id)
            rebuild_context_snapshot()
            self._json({
                "ok": True,
                "card": {
                    "id": payload["id"],
                    "format": payload["format"],
                    "fields": payload["fields"],
                },
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_switch_card(self, body):
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid json"})
            return
        card_id = data.get("name", "").strip()
        if not card_id:
            self._json({"ok": False, "error": "missing card name"}, 400)
            return
        try:
            set_current_card_name(card_id)
            ensure_card_runtime(card_id)
            self._update_state_card(card_id)
            rebuild_context_snapshot()
            payload = get_card_payload(card_id)
            self._json({
                "ok": True,
                "current": card_id,
                "card": {
                    "id": payload["id"],
                    "format": payload["format"],
                    "fields": payload["fields"],
                },
                "cards": list_cards(),
            })
        except FileNotFoundError as e:
            self._json({"ok": False, "error": str(e)}, 404)
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_save_worldbook(self, body):
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid json"})
            return
        book_name = (data.get("name") or "main").strip() or "main"
        entries = data.get("entries")
        if not isinstance(entries, list):
            self._json({"ok": False, "error": "missing entries"}, 400)
            return
        try:
            payload = save_worldbook_entries(book_name, entries)
            rebuild_context_snapshot()
            self._json({
                "ok": True,
                "worldbook": {
                    "id": payload["id"],
                    "cardId": payload["cardId"],
                    "entries": payload["entries"],
                },
            })
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_preview_worldbook(self, body):
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid json"})
            return
        book_name = (data.get("name") or "main").strip() or "main"
        text = data.get("text", "")
        try:
            preview = preview_worldbook_activation(text, book_name)
            self._json({"ok": True, "preview": preview})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)

    def _handle_save_settings(self, body):
        try:
            data = json.loads(body)
            current = DEFAULT_SETTINGS.copy()
            if SETTINGS_FILE.exists():
                try:
                    current.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
                except Exception:
                    pass
            current.update(data)
            SETTINGS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
            rebuild_context_snapshot()
            self._json({"ok": True, "settings": current})
        except json.JSONDecodeError:
            self._json({"ok": False, "error": "invalid json"})

    def _handle_reroll(self):
        try:
            from handler import load_log, save_log
            log = load_log()
            if not log or len(log) < 2:
                self._json({"ok": False, "error": "nothing to reroll"})
                return
            last_user = None
            if log[-2].get("role") == "user":
                last_user = log[-2]["content"]
            log = log[:-2]
            save_log(log)
            from handler import build_content_js
            build_content_js(CHAT_LOG, CONTENT_JS)
            rebuild_context_snapshot()
            if last_user:
                INPUT_FILE.write_text(last_user, encoding="utf-8")
                PENDING_FILE.touch()
            self._json({"ok": True, "text": last_user})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})

    def _handle_delete_turns(self, body):
        try:
            data = json.loads(body)
            from_idx = int(data.get("fromIndex", 0))
            from handler import build_content_js, load_log, save_log
            log = load_log()
            if from_idx < 0 or from_idx > len(log):
                self._json({"ok": False, "error": "fromIndex out of range"}, 400)
                return
            save_log(log[:from_idx])
            build_content_js(CHAT_LOG, CONTENT_JS)
            rebuild_context_snapshot()
            PENDING_FILE.unlink(missing_ok=True)
            self._json({"ok": True})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})

    # ── helpers ──

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8") if length else ""

    def _serve_file(self, path: Path, content_type: str):
        if path.exists():
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(path.read_bytes())
        else:
            self.send_error(404)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass

    def _update_state_card(self, card_id: str):
        try:
            current = json.loads(STATE_JS.read_text(encoding="utf-8").replace("var STATE = ", "").rstrip(";"))
        except Exception:
            current = {"time": "", "location": "", "characters": {}, "generatedCount": 0}
        current["card"] = card_id
        STATE_JS.write_text(f"var STATE = {json.dumps(current, ensure_ascii=False)};", encoding="utf-8")


def main():
    try:
        _main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        PID_FILE.unlink(missing_ok=True)
        sys.exit(1)

def _main():
    init_files()

    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    # Start auto-polling thread
    poller = threading.Thread(target=response_poller, daemon=True)
    poller.start()
    worker = threading.Thread(target=image_worker, daemon=True)
    worker.start()

    print(f"\n  OpenCode RP Bridge (TUI 注入模式)")
    print(f"  项目: {PROJECT_ROOT}")
    print(f"  TUI API: http://127.0.0.1:4096")
    print(f"  前端 → http://localhost:{PORT}/index.html")
    print(f"  PID {os.getpid()} → {PID_FILE}")
    print(f"  前提: opencode --port 4096")
    print(f"  浏览器发送 → 注入 TUI 输入框 → AI 生成 → 自动刷新\n")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), RPHandler)
    server.allow_reuse_address = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] 已停止")
        server.shutdown()
    finally:
        PID_FILE.unlink(missing_ok=True)

def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _load_image_jobs():
    try:
        return json.loads(IMAGE_JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_image_jobs(jobs):
    IMAGE_JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def _reset_stale_image_jobs():
    jobs = _load_image_jobs()
    changed = False
    for job in jobs.values():
        if job.get("status") in {"queued", "running"}:
            job["status"] = "failed"
            job["error"] = "job interrupted by server restart"
            job["finishedAt"] = _now_iso()
            changed = True
    if changed:
        _save_image_jobs(jobs)


def _create_image_job(card: str, key: str, tags: str) -> str:
    job_id = uuid4().hex
    with IMAGE_JOBS_LOCK:
        jobs = _load_image_jobs()
        jobs[job_id] = {
            "id": job_id,
            "card": card,
            "key": key,
            "tags": tags,
            "status": "queued",
            "path": "",
            "error": "",
            "createdAt": _now_iso(),
            "startedAt": "",
            "finishedAt": "",
        }
        _save_image_jobs(jobs)
    return job_id


def _update_image_job(job_id: str, **changes):
    with IMAGE_JOBS_LOCK:
        jobs = _load_image_jobs()
        if job_id not in jobs:
            return None
        jobs[job_id].update(changes)
        _save_image_jobs(jobs)
        return jobs[job_id]


def _run_image_job(job_id: str):
    job = _update_image_job(job_id, status="running", startedAt=_now_iso(), error="")
    if not job:
        return
    card = job.get("card") or "example-card"
    tags = job.get("tags", "")
    key = job.get("key", "")
    out_dir = ROOT.parent / "generated" / card
    out_dir.mkdir(parents=True, exist_ok=True)
    gen_script = ROOT.parent / "scripts" / "novelai-generate.py"
    print(f"[image-worker] generating {job_id}: {tags[:80]}...")
    try:
        result = subprocess.run(
            [sys.executable, str(gen_script), "-p", tags, "-s", "832x1216", "-o", str(out_dir)],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(ROOT.parent),
        )
        img_path = _extract_image_path(result.stdout, result.stderr, out_dir)
        if result.returncode != 0 and not img_path:
            error = (result.stderr or result.stdout or "image generation failed")[:400]
            _update_image_job(job_id, status="failed", error=error, finishedAt=_now_iso())
            return
        if not img_path:
            _update_image_job(job_id, status="failed", error="no image found", finishedAt=_now_iso())
            return
        _persist_generated_image(key, img_path)
        _update_image_job(job_id, status="done", path=img_path, finishedAt=_now_iso(), error="")
    except subprocess.TimeoutExpired:
        _update_image_job(job_id, status="failed", error="NAI API timeout (180s)", finishedAt=_now_iso())


def _extract_image_path(stdout: str, stderr: str, out_dir: Path):
    for line in (stdout.splitlines() + stderr.splitlines()):
        match = re.search(r"generated[\\/](nai_[^\\/\s]+\.png)", line)
        if match:
            return str(out_dir / match.group(1))
    files = sorted(out_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
    if files:
        return str(files[0])
    return ""


def _persist_generated_image(key: str, img_path: str):
    gen_map = {}
    if IMG_GENERATED_FILE.exists():
        try:
            gen_map = json.loads(IMG_GENERATED_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    gen_map[key] = img_path
    IMG_GENERATED_FILE.write_text(json.dumps(gen_map, ensure_ascii=False, indent=2), encoding="utf-8")
    from handler import build_content_js
    build_content_js(CHAT_LOG, CONTENT_JS)


if __name__ == "__main__":
    main()
