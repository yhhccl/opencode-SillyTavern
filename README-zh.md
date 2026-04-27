# OpenCode RP — AI 角色扮演引擎

一套基于 [OpenCode CLI](https://opencode.ai) 的完整角色扮演框架，内置 NovelAI 图片生成。支持交互式故事创作、配图生成、多角色卡管理与持久化存档。

## 功能

- **AI 角色扮演引擎** — 双生写手身份 (Atri & Deach)、叙事铁律、情绪表达/角色塑造系统
- **多角色卡支持** — 每张卡独立存档，聊天记录和状态完全隔离
- **NovelAI 生图** — 从叙事中自动提取视觉标签，通过 API 生成 V4.5/V4/V3 图片
- **渐进式加载** — 文风外置到 `skills/`，CLAUDE.md 只做索引，节省 Token
- **会话持久化** — 每轮自动保存，`/resume` 新窗口恢复上次进度
- **独立生图包** — `生图skills/` 自包含，可复制到任意项目使用

## 快速开始

### 1. 前置条件

- Python 3.8+
- 已安装 OpenCode CLI
- NovelAI API Key (如需生图功能)

### 2. 配置

```bash
# 克隆或复制本目录
cd opencode-sillytavern

# 设置 NovelAI API Key
copy .env.example .env
# 编辑 .env: NOVELAI_API_KEY=你的密钥

# 将你的角色卡 JSON 放入 角色卡/ 目录
```

### 3. 开始游玩

在 OpenCode 中输入：
```
/play example-card
```

AI 会自动加载角色卡、创建存档目录、从开场叙事开始扮演。

## 目录结构

```
opencode-sillytavern/
├── CLAUDE.md              # 核心 RP 引擎配置
├── README.md              # English README
├── README-zh.md           # 本文档
├── .gitignore
├── .env.example           # API Key 模板
├── current-card.txt       # 当前激活角色 (一行)
├── 命令速查表.md           # 完整命令参考 + 游玩指南 + FAQ
│
├── 角色卡/                 # 角色卡 JSON 文件
│   └── example-card.json  # 安全示例卡片
│
├── skills/                # RP Skill (渐进式加载)
│   ├── styles/            # 文风文件 (default / mode-a / mode-b)
│   ├── image-gen.md       # 图像标签提取规则
│   └── novelai-gen.md     # 图片生成调度器
│
├── 生图skills/             # 独立生图 Skill (可单独部署)
│   ├── SKILL.md
│   ├── .env.example
│   ├── scripts/
│   │   ├── extract-img.py
│   │   └── novelai-generate.py
│   └── references/
│       ├── prompt-guide.md
│       └── params-guide.md
│
├── scripts/               # 生图工具
│   ├── extract-img.py     # 从 RP 输出提取 [img:...]
│   └── novelai-generate.py # 调用 NovelAI API
│
├── 预设/                   # SillyTavern 预设 (参考)
│   └── 双人成行 V4.5...json
│
├── 世界书Skills/           # 世界书管理工具 (SillyTavern)
├── airp-sillytavern/       # AIRP 运行时引擎
│
└── 参考文档:
    ├── OpenCode rp jc.txt
    ├── 扮演指导 README .md
    ├── novelai API 参考.txt
    ├── 文生图世界书 (1).json
    └── memory/reference.md
```

## 命令速查

### RP 命令

| 命令 | 效果 |
|------|------|
| `/play <card>` | 启动/切换角色卡 |
| `/cards` | 列出可用卡片 |
| `/resume` | 新窗口恢复上次进度 |
| `/save` | 手动保存当前状态 |
| `/clear` | 清空上下文 |
| `/plan` | 计划模式 — 讨论剧情方向 |
| `/effort max` | 切换到 1M token 上下文 |

### 生图命令

| 命令 | 效果 |
|------|------|
| `/img 生成` | 从 rp-log.txt 提取最新 [img: ...] 并生成 |
| `/img 全部` | 生成所有待生成的标签 |
| `/img 横版` | 横版 1216x832 |
| `/img furry` | Furry 模型 |

### 脚本命令

```bash
# 提取 + 一键生成
python scripts/extract-img.py saves/{card}/rp-log.txt -g --latest-only

# 直接生成
python scripts/novelai-generate.py -p "1girl, school uniform, masterpiece, best quality"

# 列出可用模型
python scripts/novelai-generate.py --list-models

# 毛毛风格
python scripts/novelai-generate.py --furry -p "wolf girl, ..."

# 纯场景
python scripts/novelai-generate.py --background -p "sunset over ocean"
```

## 可用模型

| 别名 | API ID |
|------|--------|
| v4.5-curated ★ | `nai-diffusion-4-5-curated` |
| v4.5-full | `nai-diffusion-4-5-full` |
| v4-curated | `nai-diffusion-4-curated-preview` |
| v4-full | `nai-diffusion-4-full` |
| v3 | `nai-diffusion-3` |
| furry | `nai-diffusion-furry-3` |

## 工作流程

### 每轮自动流程

```
用户输入 → AI 写叙事
  → AI 回扫正文 → 提取视觉标签 → 输出 [img: ...]
  → 自动保存到 saves/{card}/rp-log.txt
  → 自动更新 saves/{card}/session-state.md
```

### 生图流程

```
用户: /img 生成
  → 从 saves/{card}/rp-log.txt 提取 [img: ...]
  → 调用 NovelAI API (默认 V4.5 Curated)
  → 图片保存到 generated/{card}/
```

### 多卡片切换

```
/play card-a    → 玩 A 卡 (自动保存/恢复)
/play card-b    → 切换到 B 卡 (A 卡状态保留)
/play card-a    → 回到 A 卡，从上次断点完美恢复
```

每张卡独立的 `saves/{card}/` 目录，包含各自的聊天记录、会话状态和记忆文件。

## 常见问题

**Q: 怎么添加自己的角色卡？**
A: 将 JSON 文件放入 `角色卡/` 目录，然后 `/play 你的卡名`。

**Q: 生图提示 "未设置 NOVELAI_API_KEY"**
A: 检查 `.env` 文件是否存在且内容为 `NOVELAI_API_KEY=你的密钥`。

**Q: 换卡片时旧卡进度会丢吗？**
A: 不会。每次 `/play` 或 `/switch` 会自动保存旧卡状态。

**Q: /img 生成后长时间没反应？**
A: NAI V4.5 生成约 60-120 秒，超时 3 分钟会报错，重试即可。

## 许可证

MIT

---

完整命令参考、游玩指南和 FAQ 见 `命令速查表.md`。
