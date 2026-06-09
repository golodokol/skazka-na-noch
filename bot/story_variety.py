"""Подбор уникального сюжета и анти-повтор для каждой новой сказки."""
from __future__ import annotations

import random
from dataclasses import dataclass

from story_craft import METAPHORS_BY_AGE, age_metaphor_band

SETTINGS: list[tuple[str, str]] = [
    ("cozy_room", "уютная детская комната, вечер, ночник и игрушки на полке"),
    ("moon_meadow", "лунная лужайка с росой и тихими светлячками"),
    ("rain_window", "окно, за которым мягкий дождь стучит «ка-ка-ка»"),
    ("snow_yard", "тихий зимний дворик, снег светится в темноте"),
    ("seaside_dusk", "берег моря на закате, волны шепчут «ш-ш»"),
    ("forest_edge", "опушка леса, не глубоко — только край, безопасно"),
    ("cloud_train", "облачный поезд, который едет медленно в ночь"),
    ("star_balcony", "балкон или подоконник под звёздным небом"),
    ("kitchen_warm", "тёплая кухня с запахом молока и пледа"),
    ("garden_night", "ночной сад, где цветы закрывают лепестки"),
    ("attic_quiet", "тихий чердак с лучом луны в окошке"),
    ("river_bank", "тихий берег реки, вода отражает луну"),
    ("pillow_fort", "подушечная крепость в комнате — мягкий лабиринт"),
    ("library_nook", "уголок с книгами, страницы шелестят как листья"),
]

HELPERS: list[tuple[str, str]] = [
    ("firefly", "светлячок-проводник с мягким жёлтым светом"),
    ("old_turtle", "мудрая черепаха, говорит медленно и тепло"),
    ("wind_friend", "дружелюбный ветерок, который умеет только шептать"),
    ("moon_hare", "лунный зайчик с серебристым ушком"),
    ("pillow_owl", "сонная совёнок на ветке, не пугающая"),
    ("star_baker", "звёздная пекарь, печёт «печеньки снов»"),
    ("cloud_cat", "кошка из облака, мурлычет тихо"),
    ("river_fish", "золотая рыбка в пруде, махает хвостом"),
    ("dream_boat", "лодочка из тумана, качает как колыбель"),
    ("night_garden", "садовник ночи, поливает цветы лунным светом"),
    ("paper_crane", "бумажный журавлик, который умеет летать медленно"),
    ("snow_fox", "белая лисичка, оставляет следы-сердечки на снегу"),
    ("music_box", "музыкальная шкатулка, играет одну колыбельную"),
    ("warm_moth", "мягкая моль у лампы, не страшная, светится"),
]

PLOT_ANGLES: list[tuple[str, str]] = [
    ("gift_object", "герой находит маленький подарок сна (камушек, лист, лучик)"),
    ("help_sleepy", "герой помогает кому-то уснуть — игрушке, цветку, зверьку"),
    ("collect_sounds", "герой собирает тихие звуки вечера в «коробочку»"),
    ("paint_dream", "герой «рисует» сон воздухом — мягкие цвета"),
    ("bridge_cross", "переход через мостик/порог — символ засыпания"),
    ("pack_day", "герой складывает день в рюкзачок и закрывает молнию"),
    ("follow_thread", "герой идёт по ниточке/следу, который ведёт к кровати"),
    ("warm_drink", "волшебный глоток тепла — чай, молоко, как облачко"),
    ("lullaby_echo", "эхо колыбельной откуда-то из далёкого неба"),
    ("mirror_calm", "герой видит в зеркале/лужице уже спокойное лицо"),
    ("train_stops", "поезд/корабль снов останавливается на станции «Отдых»"),
    ("blanket_sky", "небо накрывает мир одеялом — герой под ним"),
]

HERO_ROLES = [
    "Ребёнок — главный герой; любимый герой из профиля — его постоянный напарник на всю сказку.",
    "Ребёнок принимает решения; любимый герой рядом и поддерживает в каждом абзаце.",
    "Ребёнок и любимый герой идут вместе от начала до конца, как два друга.",
]


@dataclass
class VarietyPlan:
    setting_id: str
    setting: str
    helper_id: str
    helper: str
    angle_id: str
    angle: str
    metaphor: str
    hero_role: str
    avoid_block: str
    fresh_boost: int


def _used_ids(memories: list[dict], key: str) -> set[str]:
    return {m[key] for m in memories if m.get(key)}


def _pick_excluding(
    pool: list[tuple[str, str]],
    used: set[str],
    rng: random.Random,
) -> tuple[str, str]:
    fresh = [(i, t) for i, t in pool if i not in used]
    if fresh:
        return rng.choice(fresh)
    return rng.choice(pool)


