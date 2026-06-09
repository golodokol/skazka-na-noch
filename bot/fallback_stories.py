"""Запасные сказки, если LLM недоступен."""

from __future__ import annotations

from typing import TYPE_CHECKING

from name_grammar import fallback_forms, name_genitive, normalize_gender

if TYPE_CHECKING:
    from story_variety import VarietyPlan

from story_craft import suggest_day_closure

TEMPLATES = {
    "tired": (
        "{intro} "
        "Вечером небо стало мягким, как плед, и звёзды зажгли маленькие ночники.\n\n"
        "{name} {wrapped} теплом и представил{gender_suffix}, как тихая волна сна "
        "медленно накрывает комнату. Сначала замирают игрушки, потом — шорох за окном, "
        "потом и мысли становятся пушистыми, как облака.\n\n"
        "Где-то рядом мама или папа шепнули: «Я рядом». "
        "И {name} {closed} глазки, будто закрывает книгу с хорошим концом — "
        "завтра будет новый день, а сейчас — только сон и покой."
    ),
    "medium": (
        "Однажды вечером {name} {found} на подушке крошечный лучик лунного света. "
        "Лучик шепнул: «Я провожу тебя в страну снов».\n\n"
        "Они шли по тропинке из мягких шагов. Слева росли деревья с листьями-колыбельками, "
        "справа — ручей, который напевал «ш-ш-ш». {hero_line}"
        "В середине пути {name} {met} своё сегодняшнее настроение — "
        "оно было как облачко: то пушистое, то чуть взъерошенное. "
        "Лучик сказал: «Его можно положить на ладонь — оно отдохнёт».\n\n"
        "В конце тропинки была дверь из звёзд. За ней — тихая комната, "
        "где уже ждала кроватка. {name} {lay}, лучик накрыл {cover_pron} одеялом из тишины, "
        "и глазки сами закрылись, как цветочки на ночь."
    ),
    "screen_free": (
        "«Давай посмотрим сказку глазами», — сказал взрослый {name}.\n\n"
        "Перед ним развернулся спокойный луг: трава шелестит, как страницы, "
        "а в небе плывёт луна-фонарик. {name} {see}, как зайчик укладывает морковку спать, "
        "как домик огней гаснет одно за другим. {hero_line}"
        "Ничего громкого, ничего быстрого — только мягкий ветер и тёплые мысли.\n\n"
        "В конце луг превращается в подушку облаков. "
        "{name} {feel}, как веки становятся тяжёлыми и приятными, "
        "и сон приходит, как добрый друг, которого ждали весь вечер."
    ),
    "today": (
        "Сегодня у {name_gen} {was_day} насыщенный день. "
        "Сначала {day_opening} Потом {name} {felt_change}, и к вечеру всё стало мягче.\n\n"
        "Мама или папа сели рядом и сказали: «Я с тобой». "
        "Вечером {day_closure}\n\n"
        "{name} {wrapped} теплом. {hero_line}"
        "Мысли стали мягче, дыхание — ровнее. "
        "И {name} {closed} глазки, будто закрывает книгу с хорошим концом — "
        "завтра будет новый день, а сейчас — только сон и покой."
    ),
}

VARIETY_TEMPLATE = (
    "Вечером {name} {was_in} {setting}. "
    "Рядом, как каждый вечер, {hero_line}"
    "Там {met} {helper}, и тихо сказал{helper_suffix}: «Пойдём со мной».\n\n"
    "{angle_scene}"
    "{name} {listened} и почувствовал{gender_suffix}, как всё вокруг становится мягче — "
    "словно {metaphor}.\n\n"
    "{day_block}"
    "Мама или папа шепнули: «Я рядом». "
    "{name} {closed} глазки, и сон пришёл, как тёплое одеяло — "
    "завтра будет новый день, а сейчас только покой."
)


def _scene_from_angle(angle: str, name: str) -> str:
    scene = angle.replace("герой", name).strip()
    if not scene:
        return ""
    scene = scene[0].upper() + scene[1:]
    if not scene.endswith("."):
        scene += "."
    return scene + " "


def _extra_paragraphs(name: str, hero: str, gender: str, age: int) -> str:
    """Дополнительные абзацы для запасной сказки — длиннее для старшего возраста."""
    g = normalize_gender(gender)
    gender_suffix = "а" if g == "f" else ""
    listened = "слушала" if g == "f" else "слушал"
    felt = "ей" if g == "f" else "ему"
    hero_phrase = f"рядом с {hero}" if hero.strip() else "в тихой комнате"
    blocks = [
        (
            f"Они с {name} {hero_phrase} шли медленно по мягкой тропинке. "
            f"Под ногами шуршали листья, а в воздухе пахло теплом и уютом."
        ),
        (
            f"{name} {listened}, как за окном тихо стучит дождь, и {felt} "
            f"становилось спокойнее с каждым шагом."
        ),
        (
            f"Любимый герой шепнул что-то доброе, и {name} улыбнул{gender_suffix}ся. "
            f"Вместе они нашли уголок, где было особенно мягко и тепло."
        ),
        (
            f"Над ними медленно зажигались маленькие звёзды, и {name} "
            f"представил{gender_suffix}, как каждая из них — крошечный ночник."
        ),
    ]
    count = min(len(blocks), max(0, age - 3))
    if count == 0:
        return ""
    return "\n\n".join(blocks[:count]) + "\n\n"


