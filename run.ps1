# StockSense AI Retail Intelligence Platform - Master Runner
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  StockSense - AI-Powered Retail Inventory Intelligence   " -ForegroundColor Yellow
Write-Host "  QUANTIX 2K26 Hackathon | PS11 Reorder Planner           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# 1. Check Python Venv
$PythonExe = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[*] Virtual environment not found at $PythonExe. Using system python..." -ForegroundColor Yellow
    $PythonExe = "python"
}

# 2. Check and start Backend (Port 5000)
$BackendPort = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if (-not $BackendPort) {
    Write-Host "[+] Launching Flask API Backend on http://127.0.0.1:5000..." -ForegroundColor Green
    Start-Process -FilePath $PythonExe -ArgumentList "backend/app.py" -WorkingDirectory $Root -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[OK] Flask Backend already active on Port 5000." -ForegroundColor Green
}

# 3. Check and start Frontend (Port 5173)
$FrontendPort = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if (-not $FrontendPort) {
    Write-Host "[+] Launching Vite Frontend on http://127.0.0.1:5173..." -ForegroundColor Green
    $FrontendDir = Join-Path $Root "frontend"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --host 127.0.0.1 --port 5173" -WorkingDirectory $FrontendDir -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "[OK] Vite Frontend already active on Port 5173." -ForegroundColor Green
}

# 4. Verify API Health
try {
    $Health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 5
    Write-Host "[OK] Backend Health: $($Health.status) - $($Health.service)" -ForegroundColor Green
} catch {
    Write-Host "[*] Backend initializing..." -ForegroundColor Yellow
}

# 5. Open in Chrome
Write-Host "[+] Opening StockSense in Google Chrome..." -ForegroundColor Cyan
try {
    Start-Process "chrome.exe" -ArgumentList "--new-window http://127.0.0.1:5173/"
} catch {
    Start-Process "http://127.0.0.1:5173/"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  StockSense is running live at http://127.0.0.1:5173/    " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
