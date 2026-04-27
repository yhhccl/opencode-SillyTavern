#!/usr/bin/env python3
"""AIRP context integration for the web frontend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = Path(__file__).resolve().parent
AIRP_ROOT = ROOT / "airp-sillytavern"

if str(AIRP_ROOT) not in sys.path:
    sys.path.insert(0, str(AIRP_ROOT))

from runtime.engine import DEFAULT_PERSONA, DEFAULT_PRESET, do_post, do_turn  # noqa: E402
from runtime.state import SessionState  # noqa: E402

from card_store import get_card_payload, get_card_dir, get_current_card_name, get_worldbook_payload  # noqa: E402


CHAT_LOG = WEB_ROOT / "chat_log.json"
SETTINGS_FILE = WEB_ROOT / "settings.json"
CONTEXT_FILE = WEB_ROOT / "context-inspect.json"


def ensure_context_file() -> None:
    if not CONTEXT_FILE.exists():
        CONTEXT_FILE.write_text(json.dumps(default_context_payload(), ensure_ascii=False, indent=2), encoding="utf-8")


def get_context_payload() -> dict:
    ensure_context_file()
    return json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))


def build_turn_context(user_message: str) -> dict:
    card_id = get_current_card_name()
    session_dir = sync_session_from_web(card_id)
    result = do_turn(user_message, session_dir=str(session_dir))
    payload = _build_payload(card_id, result, user_message=user_message)
    CONTEXT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def finalize_turn_context(assistant_response: str) -> dict:
    current = get_context_payload()
    card_id = current.get("cardId") or get_current_card_name()
    session_dir = get_session_dir(card_id)
    post = do_post(assistant_response, session_dir=str(session_dir))
    current["assistantResponse"] = assistant_response
    current["lastPost"] = post
    current["phase"] = "completed"
    CONTEXT_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def rebuild_context_snapshot() -> dict:
    card_id = get_current_card_name()
    session_dir = sync_session_from_web(card_id)
    state = SessionState(session_dir)
    payload = {
        **default_context_payload(),
        "cardId": card_id,
        "sessionDir": str(session_dir),
        "phase": "idle",
        "state": state.to_dict(),
        "settings": _load_settings(),
    }
    CONTEXT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def sync_session_from_web(card_id: str | None = None) -> Path:
    current = card_id or get_current_card_name()
    session_dir = get_session_dir(current)
    session_dir.mkdir(parents=True, exist_ok=True)

    card = get_card_payload(current)
    worldbook = get_worldbook_payload("main", current)
    settings = _load_settings()
    history = _load_web_history()

    (session_dir / "character.json").write_text(
        json.dumps(card["raw"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "worldbook.json").write_text(
        json.dumps({"entries": worldbook["entries"]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "persona.json").write_text(
        json.dumps(DEFAULT_PERSONA, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "preset.json").write_text(
        json.dumps(_build_preset(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assistant_count = len([msg for msg in history if msg.get("role") == "assistant"])
    user_name = DEFAULT_PERSONA.get("name", "User")
    char_name = card["fields"].get("name", "")
    state = SessionState(session_dir)
    state.data["char_name"] = char_name
    state.data["user_name"] = user_name
    state.data["turn"] = assistant_count
    state.save()
    return session_dir


def get_session_dir(card_id: str) -> Path:
    return get_card_dir(card_id) / "airp-session"


def default_context_payload() -> dict:
    return {
        "cardId": "",
        "sessionDir": "",
        "phase": "idle",
        "settings": {},
        "userMessage": "",
        "assistantResponse": "",
        "metadata": {},
        "activatedLore": [],
        "messages": [],
        "systemPrompt": "",
        "stateSummary": "",
        "state": {},
        "lastPost": {},
    }


def _build_payload(card_id: str, result: dict, user_message: str) -> dict:
    session_dir = get_session_dir(card_id)
    state = SessionState(session_dir)
    return {
        "cardId": card_id,
        "sessionDir": str(session_dir),
        "phase": "awaiting_response",
        "settings": _load_settings(),
        "userMessage": user_message,
        "assistantResponse": "",
        "metadata": result.get("metadata", {}),
        "activatedLore": result.get("activated_lore", []),
        "messages": result.get("messages", []),
        "systemPrompt": result.get("system_prompt", ""),
        "stateSummary": result.get("state_summary", ""),
        "state": state.to_dict(),
        "lastPost": {},
    }


def _build_preset(settings: dict) -> dict:
    preset = dict(DEFAULT_PRESET)
    word_count = settings.get("wordCount", 600)
    try:
        word_count = int(word_count)
    except (TypeError, ValueError):
        word_count = 600
    preset["max_tokens"] = max(200, min(word_count, 2000))
    preset["raw"] = {
        "style": settings.get("style", "default"),
        "nsfw": settings.get("nsfw", "off"),
        "person": settings.get("person", "first"),
    }
    return preset


def _load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    return {}


def _load_web_history() -> list[dict]:
    if not CHAT_LOG.exists():
        return []
    raw = json.loads(CHAT_LOG.read_text(encoding="utf-8"))
    history = []
    for entry in raw:
        history.append({
            "role": entry.get("role", "user"),
            "content": entry.get("content", ""),
            "timestamp": entry.get("timestamp", ""),
        })
    return history
