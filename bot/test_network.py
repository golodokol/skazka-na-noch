"""Find working path to api.telegram.org (direct or via local SOCKS)."""
import asyncio
import json
import os
import socket

import aiohttp
from dotenv import load_dotenv

load_dotenv(__import__("pathlib").Path(__file__).resolve().parent.parent / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CONFIGURED = os.getenv("TELEGRAM_PROXY", "").strip()
PROXY_USER = os.getenv("TELEGRAM_PROXY_USER", "").strip()
PROXY_PASS = os.getenv("TELEGRAM_PROXY_PASSWORD", "").strip()

COMMON_PORTS = (10808, 10809, 1080, 7890, 7891, 9050, 8080, 8888)


def _lan_ipv4_hosts() -> list[str]:
    """Happ LAN-прокси часто слушает 192.168.x.x, а не 127.0.0.1."""
    hosts = ["127.0.0.1"]
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127."):
                continue
            if ip not in hosts:
                hosts.append(ip)
    except OSError:
        pass
    return hosts


def _effective_proxy(base: str) -> str:
    if PROXY_USER and "@" not in base.split("://", 1)[-1]:
        scheme, rest = base.split("://", 1)
        return f"{scheme}://{PROXY_USER}:{PROXY_PASS}@{rest}"
    return base


async def try_get_me(proxy: str | None) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    timeout = aiohttp.ClientTimeout(total=15)
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
        if data.get("ok"):
            user = data["result"].get("username", "?")
            return True, f"@{user}"
        return False, data.get("description", str(data))
    except asyncio.TimeoutError:
        return False, "таймаут — часто нужны TELEGRAM_PROXY_USER/PASSWORD из Happ"
    except Exception as exc:
        msg = str(exc).strip() or type(exc).__name__
        return False, msg[:120]
    finally:
        if "session" in locals():
            await session.close()


async def main() -> None:
    if not TOKEN:
        print("FAIL: TELEGRAM_BOT_TOKEN empty in .env")
        return

    print("Testing connection to api.telegram.org ...\n")

    if CONFIGURED:
        proxy = _effective_proxy(CONFIGURED)
        ok, msg = await try_get_me(proxy)
        label = f"TELEGRAM_PROXY={CONFIGURED.split('@')[-1]}"
        print(f"{'OK' if ok else 'FAIL'}  {label}")
        print(f"      {msg}\n")
        if ok:
            print("Use run-bot.bat — proxy in .env is working.")
            return
        elif "127.0.0.1" in CONFIGURED and ("10808" in CONFIGURED or "10809" in CONFIGURED):
            print(
                "Happ LAN-proksi chasto ne na 127.0.0.1.\n"
                "V Happ: Rasshirennye -> LAN -> skopiruyte Tekushchiy IP (u vas ~192.168.1.69):\n"
                "  TELEGRAM_PROXY=socks5://VASH_IP:10808\n"
                "Ili vklyuchite TUN i zakommentiruyte TELEGRAM_PROXY v .env.\n"
            )
        if PROXY_USER:
            print("Proxy failed with TELEGRAM_PROXY_USER — check credentials in Happ.\n")

    ok, msg = await try_get_me(None)
    print(f"{'OK' if ok else 'FAIL'}  direct (no proxy)")
    print(f"      {msg}\n")
    if ok:
        print("VPN routes all traffic. Run run-bot.bat (TELEGRAM_PROXY not needed).")
        return

    hosts = _lan_ipv4_hosts()
    print(f"Trying VPN proxy on {', '.join(hosts)} ...\n")
    for host in hosts:
        for port in COMMON_PORTS:
            for scheme in ("socks5", "http"):
                proxy = f"{scheme}://{host}:{port}"
                ok, msg = await try_get_me(proxy)
                if ok:
                    print(f"OK    {proxy}  ->  {msg}")
                    print(f"\nAdd to .env:\nTELEGRAM_PROXY={proxy}\n")
                    print("Then run run-bot.bat again.")
                    return
                print(f"fail  {proxy}")

    print(
        "\nNo working route found.\n"
        "Happ без Inbounds — попробуйте по порядку:\n"
        "1) Подключите VPN в Happ (зелёная кнопка)\n"
        "2) Settings → включите TUN → SAVE → переподключите VPN\n"
        "   Закомментируйте TELEGRAM_PROXY в .env и запустите test-network.bat снова\n"
        "3) Или LAN: TELEGRAM_PROXY=socks5://ТЕКУЩИЙ_IP_ИЗ_HAPP:10808\n"
        "4) Запускайте Happ от имени администратора; разрешите в брандмауэре Windows"
    )


if __name__ == "__main__":
    asyncio.run(main())
