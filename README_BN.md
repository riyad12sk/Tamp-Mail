# Tamp-Mail

Python Telegram bot and browser admin dashboard.

## Security and environment

Never commit `.env`, bot tokens, database URLs, passwords, or signing keys.
If a Telegram bot token was ever exposed in chat, terminal history, logs, or Git history, revoke it with BotFather and set a fresh `BOT_TOKEN` in your hosting environment.

Required environment variables:

- `BOT_TOKEN`: Telegram bot token
- `DATABASE_URL`: PostgreSQL connection string
- `ADMIN_IDS`: comma-separated numeric Telegram admin IDs
- `DASHBOARD_USERNAME`: dashboard login name
- `DASHBOARD_PASSWORD`: unique strong dashboard password
- `SECRET_KEY`: random secret with at least 32 characters
- `DASHBOARD_COOKIE_SECURE`: `true` when served over HTTPS (recommended)
- `TEMPMAIL_API_BASE`: provider API base URL
- `INBOX_POLL_SECONDS`: monitor interval (minimum 10 seconds)
- `MAX_EMAILS_PER_USER`: application account limit

The dashboard fails startup if its database or authentication secrets are missing. Login has a basic per-process attempt limit, session cookies are HTTP-only (Starlette default), SameSite=Lax, and logout/login forms use CSRF tokens. Use HTTPS and a strong password. The in-memory login throttle resets when the web process restarts and is not a substitute for an upstream rate limiter.

## Deploy with Render

1. Connect this repository to Render and deploy the Blueprint in `render.yaml`.
2. Set `BOT_TOKEN` and `ADMIN_IDS` for the worker.
3. Set unique `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` for the dashboard.
4. Render generates `SECRET_KEY`; keep `DASHBOARD_COOKIE_SECURE=true` when using the HTTPS service URL.
5. Check worker logs and open the dashboard service URL.

Review the current Render pricing and service availability before deploying; the service plans in the Blueprint may incur charges.

## Provider compatibility

The email provider adapter in `services/tempmail.py` uses a specific API path and response shape. The endpoint shown in the default configuration may be internal, unofficial, change without notice, or unavailable. Confirm you have permission to use the provider and consult its current official documentation before deployment. Do not assume the adapter is compatible with another provider without adapting and testing its documented API.

## Operational limitations

- Inbox polling is sequential and limited to a batch of 100 active accounts per cycle. It is intended for small-scale testing, not high-volume production.
- The monitor respects `INBOX_POLL_SECONDS` and isolates failures per mailbox.
- Deleting an address in the bot deactivates its local record; it does not prove the remote provider mailbox has been deleted.
- Email bodies and sender details are untrusted content. Treat links and attachments cautiously.
- Database initialization runs when the bot starts. Back up PostgreSQL regularly.

## Local development

Install dependencies from `requirements.txt`, configure environment variables, then run:

```bash
python main.py
uvicorn dashboard.app:app --host 127.0.0.1 --port 8000
```

For local HTTP-only testing, set `DASHBOARD_COOKIE_SECURE=false` in the local environment. Do not use that setting on a public HTTPS deployment.
