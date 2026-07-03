# 本机开发一键启动:后端(FastAPI)+ 前端(Vite,局域网可访问)
# 用法:在项目根目录 PowerShell 里运行  ./start-dev.ps1
# iPhone 同一 WiFi 下访问前端网络地址即可(启动后 Vite 会打印 Network: http://192.168.x.x:5173)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"

Write-Host "启动后端 http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process $py -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port","8000" `
    -WorkingDirectory (Join-Path $root "backend")

Start-Sleep -Seconds 3
Write-Host "启动前端 http://localhost:5173(局域网地址见下方 Network) ..." -ForegroundColor Cyan
Set-Location (Join-Path $root "frontend")
npm run dev
