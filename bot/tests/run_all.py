"""Запуск всех автотестов промпта и safety (фаза 7)."""
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BOT_DIR = TESTS_DIR.parent
PYTHON = sys.executable

MODULES = [
    "test_story_generator.py",
    "test_story_safety.py",
    "test_rewrite_pass.py",
    "test_llm_config.py",
    "test_feedback_hints.py",
    "test_integration.py",
    "test_rescue_scenarios.py",
]


def main() -> int:
    failed = []
    for name in MODULES:
        path = TESTS_DIR / name
        if not path.exists():
            print(f"SKIP {name} (not found)")
            continue
        print(f"--- {name} ---", flush=True)
        result = subprocess.run(
            [PYTHON, str(path)],
            cwd=str(BOT_DIR),
            capture_output=False,
        )
        if result.returncode != 0:
            failed.append(name)
    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print(f"All {len(MODULES)} test modules passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
