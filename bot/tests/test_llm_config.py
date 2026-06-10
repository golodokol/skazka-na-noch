"""Тесты конфигурации LLM и A/B (фаза 5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from story_generator import StoryGenerationMeta, _max_tokens_for


def test_max_tokens_by_mode():
    assert _max_tokens_for(380, "tired") <= 1500
    assert _max_tokens_for(600, "medium") <= 2500
    assert _max_tokens_for(380, "tired") >= 800
    assert _max_tokens_for(600, "medium") == 1680


def test_max_draft_retries_default():
    assert config.MAX_DRAFT_RETRIES == 1


def test_temperatures_updated():
    assert config.temperature_for_mode("tired") == 0.70
    assert config.temperature_for_mode("today") == 0.70
    assert config.temperature_for_mode("medium") == 0.75
    assert config.POLISH_TEMPERATURE == 0.50


def test_draft_model_medium_override():
    old_draft = config.OPENAI_MODEL_DRAFT
    old_medium = config.OPENAI_MODEL_MEDIUM
    try:
        config.OPENAI_MODEL_DRAFT = "gpt-4.1-mini"
        config.OPENAI_MODEL_MEDIUM = "gpt-4.1"
        assert config.draft_model_for_mode("tired") == "gpt-4.1-mini"
        assert config.draft_model_for_mode("medium") == "gpt-4.1"
    finally:
        config.OPENAI_MODEL_DRAFT = old_draft
        config.OPENAI_MODEL_MEDIUM = old_medium


def test_ab_variant():
    assert config.ab_variant(None) == "control"
    old = config.AB_TEST_ENABLED
    try:
        config.AB_TEST_ENABLED = True
        assert config.ab_variant(100) == "control"
        assert config.ab_variant(101) == "no_polish"
    finally:
        config.AB_TEST_ENABLED = old


def test_story_generation_meta_dict():
    meta = StoryGenerationMeta(
        used_llm=True,
        mode="medium",
        ab_variant="control",
        draft_model="gpt-4.1-mini",
        word_count=800,
        latency_ms=12000,
        prompt_tokens=1000,
        completion_tokens=2000,
        rewrite_applied=True,
        prompt_version="v2",
    )
    d = meta.as_dict()
    assert d["mode"] == "medium"
    assert d["rewrite_applied"] is True
    assert d["word_count"] == 800
    assert d["prompt_version"] == "v2"


if __name__ == "__main__":
    tests = [
        test_max_tokens_by_mode,
        test_max_draft_retries_default,
        test_temperatures_updated,
        test_draft_model_medium_override,
        test_ab_variant,
        test_story_generation_meta_dict,
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"All {len(tests)} tests passed.")