def _pick_metaphor(age: int, used_texts: set[str], rng: random.Random) -> str:
    band = age_metaphor_band(age)
    options = [m for m in METAPHORS_BY_AGE[band] if m not in used_texts]
    if not options:
        options = METAPHORS_BY_AGE[band]
    return rng.choice(options)


def _build_avoid_block(memories: list[dict]) -> str:
    if not memories:
        return "Нет предыдущих сказок — всё равно придумай свежий сюжет."

    lines = ["Недавние сказки — ЗАПРЕЩЕНО повторять:"]
    for i, m in enumerate(memories[:8], 1):
        parts = []
        if m.get("setting_id"):
            parts.append(f"сеттинг={m['setting_id']}")
        if m.get("helper_id"):
            parts.append(f"помощник={m['helper_id']}")
        if m.get("angle_id"):
            parts.append(f"угол={m['angle_id']}")
        if m.get("metaphor"):
            parts.append(f"метафора «{m['metaphor'][:40]}…»")
        if m.get("snippet"):
            parts.append(f"фрагмент «{m['snippet'][:55]}…»")
        lines.append(f"{i}. {', '.join(parts)}")
    lines.append(
        "Новая сказка — другие место, персонажи, действия и метафоры. "
        "Не перефразируй старые сказки."
    )
    return "\n".join(lines)


def pick_variety(
    age: int,
    memories: list[dict],
    *,
    force_fresh: bool = False,
    seed: int | None = None,
) -> VarietyPlan:
    rng = random.Random(seed)
    used_settings = _used_ids(memories, "setting_id")
    used_helpers = _used_ids(memories, "helper_id")
    used_angles = _used_ids(memories, "angle_id")
    used_metaphors = {m.get("metaphor", "") for m in memories if m.get("metaphor")}

    setting_id, setting = _pick_excluding(SETTINGS, used_settings, rng)
    helper_id, helper = _pick_excluding(HELPERS, used_helpers, rng)
    angle_id, angle = _pick_excluding(PLOT_ANGLES, used_angles, rng)
    metaphor = _pick_metaphor(age, used_metaphors, rng)
    hero_role = rng.choice(HERO_ROLES)
    fresh_boost = len(memories) + (3 if force_fresh else 0)

    return VarietyPlan(
        setting_id=setting_id,
        setting=setting,
        helper_id=helper_id,
        helper=helper,
        angle_id=angle_id,
        angle=angle,
        metaphor=metaphor,
        hero_role=hero_role,
        avoid_block=_build_avoid_block(memories),
        fresh_boost=fresh_boost,
    )


def variety_user_block(
    plan: VarietyPlan,
    *,
    child_name: str,
    favorite_hero: str,
    force_fresh: bool = False,
) -> str:
    hero_label = favorite_hero.strip() or "любимая игрушка или зверёк ребёнка"
    lines = [
        "=== УНИКАЛЬНЫЙ СЮЖЕТ (новые место и события) ===",
        "",
        f"ЛЮБИМЫЙ ГЕРОЙ «{hero_label}» — ГЛАВНЫЙ НАПАРНИК {child_name} (ОБЯЗАТЕЛЬНО):",
        f"— «{hero_label}» в сказке от первого до последнего абзаца, по имени минимум 5 раз.",
        f"— С ним диалоги, игра, мягкие вопросы — он НЕ исчезает после начала.",
        f"— Запрещено заменять «{hero_label}» другим персонажем или убирать из текста.",
        "",
        f"Сеттинг (обязательно): {plan.setting}",
        f"Гость сюжета (одна встреча вечером, ДОПОЛНИТЕЛЬНО к «{hero_label}», не вместо него): {plan.helper}",
        f"Событие (покажи в действии и диалогах, не называй «сюжет»): {plan.angle}",
        f"Образ/ощущение (вплети в описание, не произноси слово «метафора»): {plan.metaphor}",
        f"Роли: {plan.hero_role}",
        "В тексте сказки ЗАПРЕЩЕНЫ служебные слова: «метафора», «сюжет был», «сюжетный угол», "
        "«символ», «это значит» — только живая проза, как в детской книге.",
        plan.avoid_block,
    ]
    if force_fresh:
        lines.insert(
            1,
            "Родитель нажал «Ещё одну» — нужна СОВЕРШЕННО ДРУГАЯ история, но «"
            + hero_label
            + "» остаётся напарником.",
        )
    return "\n".join(lines)


def memory_from_plan(plan: VarietyPlan, mode: str, snippet: str) -> dict:
    return {
        "mode": mode,
        "setting_id": plan.setting_id,
        "helper_id": plan.helper_id,
        "angle_id": plan.angle_id,
        "metaphor": plan.metaphor,
        "snippet": snippet[:160],
    }
