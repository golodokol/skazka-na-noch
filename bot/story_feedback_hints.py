"""Подсказки в промпт на основе feedback родителя (фаза 6)."""

SCARY_FEEDBACK_EXTRA = """
ОТЗЫВ РОДИТЕЛЯ: прошлая сказка испугала или тревожила.
Усиленный режим мягкости: без тени как угрозы, без громких звуков и неожиданных поворотов,
без «вдруг», «исчез», «остался один» — только уют, предсказуемость и тепло.
"""

USER_PROMPT_HINTS: dict[str, str] = {
    "boring": (
        "Предыдущая сказка показалась скучной — добавь больше живых деталей, "
        "диалога и неожиданных мягких штрихов; меньше описаний погоды и шаблонных «мягко-тихо»."
    ),
    "other": (
        "Родитель просил другой стиль — ближе к быту ребёнка: комната, игрушки, "
        "вечерний ритуал, знакомые предметы."
    ),
    "not_calming": (
        "Предыдущая сказка не успокоила — ещё мягче, больше замедления, "
        "сенсорного тепла и ритма колыбельной к финалу."
    ),
}

# bad_reason из клавиатуры → ключ подсказки (пусто = только length/profile flow)
BAD_REASON_TO_HINT: dict[str, str] = {
    "scary": "scary",
    "boring": "boring",
    "not_calming": "not_calming",
    "other": "other",
}


def user_prompt_hint(hint_key: str) -> str:
    text = USER_PROMPT_HINTS.get(hint_key, "")
    if not text:
        return ""
    return f"УЧТИ ОТЗЫВ РОДИТЕЛЯ О ПРОШЛОЙ СКАЗКЕ:\n{text}"


def scary_feedback_extra(hint_key: str) -> str:
    if hint_key == "scary":
        return SCARY_FEEDBACK_EXTRA.strip()
    return ""
