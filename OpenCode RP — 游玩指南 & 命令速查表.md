# OpenCode RP — 游玩指南 & 命令速查表

## 游玩指南

### 首次准备 (仅一次)

1. 检查 `.env`: 确保 `NOVELAI_API_KEY=你的密钥` 已填写
2. 检查 Python: `python --version` 确认 3.8+
3. 放卡片: 将角色 JSON 放入 `角色卡/` 目录

### 启动角色卡

```
OpenCode 中输入:
  /play 巨根症

AI 自动:
  1. 更新 current-card.txt
  2. 读取角色卡 JSON
  3. 创建 saves/巨根症/ 存档目录 (首次)
  4. 发送开场叙事 (first_mes)
```

#### 新窗口启动完整步骤

```
1. 打开 OpenCode, cd 到酒馆目录
2. /effort max        ← 切换到 1M 上下文模式
3. /play 巨根症        ← AI 自动加载存档 + 角色卡
4. 直接开始扮演
```

### 日常扮演 (每轮全自动)

```
你输入: 角色动作/对话

AI 自动:
  1. 写叙事回复 (按 CLAUDE.md 规则)
  2. 回扫正文 → 提取 [img: ...] 标签
  3. Write 追加到 saves/{card}/rp-log.txt
  4. Write 更新 saves/{card}/session-state.md
  5. Write 更新 saves/{card}/memory/project.md

你只负责扮演，无需手动操作任何存档。
```

### 生图示例

AI 在叙事末尾自动输出标签:
```
[img: 1girl, black hair, school uniform, classroom, masterpiece, best quality]
```

触发生图 (用户主动):
```
/img 生成     → 生成最新一张 (约 60-120s, 图片 ~500KB)
/img 全部     → 生成本次会话所有待生标签
/img 横版     → 横版 1216x832
/img furry    → 毛毛风格
```

查看生成图片: 打开 `generated/{card}/` 目录。

### 换角色卡

```
/play 巨根症   → 换到巨根症 (自动保存旧卡, 恢复新卡存档)
/play card-b    → 换到 card-b (不存在则初始化新存档)
/cards          → 查看所有可用卡片 + 存档状态
/switch card-b  → 显式保存当前卡 + 切换
```

每张卡独立存档，切换互不干扰。明天回来 `/play 巨根症` 完美恢复。

### 恢复上次游玩 (新窗口)

```
全新 OpenCode 窗口:
  1. /effort max
  2. /play 巨根症

AI 自动:
  - Read current-card.txt → 确定角色
  - Read saves/巨根症/session-state.md → 场景全貌 (~400 token)
  - Read saves/巨根症/rp-log.txt 末 30 行 → 对话上下文 (~300 token)
  - 从 Next Direction 自然接续

总计 ~1500 token 恢复完整上下文。
```

### 常见问题

**Q: 提示 "未设置 NOVELAI_API_KEY"**
A: 检查 `.env` 文件是否存在，内容是否为 `NOVELAI_API_KEY=你的密钥`

**Q: /img 生成后长时间没反应**
A: NAI V4.5 生成约 60-120 秒。超时 3 分钟会报错，重试即可。

**Q: 角色卡改了内容但 AI 还用的旧版**
A: `/clear` 清空上下文, 重新 `/play {card}`

**Q: 存档文件 (session-state.md / rp-log.txt) 丢失了**
A: `saves/{card}/` 目录中有备份。如果全丢了，重新 `/play {card}` 从开场开始。

**Q: 切换卡片时旧卡进度会丢吗**
A: 不会。每次 `/play` 或 `/switch` 会自动 Write 保存旧卡状态。

**Q: 想把生图功能搬到别的项目**
A: 复制 `生图skills/` 整个目录到目标项目，改 `.env` 即可独立使用。

**Q: 支持多少张角色卡**
A: 无上限。每张卡独立 `saves/{card}/` 存档，互不干扰。

**Q: 怎么跳过某轮的 [img: ...] 标签输出**
A: 本系统 AI 只在"有画面感的时刻"自动输出标签，平淡对话自动跳过。如需强制跳过，说 "这轮不需要生图"。

---

## 卡片管理

| 命令 | 效果 |
|------|------|
| `/play <card>` | 启动/切换角色卡。如 `/play 巨根症` |
| `/cards` | 列出 角色卡/ 目录下所有可用卡片 + 存档状态 |
| `/switch <card>` | 保存当前进度，切换到另一张卡 |

