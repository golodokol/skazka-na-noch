# Код бота (MVP)

Telegram: [@skazkadobrolavka_bot](https://t.me/skazkadobrolavka_bot)

Документация — в [`../docs/`](../docs/), настройка BotFather — [BOTFATHER_SETUP.md](../docs/BOTFATHER_SETUP.md).

## Запуск локально

```powershell
cd $env:USERPROFILE\Documents\skazka-na-noch
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r bot\requirements.txt

# Токен только в ../.env (не коммитить!)
python bot\main.py
```

Без `OPENAI_API_KEY` бот выдаёт **запасные сказки** из `fallback_stories.py`.  
С ключом OpenAI — генерация по `prompts/system_ru.txt`.

## Структура

- `main.py` — точка входа, polling
- `handlers.py` — /start, меню, профиль, сказки
- `story_generator.py` — LLM + fallback
- `db.py` — SQLite, профили и учёт сказок (без лимита)

## Структура (план)

См. [TECH_ARCHITECTURE.md](../docs/TECH_ARCHITECTURE.md) §10.
