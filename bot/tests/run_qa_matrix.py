"""Ручная QA-матрица: генерация + проверка чеклиста (фаза 7)."""
from __future__ import annotations

import asyncio
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import OPENAI_API_KEY, PROMPT_VERSION
from story_generator import (
    generate_story,
    story_delivery_chunks,
    word_target_for,
    word_min_for,
    _reading_minutes,
    TELEGRAM_MESSAGE_LIMIT,
)
from story_safety import check_ai_cliches, check_story, story_word_count
from texts import AFTER_STORY

NAME = "Миша"
GENDER = "m"
USER_ID = 100  # чётный → control (с polish для medium/today)

SLEEP_MARKERS = (
    "сон", "спит", "спать", "закрыл глаз", "закрыла глаз",
    "покой", "тихо", "дыш", "кроват", "подушк",
)

PROPP_MARKERS = (
    "дом", "комнат", "кроват", "вечер", "устал", "тропин",
    "лун", "звезд", "звёзд", "помог", "рядом", "тепл",
    "облач", "камеш", "плед", "зайчик", "сон",
)


@dataclass
class QACase:
    id: int
    label: str
    mode: str
    age: int
    hero: str
    day_context: str = ""


@dataclass
class QAResult:
    case: QACase
    rating: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    excerpt_start: str = ""
    excerpt_end: str = ""


def build_cases() -> list[QACase]:
    cases: list[QACase] = []
    n = 1
    for age in (3, 5, 7):
        for mode in ("tired", "medium"):
            for hero in ("Зайчик", ""):
                hero_tag = "hero" if hero else "no_hero"
                cases.append(
                    QACase(
                        id=n,
                        label=f"base_a{age}_{mode}_{hero_tag}",
                        mode=mode,
                        age=age,
                        hero=hero,
                    )
                )
                n += 1
    today_specs = (
        (3, "поссорился с другом в садике"),
        (5, "очень устал, капризничал"),
        (7, "боялся темноты"),
    )
    for age, ctx in today_specs:
        for hero in ("Зайчик", ""):
            hero_tag = "hero" if hero else "no_hero"
            cases.append(
                QACase(
                    id=n,
                    label=f"today_a{age}_{hero_tag}",
                    mode="today",
                    age=age,
                    hero=hero,
                    day_context=ctx,
                )
            )
            n += 1
    return cases


from name_grammar import count_name_mentions as count_name


def propp_score(text: str) -> int:
    lower = text.lower()
    return sum(1 for m in PROPP_MARKERS if m in lower)


