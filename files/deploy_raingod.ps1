# deploy_raingod.ps1
# Complete RainGod Comfy Studio deployment script
# Runs on Windows with PowerShell — sets up all keys, validates, boots the app

Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🌧️  RAIN GOD COMFY STUDIO - DEPLOYMENT AUTOMATION" -ForegroundColor Magenta
Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ========== PART 1: OPEN ALL SIGNUP PAGES ==========
Write-Host "[1/4] Opening API signup pages..." -ForegroundColor Yellow

$signup_urls = @{
    "Comfy Cloud"  = "https://comfy.org/register"
    "Groq"         = "https://console.groq.com/keys"
    "Google AI"    = "https://aistudio.google.com"
    "Suno"         = "https://suno.com/signup"
    "OpenRouter"   = "https://openrouter.ai/auth/login"
    "HuggingFace"  = "https://huggingface.co/settings/tokens"
    "Replicate"    = "https://replicate.com/api"
    "Kaggle"       = "https://kaggle.com/settings/account"
}

foreach ($service in $signup_urls.GetEnumerator()) {
    Write-Host "  → Opening $($service.Name)..." -ForegroundColor Cyan
    Start-Process $service.Value
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "✅ All 8 tabs opened. Go sign up and collect your API keys." -ForegroundColor Green
Write-Host "   You have 5 minutes to get them all..." -ForegroundColor Gray
Write-Host ""

# ========== PART 2: WAIT FOR USER TO COLLECT KEYS ==========
Write-Host "[2/4] Waiting for API key collection..." -ForegroundColor Yellow
Start-Sleep -Seconds 300

# ========== PART 3: DEPLOY KEYS TO ENVIRONMENT ==========
Write-Host ""
Write-Host "[3/4] Deploying API keys to environment..." -ForegroundColor Yellow

$api_keys = @{
    "COMFY_API_KEY"      = Read-Host "Enter Comfy Cloud API key"
    "GROQ_API_KEY"       = Read-Host "Enter Groq API key"
    "GEMINI_API_KEY"     = Read-Host "Enter Google Gemini API key"
    "SUNO_API_KEY"       = Read-Host "Enter Suno API key"
    "OPENROUTER_API_KEY" = Read-Host "Enter OpenRouter API key"
    "HF_TOKEN"           = Read-Host "Enter HuggingFace token"
    "REPLICATE_API_KEY"  = Read-Host "Enter Replicate API key"
    "KAGGLE_API_KEY"     = Read-Host "Enter Kaggle API key (optional)"
}

# Set all keys as user environment variables (persistent)
foreach ($key in $api_keys.GetEnumerator()) {
    if ($key.Value) {
        [Environment]::SetEnvironmentVariable($key.Name, $key.Value, "User")
        Write-Host "  ✅ $($key.Name) deployed" -ForegroundColor Green
    }
}

# Also set for current session
$api_keys.GetEnumerator() | ForEach-Object {
    [Environment]::SetEnvironmentVariable($_.Name, $_.Value)
}

Write-Host ""
Write-Host "✅ All API keys deployed to user environment" -ForegroundColor Green
Write-Host ""

# ========== PART 4: VALIDATE ALL KEYS ==========
Write-Host "[4/4] Validating all API keys..." -ForegroundColor Yellow
Write-Host ""

# Call the Python validator script
python .\backend\validate_keys.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "✅ RAINGOD STUDIO READY FOR LAUNCH" -ForegroundColor Magenta
    Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start the studio, run:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  cd backend" -ForegroundColor Gray
    Write-Host "  uvicorn main:app --reload --port 8000" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Then open: http://localhost:8000" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "⚠️  Some keys failed validation. Please check your credentials." -ForegroundColor Red
    Write-Host ""
}
