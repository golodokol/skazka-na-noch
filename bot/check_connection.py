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
PROXY_USER = os.getenv("TELEGRAM_PROXY_USER", "").strip()
PROXY_PASS = os.getenv("TELEGRAM_PROXY_PASSWORD", "").strip()


def _effective_proxy() -> str:
    if not PROXY:
        return ""
    if PROXY_USER and "@" not in PROXY.split("://", 1)[-1]:
        scheme, rest = PROXY.split("://", 1)
        return f"{scheme}://{PROXY_USER}:{PROXY_PASS}@{rest}"
    return PROXY


async def main() -> None:
    if not TOKEN:
        print("FAIL: TELEGRAM_BOT_TOKEN пустой")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    timeout = aiohttp.ClientTimeout(total=30)
    proxy = _effective_proxy()

    if proxy:
        if "t.me/proxy" in proxy or proxy.startswith("https://"):
            print("FAIL: TELEGRAM_PROXY — нужен socks5:// или http://, не t.me/proxy")
            sys.exit(1)
        print(f"Используется прокси: {proxy.split('@')[-1]}")

    try:
        if proxy and proxy.startswith("socks"):
            from aiohttp_socks import ProxyConnector

            connector = ProxyConnector.from_url(proxy, family=socket.AF_INET)
            session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        else:
            connector = aiohttp.TCPConnector(family=socket.AF_INET)
            kwargs: dict = {"connector": connector, "timeout": timeout}
            if proxy:
                kwargs["proxy"] = proxy
            session = aiohttp.ClientSession(**kwargs)

        async with session:
            async with session.get(url) as resp:
                data = json.loads(await resp.text())
    except Exception as exc:
        print(f"FAIL: нет связи с api.telegram.org — {exc}")
        print("Включите VPN, Inbounds → SOCKS в Happ, или поправьте TELEGRAM_PROXY")
        sys.exit(1)

    if not data.get("ok"):
        print("FAIL: неверный токен —", data.get("description", data))
        sys.exit(1)

    bot = data["result"]
    print("OK: токен валиден")
    print(f"    @{bot.get('username')} ({bot.get('first_name')})")


if __name__ == "__main__":
    asyncio.run(main())
