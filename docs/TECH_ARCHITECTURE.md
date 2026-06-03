# Техническая архитектура

**Версия:** 1.0 · MVP

---

## 1. Обзор

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Telegram   │────▶│  Bot API     │────▶│  App Server │
│  Client     │◀────│  (webhook/   │◀────│  (Python)   │
└─────────────┘     │   polling)   │     └──────┬──────┘
                    └──────────────┘            │
                    ┌──────────────┐     ┌──────▼──────┐
                    │  TTS (P1)    │◀────│  LLM API    │
                    └──────────────┘     └──────┬──────┘
                    ┌──────────────┐     ┌──────▼──────┐
                    │  PostgreSQL  │◀────│  Safety     │
                    │  / SQLite    │     │  Filter     │
                    └──────────────┘     └──────┬──────┘
                                         ┌──────▼──────┐ (P1)
                                         │  RAG Index  │
                                         │  (Gutenberg)│
                                         └─────────────┘
```

---

## 2. Компоненты

| Компонент | Назначение | MVP |
|-----------|------------|-----|
| **Bot handler** | Команды, кнопки, FSM | P0 |
| **Story service** | Сборка промпта, вызов LLM | P0 |
| **Profile store** | Профиль ребёнка, лимиты | P0 |
| **Safety service** | Pre/post модерация | P0 |
| **Analytics** | События, retention | P0 (минимум) |
| **Payment** | Stars / Prodamus webhook | P1 |
| **TTS** | Аудио MP3/OGG | P1 |
| **RAG** | Мотивы public domain | P1 |

---

## 3. Стек (рекомендация)

| Слой | Выбор | Альтернатива |
|------|-------|--------------|
| Runtime | Python 3.11 | Node 20 + grammY |
| Bot framework | aiogram 3.x | python-telegram-bot |
| DB | SQLite → PostgreSQL | Supabase |
| Cache / rate limit | Redis (опционально) | in-memory |
| LLM | GPT-4.1 mini / Claude Haiku | GigaChat Pro (RU compliance) |
| TTS | OpenAI TTS / Yandex SpeechKit | ElevenLabs |
| Hosting | Fly.io / Railway / VPS | Yandex Cloud |
| Secrets | `.env` + platform secrets | |

---

## 4. LLM pipeline

```
1. Input: mode + profile + day_context + rescue_template?
2. Build system prompt (CONTENT_AND_SAFETY.md)
3. Fast model → draft story
4. Safety post-check → if fail, regenerate once with stricter prompt
5. Truncate to max tokens by mode
6. Persist: story_id, feedback=null, latency_ms
7. Send to Telegram (chunk if needed)
```

**Параметры генерации:**

| Режим | max_tokens | temperature |
|-------|------------|-------------|
| tired | ~600 | 0.7 |
| medium | ~1200 | 0.75 |
| screen_free | ~800 | 0.7 |

---

## 5. RAG (P1)

**Источники (public domain):**

- Project Gutenberg — Grimms, Andersen
- Wikisource — русские народные сказки (проверить статус)
- Метаданные: тон, длина, «сонность», число персонажей

**Использование:** не копировать текст — retrieval **сюжетной арки** и безопасных мотивов в промпт.

**Индекс:** embeddings (text-embedding-3-small) + vector store (Chroma / pgvector).

---

## 6. Данные

### 6.1 Таблицы (минимум)

```sql
users (
  telegram_id PK,
  created_at,
  timezone,
  push_opt_in,
  subscription_until
)

child_profiles (
  id PK,
  user_id FK,
  name,
  age_years,
  favorite_hero,
  no_scary bool,
  created_at
)

stories (
  id PK,
  user_id FK,
  mode,
  day_context_hash,  -- не хранить сырой текст в логах prod
  word_count,
  feedback,
  created_at
)

usage_weekly (
  user_id,
  week_start,
  story_count
)
```

### 6.2 Приватность

- Не логировать `day_context` в plaintext на prod (хеш или обрезка)
- TTL для сырых промптов: 7 дней (настройка)

---

## 7. Telegram integration

| Режим | Когда |
|-------|-------|
| **Webhook** | Production (HTTPS, 443) |
| **Polling** | Local dev |

**Обязательно:**

- `allowed_updates`: message, callback_query
- Rate limit: 1 генерация / 30 сек на user
- File size для TTS < 50 MB (лимит TG)

---

## 8. Надёжность

| Сценарий | Поведение |
|----------|-----------|
| LLM timeout 25s | Fallback template story (кэш 10 заготовок) |
| LLM 5xx | «Через минуту попробуйте» + retry button |
| DB down | In-memory profile session (degraded) |

---

## 9. Стоимость (оценка MVP, 100 DAU)

| Статья | ~/мес |
|--------|-------|
| LLM (3 stories/user/week) | $30–80 |
| TTS (P1, 20% users) | $20–40 |
| Hosting | $10–25 |
| **Итого** | **$60–150** |

---

## 10. Структура кода (`bot/`)

```
bot/
├── main.py              # entry, webhook/polling
├── config.py            # env
├── handlers/
│   ├── start.py
│   ├── story.py
│   └── profile.py
├── services/
│   ├── story_generator.py
│   ├── safety.py
│   └── limits.py
├── db/
│   └── models.py
└── prompts/
    └── system_ru.txt
```

См. [bot/README.md](../bot/README.md).
