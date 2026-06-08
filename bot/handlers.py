import asyncio

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import db
from keyboards import (
    BUTTON_TO_MODE,
    feedback_kb,
    gender_kb,
    main_menu_kb,
    profile_kb,
    reply_menu_kb,
    skip_hero_kb,
)
from name_grammar import GENDER_LABELS, normalize_gender
from story_generator import generate_story, split_message
from texts import (
    AFTER_STORY,
    ASK_AGE,
    ASK_GENDER,
    ASK_HERO,
    ASK_NAME,
    FEEDBACK_PROMPT,
    GENERATING,
    HELP_TEXT,
    NO_PROFILE_HINT,
    ONBOARDING_DONE,
    PRIVACY_TEXT,
    REPLY_MENU_HINT,
    SCREEN_FREE_HINT,
    TODAY_ASK,
    WELCOME_NEW,
    WELCOME_RETURN,
)

router = Router()


class Onboard(StatesGroup):
    name = State()
    gender = State()
    age = State()
    hero = State()


class EditProfile(StatesGroup):
    name = State()
    age = State()
    hero = State()


class TodayFlow(StatesGroup):
    context = State()


async def show_menu(message: Message, *, returning: bool = False) -> None:
    profile = await db.get_profile(message.from_user.id)
    if profile:
        text = WELCOME_RETURN.format(name=profile["name"])
    else:
        text = WELCOME_NEW
    await message.answer(text, reply_markup=main_menu_kb())
    hint = REPLY_MENU_HINT if not returning else "👇"
    await message.answer(hint, reply_markup=reply_menu_kb())


async def profile_or_default(telegram_id: int) -> tuple[dict, bool]:
    profile = await db.get_profile(telegram_id)
    if profile:
        return profile, True
    return {
        "name": "малыш",
        "age_years": 4,
        "gender": "m",
        "favorite_hero": "",
        "no_scary": True,
        "last_mode": None,
        "length_pref": 1.0,
    }, False


async def start_onboarding(message: Message, state: FSMContext) -> None:
    await message.answer(WELCOME_NEW)
    await message.answer(ASK_NAME)
    await state.set_state(Onboard.name)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await db.ensure_user(message.from_user.id)
    await show_menu(message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu_kb())


@router.message(F.text == "❓ Помощь")
async def reply_help(message: Message) -> None:
    await cmd_help(message)


@router.message(F.text == "🏠 Меню")
async def reply_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_menu(message, returning=True)


@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(PRIVACY_TEXT)


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    profile = await db.get_profile(message.from_user.id)
    if not profile:
        await start_onboarding(message, state)
        return
    await send_profile(message)


@router.message(F.text == "⚙️ Профиль")
async def reply_profile(message: Message, state: FSMContext) -> None:
    await cmd_profile(message, state)


@router.message(Command("story"))
async def cmd_story(message: Message, state: FSMContext) -> None:
    profile, _ = await profile_or_default(message.from_user.id)
    mode = profile.get("last_mode") or "tired"
    await run_story_generation(message, state, mode)


async def send_profile(message: Message) -> None:
    profile = await db.get_profile(message.from_user.id)
    if not profile:
        await message.answer("Профиль не настроен. Нажмите /start")
        return
    hero = profile["favorite_hero"] or "не указан"
    scary = "да" if profile["no_scary"] else "нет"
    gender_label = GENDER_LABELS.get(normalize_gender(profile.get("gender")), "мальчик")
    text = (
        f"Профиль: {profile['name']}, {profile['age_years']} лет ({gender_label})\n"
        f"Герой: {hero}\n"
        f"Без страшного: {scary}"
    )
    await message.answer(text, reply_markup=profile_kb())


@router.message(Onboard.name)
async def onboard_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Напишите имя хотя бы из 2 букв.")
        return
    await state.update_data(name=name)
    await message.answer(ASK_GENDER, reply_markup=gender_kb(prefix="onboard"))
    await state.set_state(Onboard.gender)


@router.callback_query(F.data.startswith("onboard:gender:"))
async def onboard_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = callback.data.split(":")[-1]
    if gender not in ("m", "f"):
        await callback.answer()
        return
    await state.update_data(gender=gender)
    await callback.message.answer(ASK_AGE)
    await state.set_state(Onboard.age)
    await callback.answer()


@router.message(Onboard.age)
async def onboard_age(message: Message, state: FSMContext) -> None:
    try:
        age = int((message.text or "").strip())
    except ValueError:
        await message.answer("Введите число от 2 до 7.")
        return
    if age < 2 or age > 7:
        await message.answer("Пока поддерживаем возраст 2–7 лет.")
        return
    await state.update_data(age_years=age)
    await message.answer(ASK_HERO, reply_markup=skip_hero_kb())
    await state.set_state(Onboard.hero)


@router.message(Onboard.hero)
async def onboard_hero(message: Message, state: FSMContext) -> None:
    hero = (message.text or "").strip()
    if hero in ("-", "—", "пропустить"):
        hero = ""
    data = await state.get_data()
    await db.save_profile(
        message.from_user.id,
        data["name"],
        data["age_years"],
        hero,
        gender=data.get("gender", "m"),
    )
    await state.clear()
    await message.answer(ONBOARDING_DONE)
    await show_menu(message, returning=True)


