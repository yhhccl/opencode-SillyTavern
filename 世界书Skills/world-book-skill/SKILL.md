---
name: world-book-create
description: >-
  Create, edit, and list SillyTavern World Book (世界书) entries via CLI.
  Use when the user wants to: (1) create a new world book JSON file,
  (2) add character/worldbuilding/rule entries to an existing world book,
  (3) edit specific entries by UID, (4) delete entries, (5) list entries,
  (6) batch-modify positions or trigger keys for multiple entries.
  Supports 8 injection positions (↑Char ↓Char ↑AT ↓AT @D ↑EM ↓EM Outlet),
  trigger keywords, depth, constant/selective activation, and more.
---

# SillyTavern World Book Manager

Use `scripts/world-book-create.py` to create/edit/list world book JSON files.

## Entry content rules — follow these or the card will be bad

Before writing ANY entry content, read `references/entry-conventions.md`. Critical rules in short:

### Character entries
1. **Four sections only, no more**: 基本信息 | 外貌特征 | 背景设定 | 关系设定
   - 性格 does NOT go here — separate entry
2. **外貌只写特征**: only features that deviate from what the AI already knows about this race/age. No "精致的脸蛋" "白皙的皮肤" — those are universal filler. Test: can you identify this character by appearance alone with the name covered?
3. **背景只写关键事件**: only events that actually changed who they are. Delete anything that, if removed, wouldn't change the character.
4. **关系写具体画面**: concrete interactions, not abstract claims. "有记忆起就在一起" beats "深厚的感情".
5. **数据库格式, 不是散文**: use lists and key-value pairs. No prose paragraphs.

### Worldbuilding entries
1. **用最少的字说清所有设定**: token economy is everything. Cut filler words (连接词→冒号/逗号).
2. **Only write what the AI doesn't already know**: modern Tokyo? AI knows it. Your custom school name? Write that.
3. **No subjective adjectives**: "强大的帝国"→"帝国" or real data. "神秘的"→delete.
4. **Test**: if you delete this line, would the AI still act correctly? Yes→delete.

## Configuration rules — wrong config = AI ignores your entry

### Position (--position)
| Content type | Position | Flag |
|--------------|----------|------|
| Worldview / background / rules | 0 (↑Char) | `--position 0` |
| Character detailed info | 1 (↓Char) | `--position 1` |
| NPC / scenes / items | 1 (↓Char) | `--position 1` |
| Writing rules / formatting | 2 (↑AT) | `--position 2` |
| Behavior correction (二次解释) | 4 (@D, depth=0) | `--position 4 --depth 0 --role 0` |
| **D1+ (@D depth≥1)** | **NEVER USE** | Breaks chat history |

### Activation (--constant vs --keys)
| Card type | Rule |
|-----------|------|
| **Single character card** | **ALL entries `--constant`**. Even if split into 10 entries. Iron rule. |
| Multi character card | Character overview `--constant`; individual details `--keys 名字,昵称` |
| Worldview / rules | `--constant` |
| NPCs / scenes | `--keys ...` (keyword-triggered) |

### Recurrence
**Every entry MUST have `--prevent-recursion`**. Without it: keyword cascading → token explosion.

### Keywords (--keys)
- **English commas only** (`,`), Chinese `，` fails silently
- No spaces after commas
- Cover ALL names: full name, nickname, title, alias
- Example: `--keys "林小雨,小雨,班长"`

### Scan depth
For keyword-triggered entries: `--scan-depth 2` (scan last 2 messages only).

### Order (--order)
Within same position, higher = later in prompt:
- Worldview outline: 1-3
- Character overview: 4
- Scenes/events: 50-98
- Character details: 99
- NPCs: 100

## Common commands

```bash
# New world book with worldview
python scripts/world-book-create.py output.json -n --name "Name" --add \
    --comment "世界观总纲" --content @设定.txt --constant --position 0 --prevent-recursion

# Single-character entry (ALL entries for this char must be --constant)
python scripts/world-book-create.py output.json --add \
    --comment "角色·林小雨·基础信息" --content @小雨基础.txt \
    --keys 林小雨,小雨 --constant --position 1 --prevent-recursion --order 10

# Multi-character NPC (keyword-triggered)
python scripts/world-book-create.py output.json --add \
    --comment "NPC·王老师" --content "王静：班主任..." \
    --keys 王静,王老师,班主任 --position 1 --prevent-recursion --scan-depth 2

# Behavior correction (二次解释)
python scripts/world-book-create.py output.json --add \
    --comment "林小雨·二次解释" --content "林小雨不会主动妥协..." \
    --keys 林小雨,小雨 --position 4 --depth 0 --role 0 --prevent-recursion

# List entries
python scripts/world-book-create.py output.json --list

# Edit entry
python scripts/world-book-create.py output.json --edit 3 --content @新内容.txt --keys 新关键词
```

## Batch mode

### Batch add (`--batch`)

```bash
python scripts/world-book-create.py output.json -n --name "Book Name" --batch entries.json
```

### Batch edit (`--batch-edit`)

Modify multiple existing entries at once. Each object must have `"uid"` plus any fields to change. Omitted fields are left unchanged.

```bash
python scripts/world-book-create.py existing.json --batch-edit edits.json
```

`edits.json`:
```json
[
  {"uid": 3, "content": "完全替换的新内容", "depth": 4},
  {"uid": 5, "keys": "新关键词1,新关键词2", "constant": true},
  {"uid": 7, "position": 1, "comment": "改名后的标题"}
]
```

### Batch JSON field reference
```json
[
  {
    "comment": "条目名",
    "content": "条目正文，支持 @file.txt",
    "keys": "key1,key2",
    "position": 0,
    "constant": true,
    "order": 100,
    "depth": 2,
    "preventRecursion": true,
    "scanDepth": 2
  }
]
```

All fields are optional (same defaults as CLI). `order` auto-increments if omitted. This is the recommended way to create multi-entry world books — a single command, no escaping issues, content can be long strings with newlines.

For same-field batch edits (e.g. "set all character positions to 1"), edit the JSON directly with Python.

## References

- `references/entry-conventions.md` — full content writing rules (角色卡编写铁律)
- `references/position-guide.md` — complete 8-position reference with source code mapping
