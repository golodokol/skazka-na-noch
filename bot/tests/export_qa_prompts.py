"""Экспорт промптов для ручной QA-матрицы (без LLM)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from story_generator import _build_system_prompt, _build_user_prompt, word_target_for

SAMPLES = [
    ("1 tired a3 hero", dict(mode="tired", age=3, hero="Зайчик", day_context="")),
    ("5 medium a5 hero", dict(mode="medium", age=5, hero="Зайчик", day_context="")),
    ("9 today a7 dark", dict(mode="today", age=7, hero="Зайчик", day_context="боялся темноты")),
]

NAME = "Миша"

for label, kw in SAMPLES:
    wt = word_target_for(kw["mode"], kw["age"])
    system = _build_system_prompt(
        age=kw["age"],
        name=NAME,
        hero=kw["hero"],
        mode=kw["mode"],
        word_target=wt,
        no_scary=True,
        gender="m",
        day_context=kw["day_context"],
    )
    user = _build_user_prompt(
        mode=kw["mode"],
        name=NAME,
        hero=kw["hero"],
        word_target=wt,
        day_context=kw["day_context"],
        age=kw["age"],
        gender="m",
    )
    print("=" * 72)
    print(label.upper())
    print(f"word_target={wt}")
    print("--- SYSTEM (first 1200 chars) ---")
    print(system[:1200])
    print("...")
    print("--- USER ---")
    print(user)
    print()
