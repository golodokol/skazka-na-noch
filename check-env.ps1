# Check .env and Telegram API
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Write-Host "FAIL: .env not found" -ForegroundColor Red
    exit 1
}

$lines = Get-Content ".env" -Encoding UTF8 | Where-Object { $_ -match '^\s*[^#]' }
$bad = $lines | Where-Object { $_ -notmatch '^\s*[A-Za-z_][A-Za-z0-9_]*\s*=' }
if ($bad) {
    Write-Host "WARN: invalid lines (use KEY=value):" -ForegroundColor Yellow
    $bad | ForEach-Object { Write-Host "  $_" }
}

$dup = ($lines | Where-Object { $_ -match '^\s*TELEGRAM_BOT_TOKEN\s*=' }).Count
if ($dup -gt 1) {
    Write-Host "FAIL: TELEGRAM_BOT_TOKEN duplicated in .env" -ForegroundColor Red
    exit 1
}

Write-Host "Checking token via Python..."
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
.\.venv\Scripts\pip.exe install -q aiohttp-socks 2>$null
.\.venv\Scripts\python.exe bot\check_connection.py
