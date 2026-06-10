"""Тесты post-check сказок (фаза 2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from story_safety import check_ai_cliches, check_story, check_today_verbatim, check_name_usage


GOOD_STORY = """
Петя лежал на кровати и слушал, как дождь стучит по стеклу — ровно и негромко.
Рядом с ним сидел зайчик Снежок и держал в лапках маленький камешек.
Он провёл пальцем по камешку, и тот стал гладким и тёплым.
Петя положил камешек на тумбочку, укутался в плед и закрыл глазки.
Сон подошёл к нему тихо, как дождь за окном.
""" * 8

CLICHE_STORY = """
В этот вечер наступил вечер, и история началась. Оказалось, что мальчик устал.
И тут он вдруг понял, что пора спать. Волшебный мир снов звал его.
Как из сказки, всё было удивительным и необыкновенным.
Мальчик лег и закрыл глазки, и сон пришёл к нему мягко.
""" * 10


def test_good_story_no_cliche_violation():
    assert check_ai_cliches(GOOD_STORY) == []


def test_cliche_density_detected():
    violations = check_ai_cliches(CLICHE_STORY)
    assert "ai_cliche_density" in violations


def test_cliche_opening_detected():
    text = "В этот вечер малыш лег спать. " + GOOD_STORY
    violations = check_ai_cliches(text)
    assert "ai_cliche_opening" in violations


def test_check_story_includes_cliches():
    violations = check_story(CLICHE_STORY, word_min=50)
    assert any(v in ("ai_cliche_density", "ai_cliche_opening") for v in violations)


def test_today_verbatim_short_context_skipped():
    assert check_today_verbatim("любой текст", "коротко") == []


def test_today_verbatim_detects_copy():
    ctx = "сегодня малыш поссорился с другом в садике и очень расстроился"
    story = f"Вечером {ctx}, и мама обняла его."
    assert check_today_verbatim(story, ctx) == ["verbatim_day_context"]


def test_today_verbatim_metaphor_ok():
    ctx = "сегодня малыш поссорился с другом в садике и очень расстроился"
    story = (
        "Вечером у малыша было облачко на ладони — взъерошенное и тяжёлое. "
        "Мама помогла разгладить его, и облачко стало лёгким."
    ) * 12
    assert check_today_verbatim(story, ctx) == []


def test_check_story_includes_verbatim():
    ctx = "сегодня малыш поссорился с другом в садике и очень расстроился"
    story = f"Сказка началась. {ctx}. Потом все легли спать."
    violations = check_story(story, day_context=ctx, word_min=10)
    assert "verbatim_day_context" in violations


def test_name_usage_bounds():
    name = "Миша"
    ok = " ".join([f"Миша {'устал' if i==0 else 'он лег'}." for i in range(5)])
    assert check_name_usage(ok, name) == []
    declined = "Мише было тепло. Он лег. Мишу укрыл плед. Мишей доволен. Миша уснул."
    assert check_name_usage(declined, name) == []
    too_many = " ".join(["Миша"] * 8)
    assert check_name_usage(too_many, name) == ["name_too_often"]
    too_few = "Мише было тепло. Он закрыл глазки и уснул."
    assert check_name_usage(too_few, name) == ["name_too_rare"]


if __name__ == "__main__":
    tests = [
        test_good_story_no_cliche_violation,
        test_cliche_density_detected,
        test_cliche_opening_detected,
        test_check_story_includes_cliches,
        test_today_verbatim_short_context_skipped,
        test_today_verbatim_detects_copy,
        test_today_verbatim_metaphor_ok,
        test_check_story_includes_verbatim,
        test_name_usage_bounds,
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"All {len(tests)} tests passed.")
