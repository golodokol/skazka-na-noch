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


def check_story(text: str, *, no_scary: bool = True) -> list[str]:
    """Возвращает список нарушений; пустой список = ok."""
    violations: list[str] = []
    violations.extend(_find_violations(text, UNIVERSAL_BLOCK))
    if no_scary:
        violations.extend(_find_violations(text, NO_SCARY_BLOCK))
    # Вопрос в последних 200 символах — нарушение sleep-onset
    tail = text.strip()[-200:]
    if "?" in tail or "？" in tail:
        violations.append("question_in_ending")
    return violations
