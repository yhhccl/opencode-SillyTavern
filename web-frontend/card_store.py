#!/usr/bin/env python3
"""Character card storage helpers for the web frontend."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = ROOT / "角色卡"
CURRENT_CARD_FILE = ROOT / "current-card.txt"
AIRP_ROOT = ROOT / "airp-sillytavern"

if str(AIRP_ROOT) not in sys.path:
    sys.path.insert(0, str(AIRP_ROOT))

from runtime.loader import normalize_worldbook  # noqa: E402
from runtime.worldinfo import activate  # noqa: E402

CARD_FIELD_DEFAULTS = {
    "name": "",
    "description": "",
    "personality": "",
    "scenario": "",
    "first_mes": "",
    "mes_example": "",
    "creator_notes": "",
    "system_prompt": "",
    "post_history_instructions": "",
    "tags": [],
    "creator": "",
    "character_version": "1.0",
    "alternate_greetings": [],
    "extensions": {},
}

WORLD_ENTRY_DEFAULTS = {
    "uid": 0,
    "comment": "",
    "key": [],
    "keysecondary": [],
    "content": "",
    "constant": False,
    "selective": False,
    "selectiveLogic": 0,
    "order": 100,
    "position": 1,
    "disable": False,
    "excludeRecursion": False,
    "preventRecursion": False,
    "probability": 100,
    "useProbability": True,
    "depth": 0,
    "role": 0,
    "group": "",
    "groupOverride": False,
    "groupWeight": 100,
    "scanDepth": None,
    "caseSensitive": False,
    "matchWholeWords": False,
    "automationId": "",
    "sticky": 0,
    "cooldown": 0,
    "delay": 0,
}


def list_cards() -> list[dict]:
    cards = []
    active = get_current_card_name()
    for path in sorted(CARDS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_dir():
            continue
        card_file = path / "card.json"
        if not card_file.exists():
            continue
        raw = _read_json(card_file)
        fields = extract_card_fields(raw)
        cards.append(
            {
                "id": path.name,
                "name": fields.get("name") or path.name,
                "active": path.name == active,
                "updatedAt": _mtime_iso(card_file),
            }
        )
    return cards


def get_current_card_name() -> str:
    if CURRENT_CARD_FILE.exists():
        name = CURRENT_CARD_FILE.read_text(encoding="utf-8").strip()
        if name:
            return name
    cards = list_available_card_ids()
    return cards[0] if cards else ""


def list_available_card_ids() -> list[str]:
    if not CARDS_DIR.exists():
        return []
    return [
        path.name
        for path in sorted(CARDS_DIR.iterdir(), key=lambda p: p.name.lower())
        if path.is_dir() and (path / "card.json").exists()
    ]


def set_current_card_name(card_id: str) -> None:
    card_path = get_card_dir(card_id)
    if not (card_path / "card.json").exists():
        raise FileNotFoundError(f"Card not found: {card_id}")
    CURRENT_CARD_FILE.write_text(card_id, encoding="utf-8")


def get_card_dir(card_id: str) -> Path:
    return CARDS_DIR / card_id


def get_card_payload(card_id: str | None = None) -> dict:
    current = card_id or get_current_card_name()
    if not current:
        raise FileNotFoundError("No character cards available")
    path = get_card_dir(current) / "card.json"
    raw = _read_json(path)
    fields = extract_card_fields(raw)
    return {
        "id": current,
        "path": str(path),
        "format": detect_card_format(raw),
        "raw": raw,
        "fields": fields,
    }


def save_card_fields(card_id: str, fields: dict) -> dict:
    payload = get_card_payload(card_id)
    raw = payload["raw"]
    merged = merge_card_fields(raw, fields)
    card_path = get_card_dir(card_id) / "card.json"
    card_path.write_text(json.dumps(merged, ensure_ascii=False, indent=4), encoding="utf-8")
    return get_card_payload(card_id)


def detect_card_format(raw: dict) -> str:
    if isinstance(raw.get("data"), dict):
        spec = raw.get("spec", "")
        if spec:
            return spec
        return "data-wrapper"
    return "legacy"


def extract_card_fields(raw: dict) -> dict:
    source = raw.get("data", raw)
    fields = dict(CARD_FIELD_DEFAULTS)
    for key in fields:
        if key in source:
            fields[key] = source.get(key)
    if not isinstance(fields.get("tags"), list):
        tags = fields.get("tags", [])
        if isinstance(tags, str):
            fields["tags"] = [item.strip() for item in tags.split(",") if item.strip()]
        else:
            fields["tags"] = []
    return fields


def merge_card_fields(raw: dict, incoming: dict) -> dict:
    cleaned = dict(CARD_FIELD_DEFAULTS)
    for key, default in CARD_FIELD_DEFAULTS.items():
        value = incoming.get(key, default)
        if key == "tags":
            if isinstance(value, str):
                value = [item.strip() for item in value.split(",") if item.strip()]
            elif not isinstance(value, list):
                value = []
        cleaned[key] = value

    if isinstance(raw.get("data"), dict):
        merged = json.loads(json.dumps(raw, ensure_ascii=False))
        merged.setdefault("data", {})
        merged["data"].update(cleaned)
        return merged

    merged = json.loads(json.dumps(raw, ensure_ascii=False)) if raw else {}
    merged.update(cleaned)
    return merged


def ensure_card_runtime(card_id: str) -> None:
    card_dir = get_card_dir(card_id)
    card_dir.mkdir(parents=True, exist_ok=True)
    (card_dir / "generated").mkdir(exist_ok=True)
    (card_dir / "memory").mkdir(exist_ok=True)
    (card_dir / "worldbooks").mkdir(exist_ok=True)
    main_worldbook = card_dir / "worldbooks" / "main.json"
    if not main_worldbook.exists():
        main_worldbook.write_text(json.dumps({"entries": {}}, ensure_ascii=False, indent=2), encoding="utf-8")


def list_worldbooks(card_id: str | None = None) -> list[dict]:
    current = card_id or get_current_card_name()
    worldbook_dir = get_card_dir(current) / "worldbooks"
    ensure_card_runtime(current)
    books = []
    for path in sorted(worldbook_dir.glob("*.json"), key=lambda p: p.name.lower()):
        books.append(
            {
                "id": path.stem,
                "name": path.stem,
                "updatedAt": _mtime_iso(path),
            }
        )
    return books


def get_worldbook_payload(book_name: str = "main", card_id: str | None = None) -> dict:
    current = card_id or get_current_card_name()
    path = get_card_dir(current) / "worldbooks" / f"{book_name}.json"
    ensure_card_runtime(current)
    raw = _read_json(path) if path.exists() else {"entries": {}}
    normalized = normalize_worldbook(raw)
    entries = [normalize_worldbook_entry(entry) for entry in normalized.get("entries", [])]
    return {
        "cardId": current,
        "id": book_name,
        "path": str(path),
        "entries": entries,
        "raw": raw,
    }


def save_worldbook_entries(book_name: str, entries: list[dict], card_id: str | None = None) -> dict:
    current = card_id or get_current_card_name()
    ensure_card_runtime(current)
    path = get_card_dir(current) / "worldbooks" / f"{book_name}.json"
    normalized_entries = [normalize_worldbook_entry(entry, index=i) for i, entry in enumerate(entries)]
    keyed_entries = {str(entry["uid"]): encode_worldbook_entry(entry) for entry in normalized_entries}
    path.write_text(json.dumps({"entries": keyed_entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_worldbook_payload(book_name, current)


def preview_worldbook_activation(text: str, book_name: str = "main", card_id: str | None = None) -> dict:
    payload = get_worldbook_payload(book_name, card_id)
    card = get_card_payload(card_id)
    activated = activate(
        entries=payload["entries"],
        chat_history=[{"role": "user", "content": text or ""}],
        char_name=card["fields"].get("name", ""),
        user_name="User",
    )
    return {
        "book": book_name,
        "matches": [
            {
                "uid": entry.get("uid"),
                "comment": entry.get("comment", ""),
                "keys": entry.get("key", []),
                "reason": entry.get("_activation", ""),
                "constant": entry.get("constant", False),
                "position": entry.get("position", 1),
                "order": entry.get("order", 100),
            }
            for entry in activated
        ],
    }


def normalize_worldbook_entry(entry: dict, index: int = 0) -> dict:
    merged = dict(WORLD_ENTRY_DEFAULTS)
    merged.update(entry or {})
    merged["uid"] = _safe_int(merged.get("uid"), index)
    merged["key"] = _ensure_list(merged.get("key", []))
    merged["keysecondary"] = _ensure_list(merged.get("keysecondary", []))
    merged["order"] = _safe_int(merged.get("order"), 100)
    merged["position"] = _safe_int(merged.get("position"), 1)
    merged["probability"] = _safe_int(merged.get("probability"), 100)
    merged["depth"] = _safe_int(merged.get("depth"), 0)
    merged["sticky"] = _safe_int(merged.get("sticky"), 0)
    merged["cooldown"] = _safe_int(merged.get("cooldown"), 0)
    merged["delay"] = _safe_int(merged.get("delay"), 0)
    return merged


def encode_worldbook_entry(entry: dict) -> dict:
    encoded = dict(entry)
    encoded["keys"] = ", ".join(entry.get("key", []))
    encoded.pop("key", None)
    if entry.get("keysecondary"):
        encoded["keysecondary"] = entry.get("keysecondary", [])
    return encoded


def _ensure_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
