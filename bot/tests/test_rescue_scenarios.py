"""Тесты быстрых спасений."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rescue_scenarios import RESCUE_BY_ID, RESCUE_SCENARIOS, rescue_prompt_block


def test_twelve_rescues():
    assert len(RESCUE_SCENARIOS) == 12
    assert len(RESCUE_BY_ID) == 12


def test_rescue_prompt_contains_name():
    block = rescue_prompt_block("hyper", "Маша")
    assert "Маша" in block
    assert "бодр" in block.lower()


def test_grandma_prompt_has_scene_elements():
    block = rescue_prompt_block("grandma_bedtime", "Петя")
    assert "бабушка" in block.lower()
    assert "мама" in block.lower() or "папа" in block.lower()
    assert "ОБЯЗАТЕЛЬНО" in block
    assert "Избегай" in block


def test_rescue_modes_valid():
    for s in RESCUE_SCENARIOS:
        assert s.story_mode in ("tired", "medium")
        assert len(s.label) <= 64
        assert len(f"rescue:{s.id}") <= 64


if __name__ == "__main__":
    for test in (
        test_twelve_rescues,
        test_rescue_prompt_contains_name,
        test_grandma_prompt_has_scene_elements,
        test_rescue_modes_valid,
    ):
        test()
        print(f"OK {test.__name__}")
    print("All tests passed.")
