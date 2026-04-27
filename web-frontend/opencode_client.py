"""opencode_client.py — 通过 opencode TUI 控制 API 注入消息。

前提: opencode 必须以固定端口启动: opencode --port 4096
流程: 前端输入 → clear-prompt → append-prompt → submit-prompt
       → opencode TUI 输入框收到 → AI 按 AGENTS.md 规则处理
       → AI 追加 rp-log.txt → 读取最新叙事返回
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

OC_URL = "http://127.0.0.1:4096"
DEFAULT_TIMEOUT = 300


def _post(endpoint: str, data: dict | None = None, timeout: int = 10) -> str:
    url = f"{OC_URL}{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else b""
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"opencode TUI API {endpoint} 返回 {e.code}: {body[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 opencode TUI ({OC_URL}): {e.reason}\n请确认 opencode 已启动: opencode --port 4096")
    except Exception as e:
        raise RuntimeError(f"opencode TUI API 失败: {e}")


def inject_message(text: str) -> None:
    """将消息注入 opencode TUI 输入框: 清空 → 追加文本 → 提交。"""
    _post("/tui/clear-prompt")
    time.sleep(0.15)
    _post("/tui/append-prompt", {"text": text})
    time.sleep(0.15)
    _post("/tui/submit-prompt")


def _get_card_name(cwd: Path) -> str:
    """读取当前激活的角色卡名。"""
    card_file = cwd / "current-card.txt"
    if card_file.exists():
        return card_file.read_text(encoding="utf-8").strip()
    return ""


def _read_rp_log(cwd: Path) -> tuple[Path, int]:
    """返回 rp-log.txt 路径和当前字节数。"""
    card = _get_card_name(cwd)
    if not card:
        raise RuntimeError("current-card.txt 为空, 请先 /play <角色>")
    rp_log = cwd / "角色卡" / card / "rp-log.txt"
    size = rp_log.stat().st_size if rp_log.exists() else 0
    if not rp_log.exists():
        rp_log.parent.mkdir(parents=True, exist_ok=True)
        rp_log.write_text("", encoding="utf-8")
        size = 0
    return rp_log, size


def _extract_last_narrative(filepath: Path, start_offset: int) -> str:
    """从 rp-log.txt 中读取 start_offset 之后新增的叙事正文（保留 [img:...] 标签）。"""
    import os as _os
    try:
        with open(str(filepath), "r", encoding="utf-8") as f:
            if start_offset > 0:
                f.seek(start_offset, _os.SEEK_SET)
            text = f.read()
    except Exception:
        return ""
    lines = text.splitlines()
    clean_lines = []
    meta_prefixes = (
        "【", "Write", "Read", "Bash", "Tool", "Result",
        "Session state", "Updated", "Memory project",
    )
    for line in lines:
        s = line.strip()
        if not s or s.startswith(("---", "===")):
            clean_lines.append("")
            continue
        if any(s.startswith(p) for p in meta_prefixes):
            continue
        clean_lines.append(s)
    return "\n".join(clean_lines).strip()


def send_message(
    user_text: str,
    cwd: Path,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """向 opencode TUI 注入消息，监控 rp-log.txt 增量获取回复。

    Args:
        user_text: 用户输入文本
        cwd: 项目根目录
        timeout: 等待超时 (秒)

    Returns:
        AI 生成的最新叙事回复 (含 [img: ...] 标签)
    """
    rp_log, prev_size = _read_rp_log(cwd)

    prompt = (
        f"【Web 前端 RP — 自动模式】\n\n"
        f"══════ 以下为用户在前端输入的内容 ══════\n"
        f"{user_text}\n"
        f"══════ 用户输入结束 ══════\n\n"
        f"请严格按 AGENTS.md 规则生成叙事回复:\n"
        f"- Read current-card.txt 确定角色, Read 角色卡文件\n"
        f"- 生成 200-1000 字叙事 (简体中文, *动作用斜体*, 对话不加引号)\n"
        f"- 提取 [img: ...] 标签\n"
        f"- Write 追加完整回复 (含标签) 到 rp-log.txt\n"
        f"- Write 更新 session-state.md\n\n"
        f"直接输出叙事正文，不要输出确认信息或解释。"
    )

    inject_message(prompt)

    started = time.time()
    while True:
        # 优先检测 web-response.txt (AI 可能仍会写入)
        wr = cwd / "web-frontend" / "web-response.txt"
        if wr.exists():
            reply = wr.read_text(encoding="utf-8").strip()
            if reply:
                return reply

        # 检测 rp-log.txt 增长
        if rp_log.exists():
            cur_size = rp_log.stat().st_size
            if cur_size > prev_size:
                # 段写入后稍等一下确保写入完成
                time.sleep(0.8)
                # 二次确认不再增长
                if rp_log.stat().st_size == cur_size:
                    return _extract_last_narrative(rp_log, prev_size)

        elapsed = time.time() - started
        if elapsed > timeout:
            raise RuntimeError(f"等待 AI 回复超时 ({elapsed:.0f}s > {timeout}s)")
        time.sleep(1.5)


def check_oc_alive() -> bool:
    """检查 opencode TUI 是否在运行。"""
    try:
        _post("/tui/clear-prompt", timeout=3)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    alive = check_oc_alive()
    print(f"opencode TUI ({OC_URL}): {'已连接' if alive else '未连接 - 请用 opencode --port 4096 启动'}")