@router.callback_query(F.data == "onboard:skip_hero")
async def onboard_skip_hero(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "name" not in data:
        await callback.answer("Начните с /start")
        return
    await db.save_profile(
        callback.from_user.id,
        data["name"],
        data.get("age_years", 4),
        "",
        gender=data.get("gender", "m"),
    )
    await state.clear()
    await callback.message.answer(ONBOARDING_DONE)
    await show_menu(callback.message, returning=True)
    await callback.answer()


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_menu(callback.message, returning=True)
    await callback.answer()


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery, state: FSMContext) -> None:
    profile = await db.get_profile(callback.from_user.id)
    if not profile:
        await callback.answer()
        await start_onboarding(callback.message, state)
        return
    await send_profile(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("prof:"))
async def cb_prof_edit(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":")[1]
    prompts = {
        "name": ("Новое имя ребёнка:", EditProfile.name),
        "age": ("Новый возраст (2–7):", EditProfile.age),
        "hero": ("Любимый герой:", EditProfile.hero),
    }
    if field == "gender":
        await callback.message.answer(
            "Выберите пол для правильных окончаний в сказке:",
            reply_markup=gender_kb(prefix="prof"),
        )
        await callback.answer()
        return
    if field not in prompts:
        await callback.answer()
        return
    text, st = prompts[field]
    await callback.message.answer(text)
    await state.set_state(st)
    await state.update_data(edit_field=field)
    await callback.answer()


@router.callback_query(F.data.startswith("prof:gender:"))
async def prof_set_gender(callback: CallbackQuery) -> None:
    gender = callback.data.split(":")[-1]
    if gender not in ("m", "f"):
        await callback.answer()
        return
    await db.update_profile_field(callback.from_user.id, "gender", gender)
    label = GENDER_LABELS[gender]
    await callback.message.answer(f"Пол обновлён: {label} ✓")
    await send_profile(callback.message)
    await callback.answer()


@router.message(EditProfile.name)
async def edit_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое.")
        return
    await db.update_profile_field(message.from_user.id, "name", name)
    await state.clear()
    await message.answer("Имя обновлено ✓")
    await send_profile(message)


@router.message(EditProfile.age)
async def edit_age(message: Message, state: FSMContext) -> None:
    try:
        age = int((message.text or "").strip())
    except ValueError:
        await message.answer("Число от 2 до 7.")
        return
    await db.update_profile_field(message.from_user.id, "age_years", age)
    await state.clear()
    await message.answer("Возраст обновлён ✓")
    await send_profile(message)


@router.message(EditProfile.hero)
async def edit_hero(message: Message, state: FSMContext) -> None:
    hero = (message.text or "").strip()
    await db.update_profile_field(message.from_user.id, "favorite_hero", hero)
    await state.clear()
    await message.answer("Герой обновлён ✓")
    await send_profile(message)


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":")[1]
    if mode == "today":
        await state.set_state(TodayFlow.context)
        profile, has_profile = await profile_or_default(callback.from_user.id)
        name = profile["name"] if has_profile else "малыш"
        await callback.message.answer(TODAY_ASK.format(name=name))
        await callback.answer()
        return
    await callback.answer()
    await run_story_generation(callback.message, state, mode, user_id=callback.from_user.id)


@router.message(F.text.in_(BUTTON_TO_MODE))
async def reply_mode(message: Message, state: FSMContext) -> None:
    mode = BUTTON_TO_MODE[message.text]
    if mode == "today":
        await state.set_state(TodayFlow.context)
        profile, has_profile = await profile_or_default(message.from_user.id)
        name = profile["name"] if has_profile else "малыш"
        await message.answer(TODAY_ASK.format(name=name))
        return
    await run_story_generation(message, state, mode)


@router.message(TodayFlow.context)
async def today_context(message: Message, state: FSMContext) -> None:
    ctx = (message.text or "").strip()[:500]
    await state.update_data(day_context=ctx)
    await state.clear()
    await run_story_generation(message, state, "today", day_context=ctx)


async def run_story_generation(
    message: Message,
    state: FSMContext,
    mode: str,
    day_context: str = "",
    user_id: int | None = None,
) -> None:
    uid = user_id or message.from_user.id
    profile, has_profile = await profile_or_default(uid)

    data = await state.get_data()
    if not day_context:
        day_context = data.get("day_context", "")

    await message.bot.send_chat_action(message.chat.id, "typing")
    status = await message.answer(GENERATING)

    story, _used_llm = await generate_story(
        mode=mode,
        name=profile["name"],
        age=profile["age_years"],
        hero=profile.get("favorite_hero") or "",
        day_context=day_context,
        length_pref=profile.get("length_pref") or 1.0,
        no_scary=bool(profile.get("no_scary", True)),
        gender=profile.get("gender", "m"),
    )

    extra = SCREEN_FREE_HINT if mode == "screen_free" else ""
    name = profile["name"]
    footer = AFTER_STORY.replace("{имя}", name).replace("{name}", name)
    full = story + extra + footer
    if not has_profile:
        full += NO_PROFILE_HINT

    await db.increment_usage(uid)
    await db.set_last_mode(uid, mode)

    await status.delete()
    for chunk in split_message(full):
        await message.answer(chunk)
    await message.answer(FEEDBACK_PROMPT, reply_markup=feedback_kb())


@router.callback_query(F.data.startswith("fb:"))
async def cb_feedback(callback: CallbackQuery) -> None:
    kind = callback.data.split(":")[1]
    if kind == "long":
        await db.adjust_length_pref(callback.from_user.id, 0.8)
        await callback.message.answer("Поняла — следующая сказка будет короче.")
    elif kind == "more":
        await callback.message.answer("Выберите режим:", reply_markup=main_menu_kb())
    elif kind == "asleep":
        await callback.message.answer("Спокойной ночи 🌙")
    else:
        await callback.message.answer(
            "Жаль, что не подошло. Попробуйте другой режим или /story."
        )
    await callback.answer()
