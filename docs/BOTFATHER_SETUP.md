# BotFather + связь с документацией проекта

**Репозиторий:** https://github.com/golodokol/skazka-na-noch

---

## Важно: две разные вещи

| Где | Что делаете |
|-----|-------------|
| **[@BotFather](https://t.me/BotFather)** | Создаёте бота, имя, описание, **токен**, список команд. Это «паспорт» бота в Telegram. |
| **Ваш сервер / ПК** | Запускаете **код** из папки `bot/` с этим токеном. Без запущенного кода бот в Telegram **не отвечает**. |

Документация в `docs/` описывает **что** должен делать бот. BotFather — **как он выглядит** в каталоге Telegram. Код — **как он работает**.

**Бот:** [@skazkadobrolavka_bot](https://t.me/skazkadobrolavka_bot) — код в `bot/`, запуск см. [bot/README.md](../bot/README.md).

---

## Шаг 1. Создать бота в BotFather

1. Откройте Telegram → [@BotFather](https://t.me/BotFather).
2. Отправьте: `/newbot`
3. **Имя** (отображаемое): `Сказка на ночь`  
   → соответствует [PRODUCT_CARD.md](PRODUCT_CARD.md), [GTM.md](GTM.md)
4. **Username** (латиница, оканчивается на `bot`): например `skazka_na_noch_bot`  
   → проверьте, что свободен; ссылка будет `t.me/skazka_na_noch_bot`
5. BotFather пришлёт **токен** вида `7123456789:AAH...`  
   → **никому не показывайте**, не коммитьте в GitHub.

Сохраните токен в файл (локально):

```text
Documents\skazka-na-noch\.env
```

Скопируйте из [.env.example](../.env.example):

```env
TELEGRAM_BOT_TOKEN=вставьте_токен_от_BotFather
```

---

## Шаг 2. Описание и «О боте» (тексты из документации)

Источник текстов: [BOT_FLOWS.md](BOT_FLOWS.md) §9, [PRODUCT_CARD.md](PRODUCT_CARD.md) §5.

### Description (до 512 символов)

В BotFather: `/setdescription` → выберите бота → вставьте:

```text
Вечерние сказки для малышей 2–7 лет — когда хочется тепла, а сил придумывать уже мало.

За полминуты соберу историю с именем ребёнка, любимым героем и про сегодняшний день — если расскажете пару слов о вечере.

«Нет сил» — коротко и мягко. «5 минут» — подлиннее. «Вместо мультика» — телефон экраном вниз, читаете вслух. Всё заканчивается спокойно.

Читаете вы. Я только подсказываю, что рассказать сегодня.
```

> При запуске бота текст также выставляется через API (`setMyDescription`) из `bot/texts.py` → `BOT_DESCRIPTION`.

### About (коротко, до 120 символов)

`/setabouttext`:

```text
Co-pilot для вечернего ритуала. Сказка за 30 сек. Документация: github.com/golodokol/skazka-na-noch
```

Когда будет страница privacy — добавьте ссылку в About.

---

## Шаг 3. Команды (как в BOT_FLOWS.md)

`/setcommands` → выберите бота → вставьте **точно**:

```text
start - Начать и получить сказку
story - Быстрая сказка (последний режим)
profile - Профиль ребёнка
help - Как пользоваться
privacy - Политика данных
```

Соответствие коду (когда напишете handlers):

| Команда | Документ | Поведение |
|---------|----------|-----------|
| `/start` | [BOT_FLOWS.md](BOT_FLOWS.md) §2 | Приветствие + 3 кнопки режима |
| `/story` | [MVP_SPEC.md](MVP_SPEC.md) §3 | Повтор последнего режима |
| `/profile` | [MVP_SPEC.md](MVP_SPEC.md) §4 | Профиль ребёнка |
| `/help` | [PRODUCT_CARD.md](PRODUCT_CARD.md) | Краткая помощь |
| `/privacy` | [LEGAL_AND_PRIVACY.md](LEGAL_AND_PRIVACY.md) | Текст политики |

---

## Шаг 4. Кнопка меню (опционально)

`/setmenubutton` → выберите бота → **Commands** или одна команда:

- Тип: `commands`
- Или указать Web App (только когда будет Mini App, [TECH_ARCHITECTURE.md](TECH_ARCHITECTURE.md))

Для MVP достаточно меню с командами из шага 3.

---

## Шаг 5. Аватар

`/setuserpic` → картинка **512×512**, тёплые тона, ночь, без пугающих персонажей.

Чеклист: [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) §A.

---

## Шаг 6. Связать BotFather ↔ документацию ↔ код

### Карта «где что живёт»

```
BotFather (токен, имя, команды)
        │
        ▼
   .env  TELEGRAM_BOT_TOKEN  ←── .env.example
        │
        ▼
   bot/main.py (handlers)  ←── BOT_FLOWS.md (экраны и кнопки)
        │                      CONTENT_AND_SAFETY.md (промпты)
        │                      MVP_SPEC.md (режимы: tired / medium / screen_free)
        ▼
   LLM API ключ в .env  ←── TECH_ARCHITECTURE.md
```

### Что настроить в `.env` перед запуском

| Переменная | Откуда взять | Документ |
|------------|--------------|----------|
| `TELEGRAM_BOT_TOKEN` | BotFather после `/newbot` | этот файл, §1 |
| `OPENAI_API_KEY` (или другой) | Кабинет провайдера LLM | [TECH_ARCHITECTURE.md](TECH_ARCHITECTURE.md) |

### Проверка «бот живой»

После того как код бота запущен на ПК/VPS:

1. Откройте `t.me/ВАШ_USERNAME_BOT`
2. `/start` → должно совпасть с [BOT_FLOWS.md](BOT_FLOWS.md) §2 (приветствие + кнопки)
3. Если молчит — код не запущен или неверный токен в `.env`

---

## Шаг 7. Режим работы: polling vs webhook

| Режим | Когда | Документ |
|-------|-------|----------|
| **Polling** | Разработка на ноутбуке | [TECH_ARCHITECTURE.md](TECH_ARCHITECTURE.md) §7 |
| **Webhook** | Продакшен (нужен HTTPS-домен) | там же |

BotFather webhook **не настраивает** — это делает ваш сервер командой к Telegram API после деплоя.

---

## Шаг 8. Чеклист «BotFather готов»

- [ ] Бот создан, username записан
- [ ] Токен в `.env`, **не** в Git
- [ ] Description + About соответствуют позиционированию [PRODUCT_CARD.md](PRODUCT_CARD.md)
- [ ] Команды как в [BOT_FLOWS.md](BOT_FLOWS.md) §1
- [ ] Аватар загружен
- [ ] Код бота запущен (или в очереди разработки)
- [ ] Пройден [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md)

---

## Что делать дальше (код ещё не в репозитории)

1. Реализовать MVP по [MVP_SPEC.md](MVP_SPEC.md) и [PRD.md](PRD.md) в `bot/`.
2. Локально: `pip install -r bot/requirements.txt` → `python bot/main.py` (появится после разработки).
3. Пилот: [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) §G.

Можно попросить в Cursor: *«Напиши MVP бота aiogram по BOT_FLOWS.md»* — тогда шаг 6 заработает end-to-end.

---

## Полезные ссылки

- [Документация Telegram Bots](https://core.telegram.org/bots)
- [BotFather](https://t.me/BotFather)
- Ваш репозиторий: https://github.com/golodokol/skazka-na-noch
