import re
from pathlib import Path

from config import OPENAI_API_KEY, OPENAI_MODEL
from fallback_stories import fallback_story
from name_grammar import GENDER_LABELS, grammar_block, normalize_gender
from story_craft import (
    DAY_METAPHOR_MAP,
    SKAZKO_PRINCIPLES,
    TODAY_STORY_LOGIC,
    metaphors_for_age,
    propp_arc_for_prompt,
    today_prompt_block,
)
from story_safety import (
    LENGTH_RETRY_HINT,
    LENGTH_VIOLATIONS,
    META_NARRATION_BLOCK,
    META_RETRY_HINT,
    PROSE_RETRY_HINT,
    PROSE_VIOLATIONS,
    STRICT_RETRY_HINT,
    TODAY_RETRY_HINT,
    TODAY_VIOLATIONS,
    check_story,
    no_scary_rules,
    story_word_count,
)
from story_variety import VarietyPlan, variety_user_block

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_ru.txt"
DAY_CONTEXT_MAX = 500

# ~100–110 слов/мин чтения вслух (медленно, с паузами). Символы ≈ слова × 5,5.
# Верхней границы в промпте нет — сказка разворачивается как литературный текст.
WORD_TARGETS: dict[str, dict[int, int]] = {
    "tired": {
        2: 320,
        3: 380,
        4: 650,
        5: 720,
        6: 780,
        7: 880,
    },
    "medium": {
        2: 620,
        3: 720,
        4: 1200,
        5: 1300,
        6: 1450,
        7: 1600,
    },
    "screen_free": {
        2: 420,
        3: 480,
        4: 750,
        5: 820,
        6: 900,
        7: 980,
    },
    "today": {
        2: 360,
        3: 400,
        4: 680,
        5: 760,
        6: 820,
        7: 900,
    },
}

# Устаревший справочник — для совместимости, не используется в расчёте
MODE_WORDS = {mode: targets[4] for mode, targets in WORD_TARGETS.items()}

MODE_LABELS = {
    "tired": "Нет сил",
    "medium": "5 минут",
    "screen_free": "Вместо мультика",
    "today": "Сегодняшний день",
}

MODE_INSTRUCTIONS = {
    "tired": (
        "Развёрнутая литературная сказка — связные предложения с предлогами, не телеграфный стиль. "
        "Диалоги: любимый герой минимум 3–4 реплики + реплики гостя сюжета. "
        "Пропп: шаги 1→4→7 (мир → лёгкая недостача → дар покоя → сон). Без отлучки далеко от дома."
    ),
    "medium": (
        "Полная мягкая дуга Проппа (все 7 шагов). Развёрнутые абзацы, как глава из детской книги. "
        "Событие → помощник → «укладывание» чувства → сон. Много сенсорных деталей и живых диалогов."
    ),
    "screen_free": (
        "Образы «смотрим глазами»: луг, небо, медленные движения — описывай их связным литературным языком. "
        "Пропп-отлучка = путешествие взглядом, не физический риск. Без телефона, мультиков, YouTube."
    ),
    "today": (
        "Режим «Сегодняшний день»: сказка строится на осмыслении событий дня, не на повторе слов родителя. "
        "Дуга: что было → как прошло → что почувствовал герой → мягкое завершение и сон. "
        "DAY_METAPHOR_MAP — один образ дня, вплетённый в действие. Развёрнутые абзацы."
    ),
}

MODE_TEMPERATURE = {
    "tired": 0.65,
    "medium": 0.75,
    "screen_free": 0.7,
    "today": 0.65,
}


