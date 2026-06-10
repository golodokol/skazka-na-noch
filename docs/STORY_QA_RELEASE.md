# QA и раскатка промпта v2

**Версия промпта:** `PROMPT_VERSION=v2` (фазы 1–7)  
**Цель:** проверить качество сказок перед/после выкладки и уметь откатиться.

---

## 1. Автотесты

Запуск всех модулей:

```powershell
cd $env:USERPROFILE\Documents\skazka-na-noch
.\.venv\Scripts\python.exe bot\tests\run_all.py
```

| Модуль | Что проверяет |
|--------|----------------|
| `test_story_generator.py` | сборка system/user, режимы, variety |
| `test_story_safety.py` | чёрный список, клише, verbatim today |
| `test_rewrite_pass.py` | polish-pass, accept/reject |
| `test_llm_config.py` | модели, температура, A/B |
| `test_feedback_hints.py` | bad_reason → hint |
| `test_integration.py` | smoke: все mode×age, одна метафора, feedback |

**Definition of done (авто):** `run_all.py` exit code 0, все модули зелёные.

**Definition of done (матрица):**

```powershell
# 1. Сборка промпта (без API, 24 кейса)
.\.venv\Scripts\python.exe bot\tests\run_qa_matrix.py --prompt-only

# 2. Полная генерация (нужен OPENAI_API_KEY в .env)
.\.venv\Scripts\python.exe bot\tests\run_qa_matrix.py
```

Отчёты: `docs/qa_runs/matrix_YYYY-MM-DD*.md`

---

## 2. Ручная матрица (18 кейсов)

3 возраста × 3 режима × 2 варианта героя. Режим **today** — отдельно с `day_context`.

### Базовая сетка (12 кейсов)

Профиль: `no_scary=true`. Для каждой строки — с героем («Зайчик») и без (пустой hero).

| # | Возраст | Режим | Герой | Проверить |
|---|---------|-------|-------|-----------|
| 1 | 3 | tired | да/нет | короткие фразы, 1 метафора, финал — сон |
| 2 | 3 | medium | да/нет | чуть больше деталей, без ускорения |
| 3 | 3 | screen_free | да/нет | без экранных образов |
| 4 | 5 | tired | да/нет | дуга Проппа намёком, имя 3–5 раз |
| 5 | 5 | medium | да/нет | polish (если включён), нет штампов в начале |
| 6 | 5 | screen_free | да/нет | спокойный темп |
| 7 | 7 | tired | да/нет | более сложная лексика, всё ещё сонная |
| 8 | 7 | medium | да/нет | литературность без «сказочного» пафоса |
| 9 | 7 | screen_free | да/нет | ≤4096 с footer в Telegram |

### Режим «Сегодняшний день» (6 кейсов)

`day_context` — по одному из списка; возраст 3 / 5 / 7.

| # | day_context | Проверить |
|---|-------------|-----------|
| 10 | «поссорился с другом в садике» | метафора, **нет** дословной цитаты заметки |
| 11 | «очень устал, капризничал» | батарейка/усталость, без морали |
| 12 | «боялся темноты» | при `no_scary` — только уют |

Повторить кейсы 10–12 с героем и без → **18 кейсов** суммарно с базовой сеткой (12 + 6).

### Чеклист на каждую сказку

- [ ] 7 шагов сонной дуги (хотя бы намёком)
- [ ] 1 метафора возраста, не каталог
- [ ] финал — покой, без `?` в конце
- [ ] имя ребёнка 3–5 раз (не в каждом абзаце)
- [ ] читается вслух за целевое время (`reading_min` в промпте)
- [ ] родитель: «хочу такую же завтра» или нейтрально

Записывать: дата, user_id (тестовый), mode, age, hero, оценка (👍 / 😴 / 😟), заметка.

---

## 3. Раскатка

### Перед выкладкой

1. `run_all.py` — зелёный  
2. `.env`: `PROMPT_VERSION=v2`, `ENABLE_REWRITE_PASS=1`  
3. 3–5 ручных прогонов из матрицы (tired/medium/today, возраст 3 и 5)  
4. Лог `story_generation_log` пишется (SQLite)

### Выкладка

1. Деплой кода с v2  
2. Перезапуск бота — в логе: `Prompt version: v2`  
3. Мониторинг 48 ч: fallback rate, retry_count, feedback «😟»

### A/B (опционально)

`AB_TEST_ENABLED=1` — чётный user_id = control (с polish), нечётный = без polish.  
Сравнивать долю «😴 Уснул» и «😟 Не подошло» по `ab_variant` в `story_generation_log`.

### Откат

| Симптом | Действие |
|---------|----------|
| Массовый fallback | проверить API key / лимиты; временно `ENABLE_REWRITE_PASS=0` |
| Жалобы «скучно/страшно» | смотреть `prompt_hint` в логах; при системной проблеме — откат коммита |
| Регрессия качества | `PROMPT_VERSION=v1` (если сохранена v1-ветка) или revert фаз 1–6 |

---

## 4. Связанные документы

- [STORY_PROMPT_CHECKLIST.md](./STORY_PROMPT_CHECKLIST.md) — содержание промпта  
- [CONTENT_AND_SAFETY.md](./CONTENT_AND_SAFETY.md) — safety pipeline  
- [BOT_FLOWS.md](./BOT_FLOWS.md) — сценарии бота  
