import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand

from config import PROMPT_VERSION, TELEGRAM_BOT_TOKEN
from db import init_db
from handlers import router
from session import BotSession
from texts import BOT_DESCRIPTION

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start", description="Начать и получить сказку"),
    BotCommand(command="story", description="Быстрая сказка (последний режим)"),
    BotCommand(command="profile", description="Профиль ребёнка"),
    BotCommand(command="help", description="Как пользоваться"),
    BotCommand(command="privacy", description="Политика данных"),
]


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(BOT_COMMANDS)
    await bot.set_my_description(BOT_DESCRIPTION)


async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN не задан. Создайте файл .env в корне проекта "
            "(см. .env.example и docs/BOTFATHER_SETUP.md)"
        )
        sys.exit(1)

    await init_db()

    logger.info("Prompt version: %s", PROMPT_VERSION)

    session = BotSession()
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    try:
        me = await bot.get_me()
        logger.info("Подключено: @%s (%s)", me.username, me.first_name)
        await setup_bot_commands(bot)
    except TelegramUnauthorizedError:
        logger.error(
            "Неверный токен. BotFather → /mybots → Revoke → новый токен в .env"
        )
        await bot.session.close()
        sys.exit(1)
    except Exception as exc:
        logger.error(
            "Нет связи с api.telegram.org: %s\n"
            "Запускайте bot\\main.py в PowerShell Windows (не Cursor), с VPN для всей системы.\n"
            "Если VPN через прокси — добавьте в .env: TELEGRAM_PROXY=socks5://127.0.0.1:1080",
            exc,
        )
        await bot.session.close()
        sys.exit(1)

    logger.info("Бот запущен (polling). Остановка: Ctrl+C")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