def _today_opening(day_context: str, name: str, gender: str) -> tuple[str, str]:
    """Начало и перелом для запасной «сегодня»-сказки — без дословной цитаты."""
    g = normalize_gender(gender)
    snippet = day_context.strip() if day_context else "обычный, но хороший"
    if len(snippet) > 80:
        snippet = snippet[:77] + "…"
    if g == "f":
        felt = "почувствовала"
        opening = (
            f"для {name} этот день начался с событий, похожих на маленькое приключение — "
            f"({snippet.lower()}). "
        )
    else:
        felt = "почувствовал"
        opening = (
            f"для {name} этот день начался с событий, похожих на маленькое приключение — "
            f"({snippet.lower()}). "
        )
    return opening, felt


def _format_base(
    mode: str,
    name: str,
    hero: str,
    day_context: str,
    gender: str,
) -> dict:
    hero_line = (
        f"Рядом с {name} шёл {hero} — разговаривал, играл и задавал мягкие вопросы. "
        if hero
        else ""
    )
    day_snippet = day_context.strip() if day_context else "обычный, но хороший"
    g = normalize_gender(gender)
    forms = fallback_forms(g)
    name_gen = name_genitive(name, g)
    gender_suffix = "а" if g == "f" else ""
    was_day = "была" if g == "f" else "был"
    day_opening, felt_change = _today_opening(day_context, name, gender)
    closure = suggest_day_closure(day_context, seed=hash(name) % 997)
    if closure[0].islower():
        closure = closure[0].upper() + closure[1:]
    day_closure = closure if closure.endswith(".") else closure + "."
    return {
        "name": name,
        "name_gen": name_gen,
        "was_day": was_day,
        "day_opening": day_opening,
        "felt_change": felt_change,
        "day_closure": day_closure,
        "hero_line": hero_line,
        "day_snippet": day_snippet,
        "gender_suffix": gender_suffix,
        **forms,
    }


def _variety_fallback(
    mode: str,
    name: str,
    hero: str,
    day_context: str,
    gender: str,
    variety: VarietyPlan,
    *,
    age: int = 4,
) -> str:
    g = normalize_gender(gender)
    forms = fallback_forms(g)
    gender_suffix = "а" if g == "f" else ""
    was_in = "оказалась" if g == "f" else "оказался"
    listened = "слушала" if g == "f" else "слушал"
    helper_suffix = "а" if variety.helper_id in ("pillow_owl", "star_baker", "cloud_cat", "snow_fox", "warm_moth") else ""
    hero_label = hero.strip() or "любимая игрушка"
    hero_line = f"рядом с {hero_label} они разговаривали и играли. "

    day_block = ""
    if day_context:
        name_gen = name_genitive(name, g)
        was_day = "была" if g == "f" else "был"
        opening, felt = _today_opening(day_context, name, gender)
        closure = suggest_day_closure(day_context, seed=hash(name) % 997)
        day_block = (
            f"Сначала {opening}"
            f"Потом {name} {felt}, и к вечеру {closure}.\n\n"
        )

    text = VARIETY_TEMPLATE.format(
        name=name,
        hero_line=hero_line,
        setting=variety.setting,
        helper=variety.helper,
        helper_suffix=helper_suffix,
        angle_scene=_scene_from_angle(variety.angle, name),
        metaphor=variety.metaphor,
        day_block=day_block,
        was_in=was_in,
        listened=listened,
        gender_suffix=gender_suffix,
        **forms,
    )
    extra = _extra_paragraphs(name, hero, gender, age)
    if extra:
        parts = text.rsplit("\n\n", 1)
        text = parts[0] + "\n\n" + extra + parts[1] if len(parts) == 2 else text + "\n\n" + extra

    if mode == "screen_free":
        text = (
            f"«Давай посмотрим глазами», — сказал взрослый {name}.\n\n"
            + text
        )

    return text


def fallback_story(
    mode: str,
    name: str,
    hero: str = "",
    day_context: str = "",
    gender: str = "m",
    variety: VarietyPlan | None = None,
    age: int = 4,
    word_target: int = 0,
) -> str:
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 4

    if variety:
        return _variety_fallback(
            mode, name, hero, day_context, gender, variety, age=age
        )

    template = TEMPLATES.get(mode, TEMPLATES["tired"])
    fmt = _format_base(mode, name, hero, day_context, gender)
    text = template.format(**fmt)
    if mode != "today" and day_context:
        text = (
            f"Сегодня у {fmt['name_gen']} {fmt['was_day']} такой день: {day_context.strip()}\n\n"
            + text
        )
    extra = _extra_paragraphs(name, hero, gender, age)
    if extra:
        parts = text.rsplit("\n\n", 1)
        text = parts[0] + "\n\n" + extra + parts[1] if len(parts) == 2 else text + "\n\n" + extra
    return text
