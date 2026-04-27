---
description: 退出 RP 模式 — 停止 Web 前端服务器
agent: primary
---

退出 RP 模式。项目路径: `C:\Users\hu\Desktop\opencode SillyTavern`

用 Bash 执行:

```
$pidFile = "C:\Users\hu\Desktop\opencode SillyTavern\web-frontend\server.pid"
if (Test-Path $pidFile) { $pid = Get-Content $pidFile; taskkill /F /PID $pid 2>$null; Remove-Item $pidFile; Write-Output "RP 模式已退出" } else { Write-Output "server 未运行" }
```

确认后告知用户 RP 模式已退出，可继续编辑角色卡/世界书。
