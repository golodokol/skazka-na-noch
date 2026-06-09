"""Пол ребёнка и правила согласования в русском тексте сказки."""

Gender = str  # "m" | "f"

GENDER_LABELS = {"m": "мальчик", "f": "девочка"}
GENDER_ROD = {"m": "мужской род", "f": "женский род"}
GENDER_PRONOUN = {"m": "он", "f": "она"}

_morph_analyzer = None


def normalize_gender(value: str | None) -> Gender:
    if not value:
        return "m"
    v = value.strip().lower()
    if v in ("f", "female", "girl", "девочка", "ж", "жена"):
        return "f"
    return "m"


def _preserve_case(original: str, inflected: str) -> str:
    if not original or not inflected:
        return inflected
    if original[0].isupper():
        return inflected[0].upper() + inflected[1:]
    return inflected


def _pymorphy_genitive(name: str, gender: Gender) -> str | None:
    global _morph_analyzer
    try:
        if _morph_analyzer is None:
            import pymorphy3

            _morph_analyzer = pymorphy3.MorphAnalyzer()
        tag_hint = "femn" if gender == "f" else "masc"
        parsed = _morph_analyzer.parse(name)
        chosen = parsed[0]
        for candidate in parsed:
            if tag_hint in candidate.tag:
                chosen = candidate
                break
        form = chosen.inflect({"gent"})
        if form and form.word:
            return _preserve_case(name, form.word)
    except Exception:
        return None
    return None


def _heuristic_genitive(name: str, gender: Gender) -> str:
    """Запасное склонение, если pymorphy недоступен."""
    low = name.lower()
    g = normalize_gender(gender)

    if low.endswith("ия"):
        return _preserve_case(name, name[:-2] + "ии")
    if low.endswith("ья"):
        return _preserve_case(name, name[:-2] + "ьи")
    if low.endswith("ина") or low.endswith("ена"):
        return _preserve_case(name, name[:-1] + "ы")
    if low.endswith("ша") or low.endswith("ча") or low.endswith("жа"):
        return _preserve_case(name, name[:-1] + "и")
    if low.endswith("я"):
        return _preserve_case(name, name[:-1] + "и")
    if low.endswith("а"):
        return _preserve_case(name, name[:-1] + "ы")
    if low.endswith("й"):
        return _preserve_case(name, name[:-1] + "я")
    if low.endswith("ь"):
        return _preserve_case(name, name[:-1] + "и")
    if g == "m":
        return _preserve_case(name, name + "а")
    return _preserve_case(name, name + "ы")


def name_genitive(name: str, gender: str | None = "m") -> str:
    """Имя в родительном падеже: «у Маши», «у Арины», «у Ивана»."""
    name = name.strip()
    if len(name) < 2:
        return name
    g = normalize_gender(gender)
    result = _pymorphy_genitive(name, g)
    if result:
        return result
    return _heuristic_genitive(name, g)


def today_ask(name: str, gender: str | None = "m") -> str:
    gen = name_genitive(name, gender)
    return (
        f"Расскажите одной-двумя фразами — что было у {gen} сегодня и как прошло?\n"
        f"Например: «поссорился с другом, потом помирились» или «устал после садика»."
    )


def grammar_block(name: str, gender: Gender) -> str:
    """Блок для system prompt: согласование имён, глаголов и местоимений."""
    gender = normalize_gender(gender)
    label = GENDER_LABELS[gender]
    rod = GENDER_ROD[gender]
    pron = GENDER_PRONOUN[gender]
    name_gen = name_genitive(name, gender)

    if gender == "f":
        examples_ok = (
            f"«{name} устала после долгого дня», «{name} легла на кровать рядом с игрушкой», "
            f"«она укуталась в тёплый плед», «для {name_gen} это было мягко», "
            f"«{name} закрыла глазки под одеялом»"
        )
        examples_bad = (
            f"«{name} устал», «{name} закрыл», «он укутался» (если речь о {name}), "
            f"«{name} устала. {name} легла. {name} спит.» (обрывки без предлогов)"
        )
        verb_hints = (
            "устала, закрыла, уснула, легла, укуталась, почувствовала, "
            "увидела, улыбнулась, дышала, стала тихой"
        )
        adj_hints = "маленькая, тихая, уставшая, смелая, спокойная"
    else:
        examples_ok = (
            f"«{name} устал после долгого дня», «{name} лёг на кровать рядом с игрушкой», "
            f"«он укутался в тёплый плед», «для {name_gen} это было мягко», "
            f"«{name} закрыл глазки под одеялом»"
        )
        examples_bad = (
            f"«{name} устала», «{name} закрыла», «она укуталась» (если речь о {name}), "
            f"«{name} устал. {name} лёг. {name} спит.» (обрывки без предлогов)"
        )
        verb_hints = (
            "устал, закрыл, уснул, лёг, укутался, почувствовал, "
            "увидел, улыбнулся, дышал, стал тихим"
        )
        adj_hints = "маленький, тихий, уставший, смелый, спокойный"

    return f"""ПОЛ И ГРАММАТИКА (обязательно):
Пол ребёнка: {label} ({rod}).
Имя в именительном падеже: {name}.
Имя в родительном падеже: {name_gen} (после «у {name_gen}», «для {name_gen}»).
Местоимение о герое: только «{pron}» — не путать с другим родом.
Согласуй с {name} все глаголы прошедшего времени, краткие прилагательные и причастия.
Типичные формы: {verb_hints}; прилагательные: {adj_hints}.
Пиши связными предложениями с предлогами (в, на, у, с, к, для, от, под, за, про) — не цепочкой коротких фраз.
Правильно: {examples_ok}.
Запрещено: {examples_bad}."""


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
