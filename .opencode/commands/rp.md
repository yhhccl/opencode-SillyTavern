---
description: 进入 RP 模式 — 启动 Web 前端 + TUI 注入 (无需 /loop)
agent: primary
---

进入 RP 模式。项目路径: `C:\Users\hu\Desktop\opencode SillyTavern`

用 Bash 执行以下步骤:

1. 先检查 opencode TUI 是否在端口 4096 运行:
   `Invoke-WebRequest -Uri http://127.0.0.1:4096/global/health -UseBasicParsing -TimeoutSec 3`
   如失败则提示用户需在终端执行 `opencode --port 4096`

2. 清理旧的 server 进程和缓存:
```
$prj = "C:\Users\hu\Desktop\opencode SillyTavern\web-frontend"; $pidFile = "$prj\server.pid"; if (Test-Path $pidFile) { $oldPid = Get-Content $pidFile; taskkill /F /PID $oldPid 2>$null }; Remove-Item "$prj\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item $pidFile, "$prj\.pending", "$prj\web-needs-reply", "$prj\web-response.txt" -ErrorAction SilentlyContinue
```

3. 启动 server.py:
```
Start-Process python -ArgumentList "C:\Users\hu\Desktop\opencode SillyTavern\web-frontend\server.py" -WorkingDirectory "C:\Users\hu\Desktop\opencode SillyTavern" -WindowStyle Normal; Start-Sleep 4; if (Test-Path "C:\Users\hu\Desktop\opencode SillyTavern\web-frontend\server.pid") { Write-Output "PID: $(Get-Content C:\Users\hu\Desktop\opencode SillyTavern\web-frontend\server.pid)" } else { Write-Output "启动失败" }
```

4. 确认成功后告诉用户: RP 模式已启动，浏览器 http://localhost:8765，输入 退出RP 停止。
