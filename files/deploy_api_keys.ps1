# RainGod API Key Deployment — Part 2
# Run AFTER collecting all 8 keys from signup pages.
# Sets all keys in User scope (reboot-safe, no admin required).
#
# Part 1 (open all signup tabs):
#   $urls = @{
#     "Comfy Cloud"  = "https://comfy.org"
#     "Groq"         = "https://console.groq.com"
#     "Google AI"    = "https://aistudio.google.com"
#     "Suno"         = "https://suno.com"
#     "OpenRouter"   = "https://openrouter.ai"
#     "HuggingFace"  = "https://huggingface.co/settings/tokens"
#     "Replicate"    = "https://replicate.com"
#     "Kaggle"       = "https://kaggle.com/settings"
#   }
#   foreach ($s in $urls.GetEnumerator()) { Start-Process $s.Value; Start-Sleep 2 }

Write-Host "`n🔑 RAINGOD API Key Deployment" -ForegroundColor Cyan
Write-Host "Paste each key when prompted. Press Enter to skip." -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────────`n"

$keys = @{
    "COMFY_API_KEY"      = "Comfy Cloud  (https://comfy.org)"
    "GROQ_API_KEY"       = "Groq         (https://console.groq.com)"
    "GEMINI_API_KEY"     = "Google AI    (https://aistudio.google.com)"
    "SUNO_API_KEY"       = "Suno         (https://suno.com)"
    "OPENROUTER_API_KEY" = "OpenRouter   (https://openrouter.ai)"
    "HF_TOKEN"           = "HuggingFace  (https://huggingface.co/settings/tokens)"
    "REPLICATE_API_KEY"  = "Replicate    (https://replicate.com)"
    "KAGGLE_USERNAME"    = "Kaggle username"
    "KAGGLE_KEY"         = "Kaggle API key (kaggle.com/settings)"
}

$deployed = 0
$skipped  = 0

foreach ($entry in $keys.GetEnumerator()) {
    $varName = $entry.Key
    $label   = $entry.Value

    # Check if already set
    $existing = [Environment]::GetEnvironmentVariable($varName, "User")
    if ($existing) {
        $masked = $existing.Substring(0, [Math]::Min(6, $existing.Length)) + "..."
        Write-Host "  [$varName] already set ($masked) — skip? (y/n) " -NoNewline -ForegroundColor Yellow
        $choice = Read-Host
        if ($choice -ne "n") { $skipped++; continue }
    }

    Write-Host "  $label" -ForegroundColor White
    Write-Host "  $varName = " -NoNewline -ForegroundColor Gray
    $value = Read-Host

    if ($value.Trim() -eq "") {
        Write-Host "  ⏭  Skipped" -ForegroundColor DarkGray
        $skipped++
    } else {
        [Environment]::SetEnvironmentVariable($varName, $value.Trim(), "User")
        Write-Host "  ✅ Deployed" -ForegroundColor Green
        $deployed++
    }
    Write-Host ""
}

Write-Host "─────────────────────────────────────────────────"
Write-Host "✅ Deployed: $deployed   ⏭  Skipped: $skipped" -ForegroundColor Cyan
Write-Host ""

# Validation pass
Write-Host "🔍 Validation:" -ForegroundColor Cyan
$required = @("COMFY_API_KEY","GROQ_API_KEY","GEMINI_API_KEY","SUNO_API_KEY","OPENROUTER_API_KEY","HF_TOKEN")
foreach ($k in $required) {
    $v = [Environment]::GetEnvironmentVariable($k, "User")
    if ($v) {
        $masked = $v.Substring(0, [Math]::Min(8, $v.Length)) + "..."
        Write-Host "  ✅ $k = $masked" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $k = NOT SET" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "⚠️  Restart your terminal or IDE to pick up new env vars." -ForegroundColor Yellow
Write-Host "Then run: python scripts/validate_keys.py" -ForegroundColor Cyan
