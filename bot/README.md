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
С ключом OpenAI — генерация по `prompts/system_ru.txt` (версия `PROMPT_VERSION`, по умолчанию **v2**).

## Тесты промпта

```powershell
.\.venv\Scripts\python.exe bot\tests\run_all.py
```

Отдельный модуль: `bot\tests\test_story_generator.py` и др.  
QA-матрица и раскатка: [STORY_QA_RELEASE.md](../docs/STORY_QA_RELEASE.md).

## Переменные .env (генерация)

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | LLM; без ключа — fallback |
| `OPENAI_MODEL_DRAFT` / `_POLISH` / `_MEDIUM` | модели по этапам |
| `ENABLE_REWRITE_PASS` | polish-pass при нарушениях (1/0) |
| `MAX_DRAFT_RETRIES` | retry черновика (по умолчанию 1) |
| `GENERATION_STATUS_WAIT_SEC` | «ещё пишу…» через N сек (30) |
| `ENABLE_REWRITE_PASS_ALL` | polish для tired/screen_free |
| `AB_TEST_ENABLED` | A/B polish по user_id |
| `PROMPT_VERSION` | v2 (текущий промпт) |

Полный список — в [`.env.example`](../.env.example).

## Структура

- `main.py` — точка входа, polling
- `handlers.py` — /start, меню, профиль, сказки, feedback
- `story_generator.py` — LLM + polish + fallback
- `story_safety.py` — post-check
- `story_feedback_hints.py` — hint из отзыва родителя
- `prompts/` — system, polish, few-shot
- `tests/` — автотесты промпта
- `db.py` — SQLite, профили, `story_generation_log`

## Структура (план)

См. [TECH_ARCHITECTURE.md](../docs/TECH_ARCHITECTURE.md) §10.