def sleep_in_ending(text: str) -> bool:
    tail = text.strip()[-max(len(text) // 3, 200):].lower()
    return any(m in tail for m in SLEEP_MARKERS)


def evaluate(case: QACase, story: str, meta: dict) -> QAResult:
    result = QAResult(case=case, meta=meta, rating="👍")
    word_target = word_target_for(case.mode, case.age)
    word_min = word_min_for(word_target)
    wc = story_word_count(story)
    reading_min = _reading_minutes(word_target)

    violations = check_story(
        story,
        no_scary=True,
        word_min=word_min,
        day_context=case.day_context,
        name=NAME,
    )
    if not violations:
        result.passed.append("safety")
    else:
        result.failed.append(f"safety:{','.join(violations)}")

    if not check_ai_cliches(story):
        result.passed.append("no_cliche")
    else:
        result.failed.append("cliche")

    nc = count_name(story, NAME, GENDER)
    if 3 <= nc <= 5:
        result.passed.append(f"name_count={nc}")
    else:
        result.failed.append(f"name_count={nc} (want 3-5)")

    if sleep_in_ending(story):
        result.passed.append("sleep_ending")
    else:
        result.failed.append("sleep_ending")

    if story.strip()[-200:].find("?") == -1:
        result.passed.append("no_question_end")
    else:
        result.failed.append("question_in_ending")

    ps = propp_score(story)
    if ps >= 5:
        result.passed.append(f"propp_hints={ps}")
    elif ps >= 3:
        result.passed.append(f"propp_hints={ps}(weak)")
        result.notes.append("дуга Проппа слабая")
    else:
        result.failed.append(f"propp_hints={ps}")

    if wc >= word_min:
        result.passed.append(f"words={wc}>={word_min}")
    else:
        result.failed.append(f"words={wc}<{word_min}")

    footer = AFTER_STORY.replace("{имя}", NAME).replace("{name}", NAME)
    chunks = story_delivery_chunks(story, footer)
    oversize = [len(c) for c in chunks if len(c) > TELEGRAM_MESSAGE_LIMIT]
    if not oversize:
        result.passed.append(f"telegram={len(chunks)}parts")
    else:
        result.failed.append(f"telegram_chunk>{TELEGRAM_MESSAGE_LIMIT}:{oversize}")

    if case.mode == "today" and case.day_context:
        if "verbatim_day_context" not in violations:
            result.passed.append("no_verbatim")
        else:
            result.failed.append("verbatim_day_context")

    if meta.get("fallback"):
        result.failed.append("fallback_used")
        result.notes.append("использован fallback, не LLM")

    if case.age <= 3:
        avg_sent = wc / max(story.count("."), 1)
        if avg_sent <= 25:
            result.passed.append("short_sentences")
        else:
            result.notes.append(f"длинные предложения для 3 лет (~{avg_sent:.0f} сл/предл)")

    if case.mode == "medium" and meta.get("rewrite_applied"):
        result.passed.append("polish_applied")
    elif case.mode == "medium" and not meta.get("fallback"):
        result.notes.append("polish не применён (A/B или отклонён)")

    fail_n = len(result.failed)
    if fail_n == 0:
        result.rating = "👍"
    elif fail_n <= 2 and "fallback_used" not in result.failed:
        result.rating = "😐"
    else:
        result.rating = "😟"

    result.excerpt_start = story[:350].replace("\n", " ")
    result.excerpt_end = story[-250:].replace("\n", " ")
    return result


async def run_case(case: QACase, *, prompt_only: bool = False) -> QAResult:
    if prompt_only:
        from story_generator import _build_system_prompt, _build_user_prompt

        wt = word_target_for(case.mode, case.age)
        system = _build_system_prompt(
            age=case.age,
            name=NAME,
            hero=case.hero,
            mode=case.mode,
            word_target=wt,
            no_scary=True,
            gender=GENDER,
            day_context=case.day_context,
        )
        user = _build_user_prompt(
            mode=case.mode,
            name=NAME,
            hero=case.hero,
            word_target=wt,
            day_context=case.day_context,
            age=case.age,
            gender=GENDER,
        )
        meta = {"prompt_only": True, "system_len": len(system), "user_len": len(user)}
        result = QAResult(case=case, meta=meta, rating="👍")
        checks = [
            ("narrator_voice", "ГОЛОС РАССКАЗЧИКА" in system),
            ("propp", "МОРФОЛОГИЯ СКАЗКИ" in system),
            ("one_metaphor", "ОБРАЗ ДЛЯ ЭТОЙ СКАЗКИ" in system),
            ("no_catalog", "выбери 1–2 метафоры из списка" not in system),
            ("few_shot", "ПРИМЕР ХОРОШЕГО АБЗАЦА" in system or "ПРИМЕР" in system),
        ]
        if case.mode == "today" and case.day_context:
            checks.append(("today_logic", "ЛОГИКА «СЕГОДНЯШНИЙ ДЕНЬ»" in system))
            checks.append(("verbatim_warn", "не цитировать" in user.lower() or "не повтор" in user.lower()))
        for label, ok in checks:
            if ok:
                result.passed.append(f"prompt:{label}")
            else:
                result.failed.append(f"prompt:{label}")
        if result.failed:
            result.rating = "😟"
        return result

    story, meta = await generate_story(
        mode=case.mode,
        name=NAME,
        age=case.age,
        hero=case.hero,
        day_context=case.day_context,
        no_scary=True,
        gender=GENDER,
        user_id=USER_ID,
    )
    return evaluate(case, story, meta.as_dict())


async def run_all_cases(cases: list[QACase], *, prompt_only: bool) -> list[QAResult]:
    results: list[QAResult] = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.label} ...", flush=True)
        try:
            result = await run_case(case, prompt_only=prompt_only)
            results.append(result)
            fails = ", ".join(result.failed) or "ok"
            print(f"  -> {result.rating}  fails: {fails}", flush=True)
        except Exception as exc:
            results.append(QAResult(case=case, rating="😟", failed=[f"exception:{exc}"]))
            print(f"  -> ERROR: {exc}", flush=True)
    return results


async def main() -> int:
    prompt_only = "--prompt-only" in sys.argv
    allow_fallback = "--fallback" in sys.argv
    if not OPENAI_API_KEY and not prompt_only:
        if not allow_fallback:
            print(
                "ERROR: OPENAI_API_KEY ne zadan.\n"
                "Dobavte klyuch v .env, ili: --fallback / --prompt-only"
            )
            return 1
        print("WARN: OPENAI_API_KEY pust — fallback-skazki (ne LLM v2).")

    cases = build_cases()
    mode_label = "prompt-only" if prompt_only else ("LLM" if OPENAI_API_KEY else "fallback")
    print(f"QA matrix ({mode_label}): {len(cases)} cases, PROMPT_VERSION={PROMPT_VERSION}")
    results = await run_all_cases(cases, prompt_only=prompt_only)

    counts = {"👍": 0, "😐": 0, "😟": 0}
    for r in results:
        counts[r.rating] = counts.get(r.rating, 0) + 1

    out_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "qa_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    suffix = "_prompt" if prompt_only else ""
    json_path = out_dir / f"matrix_{today}{suffix}.json"
    md_path = out_dir / f"matrix_{today}{suffix}.md"

    payload = {
        "date": today,
        "prompt_version": PROMPT_VERSION,
        "mode": mode_label,
        "llm": bool(OPENAI_API_KEY) and not prompt_only,
        "name": NAME,
        "total": len(results),
        "counts": counts,
        "results": [
            {
                "case": asdict(r.case),
                "rating": r.rating,
                "passed": r.passed,
                "failed": r.failed,
                "notes": r.notes,
                "meta": r.meta,
                "excerpt_start": r.excerpt_start,
                "excerpt_end": r.excerpt_end,
            }
            for r in results
        ],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# QA-матрица промпта v2 — {today}",
        "",
        f"**PROMPT_VERSION:** {PROMPT_VERSION}  ",
        f"**Режим:** {mode_label}  ",
        f"**Кейсов:** {len(results)}  ",
        f"**Оценки:** 👍 {counts.get('👍', 0)} · 😐 {counts.get('😐', 0)} · 😟 {counts.get('😟', 0)}",
        "",
    ]
    if prompt_only:
        lines.append("> Проверка **сборки промпта**. Для текста сказок — LLM-прогон с ключом.")
        lines.append("")
    elif not OPENAI_API_KEY:
        lines.append("> ⚠️ Fallback — LLM v2 **не проверен**. Добавьте `OPENAI_API_KEY` в `.env`.")
        lines.append("")
    lines.extend([
        "## Сводка",
        "",
        "| # | кейс | mode | age | hero | 👍/😐/😟 | fails | polish | ms |",
        "|---|------|------|-----|------|----------|-------|--------|-----|",
    ])
    for r in results:
        c = r.case
        fails = "; ".join(r.failed) if r.failed else "—"
        polish = "✓" if r.meta.get("rewrite_applied") else "—"
        ms = r.meta.get("latency_ms", r.meta.get("system_len", ""))
        hero = "Зайчик" if c.hero else "—"
        lines.append(
            f"| {c.id} | {c.label} | {c.mode} | {c.age} | {hero} | {r.rating} | {fails} | {polish} | {ms} |"
        )

    if not prompt_only:
        lines.extend(["", "## Заметки по кейсам", ""])
        for r in results:
            if r.notes or r.failed:
                lines.append(f"### {r.case.id}. {r.case.label} ({r.rating})")
                if r.failed:
                    lines.append(f"- **fail:** {', '.join(r.failed)}")
                if r.notes:
                    lines.append(f"- {', '.join(r.notes)}")
                if r.excerpt_start:
                    lines.append(f"- *начало:* …{r.excerpt_start[-200:]}")
                if r.excerpt_end:
                    lines.append(f"- *конец:* {r.excerpt_end}")
                lines.append("")

    lines.extend(["", "## Вердикт", ""])
    if prompt_only and counts.get("😟", 0) == 0:
        lines.append("✅ **Промпты OK** по всем 24 кейсам. Следующий шаг — LLM-прогон.")
    elif counts.get("😟", 0) == 0 and counts.get("👍", 0) >= len(results) * 0.7:
        lines.append("✅ **Готово к раскатке**.")
    elif counts.get("😟", 0) <= 2:
        lines.append("⚠️ **Условно готово** — см. таблицу.")
    else:
        lines.append("❌ **Не готово** — нужна доработка.")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print()
    print(f"Done: pass={counts.get('👍', 0)} warn={counts.get('😐', 0)} fail={counts.get('😟', 0)}")
    print(f"Report: {md_path}")
    return 0 if counts.get("😟", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
