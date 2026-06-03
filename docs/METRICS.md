# Метрики и аналитика

---

## 1. North Star Metric

**Количество вечеров с успешным ритуалом** = сессия 20:00–23:00 + генерация + feedback `уснул` или `спросил ещё` (не `страшно`).

---

## 2. KPI пилота (4–6 недель)

| Метрика | Определение | Цель |
|---------|-------------|------|
| **TTV** | Время от кнопки до текста | p90 < 60 сек |
| **D1 activation** | 1+ сказка в первые 24ч | > 60% |
| **D7 retention** | Вернулся в вечернее окно | ≥ 25% |
| **Evening sessions/user/week** | Среднее | ≥ 2.5 |
| **Positive feedback rate** | уснул + ещё / все | > 55% |
| **Paywall conversion** | оплата / paywall view | ≥ 3% |
| **Safety incidents** | страшно + эскалация | 0 |

---

## 3. События (analytics)

```yaml
# User lifecycle
user_started:
  props: [source, ref_code]

profile_completed:
  props: [has_name, age, no_scary]

# Core loop
mode_selected:
  props: [mode: tired|medium|screen_free|today|rescue]

day_context_sent:
  props: [length, voice_bool]

story_generated:
  props: [mode, latency_ms, word_count, fallback_bool]

story_feedback:
  props: [type: asleep|more|long|bad, subtype]

# Monetization
limit_reached:
  props: [week_count]

paywall_view: {}
payment_success:
  props: [plan, amount_rub, provider]
```

**Инструменты MVP:** PostHog / Amplitude / или таблица `events` в PostgreSQL.

---

## 4. Когорты

- По `source` (канал, реферал, органика)
- По режиму первой сказки
- По наличию `day_context`

---

## 5. Качественные метрики

Еженедельно в пилоте (Google Form / TG опрос):

1. Сколько вечеров использовали бота? (0 / 1–2 / 3+)
2. Что было бы без бота? (открытый)
3. Заплатили бы 399 ₽? (да / нет / при условии ___)
4. NPS 0–10

---

## 6. Дашборд (минимум)

| Виджет | Частота |
|--------|---------|
| DAU / вечерний DAU | daily |
| Сказок / день | daily |
| Retention D1/D7 | weekly |
| Feedback mix | weekly |
| MRR | monthly |

---

## 7. Kill criteria (остановить / pivot)

- D7 < 10% после 50 пользователей
- Positive feedback < 35%
- 2+ safety инцидента без быстрого фикса
- 0 платежей после 200 paywall views

---

## 8. Success criteria (масштабировать)

- D7 ≥ 25% на 50+ users
- ≥ 5 платящих без скидки
- 3+ цитаты «вечер удался без сил» в интервью
