# QA-матрица промпта v2 — 2026-06-09

**PROMPT_VERSION:** v2  
**Режим:** prompt-only  
**Кейсов:** 24  
**Оценки:** 👍 24 · 😐 0 · 😟 0

> Проверка **сборки промпта**. Для текста сказок — LLM-прогон с ключом.

## Сводка

| # | кейс | mode | age | hero | 👍/😐/😟 | fails | polish | ms |
|---|------|------|-----|------|----------|-------|--------|-----|
| 1 | base_a3_tired_hero | tired | 3 | Зайчик | 👍 | — | — | 6993 |
| 2 | base_a3_tired_no_hero | tired | 3 | — | 👍 | — | — | 7083 |
| 3 | base_a3_medium_hero | medium | 3 | Зайчик | 👍 | — | — | 6957 |
| 4 | base_a3_medium_no_hero | medium | 3 | — | 👍 | — | — | 7047 |
| 5 | base_a3_screen_free_hero | screen_free | 3 | Зайчик | 👍 | — | — | 6967 |
| 6 | base_a3_screen_free_no_hero | screen_free | 3 | — | 👍 | — | — | 7057 |
| 7 | base_a5_tired_hero | tired | 5 | Зайчик | 👍 | — | — | 7164 |
| 8 | base_a5_tired_no_hero | tired | 5 | — | 👍 | — | — | 7254 |
| 9 | base_a5_medium_hero | medium | 5 | Зайчик | 👍 | — | — | 7119 |
| 10 | base_a5_medium_no_hero | medium | 5 | — | 👍 | — | — | 7209 |
| 11 | base_a5_screen_free_hero | screen_free | 5 | Зайчик | 👍 | — | — | 7125 |
| 12 | base_a5_screen_free_no_hero | screen_free | 5 | — | 👍 | — | — | 7215 |
| 13 | base_a7_tired_hero | tired | 7 | Зайчик | 👍 | — | — | 7356 |
| 14 | base_a7_tired_no_hero | tired | 7 | — | 👍 | — | — | 7446 |
| 15 | base_a7_medium_hero | medium | 7 | Зайчик | 👍 | — | — | 7305 |
| 16 | base_a7_medium_no_hero | medium | 7 | — | 👍 | — | — | 7395 |
| 17 | base_a7_screen_free_hero | screen_free | 7 | Зайчик | 👍 | — | — | 7341 |
| 18 | base_a7_screen_free_no_hero | screen_free | 7 | — | 👍 | — | — | 7431 |
| 19 | today_a3_hero | today | 3 | Зайчик | 👍 | — | — | 8584 |
| 20 | today_a3_no_hero | today | 3 | — | 👍 | — | — | 8674 |
| 21 | today_a5_hero | today | 5 | Зайчик | 👍 | — | — | 8748 |
| 22 | today_a5_no_hero | today | 5 | — | 👍 | — | — | 8838 |
| 23 | today_a7_hero | today | 7 | Зайчик | 👍 | — | — | 8956 |
| 24 | today_a7_no_hero | today | 7 | — | 👍 | — | — | 9046 |

## Вердикт

✅ **Промпты OK** по всем 24 кейсам. Следующий шаг — LLM-прогон.