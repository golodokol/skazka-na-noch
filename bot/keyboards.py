from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from texts import MODE_LABELS

BUTTON_TO_MODE = {
    "😴 Нет сил": "tired",
    "⏱ 5 минут": "medium",
    "📺 Вместо мультика": "screen_free",
    "✏️ Сегодняшний день": "today",
    "✏️ Сегодня": "today",
}

REPLY_BUTTON_TEXTS = frozenset(BUTTON_TO_MODE) | {"⚙️ Профиль", "❓ Помощь", "🏠 Меню"}


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="😴 Нет сил", callback_data="mode:tired"),
                InlineKeyboardButton(text="⏱ 5 минут", callback_data="mode:medium"),
            ],
            [
                InlineKeyboardButton(
                    text="📺 Вместо мультика", callback_data="mode:screen_free"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Сегодняшний день", callback_data="mode:today"
                ),
                InlineKeyboardButton(text="⚙️ Профиль", callback_data="profile"),
            ],
        ]
    )


def feedback_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="😴 Уснул", callback_data="fb:asleep"),
                InlineKeyboardButton(text="🔄 Ещё одну", callback_data="fb:more"),
            ],
            [
                InlineKeyboardButton(text="⏳ Длинно", callback_data="fb:long"),
                InlineKeyboardButton(text="😟 Не подошло", callback_data="fb:bad"),
            ],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")],
        ]
    )


def feedback_bad_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="😨 Испугался / тревожно", callback_data="fb:bad:scary"
                ),
                InlineKeyboardButton(
                    text="😐 Не зацепило", callback_data="fb:bad:boring"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🌊 Не успокоило", callback_data="fb:bad:not_calming"
                ),
            ],
            [
                InlineKeyboardButton(text="📏 Коротко", callback_data="fb:bad:short"),
                InlineKeyboardButton(
                    text="🎭 Не тот герой", callback_data="fb:bad:hero"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Не про сегодня", callback_data="fb:bad:today"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Свой вариант", callback_data="fb:bad:other"
                ),
                InlineKeyboardButton(text="🔄 Другую сказку", callback_data="fb:more"),
            ],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")],
        ]
    )


def feedback_action_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Ещё одну", callback_data="fb:more"),
                InlineKeyboardButton(text="🏠 В меню", callback_data="menu"),
            ],
        ]
    )


def gender_kb(*, prefix: str = "onboard") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👦 Мальчик", callback_data=f"{prefix}:gender:m"
                ),
                InlineKeyboardButton(
                    text="👧 Девочка", callback_data=f"{prefix}:gender:f"
                ),
            ],
        ]
    )


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="prof:name")],
            [
                InlineKeyboardButton(
                    text="👦👧 Мальчик / девочка", callback_data="prof:gender"
                ),
            ],
            [InlineKeyboardButton(text="✏️ Изменить возраст", callback_data="prof:age")],
            [InlineKeyboardButton(text="✏️ Любимый герой", callback_data="prof:hero")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")],
        ]
    )


def skip_hero_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="onboard:skip_hero")]
        ]
    )


def reply_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="😴 Нет сил"),
                KeyboardButton(text="⏱ 5 минут"),
            ],
            [
                KeyboardButton(text="📺 Вместо мультика"),
                KeyboardButton(text="✏️ Сегодня"),
            ],
            [
                KeyboardButton(text="⚙️ Профиль"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите режим или напишите фразу про день…",
    )
