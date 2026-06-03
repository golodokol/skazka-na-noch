# Start @skazkadobrolavka_bot
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = @(
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "python"
) | Where-Object { $_ -eq "python" -or (Test-Path $_) } | Select-Object -First 1

if (-not $python) {
    Write-Host "Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host ".env missing. Copy from .env.example and add TELEGRAM_BOT_TOKEN" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating venv..."
    & $python -m venv .venv
}

Write-Host "Installing dependencies..."
.\.venv\Scripts\pip.exe install -q -r bot\requirements.txt

Write-Host "Bot starting. Stop with Ctrl+C"
.\.venv\Scripts\python.exe bot\main.py
