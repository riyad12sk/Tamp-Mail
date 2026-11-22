
import asyncpg
from config import settings

_pool = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    language TEXT NOT NULL DEFAULT 'en',
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_accounts (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL
        REFERENCES users(telegram_id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    api_token TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(telegram_id, email)
);

CREATE INDEX IF NOT EXISTS idx_email_accounts_active
ON email_accounts(is_active);

CREATE INDEX IF NOT EXISTS idx_email_accounts_user
ON email_accounts(telegram_id);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL
        REFERENCES email_accounts(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,
    sender TEXT,
    subject TEXT,
    body TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(account_id, external_id)
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT,
    action TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def init_db():
    global _pool

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is missing.")

    if _pool is not None:
        return

    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=5,
        command_timeout=30
    )

    try:
        async with _pool.acquire() as conn:
            await conn.execute(SCHEMA)
    except Exception:
        await close_db()
        raise


async def close_db():
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None


def pool():
    if _pool is None:
        raise RuntimeError("Database pool is not initialized.")

    return _pool


async def upsert_user(telegram_id, username=None, first_name=None):

    inserted = await pool().fetchval(
        """
        INSERT INTO users (telegram_id, username, first_name)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id) DO NOTHING
        RETURNING TRUE
        """,
        telegram_id, username, first_name
    )

    if inserted:
        return True

    await pool().execute(
        """
        UPDATE users
        SET username = COALESCE($2, username),
            first_name = COALESCE($3, first_name),
            last_seen = NOW()
        WHERE telegram_id = $1
        """,
        telegram_id, username, first_name
    )

    return False


async def get_user(telegram_id):

    return await pool().fetchrow(
        "SELECT * FROM users WHERE telegram_id = $1",
        telegram_id
    )


async def set_language(telegram_id, language):

    if language not in ("bn", "en"):
        raise ValueError("Unsupported language.")

    await pool().execute(
        """
        INSERT INTO users (telegram_id, language)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id)
        DO UPDATE SET language = EXCLUDED.language
        """,
        telegram_id, language
    )


async def is_blocked(telegram_id):

    result = await pool().fetchval(
        """
        SELECT is_blocked
        FROM users
        WHERE telegram_id = $1
        """,
        telegram_id
    )

    return bool(result)


async def set_blocked(telegram_id, blocked):

    await pool().execute(
        """
        INSERT INTO users (telegram_id, is_blocked)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id)
        DO UPDATE SET is_blocked = EXCLUDED.is_blocked
        """,
        telegram_id, blocked
    )

    await log_action(
        telegram_id,
        "user_blocked" if blocked else "user_unblocked"
    )


async def all_user_ids():

    rows = await pool().fetch(
        """
        SELECT telegram_id
        FROM users
        WHERE is_blocked = FALSE
        ORDER BY created_at DESC
        """
    )

    return [row["telegram_id"] for row in rows]


async def user_count():

    count = await pool().fetchval(
        "SELECT COUNT(*) FROM users"
    )

    return count or 0


async def log_action(telegram_id, action, details=None):

    await pool().execute(
        """
        INSERT INTO activity_logs
        (telegram_id, action, details)
        VALUES ($1, $2, $3)
        """,
        telegram_id, action, details
    )