## RP 核心命令

| 命令 | 效果 | 说明 |
|------|------|------|
| `/plan` | 计划模式 | 卡文时用，和 AI 讨论剧情方向 |
| `/clear` | 清空上下文 | 新会话开端使用 |
| `/compact` | 手动压缩上下文 | 上下文过长时手动触发 |
| `/branch <名称>` | 切分支 | 如 `/branch 巨根症`，切不同剧情线 |
| `/loop` | 循环执行 | 全自动烧 Token 模式 |
| `/resume` | 恢复上次 RP | 新窗口恢复：读 session-state.md + rp-log.txt 末段 → 接续 |
| `/save` | 手动保存状态 | 立即写入 session-state.md |
| `/effort max` | 最大推理 | 切换到 1M token 上下文 |

## 文风切换

| 命令 | 效果 |
|------|------|
| "切换模式A" | 切换到 NSFW 增强文风 |
| "切换模式B" | 切换到重口文风 |

`默认`：日系轻小说文风，自动启用。

## 生图命令

| 命令 | 效果 |
|------|------|
| `/img 生成` | 从 saves/{card}/rp-log.txt 提取最新 [img: ...] 并生成 |
| `/img 全部` | 生成 rp-log.txt 中所有未生成的标签 |
| `/img 横版` | 同上，横版 1216x832 |
| `/img furry` | 同上，使用 Furry 模型 |

## 生图脚本命令

```bash
# 提取 + 一键生成
python scripts/extract-img.py saves/{card}/rp-log.txt -g --latest-only

# 只提取不生成
python scripts/extract-img.py saves/{card}/rp-log.txt

# 直接生成
python scripts/novelai-generate.py -p "1girl, black hair, school uniform"

# 批量生成队列
python scripts/novelai-generate.py -q image-queue.txt

# 毛毛风格
python scripts/novelai-generate.py --furry -p "wolf girl, ..."

# 纯场景
python scripts/novelai-generate.py --background -p "sunset over ocean"

# 横版
python scripts/novelai-generate.py -s 1216x832 -p "prompt"

# 列出可用模型
python scripts/novelai-generate.py --list-models
```

## 生图主要参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-m` | `nai-diffusion-4-5-curated` | 模型 |
| `-s` | `832x1216` | 尺寸 (WxH) |
| `--steps` | 28 | 采样步数 |
| `--scale` | 5 | CFG Scale |
| `-o` | `generated` | 输出目录 |

## 可用模型

| 别名 | API ID |
|------|--------|
| v4.5-curated ★ | `nai-diffusion-4-5-curated` |
| v4.5-full | `nai-diffusion-4-5-full` |
| v4-curated | `nai-diffusion-4-curated-preview` |
| v4-full | `nai-diffusion-4-full` |
| v3 | `nai-diffusion-3` |
| furry | `nai-diffusion-furry-3` |

## 目录结构

```
酒馆/
├── CLAUDE.md            ← 全局 RP 引擎配置
├── current-card.txt      ← 当前激活的角色卡名
├── 角色卡/               ← 所有卡片 JSON
│   └── 巨根症患者的世界 (2).json
├── saves/                ← 每张卡独立存档
│   └── {card}/
│       ├── session-state.md
│       ├── rp-log.txt
│       ├── image-queue.txt
│       └── memory/
│           ├── project.md
│           ├── feedback.md
│           └── user.md
├── generated/            ← 图片输出 (按角色分目录)
│   └── {card}/
├── skills/               ← 文风 + 生图 Skill
├── scripts/              ← 生图脚本
└── memory/
    └── reference.md      ← 全局文件索引
```

## 多卡片工作流

```
初次使用卡片:
  /play 巨根症
  → AI 读角色卡 JSON → 初始化 saves/巨根症/ → 从 first_mes 开始

恢复卡片:
  /play 巨根症 (或 /resume)
  → Read saves/巨根症/session-state.md
  → Read saves/巨根症/rp-log.txt 末 30 行
  → 自然接续

切换卡片:
  /switch card-b
  → 保存当前卡状态 → 更新 current-card.txt → 读新卡存档

日常 RP (每轮):
  AI 写叙事 → 提取标签 → Write saves/{card}/rp-log.txt
                  → Write saves/{card}/session-state.md
```
