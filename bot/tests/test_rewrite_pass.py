"""Тесты rewrite-pass (фаза 4)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from config import rewrite_pass_for_mode
from story_generator import (
    _build_polish_user,
    _load_polish_system,
    accept_polished_story,
)


def _long_story(prefix: str = "Тихий") -> str:
    base = (
        f"{prefix} вечер в комнате, где на полке стояла игрушка. "
        "Ребёнок лег на кровать рядом с другом и укутался в плед. "
        "За окном шёл дождь, и капли стучали по стеклу ровно и негромко. "
        "Они говорили шёпотом о том, как прошёл день, и постепенно голоса стали тише. "
        "Свет ночника стал желтее, мысли потекли медленнее, и скоро наступил сон. "
    )
    return (base * 12).strip()


def test_rewrite_pass_modes():
    assert rewrite_pass_for_mode("medium") is True
    assert rewrite_pass_for_mode("today") is True
    assert rewrite_pass_for_mode("tired") is False
    assert rewrite_pass_for_mode("screen_free") is False


def test_ab_user_disables_rewrite():
    old = config.AB_TEST_ENABLED
    try:
        config.AB_TEST_ENABLED = True
        assert rewrite_pass_for_mode("medium", user_id=100) is True
        assert rewrite_pass_for_mode("medium", user_id=101) is False
    finally:
        config.AB_TEST_ENABLED = old


def test_accept_polished_keeps_length():
    draft = _long_story()
    polished = draft + " " + _long_story("Ещё")
    assert accept_polished_story(draft, polished, word_min=100) is True


def test_reject_polished_if_too_short():
    draft = _long_story()
    polished = draft[: len(draft) // 2]
    assert accept_polished_story(draft, polished, word_min=100) is False


def test_reject_polished_with_cliches():
    draft = _long_story()
    polished = (
        "В этот вечер наступил вечер, и история началась. "
        "Оказалось, что и тут он вдруг понял. "
        + _long_story("Шум")
    )
    assert accept_polished_story(draft, polished, word_min=50) is False


def test_polish_prompts():
    system = _load_polish_system(name="Маша", hero="Луна", word_min=500, no_scary=True)
    assert "Маша" in system
    assert "Луна" in system
    assert "500" in system
    user = _build_polish_user("Черновик сказки.", word_min=500)
    assert "Черновик сказки." in user
    assert "500" in user


if __name__ == "__main__":
    tests = [
        test_rewrite_pass_modes,
        test_ab_user_disables_rewrite,
        test_accept_polished_keeps_length,
        test_reject_polished_if_too_short,
        test_reject_polished_with_cliches,
        test_polish_prompts,
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"All {len(tests)} tests passed.")
