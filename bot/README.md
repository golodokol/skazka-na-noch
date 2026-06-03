# Код бота (MVP)

Здесь будет реализация Telegram-бота. Документация — в [`../docs/`](../docs/).

## Следующие шаги разработки

1. `pip install aiogram openai sqlalchemy python-dotenv`
2. Реализовать handlers по [BOT_FLOWS.md](../docs/BOT_FLOWS.md)
3. Подключить промпт из [CONTENT_AND_SAFETY.md](../docs/CONTENT_AND_SAFETY.md)
4. Пройти [LAUNCH_CHECKLIST.md](../docs/LAUNCH_CHECKLIST.md)

## Минимальный запуск (после реализации)

```bash
cd bot
cp ../.env.example ../.env
# заполнить TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
python main.py
```

## Структура (план)

См. [TECH_ARCHITECTURE.md](../docs/TECH_ARCHITECTURE.md) §10.
