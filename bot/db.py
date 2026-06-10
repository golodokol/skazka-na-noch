import aiosqlite
from datetime import date, timedelta
from pathlib import Path

from config import DATABASE_PATH


def week_start(d: date | None = None) -> str:
    d = d or date.today()
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat()


async def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_mode TEXT,
                length_pref REAL DEFAULT 1.0
            );
            CREATE TABLE IF NOT EXISTS child_profiles (
                user_id INTEGER PRIMARY KEY REFERENCES users(telegram_id),
                name TEXT NOT NULL DEFAULT 'Малыш',
                age_years INTEGER NOT NULL DEFAULT 4,
                gender TEXT NOT NULL DEFAULT 'm',
                favorite_hero TEXT DEFAULT '',
                no_scary INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS usage_weekly (
                user_id INTEGER,
                week_start TEXT,
                story_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, week_start)
            );
            CREATE TABLE IF NOT EXISTS story_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                mode TEXT,
                setting_id TEXT,
                helper_id TEXT,
                angle_id TEXT,
                metaphor TEXT,
                snippet TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_story_memory_user
                ON story_memory(user_id, id DESC);
            CREATE TABLE IF NOT EXISTS story_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                feedback TEXT NOT NULL,
                bad_reason TEXT,
                bad_text TEXT,
                mode TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_story_feedback_user
                ON story_feedback(user_id, id DESC);
            CREATE TABLE IF NOT EXISTS story_generation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                mode TEXT,
                ab_variant TEXT,
                draft_model TEXT,
                polish_model TEXT,
                rewrite_attempted INTEGER DEFAULT 0,
                rewrite_applied INTEGER DEFAULT 0,
                fallback INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                word_count INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_story_gen_log_user
                ON story_generation_log(user_id, id DESC);
            """
        )
        await db.commit()
        await _migrate_gender_column(db)
        await _migrate_prompt_hint_column(db)
        await _migrate_story_gen_log_columns(db)


STORY_MEMORY_KEEP = 12


async def get_story_memories(telegram_id: int, limit: int = STORY_MEMORY_KEEP) -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT mode, setting_id, helper_id, angle_id, metaphor, snippet
            FROM story_memory
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (telegram_id, limit),
        )
        return [dict(row) for row in await cur.fetchall()]


async def add_story_memory(telegram_id: int, memory: dict) -> None:
    await ensure_user(telegram_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO story_memory
                (user_id, mode, setting_id, helper_id, angle_id, metaphor, snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                memory.get("mode", ""),
                memory.get("setting_id", ""),
                memory.get("helper_id", ""),
                memory.get("angle_id", ""),
                memory.get("metaphor", ""),
                memory.get("snippet", ""),
            ),
        )
        await db.execute(
            """
            DELETE FROM story_memory
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM story_memory
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (telegram_id, telegram_id, STORY_MEMORY_KEEP),
        )
        await db.commit()


async def log_story_generation(telegram_id: int, meta: dict) -> None:
    """Лог генерации для A/B и метрик (latency, tokens, rewrite)."""
    await ensure_user(telegram_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO story_generation_log (
                user_id, mode, ab_variant, draft_model, polish_model,
                rewrite_attempted, rewrite_applied, fallback,
                latency_ms, draft_latency_ms, polish_latency_ms,
                word_count, prompt_tokens, completion_tokens, retry_count,
                prompt_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                meta.get("mode", ""),
                meta.get("ab_variant", ""),
                meta.get("draft_model", ""),
                meta.get("polish_model", ""),
                1 if meta.get("rewrite_attempted") else 0,
                1 if meta.get("rewrite_applied") else 0,
                1 if meta.get("fallback") else 0,
                int(meta.get("latency_ms") or 0),
                int(meta.get("draft_latency_ms") or 0),
                int(meta.get("polish_latency_ms") or 0),
                int(meta.get("word_count") or 0),
                int(meta.get("prompt_tokens") or 0),
                int(meta.get("completion_tokens") or 0),
                int(meta.get("retry_count") or 0),
                meta.get("prompt_version", ""),
            ),
        )
        await db.commit()


async def _migrate_story_gen_log_columns(db: aiosqlite.Connection) -> None:
    cur = await db.execute("PRAGMA table_info(story_generation_log)")
    cols = {row[1] for row in await cur.fetchall()}
    if "prompt_version" not in cols:
        await db.execute(
            "ALTER TABLE story_generation_log ADD COLUMN prompt_version TEXT NOT NULL DEFAULT ''"
        )
    if "draft_latency_ms" not in cols:
        await db.execute(
            "ALTER TABLE story_generation_log ADD COLUMN draft_latency_ms INTEGER DEFAULT 0"
        )
    if "polish_latency_ms" not in cols:
        await db.execute(
            "ALTER TABLE story_generation_log ADD COLUMN polish_latency_ms INTEGER DEFAULT 0"
        )
    await db.commit()


