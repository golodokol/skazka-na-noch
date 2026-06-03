import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError

from config import TELEGRAM_BOT_TOKEN
from db import init_db
from handlers import router
from session import BotSession

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN не задан. Создайте файл .env в корне проекта "
            "(см. .env.example и docs/BOTFATHER_SETUP.md)"
        )
        sys.exit(1)

    await init_db()

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