def _age_lexicon(age: int) -> str:
    grammar = (
        "ОБЯЗАТЕЛЬНО используй предлоги (в, на, у, за, под, к, от, про, с, для, без, между) "
        "и местоимения (он, она, они, мы, его, ей, им, свой, этот, тот, здесь, там) — "
        "они связывают действия и показывают, кто где и с кем. "
        "Не пиши цепочками коротких фраз без предлогов."
    )
    if age <= 3:
        return (
            "Понятные слова для малыша, но фразы связные — как в книге, не обрывки. "
            f"{grammar}"
        )
    if age <= 5:
        return (
            "Слова понятные дошкольнику, текст — связная проза из полных предложений. "
            "Можно придаточные («когда…», «потому что…», «рядом с…»). "
            f"{grammar}"
        )
    return (
        "Литературный язык детской прозы: плавные переходы между предложениями. "
        f"{grammar}"
    )


def _connected_prose_block(name: str, gender: str) -> str:
    g = normalize_gender(gender)
    if g == "f":
        bad = f"«{name} устала. {name} легла. Закрыла глазки. Сон пришёл.»"
        good = (
            f"«После долгого дня {name} устала. Она легла на кровать рядом с любимой игрушкой, "
            f"укуталась в тёплый плед, и под одеялом ей стало спокойно.»"
        )
    else:
        bad = f"«{name} устал. {name} лёг. Закрыл глазки. Сон пришёл.»"
        good = (
            f"«После долгого дня {name} устал. Он лёг на кровать рядом с любимой игрушкой, "
            f"укутался в тёплый плед, и под одеялом ему стало спокойно.»"
        )
    return f"""СВЯЗНАЯ РЕЧЬ (КРИТИЧНО — русский язык):
Плохо (так НЕ писать): {bad}
Хорошо (так писать): {good}
Правило: в каждом предложении — предлог или местоимение; связывай фразы, не перечисляй действия списком."""


def _literary_style_block() -> str:
    return """СТИЛЬ (литературная сказка для чтения вслух):
- Пиши как автор детской книги: цельные абзацы, ритм, образность — не конспект и не список действий.
- В каждом абзаце — предлоги и местоимения: «он подошёл к окну», «для неё это было», «рядом с ними», «оттуда донеслось».
- Чередуй: описание → диалог → действие → ощущение. Не повторяй одну конструкцию подряд.
- Верхней границы объёма нет — если сюжет просится дальше, развивай его.
- ЗАПРЕЩЕНО в тексте сказки (служебные слова, детям непонятны): «метафора этого вечера/дня», «сюжет был такой», «главная метафора», «сюжетный угол», «это символ», «история про то что». Смысл показывай действием и образами — без объяснений."""


