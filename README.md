# OpenCode RP — AI Character Roleplay Engine

A complete roleplay framework for [OpenCode CLI](https://opencode.ai) with built-in NovelAI image generation. Play interactive stories with AI characters, generate companion illustrations, and manage multiple character cards with persistent save states.

## Features

- **AI Roleplay Engine** — Dual-writer identity (Atri & Deach), narrative iron rules, emotion/character shaping system
- **Multi-Character Support** — One card per character, fully independent saves and chat history
- **NovelAI Image Gen** — Auto-extract visual tags from narrative, generate V4.5/V4/V3 images via API
- **Progressive Style Loading** — Styles in `skills/`, index-only in `CLAUDE.md`, saves tokens
- **Session Persistence** — Auto-save after every turn, `/resume` to continue from new window
- **Portable Image Skill** — `生图skills/` is self-contained, can be copied to any project

## Quick Start

### 1. Prerequisites

- Python 3.8+
- OpenCode CLI installed
- NovelAI API key (for image generation)

### 2. Setup

```bash
# Clone or copy this directory
cd opencode-sillytavern

# Set your NovelAI API key
cp .env.example .env
# Edit .env: NOVELAI_API_KEY=your_key_here

# Place your character card JSON in 角色卡/
```

### 3. Start Playing

In OpenCode:
```
/play example-card
```

AI will auto-load the card, create save directories, and begin from `first_mes`.

## Directory Structure

```
opencode-sillytavern/
├── CLAUDE.md              # Core RP engine config
├── README.md
├── README-zh.md
├── .gitignore
├── .env.example           # API key template
├── current-card.txt       # Active card name
├── 命令速查表.md           # Full command reference (Chinese)
│
├── 角色卡/                 # Character cards
│   └── example-card.json  # Safe example card
│
├── skills/                # RP skills (progressive loading)
│   ├── styles/            # Writing styles
│   ├── image-gen.md       # Image prompt rules
│   └── novelai-gen.md     # Image gen scheduler
│
├── 生图skills/             # Standalone image gen skill
│   ├── SKILL.md
│   ├── .env.example
│   ├── scripts/
│   └── references/
│
├── scripts/               # Image gen tools
│   ├── extract-img.py     # Extract [img:...] from RP output
│   └── novelai-generate.py # Call NovelAI API
│
├── 预设/                   # SillyTavern presets (reference)
│   └── 双人成行 V4.5...json
│
├── 世界书Skills/           # World book manager (SillyTavern)
├── airp-sillytavern/       # AIRP runtime engine
│
└── reference docs:
    ├── OpenCode rp jc.txt
    ├── 扮演指导 README .md
    ├── novelai API 参考.txt
    ├── 文生图世界书 (1).json
    └── memory/reference.md
```

## Commands

### RP Commands

| Command | Effect |
|---------|--------|
| `/play <card>` | Start/switch character card |
| `/cards` | List available cards |
| `/resume` | Resume from last session |
| `/save` | Force save current state |
| `/clear` | Clear context |
| `/plan` | Plan mode — discuss plot direction |

### Image Generation

| Command | Effect |
|---------|--------|
| `/img 生成` | Generate latest [img:...] via NAI |
| `/img 全部` | Generate all pending tags |
| `/img 横版` | Landscape 1216x832 |
| `/img furry` | Furry model |

### Scripts

```bash
# Extract + generate in one step
python scripts/extract-img.py saves/{card}/rp-log.txt -g --latest-only

# Direct generation
python scripts/novelai-generate.py -p "1girl, school uniform, masterpiece, best quality"

# List available models
python scripts/novelai-generate.py --list-models
```

## Models

| Alias | API ID |
|-------|--------|
| v4.5-curated ★ | `nai-diffusion-4-5-curated` |
| v4.5-full | `nai-diffusion-4-5-full` |
| v4-curated | `nai-diffusion-4-curated-preview` |
| v4-full | `nai-diffusion-4-full` |
| v3 | `nai-diffusion-3` |
| furry | `nai-diffusion-furry-3` |

## How It Works

### Per-Turn Flow

```
User input → AI writes narrative
  → AI scans own output → extracts visual tags → outputs [img: ...]
  → Auto-saves to saves/{card}/rp-log.txt
  → Auto-updates saves/{card}/session-state.md
```

### Image Generation Flow

```
User: /img 生成
  → Extract [img: ...] from saves/{card}/rp-log.txt
  → Call NovelAI API (V4.5 Curated by default)
  → Image saved to generated/{card}/
```

### Multi-Card Flow

```
/play card-a    → Play card A (saves/reloads automatically)
/play card-b    → Switch to card B (card A state preserved)
/play card-a    → Back to card A, exactly where you left off
```

Each card has independent `saves/{card}/` directory with its own chat history, session state, and memory.

## License

MIT

---

See `命令速查表.md` for the complete command reference with play guide and FAQ.

See `README-zh.md` for the Chinese version.
