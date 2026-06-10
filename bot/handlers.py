from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import asyncio

import db
from config import GENERATION_STATUS_WAIT_SEC
from keyboards import (
    BUTTON_TO_MODE,
    RESCUE_REPLY_BUTTON,
    USER_MODES,
    feedback_action_kb,
    feedback_bad_kb,
    feedback_kb,
    gender_kb,
    main_menu_kb,
    profile_kb,
    reply_menu_kb,
    rescue_picker_kb,
    skip_hero_kb,
)
from name_grammar import GENDER_LABELS, normalize_gender, today_ask
from rescue_scenarios import RESCUE_BY_ID
from story_feedback_hints import BAD_REASON_TO_HINT
from story_generator import generate_story, story_delivery_chunks
from story_variety import memory_from_plan, pick_variety
from texts import (
    AFTER_STORY,
    ASK_AGE,
    ASK_GENDER,
    ASK_HERO,
    ASK_NAME,
    FEEDBACK_PROMPT,
    FEEDBACK_BAD_BORING,
    FEEDBACK_BAD_HERO,
    FEEDBACK_BAD_NOT_CALMING,
    FEEDBACK_BAD_OTHER_ASK,
    FEEDBACK_BAD_PROMPT,
    FEEDBACK_BAD_SCARY,
    FEEDBACK_BAD_SHORT,
    FEEDBACK_BAD_THANKS,
    FEEDBACK_BAD_TODAY,
    GENERATING,
    GENERATING_SLOW,
    HELP_TEXT,
    NO_PROFILE_HINT,
    ONBOARDING_DONE,
    PRIVACY_TEXT,
    RESCUE_PICKER_INTRO,
    WELCOME_NEW,
    WELCOME_RETURN,
)

router = Router()

LEGACY_MODE_MAP = {"screen_free": "tired"}


def normalize_mode(mode: str) -> str:
    """Активные режимы + маппинг снятых с меню (screen_free → tired)."""
    mode = LEGACY_MODE_MAP.get(mode, mode)
    if mode in USER_MODES:
        return mode
    return "tired"


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


class FeedbackFlow(StatesGroup):
    other_text = State()


async def show_menu(message: Message) -> None:
    profile = await db.get_profile(message.from_user.id)
    if profile:
        text = WELCOME_RETURN.format(name=profile["name"])
    else:
        text = WELCOME_NEW
    await message.answer(text, reply_markup=reply_menu_kb())


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
    await show_menu(message)


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
    mode = normalize_mode(profile.get("last_mode") or "tired")
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
    await show_menu(message)


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
    await show_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_menu(callback.message)
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


@router.callback_query(F.data.regexp(r"^prof:gender:[mf]$"))
async def prof_set_gender(callback: CallbackQuery) -> None:
    gender = callback.data.split(":")[-1]
    await db.update_profile_field(callback.from_user.id, "gender", gender)
    label = GENDER_LABELS[gender]
    await callback.message.answer(f"Пол обновлён: {label} ✓")
    await send_profile(callback.message)
    await callback.answer()


@router.callback_query(F.data.in_({"prof:name", "prof:age", "prof:hero", "prof:gender"}))
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


@router.callback_query(F.data == "rescue:menu")
async def cb_rescue_menu(callback: CallbackQuery) -> None:
    await callback.message.answer(RESCUE_PICKER_INTRO, reply_markup=rescue_picker_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("rescue:"))
async def cb_rescue(callback: CallbackQuery, state: FSMContext) -> None:
    rescue_id = callback.data.split(":", 1)[1]
    if rescue_id == "menu":
        return
    if rescue_id not in RESCUE_BY_ID:
        await callback.answer("Не нашла этот сценарий")
        return
    scenario = RESCUE_BY_ID[rescue_id]
    await callback.answer()
    await run_story_generation(
        callback.message,
        state,
        mode=scenario.story_mode,
        user_id=callback.from_user.id,
        rescue_id=rescue_id,
    )


@router.message(F.text == RESCUE_REPLY_BUTTON)
async def reply_rescue(message: Message) -> None:
    await message.answer(RESCUE_PICKER_INTRO, reply_markup=rescue_picker_kb())


@router.callback_query(F.data.startswith("mode:"))
async def cb_mode(callback: CallbackQuery, state: FSMContext) -> None:
    mode = normalize_mode(callback.data.split(":")[1])
    if mode == "today":
        await state.set_state(TodayFlow.context)
        profile, has_profile = await profile_or_default(callback.from_user.id)
        await callback.message.answer(
            today_ask(profile["name"], profile.get("gender", "m"))
        )
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
        await message.answer(today_ask(profile["name"], profile.get("gender", "m")))
        return
    await run_story_generation(message, state, mode)


@router.message(TodayFlow.context)
async def today_context(message: Message, state: FSMContext) -> None:
    ctx = (message.text or "").strip()[:500]
    await state.update_data(day_context=ctx)
    await state.clear()
    await run_story_generation(message, state, "today", day_context=ctx)


async def _slow_generation_notice(status_msg: Message) -> None:
    """Через N секунд обновляет статус, если сказка ещё генерируется."""
    await asyncio.sleep(GENERATION_STATUS_WAIT_SEC)
    try:
        await status_msg.edit_text(GENERATING_SLOW)
    except Exception:
        pass


