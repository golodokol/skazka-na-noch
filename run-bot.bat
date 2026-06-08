@echo off
cd /d "%~dp0"

if not exist ".env" (
    echo .env missing. Add TELEGRAM_BOT_TOKEN
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating venv...
    python -m venv .venv
)

echo Installing dependencies...
".venv\Scripts\pip.exe" install -q -r bot\requirements.txt

echo Bot starting. Stop with Ctrl+C
".venv\Scripts\python.exe" bot\main.py
pause
