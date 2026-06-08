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
            """
        )
        await db.commit()
        await _migrate_gender_column(db)


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
    async with aiosqlite.connect(DATABASE_PATH) as db:
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
            UPDATE users SET length_pref = MAX(0.5, MIN(1.5, length_pref * ?))
            WHERE telegram_id = ?
            """,
            (factor, telegram_id),
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
