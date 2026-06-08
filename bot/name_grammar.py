"""Пол ребёнка и правила согласования в русском тексте сказки."""

Gender = str  # "m" | "f"

GENDER_LABELS = {"m": "мальчик", "f": "девочка"}
GENDER_ROD = {"m": "мужской род", "f": "женский род"}
GENDER_PRONOUN = {"m": "он", "f": "она"}


def normalize_gender(value: str | None) -> Gender:
    if not value:
        return "m"
    v = value.strip().lower()
    if v in ("f", "female", "girl", "девочка", "ж", "жена"):
        return "f"
    return "m"


def grammar_block(name: str, gender: Gender) -> str:
    """Блок для system prompt: согласование имён, глаголов и местоимений."""
    gender = normalize_gender(gender)
    label = GENDER_LABELS[gender]
    rod = GENDER_ROD[gender]
    pron = GENDER_PRONOUN[gender]

    if gender == "f":
        examples_ok = (
            f"«{name} устала», «{name} закрыла глазки», «она укуталась», "
            f"«маленькая {name}», «{name} уснула», «{name} почувствовала тепло»"
        )
        examples_bad = (
            f"«{name} устал», «{name} закрыл», «он укутался» (если речь о {name}), "
            f"«маленький {name}»"
        )
        verb_hints = (
            "устала, закрыла, уснула, легла, укуталась, почувствовала, "
            "увидела, улыбнулась, дышала, стала тихой"
        )
        adj_hints = "маленькая, тихая, уставшая, смелая, спокойная"
    else:
        examples_ok = (
            f"«{name} устал», «{name} закрыл глазки», «он укутался», "
            f"«маленький {name}», «{name} уснул», «{name} почувствовал тепло»"
        )
        examples_bad = (
            f"«{name} устала», «{name} закрыла», «она укуталась» (если речь о {name}), "
            f"«маленькая {name}»"
        )
        verb_hints = (
            "устал, закрыл, уснул, лёг, укутался, почувствовал, "
            "увидел, улыбнулся, дышал, стал тихим"
        )
        adj_hints = "маленький, тихий, уставший, смелый, спокойный"

    return f"""ПОЛ И ГРАММАТИКА (обязательно):
Пол ребёнка: {label} ({rod}).
Имя в именительном падеже: {name}.
Местоимение о герое: только «{pron}» — не путать с другим родом.
Согласуй с {name} все глаголы прошедшего времени, краткие прилагательные и причастия.
Типичные формы: {verb_hints}; прилагательные: {adj_hints}.
Правильно: {examples_ok}.
Запрещено: {examples_bad}.
Имя {name} в тексте — 2–4 раза; в косвенных падежах склоняй осторожно (Маша → у Маши), при сомнении — именительный."""


def fallback_forms(gender: Gender) -> dict[str, str]:
    """Формы для запасных сказок без LLM."""
    if normalize_gender(gender) == "f":
        return {
            "intro": "Жила-была {name} — добрая и немного уставшая после долгого дня.",
            "wrapped": "укуталась",
            "closed": "закрыла",
            "found": "нашла",
            "met": "встретила",
            "lay": "легла",
            "cover_pron": "её",
            "see": "видит",
            "feel": "чувствует",
        }
    return {
        "intro": "Жил-был {name} — добрый и немного уставший после долгого дня.",
        "wrapped": "укутался",
        "closed": "закрыл",
        "found": "нашёл",
        "met": "встретил",
        "lay": "лёг",
        "cover_pron": "его",
        "see": "видит",
        "feel": "чувствует",
    }
