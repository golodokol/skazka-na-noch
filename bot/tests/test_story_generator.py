"""Тесты сборки промпта (фаза 1)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prompts.few_shot_ru import few_shot_for_age
from story_craft import METAPHORS_BY_AGE, context_blocks_for_prompt, pick_metaphor_for_age
from story_generator import (
    TELEGRAM_MESSAGE_LIMIT,
    _build_system_prompt,
    _build_user_prompt,
    story_delivery_chunks,
)
from story_variety import pick_variety, variety_user_block


def _base_system(**kwargs):
    defaults = dict(
        age=5,
        name="Маша",
        hero="единорог Луна",
        mode="tired",
        word_target=720,
        no_scary=True,
        gender="f",
        day_context="",
    )
    defaults.update(kwargs)
    return _build_system_prompt(**defaults)


def test_system_has_narrator_voice_first():
    prompt = _base_system()
    voice_pos = prompt.index("ГОЛОС РАССКАЗЧИКА")
    propp_pos = prompt.index("МОРФОЛОГИЯ СКАЗКИ")
    assert voice_pos < propp_pos


def test_system_no_sleep_onset_percentages():
    prompt = _base_system()
    assert "~10%" not in prompt
    assert "SLEEP-ONSET" not in prompt
    assert "ДУГА ВЕЧЕРА" in prompt


def test_day_metaphor_only_when_needed():
    tired = _base_system(mode="tired")
    assert "ПЕРЕВОД СОБЫТИЙ ДНЯ" not in tired

    today_ctx = _base_system(mode="today", day_context="поссорилась в садике")
    assert "ПЕРЕВОД СОБЫТИЙ ДНЯ" in today_ctx
    assert "ЛОГИКА «СЕГОДНЯШНИЙ ДЕНЬ»" in today_ctx

    tired_with_ctx = _base_system(mode="tired", day_context="устала после прогулки")
    assert "ПЕРЕВОД СОБЫТИЙ ДНЯ" in tired_with_ctx
    assert "ЛОГИКА «СЕГОДНЯШНИЙ ДЕНЬ»" not in tired_with_ctx


def test_context_blocks_helper():
    metaphor = pick_metaphor_for_age(4, seed=42)
    blocks = context_blocks_for_prompt(
        mode="medium", day_context="", age=4, metaphor=metaphor
    )
    assert "ОБРАЗ ДЛЯ ЭТОЙ СКАЗКИ" in blocks
    assert metaphor in blocks
    assert "выбери 1–2 метафоры из списка" not in blocks
    assert "ПЕРЕВОД СОБЫТИЙ ДНЯ" not in blocks


def test_single_metaphor_not_full_catalog():
    prompt = _base_system(age=5, name="Петя")
    listed = METAPHORS_BY_AGE["4-5"]
    present = sum(1 for m in listed if m in prompt)
    assert present <= 2
    assert "ОБРАЗ ДЛЯ ЭТОЙ СКАЗКИ" in prompt
    assert "Плохо:" in prompt and "Хорошо:" in prompt


def test_hero_requirements_softened():
    prompt = _base_system()
    assert "в каждом абзаце" not in prompt.lower() or "максимум один раз" in prompt
    assert "3–5 раз" in prompt
    assert "2–4 короткие" in prompt
    assert "ИМЯ РЕБЁНКА" in prompt


def test_variety_uses_plan_metaphor_in_system():
    plan = pick_variety(5, [], seed=123)
    prompt = _base_system(age=5, variety=plan)
    assert plan.metaphor in prompt
    user = variety_user_block(plan, child_name="Маша", favorite_hero="Луна")
    assert "минимум 5 раз" not in user
    assert "3–5 раз" in user


def test_user_prompt_no_propp_duplicate():
    user = _build_user_prompt(
        mode="tired",
        name="Маша",
        hero="Луна",
        word_target=720,
        day_context="",
        age=5,
        gender="f",
    )
    assert "Пропп" not in user
    assert "метафор" not in user.lower()
    assert "минимум" in user.lower() and "слов" in user.lower()


def test_skazko_principles_compressed():
    prompt = _base_system()
    assert "ПРИНЦИПЫ ДЛЯ АВТОРА" in prompt
    assert prompt.count("ПРИНЦИПЫ") == 1


def test_system_has_few_shot_and_cliche_avoid():
    prompt = _base_system(age=5)
    assert "ПРИМЕР РИТМА" in prompt
    assert "не копируй сюжет" in prompt.lower()
    assert "ИЗБЕГАЙ ШТАМПОВ ИИ" in prompt
    assert "Петя лежал на кровати" in prompt


def test_few_shot_band_by_age():
    young = few_shot_for_age(2)
    old = few_shot_for_age(7)
    assert "Катя" in young
    assert "Алиса" in old


def test_story_delivery_short_single_message():
    story = "Короткая сказка.\n\nВторой абзац."
    suffix = "\n\nХвост."
    chunks = story_delivery_chunks(story, suffix)
    assert chunks == [story + suffix]


def test_story_delivery_long_two_messages():
    para = "Абзац сказки. " * 120
    story = f"{para}\n\n{para}\n\n{para}"
    suffix = "\n\n" + "Хвост после сказки. " * 5
    chunks = story_delivery_chunks(story, suffix)
    assert len(chunks) == 2
    assert all(len(c) <= TELEGRAM_MESSAGE_LIMIT for c in chunks)
    assert story.startswith(chunks[0])
    assert suffix in chunks[1]
    assert chunks[1].replace(suffix, "").strip() in story


if __name__ == "__main__":
    tests = [
        test_system_has_narrator_voice_first,
        test_system_no_sleep_onset_percentages,
        test_day_metaphor_only_when_needed,
        test_context_blocks_helper,
        test_single_metaphor_not_full_catalog,
        test_hero_requirements_softened,
        test_variety_uses_plan_metaphor_in_system,
        test_user_prompt_no_propp_duplicate,
        test_skazko_principles_compressed,
        test_system_has_few_shot_and_cliche_avoid,
        test_few_shot_band_by_age,
        test_story_delivery_short_single_message,
        test_story_delivery_long_two_messages,
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"All {len(tests)} tests passed.")
