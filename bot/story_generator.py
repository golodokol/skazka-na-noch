import re
from pathlib import Path

from config import OPENAI_API_KEY, OPENAI_MODEL
from fallback_stories import fallback_story
from name_grammar import GENDER_LABELS, grammar_block, normalize_gender
from story_craft import (
    DAY_METAPHOR_MAP,
    SKAZKO_PRINCIPLES,
    metaphors_for_age,
    propp_arc_for_prompt,
)
from story_safety import STRICT_RETRY_HINT, check_story, no_scary_rules

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_ru.txt"
DAY_CONTEXT_MAX = 500

# Базовая длина (слова) по режиму и возрасту.
# ~120 слов/мин чтения вслух. Символы ≈ слова × 5,5 (кириллица + пробелы).
# Было: одна длина на всех (tired 350, medium 700…).
WORD_TARGETS: dict[str, dict[int, int]] = {
    "tired": {
        2: 280,   # ~2 мин, ~1540 симв.
        3: 320,   # ~2,5 мин, ~1760
        4: 380,   # ~3 мин, ~2090  (+8% к старому 350)
        5: 420,   # ~3,5 мин, ~2310
        6: 580,   # ~4,8 мин, ~3190
        7: 660,   # ~5,5 мин, ~3630
    },
    "medium": {
        2: 520,   # ~4 мин
        3: 600,   # ~5 мин
        4: 720,   # ~6 мин
        5: 780,   # ~6,5 мин
        6: 1020,  # ~8,5 мин, ~5610 симв.
        7: 1140,  # ~9,5 мин, ~6270 симв.
    },
    "screen_free": {
        2: 360,
        3: 400,
        4: 460,
        5: 500,
        6: 680,   # ~5,7 мин
        7: 760,   # ~6,3 мин
    },
    "today": {
        2: 300,
        3: 340,
        4: 400,
        5: 440,
        6: 600,   # ~5 мин
        7: 680,   # ~5,7 мин
    },
}

# Устаревший справочник — для совместимости, не используется в расчёте
MODE_WORDS = {mode: targets[4] for mode, targets in WORD_TARGETS.items()}

MODE_LABELS = {
    "tired": "Нет сил (короткая)",
    "medium": "5 минут",
    "screen_free": "Вместо мультика",
    "today": "Сегодняшний день",
}

MODE_INSTRUCTIONS = {
    "tired": (
        "Очень короткие абзацы (2–3 предложения). Минимум диалогов — одна короткая реплика помощника. "
        "Пропп: только шаги 1→4→7 (мир → лёгкая недостача → дар покоя → сон). Без отлучки-дальше комнаты."
    ),
    "medium": (
        "Полная мягкая дуга Проппа (все 7 шагов). Маленькое событие → помощник → «укладывание» чувства → сон. "
        "Можно чуть больше деталей и одну сенсорную деталь (тепло, запах, звук «ш-ш»)."
    ),
    "screen_free": (
        "Образы «смотрим глазами»: луг, небо, медленные движения (Шорохова: зрительная игра без экрана). "
        "Пропп-отлучка = путешествие взглядом, не физический риск. Без телефона, мультиков, YouTube."
    ),
    "today": (
        "Обязательно DAY_METAPHOR_MAP: событие дня только через метафору, без обвинений. "
        "Пропп §2 и §5 — недостача и «укладывание» чувства. Короткие абзацы."
    ),
}

MODE_TEMPERATURE = {
    "tired": 0.65,
    "medium": 0.75,
    "screen_free": 0.7,
    "today": 0.65,
}


def _age_lexicon(age: int) -> str:
    if age <= 3:
        return (
            "Предложения до 6–8 слов. Только простые слова: спать, тёплый, мягкий, дом, мама, папа. "
            "Без «однако», «вдруг оказалось», без абстракций."
        )
    if age <= 5:
        return (
            "Предложения до 10 слов. Простые глаголы в настоящем времени. "
            "Минимум придаточных предложений."
        )
    return (
        "Предложения до 12–14 слов. Допустима лёгкая метафора, но без сложной лексики и иронии."
    )


def word_target_for(mode: str, age: int, length_pref: float = 1.0) -> int:
    """Целевое число слов с учётом режима, возраста (2–7) и prefs родителя."""
    age = max(2, min(7, age))
    table = WORD_TARGETS.get(mode, WORD_TARGETS["tired"])
    base = table.get(age, table[4])
    return max(80, int(base * length_pref))


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _build_system_prompt(
    *,
    age: int,
    name: str,
    hero: str,
    mode: str,
    word_target: int,
    no_scary: bool,
    gender: str,
) -> str:
    word_min = max(80, int(word_target * 0.6))
    hero_display = hero or "добрый зверёк"
    g = normalize_gender(gender)
    return _load_prompt_template().format(
        age=age,
        name=name,
        hero=hero_display,
        mode_label=MODE_LABELS.get(mode, mode),
        gender_grammar=grammar_block(name, g),
        age_lexicon=_age_lexicon(age),
        age_metaphors=metaphors_for_age(age),
        propp_arc=propp_arc_for_prompt(hero_display),
        skazko_principles=SKAZKO_PRINCIPLES.strip(),
        day_metaphor_map=DAY_METAPHOR_MAP.strip(),
        word_target=word_target,
        word_min=word_min,
        no_scary_rules=no_scary_rules(no_scary),
        mode_instructions=MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["tired"]),
    )


