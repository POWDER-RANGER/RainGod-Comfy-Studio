# ==============================================================
# start_all.ps1 — RainGod Studio One-Click Boot
# Launches: Ollama + FastAPI backend + opens browser
# ==============================================================

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

Write-Host ""
Write-Host "  🌧️  RAINGOD STUDIO — STARTING UP" -ForegroundColor Magenta
Write-Host ""

# Step 1: Verify Ollama is installed
Write-Host "  [1/3] Checking Ollama..." -ForegroundColor Yellow
$ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCheck) {
    Write-Host "  ❌ Ollama not found. Install from https://ollama.com" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ Ollama found" -ForegroundColor Green

# Step 2: Start Ollama serve in background
Write-Host "  [2/3] Starting Ollama service..." -ForegroundColor Yellow
$ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($ollamaProc) {
    Write-Host "  ✅ Ollama already running (PID $($ollamaProc.Id))" -ForegroundColor Green
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "ollama serve" -WindowStyle Minimized
    Start-Sleep -Seconds 2
    Write-Host "  ✅ Ollama serve launched (minimized)" -ForegroundColor Green
}

# Step 3: Start FastAPI backend
Write-Host "  [3/3] Starting RainGod backend on http://localhost:8000 ..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Press Ctrl+C to stop the server" -ForegroundColor DarkGray
Write-Host "  Studio UI: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:  http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "  Health:    http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "  ─────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# Open browser after short delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 4
    Start-Process "http://localhost:8000"
} | Out-Null

# Launch uvicorn (blocking — stays in this terminal)
uvicorn backend.main:app --reload --port 8000
