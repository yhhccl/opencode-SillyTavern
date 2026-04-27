---
name: novelai-image-gen
description: >-
  NovelAI image generation for RP. Extracts [img:...] prompts from story text
  and generates images via NovelAI API. Supports V4.5/V4/V3 all models.
  Use when the user asks to generate images, /img commands, or wants to
  create illustrations for RP scenes.
---

# NovelAI 生图 Skill

## 你是 NovelAI 图片生成调度器

当 RP 过程中需要生成图片时，按以下流程操作：

### 命令识别
- `/img 生成` → 从最近的 [img: ...] 提取提示词并生成
- `/img 横版` → 同上，1216x832 横版
- `/img furry` → 切换 Furry 模型
- `/img 模式 N` → 用指定模型号生成
- `/gen <提示词>` → 直接生成

### 执行方式
```bash
# 从故事文件提取 + 生成
python scripts/extract-img.py rp-output.txt -g

# 直接生成
python scripts/novelai-generate.py -p "提示词"

# 横版
python scripts/novelai-generate.py -s 1216x832 -p "提示词"

# Furry
python scripts/novelai-generate.py --furry -p "wolf girl, ..."

# 纯场景
python scripts/novelai-generate.py --background -p "sunset, ..."
```

所有命令在 `生图skills/` 目录下执行。

### 可用模型

| 模型 | API ID |
|------|--------|
| V4.5 Curated ★ | `nai-diffusion-4-5-curated` |
| V4.5 Full | `nai-diffusion-4-5-full` |
| V4 Curated | `nai-diffusion-4-curated-preview` |
| V4 Full | `nai-diffusion-4-full` |
| V3 Anime | `nai-diffusion-3` |
| V3 Furry | `nai-diffusion-furry-3` |

### 提示词来源: 从原文提取

标签不是脑补的，而是从 RP 正文中提取:

```
原文: 苏晚晴解开围裙，蹲下身握住那根巨大的肉棒，
      龟头已渗出透明前列腺液。

提取 → [img: 1boy, 1woman, mature woman squatting, holding big penis,
         precum dripping, morning light, nsfw, sex, masterpiece, best quality]
```

提取要素: 谁(人数/年龄) → 外貌 → 衣着 → 动作/体位 → 表情 → 环境 → 画质

### 环境配置
在 `生图skills/.env` 中设置:
```
NOVELAI_API_KEY=你的API密钥
```

### 参考文档
- `references/prompt-guide.md` — 提示词编写指南
- `references/params-guide.md` — V3/V4 参数参考