def word_target_for(mode: str, age: int, length_pref: float = 1.0) -> int:
    """Целевое число слов с учётом режима, возраста (2–7) и prefs родителя."""
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 4
    age = max(2, min(7, age))
    table = WORD_TARGETS.get(mode, WORD_TARGETS["tired"])
    base = table.get(age, table[4])
    return max(80, int(base * length_pref))


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _reading_minutes(word_target: int) -> int:
    """Нижняя оценка времени чтения вслух (медленно, с паузами)."""
    return max(3, word_target // 110)


def _min_paragraphs(word_target: int) -> int:
    if word_target >= 1200:
        return 14
    if word_target >= 800:
        return 11
    if word_target >= 500:
        return 8
    return 6


def _max_tokens_for(word_target: int) -> int:
    """Без верхнего потолка на длину сказки — только запас под русский текст."""
    return max(2048, int(word_target * 3.2))


def _hero_participation_block(name: str, hero: str) -> str:
    hero_display = hero.strip() or "любимая игрушка или зверёк ребёнка"
    name_rule = (
        f"Имя «{hero_display}» — минимум 5–7 раз в тексте, в том числе в диалогах."
        if hero.strip()
        else f"Укажи любимую игрушку или зверька по имени минимум 5 раз."
    )
    return f"""ЛЮБИМЫЙ ГЕРОЙ «{hero_display}» (ОБЯЗАТЕЛЬНО В КАЖДОЙ СКАЗКЕ):
- Постоянный напарник ребёнка {name} — от первого до последнего абзаца. {name_rule}
- Минимум 3–5 реплик: разговаривает с {name}, играет, подбадривает, задаёт мягкие вопросы.
- Действует вместе с ребёнком: идёт рядом, помогает, реагирует на события.
- Если в user prompt есть «гость сюжета» — это ДРУГОЙ, эпизодический персонаж; «{hero_display}» всё равно остаётся.
- Запрещено: убрать «{hero_display}», заменить гостем сюжета, «прошёл мимо», одна реплика и исчез."""


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
    word_min = max(100, int(word_target * 0.8))
    hero_display = hero or "добрый зверёк"
    g = normalize_gender(gender)
    reading_min = _reading_minutes(word_target)
    return _load_prompt_template().format(
        age=age,
        name=name,
        hero=hero_display,
        mode_label=MODE_LABELS.get(mode, mode),
        gender_grammar=grammar_block(name, g),
        connected_prose=_connected_prose_block(name, g),
        age_lexicon=_age_lexicon(age),
        literary_style=_literary_style_block(),
        age_metaphors=metaphors_for_age(age),
        propp_arc=propp_arc_for_prompt(hero_display),
        skazko_principles=SKAZKO_PRINCIPLES.strip(),
        day_metaphor_map=DAY_METAPHOR_MAP.strip(),
        word_target=word_target,
        word_min=word_min,
        reading_min=reading_min,
        min_paragraphs=_min_paragraphs(word_target),
        hero_participation=_hero_participation_block(name, hero),
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
    variety: VarietyPlan | None = None,
    force_fresh: bool = False,
) -> str:
    hero_hint = hero or "добрый зверёк, которого любит ребёнок"
    g = normalize_gender(gender)
    gender_label = GENDER_LABELS[g]
    word_min = max(100, int(word_target * 0.8))
    lines = [
        "Напиши сонную сказку для чтения вслух родителем — как главу из детской книги.",
        f"Режим: {MODE_LABELS.get(mode, mode)}.",
        f"Ребёнок: {gender_label}, имя {name}.",
        f"Строго соблюдай {gender_label} род во всех глаголах и прилагательных про {name}.",
        "Следуй 7 шагам Проппа (мягкая сонная версия) из system prompt.",
        "Без заголовка. Только текст сказки абзацами.",
        "Не используй слова «метафора», «сюжет был», «сюжетный угол» — только живая сказка.",
        "",
        f"ДЛИНА: минимум {word_min} слов, ориентир от {word_target} слов и больше — верхней границы нет, "
        "разверни историю полностью. Обязательны предлоги и местоимения в каждом абзаце.",
        f"ЛЮБИМЫЙ ГЕРОЙ «{hero_hint}» — обязателен в каждом абзаце: по имени, в диалогах, рядом с {name}.",
    ]
    if variety:
        lines.append("")
        lines.append(
            variety_user_block(
                variety,
                child_name=name,
                favorite_hero=hero,
                force_fresh=force_fresh,
            )
        )
    else:
        lines.append(f"Главный герой — {name}; напарник — {hero_hint}.")
        lines.append(f"Используй 1–2 метафоры для возраста {age} из списка в system prompt.")
    if mode == "today" and day_context:
        lines.append("")
        lines.append(today_prompt_block(day_context, name, seed=hash(name) % 997))
        lines.append(
            "Следуй логике TODAY_STORY_LOGIC из system prompt. "
            "Связки «сначала — потом — поэтому». Без цитирования заметки родителя. "
            "Разные образы в каждой сказке — не «облачко» по умолчанию."
        )
    elif day_context:
        lines.append(f"Сегодня у ребёнка: {day_context}")
        lines.append(
            "Переведи событие в образ из DAY_METAPHOR_MAP — покажи действием, "
            "без слов «метафора» и «сюжет». "
            "Без поучений, обвинений и прямых названий проблемы."
        )
    elif mode == "today":
        lines.append(
            "Родитель не описал день — придумай мягкий обычный день с лёгкой усталостью "
            "и логикой «день прошёл → стало спокойнее → сон»."
        )
    elif not variety:
        lines.append("Обычный спокойный день — лёгкая недостача «устал после дня».")
    return "\n".join(lines)


def _temperature_for(mode: str, variety: VarietyPlan | None) -> float:
    base = MODE_TEMPERATURE.get(mode, 0.7)
    if not variety:
        return base
    boost = min(0.2, variety.fresh_boost * 0.04)
    return min(0.95, base + boost)


def _retry_hint(violations: list[str], *, word_min: int = 0, word_count: int = 0) -> str:
    vlabel = ", ".join(violations[:5])
    if any(v in LENGTH_VIOLATIONS for v in violations):
        return LENGTH_RETRY_HINT.format(word_count=word_count, word_min=word_min)
    if any(v in TODAY_VIOLATIONS for v in violations):
        return TODAY_RETRY_HINT.format(violations=vlabel)
    if any(v in PROSE_VIOLATIONS for v in violations):
        return PROSE_RETRY_HINT.format(violations=vlabel)
    if any(v in META_NARRATION_BLOCK for v in violations):
        return META_RETRY_HINT.format(violations=vlabel)
    return STRICT_RETRY_HINT.format(violations=vlabel)


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
        max_tokens=_max_tokens_for(word_target),
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
    variety: VarietyPlan | None = None,
    force_fresh: bool = False,
) -> tuple[str, bool]:
    """
    Returns (story_text, used_llm).
    """
    gen_mode = "today" if mode == "today" else mode
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 4
    word_target = word_target_for(gen_mode, age, length_pref)
    word_min = max(100, int(word_target * 0.8))
    day_context = (day_context or "").strip()[:DAY_CONTEXT_MAX]

    if not OPENAI_API_KEY:
        return (
            fallback_story(
                gen_mode,
                name,
                hero,
                day_context,
                gender=gender,
                variety=variety,
                age=age,
                word_target=word_target,
            ),
            False,
        )

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
    if gen_mode == "today" and day_context:
        system += "\n\n" + TODAY_STORY_LOGIC.strip()
    if variety:
        hero_label = hero.strip() or "любимый герой ребёнка"
        system += (
            "\n\nПЕРСОНАЖИ (не путать):\n"
            f"1. Ребёнок {name} — главный герой.\n"
            f"2. «{hero_label}» — любимый герой из профиля, постоянный напарник, обязателен в каждой сказке.\n"
            "3. «Гость сюжета» из user prompt — эпизодический персонаж для уникальности; "
            f"НЕ заменяет «{hero_label}».\n"
            "В каждой сказке должны быть и 2, и (если указан) 3."
        )
        system += (
            "\n\nВАЖНО: каждая новая сказка — уникальный сюжет. "
            "Не повторяй сеттинги, гостей сюжета, действия и метафоры из списка «ЗАПРЕЩЕНО» в user prompt."
        )
    user = _build_user_prompt(
        mode=gen_mode,
        name=name,
        hero=hero,
        word_target=word_target,
        day_context=day_context,
        age=age,
        gender=g,
        variety=variety,
        force_fresh=force_fresh,
    )
    temperature = _temperature_for(gen_mode, variety)

    best_text: str | None = None
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
        best_text = text

        for attempt in range(2):
            violations = check_story(
                text,
                no_scary=no_scary,
                word_min=word_min,
                day_context=day_context if gen_mode == "today" else "",
            )
            if not violations:
                break
            wc = story_word_count(text)
            hint = _retry_hint(violations, word_min=word_min, word_count=wc)
            text = await _call_llm(
                client,
                system=system + "\n\n" + hint,
                user=user + "\n\n" + hint,
                word_target=word_target,
                temperature=max(0.5, temperature - 0.05 * (attempt + 1)),
            )
            if story_word_count(text) >= story_word_count(best_text):
                best_text = text

        return best_text or text, True
    except Exception:
        if best_text and story_word_count(best_text) >= 40:
            return best_text, True
        return (
            fallback_story(
                gen_mode,
                name,
                hero,
                day_context,
                gender=gender,
                variety=variety,
                age=age,
                word_target=word_target,
            ),
            False,
        )


def split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts
