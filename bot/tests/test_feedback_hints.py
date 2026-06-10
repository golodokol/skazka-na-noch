"""Тесты feedback → prompt (фаза 6)."""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from story_feedback_hints import BAD_REASON_TO_HINT, user_prompt_hint
from story_generator import _build_system_prompt, _build_user_prompt
from story_variety import pick_variety


def test_bad_reason_mapping():
    assert BAD_REASON_TO_HINT["boring"] == "boring"
    assert BAD_REASON_TO_HINT["scary"] == "scary"
    assert "short" not in BAD_REASON_TO_HINT


def test_user_prompt_hint_boring():
    hint = user_prompt_hint("boring")
    assert "скучной" in hint
    assert user_prompt_hint("scary") == ""


def test_system_prompt_scary_feedback():
    prompt = _build_system_prompt(
        age=5,
        name="Маша",
        hero="Луна",
        mode="tired",
        word_target=720,
        no_scary=True,
        gender="f",
        prompt_hint="scary",
    )
    assert "испугала" in prompt.lower() or "испугала" in prompt


def test_user_prompt_includes_hint():
    user = _build_user_prompt(
        mode="tired",
        name="Маша",
        hero="Луна",
        word_target=720,
        day_context="",
        age=5,
        gender="f",
        prompt_hint="boring",
    )
    assert "УЧТИ ОТЗЫВ" in user
    assert "скучной" in user


def test_variety_fresh_boost_offset():
    plan = pick_variety(5, [], seed=1, fresh_boost_offset=2)
    plan_base = pick_variety(5, [], seed=1, fresh_boost_offset=0)
    assert plan.fresh_boost == plan_base.fresh_boost + 2


async def _test_db_prompt_hint_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        old_path = config.DATABASE_PATH
        config.DATABASE_PATH = db_path
        db.DATABASE_PATH = db_path
        try:
            await db.init_db()
            await db.set_prompt_hint(42, "boring")
            assert await db.get_prompt_hint(42) == "boring"
            await db.clear_prompt_hint(42)
            assert await db.get_prompt_hint(42) == ""
        finally:
            config.DATABASE_PATH = old_path
            db.DATABASE_PATH = old_path


async def _test_feedback_variety_boost():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        old_path = config.DATABASE_PATH
        config.DATABASE_PATH = db_path
        db.DATABASE_PATH = db_path
        try:
            await db.init_db()
            uid = 99
            for _ in range(3):
                await db.save_story_feedback(uid, "asleep")
            assert await db.feedback_variety_boost(uid) == 2
            await db.save_story_feedback(uid, "long")
            assert await db.feedback_variety_boost(uid) == 0
        finally:
            config.DATABASE_PATH = old_path
            db.DATABASE_PATH = old_path


def test_db_async():
    asyncio.run(_test_db_prompt_hint_roundtrip())
    asyncio.run(_test_feedback_variety_boost())


if __name__ == "__main__":
    tests = [
        test_bad_reason_mapping,
        test_user_prompt_hint_boring,
        test_system_prompt_scary_feedback,
        test_user_prompt_includes_hint,
        test_variety_fresh_boost_offset,
        test_db_async,
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"All {len(tests)} tests passed.")
