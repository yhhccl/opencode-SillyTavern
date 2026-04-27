# OpenCode RP — 项目规格文档

> 文档类型：开发规划 / 内部规格
>
> 适用对象：主要给开发者、维护者使用。
>
> 普通使用者可以跳过这份文档，不影响安装、启动、聊天、角色卡编辑和世界书使用。

## 1. 架构总览

```
浏览器 (微信风格 SPA)
  ↕ HTTP :8765 (JSON API)
server.py (ThreadingHTTPServer + poller后台线程)
  ↕ 文件 IPC (web-input.txt / .pending / web-needs-reply / web-response.txt)
OpenCode AI (/loop 检测+生成)
  ↕ CLI 调用
scripts/novelai-generate.py → NovelAI API → generated/{card}/
```

**数据流闭环:**
```
用户输入 → POST /api/submit {"text":"你好"}
  → server 写 web-input.txt + .pending
  → poller 线程检测 → 转 web-needs-reply 信号
  → OpenCode /loop 检测信号 → 读输入 → 生成叙事+[img:...] → 写 web-response.txt
  → poller 检测 → handler.py 追加 chat_log.json → 重建 content.js
  → 浏览器 1.5s 轮询 /api/content → DOM 刷新
```

---

## 2. 已完成功能

**Web 前端 (index.html)**
- 微信风格聊天气泡：用户右绿泡、AI 左白泡
- 头像圆圈：用户"我"绿底、AI 首字"A"灰底
- 每轮 AI 回复底部 `[img:...]` 渲染为 "🎨 生成插图"按钮
- 发送后 `#status-bar` 闪动 "AI 思考中..."
- 1.5s 高频轮询 /api/content，变化后自动渲染
- 亮/暗主题切换（CSS 变量 `data-theme`）
- 设置侧栏（文风/NSFW/字数，POST 保存到 settings.json）
- 已生成图片展示在气泡底部，刷新不丢

**后端服务器 (server.py)**
- ThreadingHTTPServer，端口 8765
- 7 个 REST API 端点全部可用
- 后台轮询线程：.pending → web-needs-reply → 等 web-response.txt → handler → 清除
- `/api/image-gen` 调用 novelai-generate.py 生图
- `/api/image?path=...` 提供图片文件

**聊天管理 (handler.py)**
- `chat_log.json` 持久化（`{"role":"user/assistant","content":"..."}`）
- `build_content_js()` 输出 WeChat HTML + 头像 + 生图按钮 + 已生成图片
- `img_generated.json` 映射持久化
- re-roll 支持

**AI 自动轮询**
- /loop 检测 web-needs-reply → 生成 → 写 web-response.txt

**NovelAI 生图**
- 支持 V4.5/V4/V3 全系列
- `.env` 读 API Key
- extract-img.py 提取 [img:...]

**角色卡资料库**
- 每卡独立文件夹：card.json / worldbooks/ / generated/ / rp-log.txt / session-state.md / memory/

---

## 3. 需要修复/完善的功能

**P0 — 阻断性**
1. 图片生成同步阻塞（subprocess 180s，HTTP 线程卡死）→ 改异步队列
2. Windows 路径编码问题（`C:\\...\\酒馆\\...` 无法直接做 URL）
3. `.env` 自动检测 → server 启动时验证

**P1 — 体验关键**
4. 生图按钮 loading 态 + 失败重试
5. 消息时间戳
6. 图片生成队列（目前并发生图会崩）
7. /play 加载卡片时自动注入世界书

**P2 — 增强**
8. 输入框 placeholder
9. 消息长按菜单
10. 图片预览/下载

---

## 4. API 契约

| 方法 | 路径 | 请求体 | 响应 |
|------|------|--------|------|
| POST | /api/submit | `{"text":"消息"}` | `{"ok":true}` |
| GET | /api/pending | - | `{"pending":bool,"text":""}` |
| GET | /api/state | - | JS 文件 |
| GET | /api/content | - | JS 文件（含 CONTENT_HTML, TURN_OPTIONS, IMG_GENERATED） |
| GET | /api/settings | - | `{"style":"default",...}` |
| POST | /api/settings | `{"nsfw":"direct"}` | `{"ok":true}` |
| POST | /api/reroll | - | `{"ok":true,"text":"..."}` |
| POST | /api/image-gen | `{"key":"1_0","tags":"1girl,..."}` | `{"ok":true,"path":"..."}` |
| GET | /api/image | `?path=...` | image/png |

**轮询文件协议:**
```
web-input.txt     ← 用户输入
.pending          ← 有未处理输入
web-needs-reply   ← 等待 OpenCode 生成
web-response.txt  ← AI 回复 (poller 读后删除)
chat_log.json     ← `[{role, content}]` 历史
content.js        ← `var CONTENT_HTML="...";var TURN_OPTIONS=[];var IMG_GENERATED={};`
state.js          ← `var STATE={...}` 场景状态
img_generated.json← `{"1_0":"C:\\...\\nai.png"}`
settings.json     ← `{"style":"default",...}`
```

---

## 5. WeChat HTML 结构规范

**用户消息（右对齐绿色气泡）:**
```html
<div class="msg-row self">
  <div class="msg self">消息文本</div>
  <div class="avatar self">我</div>
</div>
```

**AI 消息（左对齐白色气泡）:**
```html
<div class="msg-row other">
  <div class="avatar other">A</div>
  <div class="msg other">
    回复文本...
    <div class="gen-btn" data-key="1_0" data-tags="1girl,..." onclick="genImgPrompt(this)">
      🎨 生成插图
    </div>
    <div class="gen-img-wrap" id="img-1_0"></div>
  </div>
</div>
```

**CSS 变量:**
```css
:root {--bg:#ededed;--white:#fff;--green:#95ec69;--text:#333;--muted:#999;--bar:#2e2e2e;--bar-text:#fff;--input-bg:#f7f7f7;--sep:rgba(0,0,0,.12)}
[data-theme="dark"] {--bg:#111;--white:#1e1e1e;--green:#056162;--text:#e0e0e0;--muted:#555;--bar:#1a1a1a;--bar-text:#e0e0e0;--input-bg:#262626;--sep:rgba(255,255,255,.08)}
```

---

## 6. 文件结构

```
opencode SillyTavern/
├── web-frontend/           ← 重构核心
│   ├── server.py           ← HTTP+轮询 :8765
│   ├── handler.py          ← 聊天管理+content.js
│   ├── index.html          ← 微信风格 SPA
│   ├── settings.json       ← 设置持久化
│   ├── state.js            ← 场景状态 (运行时)
│   ├── content.js          ← 渲染数据 (运行时)
│   ├── chat_log.json       ← 历史 (运行时)
│   └── img_generated.json  ← 图片映射 (运行时)
├── scripts/
│   ├── novelai-generate.py ← NAI 生图
│   └── extract-img.py      ← [img:...] 提取
├── roles/
│   └── example-card/
│       ├── card.json       ← 角色卡
│       ├── worldbooks/     ← 世界书
│       ├── generated/      ← 图片输出
│       └── memory/         ← 跨会话记忆
├── CLAUDE.md               ← AI引擎配置
├── skills/                 ← 文风+生图规则
└── .env / .env.example     ← API Key
```
