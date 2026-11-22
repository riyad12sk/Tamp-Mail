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
    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    api_token TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(telegram_id, email)
);
CREATE INDEX IF NOT EXISTS idx_email_accounts_active ON email_accounts(is_active);
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,
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
    _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5, command_timeout=30)
    async with _pool.acquire() as conn:
        await conn.execute(SCHEMA)

async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

def pool():
    if _pool is None:
        raise RuntimeError("Database pool is not initialized.")
    return _pool

async def log_action(telegram_id, action, details=None):
    await pool().execute(
        "INSERT INTO activity_logs(telegram_id, action, details) VALUES($1,$2,$3)",
        telegram_id, action, details
    )
