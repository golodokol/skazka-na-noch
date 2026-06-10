# Ключ из буфера обмена → .env.local (после копирования с platform.openai.com)
$clip = (Get-Clipboard -Raw).Trim()
$root = Split-Path $PSScriptRoot -Parent
$path = Join-Path $root ".env.local"

if ($clip -match '^sk-[A-Za-z0-9_-]{20,}') {
    @"
# OpenAI (не коммитить)
OPENAI_API_KEY=$clip
"@ | Set-Content -Path $path -Encoding utf8
    Write-Host "OK: OPENAI_API_KEY zapisан v .env.local"
} else {
    Write-Host "V bufere net klyucha sk-... Skopiruyte s https://platform.openai.com/api-keys"
    exit 1
}