def _build_user_prompt(
    *,
    mode: str,
    name: str,
    hero: str,
    word_target: int,
    day_context: str,
    age: int,
    gender: str,
) -> str:
    hero_hint = hero or "добрый зверёк, которого любит ребёнок"
    g = normalize_gender(gender)
    gender_label = GENDER_LABELS[g]
    lines = [
        "Напиши сонную сказку для чтения вслух родителем.",
        f"Режим: {MODE_LABELS.get(mode, mode)} (~{word_target} слов).",
        f"Ребёнок: {gender_label}, имя {name}. Герой сказки — {name} или {hero_hint}.",
        f"Строго соблюдай {gender_label} род во всех глаголах и прилагательных про {name}.",
        "Следуй 7 шагам Проппа (мягкая сонная версия) из system prompt.",
        f"Используй 1–2 метафоры для возраста {age} из списка в system prompt.",
        "Без заголовка. Только текст сказки абзацами.",
    ]
    if day_context:
        lines.append(f"Сегодня у ребёнка: {day_context}")
        lines.append(
            "Переведи событие в метафору из DAY_METAPHOR_MAP. "
            "Без поучений, обвинений и прямых названий проблемы."
        )
    else:
        lines.append("Обычный спокойный день — лёгкая недостача «устал после дня».")
    return "\n".join(lines)


def _postprocess_story(text: str) -> str:
    text = text.strip()
    # Убрать markdown-заголовки и префиксы
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^(сказка|title)\s*:\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    # Убрать вопросительные предложения в конце
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    while paragraphs:
        last = paragraphs[-1]
        if "?" in last or "？" in last:
            # если весь абзац — один вопрос, убираем
            if last.rstrip().endswith("?") or last.rstrip().endswith("？"):
                paragraphs.pop()
                continue
        break
    return "\n\n".join(paragraphs)


async def _call_llm(
    client,
    *,
    system: str,
    user: str,
    word_target: int,
    temperature: float,
) -> str:
    resp = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=min(2800, word_target * 2),
    )
    text = (resp.choices[0].message.content or "").strip()
    if len(text) < 100:
        raise ValueError("story too short")
    return _postprocess_story(text)


async def generate_story(
    mode: str,
    name: str,
    age: int,
    hero: str = "",
    day_context: str = "",
    length_pref: float = 1.0,
    no_scary: bool = True,
    gender: str = "m",
) -> tuple[str, bool]:
    """
    Returns (story_text, used_llm).
    """
    gen_mode = "today" if mode == "today" else mode
    word_target = word_target_for(gen_mode, age, length_pref)
    day_context = (day_context or "").strip()[:DAY_CONTEXT_MAX]

    if not OPENAI_API_KEY:
        return fallback_story(gen_mode, name, hero, day_context, gender=gender), False

    g = normalize_gender(gender)
    system = _build_system_prompt(
        age=age,
        name=name,
        hero=hero,
        mode=gen_mode,
        word_target=word_target,
        no_scary=no_scary,
        gender=g,
    )
    user = _build_user_prompt(
        mode=gen_mode,
        name=name,
        hero=hero,
        word_target=word_target,
        day_context=day_context,
        age=age,
        gender=g,
    )
    temperature = MODE_TEMPERATURE.get(gen_mode, 0.7)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        text = await _call_llm(
            client,
            system=system,
            user=user,
            word_target=word_target,
            temperature=temperature,
        )

        violations = check_story(text, no_scary=no_scary)
        if violations:
            strict_user = (
                user
                + "\n\n"
                + STRICT_RETRY_HINT.format(violations=", ".join(violations[:5]))
            )
            text = await _call_llm(
                client,
                system=system + "\n\n" + STRICT_RETRY_HINT.format(
                    violations=", ".join(violations[:5])
                ),
                user=strict_user,
                word_target=word_target,
                temperature=max(0.5, temperature - 0.1),
            )
            if check_story(text, no_scary=no_scary):
                raise ValueError("safety retry failed")

        return text, True
    except Exception:
        return fallback_story(gen_mode, name, hero, day_context, gender=gender), False


def split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts
