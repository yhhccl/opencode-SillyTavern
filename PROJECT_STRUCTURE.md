# 项目文件结构

本文档用于 GitHub 发布前快速说明仓库结构、源码边界和运行时文件边界。

## 建议阅读顺序

如果你只是想使用项目，优先看这些：

1. `README-zh.md`
2. `使用教程.md`
3. `角色卡/example-card/`

下面这些文档属于开发或规划资料，可以按需阅读：

- `PROJECT_SPEC.md`：项目规格与开发规划
- `前端角色卡世界书改造执行方案.md`：前端改造方案与阶段任务
- `OpenCode RP — 游玩指南 & 命令速查表.md`：更细的命令参考

```text
opencode SillyTavern/
├── README.md                         # 英文说明
├── README-zh.md                      # 中文说明
├── PROJECT_SPEC.md                   # 项目规格与阶段目标
├── PROJECT_STRUCTURE.md              # 本文件: GitHub 发布结构说明
├── AGENTS.md                         # OpenCode/Codex 使用规则
├── CLAUDE.md                         # Claude Code 使用规则
├── .env.example                      # 根目录环境变量示例
├── .gitignore                        # GitHub 发布忽略规则
├── OpenCode RP — 游玩指南 & 命令速查表.md
├── OpenCode rp jc.txt
├── novelai API 参考.txt
├── 扮演指导 README .md
├── 文生图世界书 (1).json
│
├── web-frontend/                     # Web 聊天前端与本地桥接服务
│   ├── index.html                    # 移动端聊天 UI、角色卡/世界书编辑面板
│   ├── server.py                     # HTTP API、自动轮询、异步生图队列
│   ├── handler.py                    # 聊天日志与 content.js 渲染器
│   ├── card_store.py                 # 角色卡与世界书读写
│   └── airp_context.py               # AIRP 上下文接入
│
├── airp-sillytavern/                 # AIRP 上下文运行层
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   ├── references/
│   │   └── sillytavern-structure.md
│   ├── runtime/
│   │   ├── __main__.py
│   │   ├── commands.py
│   │   ├── context_builder.py
│   │   ├── engine.py
│   │   ├── loader.py
│   │   ├── macros.py
│   │   ├── state.py
│   │   ├── tokenizer.py
│   │   └── worldinfo.py
│   ├── schemas/
│   │   └── state.schema.json
│   └── templates/
│       ├── character-card-v2.json
│       ├── default-preset.json
│       ├── persona.json
│       └── worldbook.json
│
├── scripts/                          # 根目录通用脚本
│   ├── extract-img.py                # 从 RP 日志提取 [img: ...] 标签
│   └── novelai-generate.py           # NovelAI 生图调用脚本
│
├── skills/                           # OpenCode RP 技能与文风
│   ├── image-gen.md
│   ├── novelai-gen.md
│   └── styles/
│       ├── default.md
│       ├── mode-a.md
│       └── mode-b.md
│
├── 生图skills/                       # 独立 NovelAI 生图 skill 包
│   ├── SKILL.md
│   ├── .env.example
│   ├── references/
│   │   ├── params-guide.md
│   │   └── prompt-guide.md
│   └── scripts/
│       ├── extract-img.py
│       └── novelai-generate.py
│
├── 世界书Skills/                     # 世界书管理 skill 包
│   ├── README.md
│   ├── SKILL.md
│   └── world-book-skill/
│       ├── SKILL.md
│       ├── agents/
│       │   └── openai.yaml
│       ├── references/
│       │   ├── entry-conventions.md
│       │   └── position-guide.md
│       └── scripts/
│           └── world-book-create.py
│
├── 角色卡/                           # 角色卡目录
│   └── example-card/                 # GitHub 示例卡
│       ├── card.json                 # 示例角色卡
│       └── worldbooks/
│           └── main.json             # 示例世界书
│
├── memory/
│   └── reference.md                  # 全局参考记忆
│
└── 预设/                             # 提示词/模型预设示例
    ├── Izumi 0407 (1)_优化版 测试.json
    ├── 【DarkSide-Cacher】v1.0.json
    ├── 双人成行 V4.5不测试会不会炸呢？.json
    └── 梦境思客V2-0427.json
```

## 不建议发布到 GitHub 的文件

这些文件已经在 `.gitignore` 中排除，属于本地运行状态、聊天记录、生成图片或密钥:

```text
.env
generated/
state.js
current-card.txt
web-frontend/chat_log.json
web-frontend/content.js
web-frontend/context-inspect.json
web-frontend/image_jobs.json
web-frontend/img_generated.json
web-frontend/settings.json
web-frontend/state.js
web-frontend/server-*.log
web-frontend/web-input.txt
web-frontend/web-response.txt
web-frontend/web-needs-reply
web-frontend/.pending
角色卡/*/airp-session/
角色卡/*/memory/
角色卡/*/generated/
角色卡/*/rp-log.txt
角色卡/*/session-state.md
```

## GitHub 发布建议

1. 确认 `.env` 没有被加入 Git。
2. 提交 `角色卡/example-card/card.json` 和 `角色卡/example-card/worldbooks/main.json` 作为示例，其他用户私有角色卡不要提交。
3. `web-frontend/` 只提交源码文件，不提交运行中生成的 `content.js`、`chat_log.json`、`image_jobs.json` 等文件。
4. 如果从旧结构迁移，删除索引中的旧文件 `角色卡/example-card.json`，改为提交新的目录结构 `角色卡/example-card/`。
5. 发布前运行:

```powershell
python -m py_compile web-frontend\server.py web-frontend\handler.py web-frontend\card_store.py web-frontend\airp_context.py
git status --short
```
