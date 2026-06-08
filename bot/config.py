import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", "").strip()
TELEGRAM_PROXY_USER = os.getenv("TELEGRAM_PROXY_USER", "").strip()
TELEGRAM_PROXY_PASSWORD = os.getenv("TELEGRAM_PROXY_PASSWORD", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


def effective_telegram_proxy() -> str:
    """SOCKS/HTTP URL; подставляет логин/пароль из TELEGRAM_PROXY_USER/PASSWORD."""
    proxy = TELEGRAM_PROXY
    if not proxy:
        return ""
    if TELEGRAM_PROXY_USER and "@" not in proxy.split("://", 1)[-1]:
        scheme, rest = proxy.split("://", 1)
        return f"{scheme}://{TELEGRAM_PROXY_USER}:{TELEGRAM_PROXY_PASSWORD}@{rest}"
    return proxy
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
DATABASE_PATH = ROOT / "data" / "bot.db"
