"""Проверка токена и доступа к api.telegram.org."""
import asyncio
import json
import os
import socket
import sys

import aiohttp
from dotenv import load_dotenv

load_dotenv(Path := __import__("pathlib").Path(__file__).resolve().parent.parent / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
PROXY = os.getenv("TELEGRAM_PROXY", "").strip()


async def main() -> None:
    if not TOKEN:
        print("FAIL: TELEGRAM_BOT_TOKEN пустой")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(family=socket.AF_INET)

    kwargs: dict = {"timeout": timeout, "connector": connector}
    if PROXY:
        if "t.me/proxy" in PROXY or PROXY.startswith("https://"):
            print("FAIL: TELEGRAM_PROXY — нужен socks5:// или http://, не t.me/proxy")
            sys.exit(1)
        kwargs["proxy"] = PROXY
        print(f"Используется прокси: {PROXY.split('@')[-1]}")  # без credentials в лог

    try:
        async with aiohttp.ClientSession(**kwargs) as session:
            async with session.get(url) as resp:
                data = json.loads(await resp.text())
    except Exception as exc:
        print(f"FAIL: нет связи с api.telegram.org — {exc}")
        print("Включите VPN для всей системы или укажите TELEGRAM_PROXY=socks5://127.0.0.1:ПОРТ")
        sys.exit(1)

    if not data.get("ok"):
        print("FAIL: неверный токен —", data.get("description", data))
        sys.exit(1)

    bot = data["result"]
    print("OK: токен валиден")
    print(f"    @{bot.get('username')} ({bot.get('first_name')})")


if __name__ == "__main__":
    asyncio.run(main())
