import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from config import (
    MAX_DRAFT_RETRIES,
    OPENAI_API_KEY,
    POLISH_TEMPERATURE,
    PROMPT_VERSION,
    ab_variant,
    draft_model_for_mode,
    polish_model_for_mode,
    rewrite_pass_for_mode,
    temperature_for_mode,
)
from fallback_stories import fallback_story
from name_grammar import GENDER_LABELS, grammar_block, name_genitive, normalize_gender
from prompts.few_shot_ru import few_shot_for_age
from story_craft import (
    AI_CLICHE_AVOID,
    EVENING_ARC,
    LITERARY_STYLE,
    NARRATOR_VOICE,
    READ_ALOUD_RHYTHM,
    SKAZKO_PRINCIPLES,
    context_blocks_for_prompt,
    pick_metaphor_for_age,
    propp_arc_for_prompt,
    today_prompt_block,
)
from story_safety import (
    CLICHE_RETRY_HINT,
    CLICHE_VIOLATIONS,
    LENGTH_RETRY_HINT,
    LENGTH_VIOLATIONS,
    META_NARRATION_BLOCK,
    META_RETRY_HINT,
    NAME_RETRY_HINT,
    NAME_VIOLATIONS,
    PROSE_RETRY_HINT,
    PROSE_VIOLATIONS,
    STRICT_RETRY_HINT,
    TODAY_RETRY_HINT,
    TODAY_VIOLATIONS,
    check_story,
    no_scary_rules,
    story_word_count,
)
from rescue_scenarios import RESCUE_BY_ID, rescue_prompt_block
from story_feedback_hints import scary_feedback_extra, user_prompt_hint
from story_variety import VarietyPlan, variety_user_block

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_ru.txt"
POLISH_PATH = Path(__file__).parent / "prompts" / "polish_ru.txt"
POLISH_MIN_LENGTH_RATIO = 0.9
DAY_CONTEXT_MAX = 500


@dataclass
class StoryGenerationMeta:
    used_llm: bool = False
    fallback: bool = False
    mode: str = ""
    ab_variant: str = "control"
    draft_model: str = ""
    polish_model: str = ""
    rewrite_attempted: bool = False
    rewrite_applied: bool = False
    latency_ms: int = 0
    draft_latency_ms: int = 0
    polish_latency_ms: int = 0
    word_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    retry_count: int = 0
    prompt_hint: str = ""
    prompt_version: str = ""
    rescue_id: str = ""

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "ab_variant": self.ab_variant,
            "draft_model": self.draft_model,
            "polish_model": self.polish_model,
            "rewrite_attempted": self.rewrite_attempted,
            "rewrite_applied": self.rewrite_applied,
            "fallback": self.fallback,
            "latency_ms": self.latency_ms,
            "draft_latency_ms": self.draft_latency_ms,
            "polish_latency_ms": self.polish_latency_ms,
            "word_count": self.word_count,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "retry_count": self.retry_count,
            "prompt_hint": self.prompt_hint,
            "prompt_version": self.prompt_version,
            "rescue_id": self.rescue_id,
        }

# ~100–110 слов/мин чтения вслух (медленно, с паузами). Символы ≈ слова × 5,5.
# Верхней границы в промпте нет — сказка разворачивается как литературный текст.
TELEGRAM_MESSAGE_LIMIT = 4096
LENGTH_MIN_RATIO = 0.85  # word_min для промпта и retry
LENGTH_CHECK_RATIO = 0.70  # порог story_too_short в post-check

