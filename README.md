# Сказка на ночь

**Репозиторий:** https://github.com/golodokol/skazka-na-noch

Telegram-бот — **вечерний co-pilot для уставших родителей**: персональная сонная сказка за 30 секунд без когнитивной нагрузки, с сохранением тёплого контакта с ребёнком.

## Статус проекта

| Этап | Статус |
|------|--------|
| Продуктовое исследование (JTBD, интервью) | ✅ Завершено |
| Документация для запуска | ✅ Этот репозиторий |
| Разработка MVP-бота | 🔲 Следующий шаг |
| Пилот (20–50 семей) | 🔲 |

## Ключевое в одном абзаце

Родители платят не за «ещё одну библиотеку сказок», а за **ритуал без усилий** в 21:00–22:00. Бот в Telegram даёт готовую персональную историю быстрее, чем YouTube, в формате «прочитай сам» или «аудио, экран вниз» — без замены мамы/папы.

## Документация

| Документ | Назначение |
|----------|------------|
| [docs/PRODUCT_CARD.md](docs/PRODUCT_CARD.md) | **Карточка продукта** — выводы, ЦА, killer feature, value moment |
| [docs/PRD.md](docs/PRD.md) | Product Requirements Document |
| [docs/MVP_SPEC.md](docs/MVP_SPEC.md) | Спецификация MVP (функции, scope, фазы) |
| [docs/BOT_FLOWS.md](docs/BOT_FLOWS.md) | Сценарии, команды, клавиатуры |
| [docs/TECH_ARCHITECTURE.md](docs/TECH_ARCHITECTURE.md) | Архитектура: LLM, RAG, safety, инфра |
| [docs/CONTENT_AND_SAFETY.md](docs/CONTENT_AND_SAFETY.md) | Промпты, sleep-onset, модерация |
| [docs/MONETIZATION.md](docs/MONETIZATION.md) | Тарифы, платежи, метрики выручки |
| [docs/METRICS.md](docs/METRICS.md) | KPI, гипотезы, аналитика |
| [docs/GTM.md](docs/GTM.md) | Go-to-market, каналы, копирайт |
| [docs/LEGAL_AND_PRIVACY.md](docs/LEGAL_AND_PRIVACY.md) | Персональные данные, возраст, оферта |
| [docs/LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md) | Чеклист запуска в Telegram |
| [research/product-research-full.md](research/product-research-full.md) | Полный исследовательский свод |

## Быстрый старт (разработка)

1. Создать бота через [@BotFather](https://t.me/BotFather), сохранить токен.
2. Скопировать `.env.example` → `.env`, заполнить переменные.
3. Реализовать сценарии из `docs/BOT_FLOWS.md` и промпты из `docs/CONTENT_AND_SAFETY.md`.
4. Пройти [docs/LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md) перед публичным релизом.

## Структура репозитория

```
skazka-na-noch/
├── README.md
├── .env.example
├── docs/                 # Продуктовая и запускная документация
├── research/             # Исследования
└── bot/                  # Код бота (MVP — на этапе разработки)
```

## Контакты и версия

- Версия документации: **1.0** (июнь 2026)
- Источники: JTBD-отчёт, 10 бизнес-идей (P1), 2 проблемных интервью, desk research
