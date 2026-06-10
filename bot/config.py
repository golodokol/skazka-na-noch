import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.local", override=True)  # секреты (OPENAI_API_KEY), не в git

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


# LLM: OPENAI_MODEL — legacy alias для draft
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
OPENAI_MODEL_DRAFT = os.getenv("OPENAI_MODEL_DRAFT", OPENAI_MODEL).strip() or OPENAI_MODEL
OPENAI_MODEL_POLISH = os.getenv("OPENAI_MODEL_POLISH", OPENAI_MODEL).strip() or OPENAI_MODEL
OPENAI_MODEL_MEDIUM = (
    os.getenv("OPENAI_MODEL_MEDIUM", OPENAI_MODEL_DRAFT).strip() or OPENAI_MODEL_DRAFT
)

# v2 — промпт после фаз 1–6 (голос, few-shot, rewrite-pass, feedback hints)
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v2").strip() or "v2"

DATABASE_PATH = ROOT / "data" / "bot.db"

# Температура по режимам (фаза 5)
MODE_TEMPERATURE: dict[str, float] = {
    "tired": float(os.getenv("TEMP_TIRED", "0.70")),
    "medium": float(os.getenv("TEMP_MEDIUM", "0.75")),
    "screen_free": float(os.getenv("TEMP_SCREEN_FREE", "0.70")),
    "today": float(os.getenv("TEMP_TODAY", "0.70")),
}
POLISH_TEMPERATURE = float(os.getenv("POLISH_TEMPERATURE", "0.50"))

# Скорость генерации
MAX_DRAFT_RETRIES = max(0, int(os.getenv("MAX_DRAFT_RETRIES", "1")))
GENERATION_STATUS_WAIT_SEC = max(10, int(os.getenv("GENERATION_STATUS_WAIT_SEC", "30")))

# Rewrite-pass (фаза 4)
_ENABLE_REWRITE = os.getenv("ENABLE_REWRITE_PASS", "1").strip().lower() in ("1", "true", "yes")
_REWRITE_ALL = os.getenv("ENABLE_REWRITE_PASS_ALL", "0").strip().lower() in ("1", "true", "yes")
REWRITE_PASS_MODES = frozenset({"medium", "today"})
REWRITE_PASS_OPTIONAL_MODES = frozenset({"tired", "screen_free"})

# A/B: чётный user_id = control (rewrite по правилам), нечётный = без polish
AB_TEST_ENABLED = os.getenv("AB_TEST_ENABLED", "0").strip().lower() in ("1", "true", "yes")


def ab_variant(user_id: int | None) -> str:
    """control — polish по правилам; no_polish — без rewrite-pass."""
    if not AB_TEST_ENABLED or user_id is None:
        return "control"
    return "control" if user_id % 2 == 0 else "no_polish"


def draft_model_for_mode(mode: str) -> str:
    """Модель черновика; medium может быть сильнее (OPENAI_MODEL_MEDIUM)."""
    if mode == "medium":
        return OPENAI_MODEL_MEDIUM
    return OPENAI_MODEL_DRAFT


def polish_model_for_mode(mode: str) -> str:
    return OPENAI_MODEL_POLISH


def temperature_for_mode(mode: str) -> float:
    return MODE_TEMPERATURE.get(mode, 0.70)


def rewrite_pass_for_mode(mode: str, user_id: int | None = None) -> bool:
    """Нужен ли rewrite-pass для режима генерации."""
    if ab_variant(user_id) == "no_polish":
        return False
    if not _ENABLE_REWRITE:
        return False
    if mode in REWRITE_PASS_MODES:
        return True
    return _REWRITE_ALL and mode in REWRITE_PASS_OPTIONAL_MODES