async def run_story_generation(
    message: Message,
    state: FSMContext,
    mode: str,
    day_context: str = "",
    user_id: int | None = None,
    force_fresh: bool = False,
    rescue_id: str = "",
) -> None:
    uid = user_id or message.from_user.id
    profile, has_profile = await profile_or_default(uid)
    mode = normalize_mode(mode)

    data = await state.get_data()
    if not day_context:
        day_context = data.get("day_context", "")

    memories = await db.get_story_memories(uid)
    fresh_boost_offset = await db.feedback_variety_boost(uid)
    prompt_hint = await db.get_prompt_hint(uid)
    variety = pick_variety(
        profile["age_years"],
        memories,
        force_fresh=force_fresh,
        seed=uid + len(memories) * 997 + (9991 if force_fresh else 0),
        fresh_boost_offset=fresh_boost_offset,
    )

    await message.bot.send_chat_action(message.chat.id, "typing")
    status = await message.answer(GENERATING)
    slow_notice = asyncio.create_task(_slow_generation_notice(status))
    try:
        story, gen_meta = await generate_story(
            mode=mode,
            name=profile["name"],
            age=profile["age_years"],
            hero=profile.get("favorite_hero") or "",
            day_context=day_context,
            length_pref=profile.get("length_pref") or 1.0,
            no_scary=bool(profile.get("no_scary", True)),
            gender=profile.get("gender", "m"),
            variety=variety,
            force_fresh=force_fresh,
            user_id=uid,
            prompt_hint=prompt_hint,
            rescue_id=rescue_id,
        )
    finally:
        slow_notice.cancel()
        with asyncio.suppress(asyncio.CancelledError):
            await slow_notice
    await db.log_story_generation(uid, gen_meta.as_dict())
    if prompt_hint:
        await db.clear_prompt_hint(uid)

    snippet = story[:160].replace("\n", " ")
    await db.add_story_memory(uid, memory_from_plan(variety, mode, snippet))

    name = profile["name"]
    footer = AFTER_STORY.replace("{имя}", name).replace("{name}", name)
    suffix = footer
    if not has_profile:
        suffix += NO_PROFILE_HINT

    await db.increment_usage(uid)
    await db.set_last_mode(uid, mode)

    await status.delete()
    for chunk in story_delivery_chunks(story, suffix):
        await message.answer(chunk)
    await message.answer(FEEDBACK_PROMPT, reply_markup=feedback_kb())


async def _handle_bad_reason(
    callback: CallbackQuery,
    state: FSMContext,
    reason: str,
) -> None:
    uid = callback.from_user.id
    profile, _ = await profile_or_default(uid)
    mode = profile.get("last_mode") or ""

    if reason == "other":
        await state.set_state(FeedbackFlow.other_text)
        await callback.message.answer(FEEDBACK_BAD_OTHER_ASK)
        await callback.answer()
        return

    await db.save_story_feedback(uid, "bad", bad_reason=reason, mode=mode)
    hint_key = BAD_REASON_TO_HINT.get(reason)
    if hint_key:
        await db.set_prompt_hint(uid, hint_key)

    if reason == "scary":
        await callback.message.answer(
            FEEDBACK_BAD_SCARY, reply_markup=feedback_action_kb()
        )
    elif reason == "boring":
        await callback.message.answer(
            FEEDBACK_BAD_BORING, reply_markup=feedback_action_kb()
        )
    elif reason == "not_calming":
        await callback.message.answer(
            FEEDBACK_BAD_NOT_CALMING, reply_markup=main_menu_kb()
        )
    elif reason == "short":
        await db.adjust_length_pref(uid, 1.15)
        await callback.message.answer(
            FEEDBACK_BAD_SHORT, reply_markup=feedback_action_kb()
        )
    elif reason == "hero":
        await callback.message.answer(FEEDBACK_BAD_HERO, reply_markup=profile_kb())
    elif reason == "today":
        await state.set_state(TodayFlow.context)
        await callback.message.answer(FEEDBACK_BAD_TODAY)
        await callback.message.answer(
            today_ask(profile["name"], profile.get("gender", "m"))
        )
    await callback.answer()


@router.message(FeedbackFlow.other_text)
async def feedback_other_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Напишите хотя бы пару слов — или нажмите /start.")
        return
    profile, _ = await profile_or_default(message.from_user.id)
    await db.save_story_feedback(
        message.from_user.id,
        "bad",
        bad_reason="other",
        bad_text=text[:500],
        mode=profile.get("last_mode") or "",
    )
    await db.set_prompt_hint(message.from_user.id, "other")
    await state.clear()
    await message.answer(FEEDBACK_BAD_THANKS, reply_markup=feedback_action_kb())


@router.callback_query(F.data.startswith("fb:"))
async def cb_feedback(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    kind = parts[1]

    if kind == "bad":
        if len(parts) == 2:
            await callback.message.answer(
                FEEDBACK_BAD_PROMPT, reply_markup=feedback_bad_kb()
            )
            await callback.answer()
            return
        if len(parts) >= 3:
            await _handle_bad_reason(callback, state, parts[2])
            return

    if kind == "long":
        await db.save_story_feedback(callback.from_user.id, "long")
        await db.adjust_length_pref(callback.from_user.id, 0.8)
        await callback.message.answer("Поняла — следующая сказка будет короче.")
    elif kind == "more":
        await db.save_story_feedback(callback.from_user.id, "more")
        profile, _ = await profile_or_default(callback.from_user.id)
        mode = normalize_mode(profile.get("last_mode") or "tired")
        await callback.answer()
        await run_story_generation(
            callback.message,
            state,
            mode,
            user_id=callback.from_user.id,
            force_fresh=True,
        )
        return
    elif kind == "asleep":
        await db.save_story_feedback(callback.from_user.id, "asleep")
        await callback.message.answer("Спокойной ночи 🌙")
    await callback.answer()