async def _migrate_prompt_hint_column(db: aiosqlite.Connection) -> None:
    cur = await db.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in await cur.fetchall()}
    if "prompt_hint" not in cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN prompt_hint TEXT NOT NULL DEFAULT ''"
        )
        await db.commit()


async def _migrate_gender_column(db: aiosqlite.Connection) -> None:
    cur = await db.execute("PRAGMA table_info(child_profiles)")
    cols = {row[1] for row in await cur.fetchall()}
    if "gender" not in cols:
        await db.execute(
            "ALTER TABLE child_profiles ADD COLUMN gender TEXT NOT NULL DEFAULT 'm'"
        )
        await db.commit()


async def ensure_user(telegram_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
            (telegram_id,),
        )
        await db.commit()


async def get_profile(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT c.name, c.age_years, c.gender, c.favorite_hero, c.no_scary,
                   u.last_mode, u.length_pref
            FROM child_profiles c
            JOIN users u ON u.telegram_id = c.user_id
            WHERE c.user_id = ?
            """,
            (telegram_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def save_profile(
    telegram_id: int,
    name: str,
    age_years: int,
    favorite_hero: str = "",
    gender: str = "m",
) -> None:
    await ensure_user(telegram_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO child_profiles (user_id, name, age_years, gender, favorite_hero)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name=excluded.name,
                age_years=excluded.age_years,
                gender=excluded.gender,
                favorite_hero=excluded.favorite_hero
            """,
            (telegram_id, name, age_years, gender, favorite_hero),
        )
        await db.commit()


async def update_profile_field(telegram_id: int, field: str, value) -> None:
    allowed = {"name", "age_years", "gender", "favorite_hero"}
    if field not in allowed:
        return
    await ensure_user(telegram_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT 1 FROM child_profiles WHERE user_id = ?",
            (telegram_id,),
        )
        if not await cur.fetchone():
            await db.execute(
                """
                INSERT INTO child_profiles (user_id, name, age_years, gender)
                VALUES (?, 'Малыш', 4, 'm')
                """,
                (telegram_id,),
            )
        await db.execute(
            f"UPDATE child_profiles SET {field} = ? WHERE user_id = ?",
            (value, telegram_id),
        )
        await db.commit()


async def set_last_mode(telegram_id: int, mode: str) -> None:
    await ensure_user(telegram_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET last_mode = ? WHERE telegram_id = ?",
            (mode, telegram_id),
        )
        await db.commit()


async def adjust_length_pref(telegram_id: int, factor: float) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE users SET length_pref = MAX(0.5, length_pref * ?)
            WHERE telegram_id = ?
            """,
            (factor, telegram_id),
        )
        await db.commit()


async def set_prompt_hint(telegram_id: int, hint_key: str) -> None:
    await ensure_user(telegram_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET prompt_hint = ? WHERE telegram_id = ?",
            (hint_key.strip(), telegram_id),
        )
        await db.commit()


async def get_prompt_hint(telegram_id: int) -> str:
    await ensure_user(telegram_id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT prompt_hint FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cur.fetchone()
        return (row[0] or "").strip() if row else ""


async def clear_prompt_hint(telegram_id: int) -> None:
    await set_prompt_hint(telegram_id, "")


async def get_recent_feedback_types(telegram_id: int, limit: int = 5) -> list[str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            """
            SELECT feedback FROM story_feedback
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (telegram_id, limit),
        )
        return [row[0] for row in await cur.fetchall()]


async def feedback_variety_boost(telegram_id: int) -> int:
    """+2 к fresh_boost, если последние 3 отзыва — «уснул»."""
    recent = await get_recent_feedback_types(telegram_id, 3)
    if len(recent) >= 3 and all(f == "asleep" for f in recent):
        return 2
    return 0


async def save_story_feedback(
    telegram_id: int,
    feedback: str,
    *,
    bad_reason: str = "",
    bad_text: str = "",
    mode: str = "",
) -> None:
    await ensure_user(telegram_id)
    if not mode:
        profile = await get_profile(telegram_id)
        mode = (profile or {}).get("last_mode") or ""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO story_feedback
                (user_id, feedback, bad_reason, bad_text, mode)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, feedback, bad_reason or None, bad_text or None, mode or None),
        )
        await db.commit()


async def get_weekly_count(telegram_id: int) -> int:
    ws = week_start()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT story_count FROM usage_weekly WHERE user_id = ? AND week_start = ?",
            (telegram_id, ws),
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def increment_usage(telegram_id: int) -> int:
    await ensure_user(telegram_id)
    ws = week_start()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO usage_weekly (user_id, week_start, story_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, week_start) DO UPDATE SET
                story_count = story_count + 1
            """,
            (telegram_id, ws),
        )
        await db.commit()
        cur = await db.execute(
            "SELECT story_count FROM usage_weekly WHERE user_id = ? AND week_start = ?",
            (telegram_id, ws),
        )
        row = await cur.fetchone()
        return row[0]
