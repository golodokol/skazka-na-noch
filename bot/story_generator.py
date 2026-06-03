from pathlib import Path

from config import OPENAI_API_KEY, OPENAI_MODEL
from fallback_stories import fallback_story

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_ru.txt"

MODE_WORDS = {
    "tired": 350,
    "medium": 700,
    "screen_free": 450,
    "today": 400,
}

MODE_LABELS = {
    "tired": "Нет сил (короткая)",
    "medium": "5 минут",
    "screen_free": "Вместо мультика",
    "today": "Сегодняшний день",
}

NO_SCARY = (
    "Не используй: монстров, пугающих взрослых, Бабу-Ягу, потерю родителей, "
    "панику, болезни, смерть."
)


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def generate_story(
    mode: str,
    name: str,
    age: int,
    hero: str = "",
    day_context: str = "",
    length_pref: float = 1.0,
) -> tuple[str, bool]:
    """
    Returns (story_text, used_llm).
    """
    word_target = int(MODE_WORDS.get(mode, 400) * length_pref)
    if not OPENAI_API_KEY:
        return (
            fallback_story(mode, name, hero, day_context),
            False,
        )

    system = _load_prompt_template().format(
        age=age,
        name=name,
        hero=hero or "добрый зверёк",
        mode_label=MODE_LABELS.get(mode, mode),
        day_context=day_context or "обычный спокойный день",
        word_target=word_target,
        no_scary_rules=NO_SCARY,
        mode=mode,
    )
    user = f"Напиши сонную сказку для чтения вслух. Режим: {mode}."
    if day_context:
        user += f" Контекст дня: {day_context}"

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.75,
            max_tokens=min(2000, word_target * 2),
        )
        text = (resp.choices[0].message.content or "").strip()
        if len(text) < 100:
            raise ValueError("story too short")
        return text, True
    except Exception:
        return fallback_story(mode, name, hero, day_context), False


def split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts
