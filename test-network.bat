@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    ".venv\Scripts\pip.exe" install -q -r bot\requirements.txt
) else (
    ".venv\Scripts\pip.exe" install -q aiohttp-socks 2>nul
)
".venv\Scripts\python.exe" bot\test_network.py
pause
