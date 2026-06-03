from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from texts import MODE_LABELS


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


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="prof:name")],
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
