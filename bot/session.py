import socket

from aiogram.client.session.aiohttp import AiohttpSession

from config import TELEGRAM_PROXY


class BotSession(AiohttpSession):
    """Сессия с IPv4 (обход проблем IPv6/VPN на Windows)."""

    def __init__(self) -> None:
        proxy = TELEGRAM_PROXY or None
        super().__init__(proxy=proxy)
        self._connector_init["family"] = socket.AF_INET