# Ориентир ~100 сл/мин: tired 2–3 мин, medium ~5 мин, screen_free/today между ними.
WORD_TARGETS: dict[str, dict[int, int]] = {
    "tired": {
        2: 250,
        3: 300,
        4: 330,
        5: 380,
        6: 400,
        7: 420,
    },
    "medium": {
        2: 450,
        3: 500,
        4: 550,
        5: 600,
        6: 650,
        7: 680,
    },
    "screen_free": {
        2: 350,
        3: 400,
        4: 480,
        5: 520,
        6: 580,
        7: 620,
    },
    "today": {
        2: 280,
        3: 320,
        4: 400,
        5: 480,
        6: 520,
        7: 580,
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
        "Развёрнутая литературная сказка — связные предложения, не телеграфный стиль. "
        "Диалоги: любимый герой 2–4 короткие реплики + реплики гостя сюжета. "
        "Пропп: шаги 1→4→7 (мир → лёгкая недостача → дар покоя → сон). "
        "Разверни середину: сенсорные детали, не спеши к финалу."
    ),
    "medium": (
        "Полная мягкая дуга Проппа (все 7 шагов). Развёрнутые абзацы, как глава из детской книги. "
        "Событие → помощник → «укладывание» чувства → сон. "
        "Много сенсорных деталей, живых диалогов — не меньше целевого объёма слов."
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


def _age_lexicon(age: int) -> str:
    if age <= 3:
        return "Понятные слова для малыша, фразы связные — как в книге, не обрывки."
    if age <= 5:
        return (
            "Слова понятные дошкольнику, связная проза. "
            "Можно придаточные («когда…», «потому что…», «рядом с…»)."
        )
    return "Литературный язык детской прозы: плавные переходы между предложениями."


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
    return f"""СВЯЗНАЯ РЕЧЬ:
Плохо: {bad}
Хорошо: {good}
Связывай фразы предлогами и местоимениями — не перечисляй действия списком."""


def word_min_for(word_target: int) -> int:
    """Минимум слов для промпта, retry и post-check."""
    return max(120, int(word_target * LENGTH_MIN_RATIO))


def word_target_for(mode: str, age: int, length_pref: float = 1.0) -> int:
    """Целевое число слов с учётом режима, возраста (2–7) и prefs родителя."""
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 4
    age = max(2, min(7, age))
    table = WORD_TARGETS.get(mode, WORD_TARGETS["tired"])
    base = int(table.get(age, table[4]) * length_pref)
    return max(80, base)


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _reading_minutes(word_target: int) -> int:
    """Нижняя оценка времени чтения вслух (медленно, с паузами)."""
    return max(3, word_target // 110)


def _min_paragraphs(word_target: int) -> int:
    if word_target >= 600:
        return 8
    if word_target >= 400:
        return 6
    return 5


_MODE_MAX_TOKENS: dict[str, int] = {
    "tired": 1500,
    "screen_free": 1800,
    "today": 2000,
    "medium": 2500,
}


def _max_tokens_for(word_target: int, mode: str = "tired") -> int:
    """Потолок completion-токенов по режиму — быстрее генерация."""
    cap = _MODE_MAX_TOKENS.get(mode, 2000)
    estimated = int(word_target * 2.8)
    return min(cap, max(estimated, 800))


def _name_usage_block(name: str, gender: str) -> str:
    g = normalize_gender(gender)
    pron = "она" if g == "f" else "он"
    name_gen = name_genitive(name, g)
    return f"""ИМЯ РЕБЁНКА «{name}» (обязательно в тексте):
- Имя должно звучать 3–5 раз на всю сказку — в любом падеже («{name}», «{name_gen}» и т.д.).
- Первый абзац — обязательно с именем ребёнка.
- Между упоминаниями имени используй «{pron}»; запрещено писать всю сказку только местоимениями.
- В одном абзаце имя — максимум один раз."""


def _hero_participation_block(name: str, hero: str) -> str:
    hero_display = hero.strip() or "любимая игрушка или зверёк ребёнка"
    hero_name_rule = (
        f"Имя «{hero_display}» — 3–5 раз (отдельно от имени ребёнка)."
        if hero.strip()
        else "Укажи игрушку или зверька по имени 3–5 раз."
    )
    return f"""ЛЮБИМЫЙ ГЕРОЙ «{hero_display}»:
- Постоянный напарник — в большинстве сцен, особенно в начале и в финале. {hero_name_rule}
- 2–4 короткие тёплые реплики — свой голос, не поучения.
- Действует рядом с ребёнком: идёт вместе, помогает, реагирует на события.
- «Гость сюжета» из user prompt — другой, эпизодический; «{hero_display}» остаётся.
- Запрещено: убрать «{hero_display}», заменить гостем, одна реплика и исчез."""


def _build_system_prompt(
    *,
    age: int,
    name: str,
    hero: str,
    mode: str,
    word_target: int,
    no_scary: bool,
    gender: str,
    day_context: str = "",
    variety: VarietyPlan | None = None,
    prompt_hint: str = "",
    rescue_id: str = "",
) -> str:
    word_min = word_min_for(word_target)
    hero_display = hero or "добрый зверёк"
    g = normalize_gender(gender)
    reading_min = _reading_minutes(word_target)
    metaphor = (
        variety.metaphor
        if variety
        else pick_metaphor_for_age(age, seed=hash(f"{name}:{mode}") % 997)
    )
    scary_rules = no_scary_rules(no_scary)
    extra_scary = scary_feedback_extra(prompt_hint)
    if extra_scary:
        scary_rules = f"{scary_rules}\n{extra_scary}"
    return _load_prompt_template().format(
        age=age,
        name=name,
        hero=hero_display,
        mode_label=MODE_LABELS.get(mode, mode),
        narrator_voice=NARRATOR_VOICE.strip(),
        read_aloud_rhythm=READ_ALOUD_RHYTHM.strip(),
        gender_grammar=grammar_block(name, g),
        connected_prose=_connected_prose_block(name, g),
        age_lexicon=_age_lexicon(age),
        literary_style=LITERARY_STYLE.strip(),
        ai_cliche_avoid=AI_CLICHE_AVOID.strip(),
        few_shot=few_shot_for_age(age),
        evening_arc=EVENING_ARC.strip(),
        propp_arc=propp_arc_for_prompt(hero_display),
        skazko_principles=SKAZKO_PRINCIPLES.strip(),
        context_blocks=context_blocks_for_prompt(
            mode=mode,
            day_context=day_context,
            age=age,
            metaphor=metaphor,
        ),
        word_target=word_target,
        word_min=word_min,
        reading_min=reading_min,
        min_paragraphs=_min_paragraphs(word_target),
        name_usage=_name_usage_block(name, g),
        hero_participation=_hero_participation_block(name, hero),
        no_scary_rules=scary_rules,
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
    prompt_hint: str = "",
    rescue_id: str = "",
) -> str:
    hero_hint = hero or "добрый зверёк, которого любит ребёнок"
    g = normalize_gender(gender)
    gender_label = GENDER_LABELS[g]
    lines = [
        f"Напиши сонную сказку. Режим: {MODE_LABELS.get(mode, mode)}.",
        f"Ребёнок: {gender_label}, имя {name}. Соблюдай {gender_label} род.",
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
    if rescue_id and rescue_id in RESCUE_BY_ID:
        lines.append("")
        lines.append(rescue_prompt_block(rescue_id, name))
    elif mode == "today" and day_context:
        lines.append("")
        lines.append(today_prompt_block(day_context, name, seed=hash(name) % 997))
    elif day_context:
        lines.append(f"Сегодня у ребёнка: {day_context}")
        lines.append("Перескажи событие как сцену в сказке — своими словами.")
    elif mode == "today":
        lines.append(
            "Родитель не описал день — придумай мягкий обычный день с лёгкой усталостью."
        )
    elif not variety:
        lines.append("Обычный спокойный вечер — лёгкая усталость после дня.")
    hint_block = user_prompt_hint(prompt_hint)
    if hint_block:
        lines.append("")
        lines.append(hint_block)
    word_min = word_min_for(word_target)
    pron = "она" if g == "f" else "он"
    lines.append("")
    name_gen = name_genitive(name, g)
    lines.append(
        f"ОБЯЗАТЕЛЬНО: минимум {word_min} слов (ориентир {word_target}). "
        f"Первый абзац — с именем «{name}»; всего 3–5 упоминаний имени по тексту "
        f"(можно «{name_gen}» и др. падежи); между ними — «{pron}»."
    )
    return "\n".join(lines)


def _temperature_for(mode: str, variety: VarietyPlan | None) -> float:
    base = temperature_for_mode(mode)
    if not variety:
        return base
    boost = min(0.2, variety.fresh_boost * 0.04)
    return min(0.95, base + boost)


def _retry_hint(
    violations: list[str],
    *,
    word_min: int = 0,
    word_count: int = 0,
    name: str = "",
    gender: str = "m",
) -> str:
    vlabel = ", ".join(violations[:5])
    if any(v in NAME_VIOLATIONS for v in violations):
        g = normalize_gender(gender)
        name_gen = name_genitive(name, g) if name else "ребёнка"
        return NAME_RETRY_HINT.format(
            name=name or "ребёнок",
            name_gen=name_gen,
            violations=vlabel,
        )
    if any(v in LENGTH_VIOLATIONS for v in violations):
        return LENGTH_RETRY_HINT.format(word_count=word_count, word_min=word_min)
    if any(v in TODAY_VIOLATIONS for v in violations):
        return TODAY_RETRY_HINT.format(violations=vlabel)
    if any(v in PROSE_VIOLATIONS for v in violations):
        return PROSE_RETRY_HINT.format(violations=vlabel)
    if any(v in CLICHE_VIOLATIONS for v in violations):
        return CLICHE_RETRY_HINT.format(violations=vlabel)
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


def _load_polish_system(
    *,
    name: str,
    hero: str,
    word_min: int,
    no_scary: bool,
) -> str:
    hero_display = hero.strip() or "любимый герой ребёнка"
    return POLISH_PATH.read_text(encoding="utf-8").format(
        name=name,
        hero=hero_display,
        word_min=word_min,
        no_scary_rules=no_scary_rules(no_scary),
    )


def _build_polish_user(draft: str, word_min: int) -> str:
    return (
        f"Перепиши сказку ниже: проза плавнее, без штампов. "
        f"Минимум {word_min} слов — не сокращай.\n\n"
        f"---\n{draft.strip()}\n---"
    )


def accept_polished_story(
    draft: str,
    polished: str,
    *,
    word_min: int,
    no_scary: bool = True,
    day_context: str = "",
    name: str = "",
    gender: str = "m",
) -> bool:
    """Принять polish, если не короче draft и проходит safety."""
    draft_wc = story_word_count(draft)
    polished_wc = story_word_count(polished)
    if polished_wc < int(draft_wc * POLISH_MIN_LENGTH_RATIO):
        return False
    violations = check_story(
        polished,
        no_scary=no_scary,
        word_min=word_min,
        day_context=day_context,
        name=name,
        gender=gender,
    )
    return not violations


async def _call_llm(
    client,
    *,
    system: str,
    user: str,
    word_target: int,
    temperature: float,
    model: str,
    mode: str = "tired",
) -> tuple[str, int, int]:
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=_max_tokens_for(word_target, mode),
    )
    text = (resp.choices[0].message.content or "").strip()
    if len(text) < 100:
        raise ValueError("story too short")
    usage = resp.usage
    prompt_tokens = int(usage.prompt_tokens or 0) if usage else 0
    completion_tokens = int(usage.completion_tokens or 0) if usage else 0
    return _postprocess_story(text), prompt_tokens, completion_tokens


async def _maybe_polish_story(
    client,
    *,
    draft: str,
    name: str,
    hero: str,
    word_target: int,
    word_min: int,
    no_scary: bool,
    day_context: str,
    polish_model: str,
    gender: str = "m",
    mode: str = "medium",
) -> tuple[str, bool, int, int]:
    system = _load_polish_system(
        name=name, hero=hero, word_min=word_min, no_scary=no_scary
    )
    user = _build_polish_user(draft, word_min)
    try:
        polished, p_tok, c_tok = await _call_llm(
            client,
            system=system,
            user=user,
            word_target=word_target,
            temperature=POLISH_TEMPERATURE,
            model=polish_model,
            mode=mode,
        )
    except Exception:
        return draft, False, 0, 0
    if accept_polished_story(
        draft,
        polished,
        word_min=word_min,
        no_scary=no_scary,
        day_context=day_context,
        name=name,
        gender=gender,
    ):
        return polished, True, p_tok, c_tok
    return draft, False, p_tok, c_tok


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
    user_id: int | None = None,
    prompt_hint: str = "",
    rescue_id: str = "",
) -> tuple[str, StoryGenerationMeta]:
    """
    Returns (story_text, generation_meta).
    """
    t0 = time.perf_counter()
    if rescue_id and rescue_id in RESCUE_BY_ID:
        gen_mode = RESCUE_BY_ID[rescue_id].story_mode
    else:
        rescue_id = ""
        gen_mode = "today" if mode == "today" else mode
    variant = ab_variant(user_id)
    draft_model = draft_model_for_mode(gen_mode)
    polish_model = polish_model_for_mode(gen_mode)
    meta = StoryGenerationMeta(
        mode=gen_mode,
        ab_variant=variant,
        draft_model=draft_model,
        polish_model=polish_model,
        prompt_hint=prompt_hint,
        prompt_version=PROMPT_VERSION,
        rescue_id=rescue_id,
    )
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 4
    word_target = word_target_for(gen_mode, age, length_pref)
    word_min = word_min_for(word_target)
    day_context = (day_context or "").strip()[:DAY_CONTEXT_MAX]

    if not OPENAI_API_KEY:
        meta.fallback = True
        story = fallback_story(
            gen_mode,
            name,
            hero,
            day_context,
            gender=gender,
            variety=variety,
            age=age,
            word_target=word_target,
        )
        meta.word_count = story_word_count(story)
        meta.latency_ms = int((time.perf_counter() - t0) * 1000)
        return story, meta

    g = normalize_gender(gender)
    system = _build_system_prompt(
        age=age,
        name=name,
        hero=hero,
        mode=gen_mode,
        word_target=word_target,
        no_scary=no_scary,
        gender=g,
        day_context=day_context,
        variety=variety,
        prompt_hint=prompt_hint,
        rescue_id=rescue_id,
    )
    if rescue_id:
        label = RESCUE_BY_ID[rescue_id].label
        system += f"\n\nРЕЖИМ СПАСЕНИЯ: {label}. Следуй ситуации из user prompt."
    if variety:
        hero_label = hero.strip() or "любимый герой ребёнка"
        system += (
            "\n\nПЕРСОНАЖИ (не путать):\n"
            f"1. Ребёнок {name} — главный герой.\n"
            f"2. «{hero_label}» — любимый герой из профиля, постоянный напарник.\n"
            "3. «Гость сюжета» из user prompt — эпизодический персонаж; "
            f"НЕ заменяет «{hero_label}»."
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
        prompt_hint=prompt_hint,
        rescue_id=rescue_id,
    )

    best_text: str | None = None
    total_prompt_tokens = 0
    total_completion_tokens = 0
    retry_count = 0
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        draft_t0 = time.perf_counter()
        text, p_tok, c_tok = await _call_llm(
            client,
            system=system,
            user=user,
            word_target=word_target,
            temperature=temperature,
            model=draft_model,
            mode=gen_mode,
        )
        meta.draft_latency_ms = int((time.perf_counter() - draft_t0) * 1000)
        total_prompt_tokens += p_tok
        total_completion_tokens += c_tok
        best_text = text

        check_day = day_context if gen_mode == "today" else ""
        for attempt in range(MAX_DRAFT_RETRIES):
            violations = check_story(
                text,
                no_scary=no_scary,
                word_min=word_min,
                day_context=check_day,
                name=name,
                gender=g,
            )
            if not violations:
                break
            retry_count += 1
            wc = story_word_count(text)
            hint = _retry_hint(
                violations,
                word_min=word_min,
                word_count=wc,
                name=name,
                gender=g,
            )
            retry_t0 = time.perf_counter()
            text, p_tok, c_tok = await _call_llm(
                client,
                system=system + "\n\n" + hint,
                user=user + "\n\n" + hint,
                word_target=word_target,
                temperature=max(0.5, temperature - 0.05 * (attempt + 1)),
                model=draft_model,
                mode=gen_mode,
            )
            meta.draft_latency_ms += int((time.perf_counter() - retry_t0) * 1000)
            total_prompt_tokens += p_tok
            total_completion_tokens += c_tok
            if story_word_count(text) >= story_word_count(best_text):
                best_text = text

        final_text = best_text or text
        final_violations = check_story(
            final_text,
            no_scary=no_scary,
            word_min=word_min,
            day_context=check_day,
            name=name,
            gender=g,
        )
        if rewrite_pass_for_mode(gen_mode, user_id) and final_violations:
            meta.rewrite_attempted = True
            polish_t0 = time.perf_counter()
            final_text, applied, p_tok, c_tok = await _maybe_polish_story(
                client,
                draft=final_text,
                name=name,
                hero=hero,
                word_target=word_target,
                word_min=word_min,
                no_scary=no_scary,
                day_context=check_day,
                polish_model=polish_model,
                gender=g,
                mode=gen_mode,
            )
            meta.polish_latency_ms = int((time.perf_counter() - polish_t0) * 1000)
            meta.rewrite_applied = applied
            total_prompt_tokens += p_tok
            total_completion_tokens += c_tok

        meta.used_llm = True
        meta.retry_count = retry_count
        meta.prompt_tokens = total_prompt_tokens
        meta.completion_tokens = total_completion_tokens
        meta.word_count = story_word_count(final_text)
        meta.latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "story_generated mode=%s ab=%s draft=%s polish_applied=%s hint=%s "
            "words=%s latency_ms=%s draft_ms=%s polish_ms=%s tokens=%s/%s retries=%s rescue=%s",
            gen_mode,
            variant,
            draft_model,
            meta.rewrite_applied,
            prompt_hint or "-",
            meta.word_count,
            meta.latency_ms,
            meta.draft_latency_ms,
            meta.polish_latency_ms,
            meta.prompt_tokens,
            meta.completion_tokens,
            retry_count,
            rescue_id or "-",
        )
        return final_text, meta
    except Exception:
        if best_text and story_word_count(best_text) >= 40:
            meta.used_llm = True
            meta.word_count = story_word_count(best_text)
            meta.retry_count = retry_count
            meta.prompt_tokens = total_prompt_tokens
            meta.completion_tokens = total_completion_tokens
            meta.latency_ms = int((time.perf_counter() - t0) * 1000)
            return best_text, meta
        meta.fallback = True
        story = fallback_story(
            gen_mode,
            name,
            hero,
            day_context,
            gender=gender,
            variety=variety,
            age=age,
            word_target=word_target,
        )
        meta.word_count = story_word_count(story)
        meta.latency_ms = int((time.perf_counter() - t0) * 1000)
        return story, meta


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Режет текст по лимиту символов (fallback, если не влезает в 2 части)."""
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts


def _split_story_at_paragraph(story: str, target: int) -> tuple[str, str]:
    """Делит сказку на две части по границе абзаца около target."""
    if target <= 0:
        return "", story
    split_at = story.rfind("\n\n", 0, target)
    if split_at < len(story) * 0.2:
        split_at = story.find("\n\n", target)
    if split_at < 0:
        split_at = target
    part1 = story[:split_at].strip()
    part2 = story[split_at:].strip()
    return part1, part2


def story_delivery_chunks(
    story: str,
    suffix: str = "",
    limit: int = TELEGRAM_MESSAGE_LIMIT,
) -> list[str]:
    """Длинные сказки — двумя сообщениями: текст + (продолжение + хвост)."""
    full = story + suffix
    if len(full) <= limit:
        return [full]

    if len(suffix) >= limit:
        return split_message(full, limit)

    max_tail = limit - len(suffix)
    part1, part2 = _split_story_at_paragraph(story, len(story) // 2)

    while part2 and len(part2) + len(suffix) > limit:
        earlier = story.rfind("\n\n", 0, max(0, len(part1) - 80))
        if earlier <= 0 or earlier == len(part1):
            break
        part1, part2 = story[:earlier].strip(), story[earlier:].strip()

    if not part1 or len(part2) + len(suffix) > limit:
        return split_message(full, limit)

    chunks: list[str] = []
    if part1:
        chunks.append(part1)
    chunks.append(part2 + suffix)
    return chunks
