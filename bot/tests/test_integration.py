"""Интеграционные smoke-тесты сборки промпта (фаза 7)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PROMPT_VERSION, rewrite_pass_for_mode, temperature_for_mode
from story_generator import (
    StoryGenerationMeta,
    _build_system_prompt,
    _build_user_prompt,
    word_target_for,
)
from story_variety import pick_variety


MODES = ("tired", "medium", "today")
AGES = (3, 5, 7)


def test_prompt_version():
    assert PROMPT_VERSION in ("v1", "v2")


def test_all_modes_build_prompts():
    for mode in MODES:
        for age in AGES:
            system = _build_system_prompt(
                age=age,
                name="Тест",
                hero="Зайчик",
                mode=mode,
                word_target=word_target_for(mode, age),
                no_scary=True,
                gender="m",
                day_context="устал после садика" if mode == "today" else "",
            )
            user = _build_user_prompt(
                mode=mode,
                name="Тест",
                hero="Зайчик",
                word_target=word_target_for(mode, age),
                day_context="устал после садика" if mode == "today" else "",
                age=age,
                gender="m",
            )
            assert len(system) > 500
            assert len(user) > 50
            assert system.count("ГОЛОС РАССКАЗЧИКА") == 1
            assert system.count("МОРФОЛОГИЯ СКАЗКИ") == 1
            assert "Пропп" not in user


def test_no_full_metaphor_catalog():
    system = _build_system_prompt(
        age=5,
        name="Маша",
        hero="Луна",
        mode="tired",
        word_target=720,
        no_scary=True,
        gender="f",
    )
    assert "выбери 1–2 метафоры из списка" not in system
    assert "ОБРАЗ ДЛЯ ЭТОЙ СКАЗКИ" in system


def test_today_includes_day_logic_only_with_context():
    with_ctx = _build_system_prompt(
        age=5,
        name="Маша",
        hero="Луна",
        mode="today",
        word_target=760,
        no_scary=True,
        gender="f",
        day_context="поссорился с другом",
    )
    without = _build_system_prompt(
        age=5,
        name="Маша",
        hero="Луна",
        mode="today",
        word_target=760,
        no_scary=True,
        gender="f",
        day_context="",
    )
    assert "ЛОГИКА «СЕГОДНЯШНИЙ ДЕНЬ»" in with_ctx
    assert "ЛОГИКА «СЕГОДНЯШНИЙ ДЕНЬ»" not in without


def test_word_targets_monotonic_by_age():
    for mode in MODES:
        prev = 0
        for age in range(2, 7):
            target = word_target_for(mode, age)
            assert target >= prev
            prev = target
        assert word_target_for(mode, 7) >= 80


def test_variety_and_feedback_hint_together():
    plan = pick_variety(5, [], seed=42, fresh_boost_offset=2)
    user = _build_user_prompt(
        mode="tired",
        name="Маша",
        hero="Луна",
        word_target=720,
        day_context="",
        age=5,
        gender="f",
        variety=plan,
        prompt_hint="boring",
    )
    assert plan.setting[:20] in user
    assert "скучной" in user


def test_generation_meta_serializable():
    meta = StoryGenerationMeta(
        used_llm=True,
        mode="medium",
        prompt_hint="boring",
        rewrite_applied=True,
        prompt_version=PROMPT_VERSION,
    )
    d = meta.as_dict()
    assert d["prompt_hint"] == "boring"
    assert d["rewrite_applied"] is True
    assert d["prompt_version"] == PROMPT_VERSION


def test_config_defaults_phase5():
    assert temperature_for_mode("tired") == 0.70
    assert rewrite_pass_for_mode("medium") is True


if __name__ == "__main__":
    tests = [
        test_prompt_version,
        test_all_modes_build_prompts,
        test_no_full_metaphor_catalog,
        test_today_includes_day_logic_only_with_context,
        test_word_targets_monotonic_by_age,
        test_variety_and_feedback_hint_together,
        test_generation_meta_serializable,
        test_config_defaults_phase5,
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"All {len(tests)} tests passed.")
