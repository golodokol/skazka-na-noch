import socket

from aiogram.client.session.aiohttp import AiohttpSession

from config import effective_telegram_proxy


class BotSession(AiohttpSession):
    """Сессия с IPv4 (обход проблем IPv6/VPN на Windows)."""

    def __init__(self) -> None:
        proxy = effective_telegram_proxy() or None
        super().__init__(proxy=proxy)
        self._connector_init["family"] = socket.AF_INET
