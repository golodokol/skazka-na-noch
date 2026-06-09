"""Проверка сгенерированных сказок и строгий retry."""
import re

NO_SCARY_RULES = (
    "Не используй: монстров, пугающих взрослых, Бабу-Ягу, Лешего, "
    "темноту как угрозу, потерю родителей, панику, тюрьмы, болезни, смерть, "
    "ранения, кровь, оружие."
)

SCARY_RELAXED_RULES = (
    "Избегай явного ужаса и насилия. Допустимы мягкие приключения без страха."
)

# Паттерны для post-check (регистронезависимо)
UNIVERSAL_BLOCK = [
    r"\bкров[ьи]\w*",
    r"\bумер\w*",
    r"\bубил\w*",
    r"\bубью\w*",
    r"\bоружи\w*",
    r"\bнасили\w*",
    r"\bты\s+плох\w*",
    r"\bстыд\w*",
]

NO_SCARY_BLOCK = [
    r"\bмонстр\w*",
    r"\bбаба[-\s]?яга",
    r"\bлеш\w*",
    r"\bстраш\w*",
    r"\bужас\w*",
    r"\bкошмар\w*",
    r"\bпаник\w*",
    r"\bпотеря\w*\s+мам",
    r"\bпотеря\w*\s+пап",
    r"\bзл\w*\s+взросл",
    r"\bпиков\w*\s+дам",
]

# Мета-язык из промпта, который не должен попадать в текст для детей
META_NARRATION_BLOCK = [
    r"метафора\s+(этого|вечера|дня|сказки|ночи)",
    r"главная\s+метафора",
    r"сюжет\s+был",
    r"сюжетный\s+угол",
    r"это\s+метафора",
    r"как\s+метафора",
    r"была\s+метафора",
    r"история\s+была\s+о",
    r"история\s+про\s+то",
    r"по\s+сюжету",
    r"символ\s+(того|этого|засыпания|сна)",
]

META_RETRY_HINT = (
    "Убери служебные слова ({violations}): «метафора», «сюжет был», «сюжетный угол». "
    "Перепиши те же события живой прозой — как в детской книге, без объяснений для читателя."
)

PROSE_VIOLATIONS = frozenset({"low_preposition_density", "paragraphs_missing_prepositions"})

LENGTH_VIOLATIONS = frozenset({"story_too_short"})

TODAY_VIOLATIONS = frozenset({"verbatim_day_context"})

PROSE_RETRY_HINT = (
    "Текст слишком рубленый, мало предлогов и местоимений ({violations}). "
    "Перепиши связными предложениями: «она легла на кровать», «рядом с ним», «под одеялом», "
    "«для неё это было тепло» — в каждом предложении предлог или местоимение. "
    "Не цепочка «Имя сделала. Имя легла.»"
)

LENGTH_RETRY_HINT = (
    "Текст слишком короткий ({word_count} слов, нужно минимум {word_min}). "
    "Разверни историю: больше абзацев, диалогов между героем и любимым персонажем, "
    "описаний (звук, тепло, свет). Не заканчивай раньше времени."
)

TODAY_RETRY_HINT = (
    "Текст повторяет слова родителя дословно ({violations}). "
    "Перескажи день как автор: что было → как прошло → что почувствовал герой → "
    "как день мягко завершился. Свои формулировки, связки «сначала — потом — поэтому»."
)

_PREP_MARKERS = (
    " в ", " во ", " на ", " у ", " за ", " под ", " к ", " ко ", " от ", " ото ",
    " про ", " с ", " со ", " для ", " без ", " между ", " через ", " над ",
    " перед ", " при ", " из ", " изо ", " по ", " до ", " о ", " об ", " обо ",
)
_PRON_MARKERS = (
    " он ", " она ", " они ", " его ", " ей ", " им ", " их ", " ему ",
    " ним ", " неё ", " ней ", " нем ", " мы ", " свой ", " своя ", " свои ",
    " этот ", " эта ", " это ", " эти ", " тот ", " та ", " то ", " те ",
    " здесь ", " там ", " тут ",
)

STRICT_RETRY_HINT = (
    "СТРОГИЙ РЕЖИМ: предыдущий текст нарушил правила ({violations}). "
    "Перепиши сказку полностью: ещё мягче, без запрещённых образов, "
    "с обязательным засыпанием героя в конце."
)


def no_scary_rules(no_scary: bool) -> str:
    return NO_SCARY_RULES if no_scary else SCARY_RELAXED_RULES


def _find_violations(text: str, patterns: list[str]) -> list[str]:
    found = []
    lower = text.lower()
    for pat in patterns:
        if re.search(pat, lower, re.IGNORECASE):
            found.append(pat)
    return found


def _grammar_markers(text: str) -> int:
    padded = f" {text.lower()} "
    return sum(padded.count(m) for m in _PREP_MARKERS) + sum(
        padded.count(m) for m in _PRON_MARKERS
    )


def _word_count(text: str) -> int:
    return len(re.findall(r"[а-яё]+", text.lower(), re.IGNORECASE))


def check_connected_prose(text: str) -> list[str]:
    """Проверка связности: достаточно предлогов и местоимений."""
    words = _word_count(text)
    if words < 40:
        return []

    markers = _grammar_markers(text)
    if markers / words < 0.055:
        return ["low_preposition_density"]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    thin = 0
    substantive = 0
    for paragraph in paragraphs:
        p_words = _word_count(paragraph)
        if p_words < 15:
            continue
        substantive += 1
        if _grammar_markers(paragraph) < 2:
            thin += 1
    if substantive and thin > max(1, substantive * 0.35):
        return ["paragraphs_missing_prepositions"]
    return []


def check_story_length(text: str, word_min: int) -> list[str]:
    """Сказка слишком короткая относительно возраста и режима."""
    if word_min <= 0:
        return []
    if _word_count(text) < int(word_min * 0.45):
        return ["story_too_short"]
    return []


def story_word_count(text: str) -> int:
    return _word_count(text)


def check_today_verbatim(text: str, day_context: str) -> list[str]:
    """Сказка не должна цитировать заметку родителя."""
    ctx = day_context.strip().lower()
    if len(ctx) < 12:
        return []
    body = text.lower()
    # длинный фрагмент заметки в тексте
    for size in (min(len(ctx), 60), min(len(ctx), 40)):
        if size >= 15 and ctx[:size] in body:
            return ["verbatim_day_context"]
    return []


def check_story(
    text: str,
    *,
    no_scary: bool = True,
    word_min: int = 0,
    day_context: str = "",
) -> list[str]:
    """Возвращает список нарушений; пустой список = ok."""
    violations: list[str] = []
    violations.extend(_find_violations(text, UNIVERSAL_BLOCK))
    violations.extend(_find_violations(text, META_NARRATION_BLOCK))
    violations.extend(check_connected_prose(text))
    violations.extend(check_story_length(text, word_min))
    if day_context:
        violations.extend(check_today_verbatim(text, day_context))
    if no_scary:
        violations.extend(_find_violations(text, NO_SCARY_BLOCK))
    # Вопрос в последних 200 символах — нарушение sleep-onset
    tail = text.strip()[-200:]
    if "?" in tail or "？" in tail:
        violations.append("question_in_ending")
    return violations
