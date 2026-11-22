
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def read_int(name, default, minimum=1):
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:

    bot_token: str = os.getenv("BOT_TOKEN", "")

    database_url: str = os.getenv("DATABASE_URL", "")

    admin_ids: tuple = tuple(
        int(x.strip())
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    )

    admin_username: str = os.getenv(
        "DASHBOARD_USERNAME", "admin"
    )

    admin_password: str = os.getenv(
        "DASHBOARD_PASSWORD", ""
    )

    secret_key: str = os.getenv(
        "SECRET_KEY", ""
    )

    tempmail_api_base: str = os.getenv(
        "TEMPMAIL_API_BASE",
        "https://api.internal.temp-mail.io/api/v3"
    )

    inbox_poll_seconds: int = read_int(
        "INBOX_POLL_SECONDS", 10, 10
    )

    max_emails_per_user: int = read_int(
        "MAX_EMAILS_PER_USER", 5, 1
    )

    log_level: str = os.getenv(
        "LOG_LEVEL", "INFO"
    )

    app_timezone: str = os.getenv(
        "APP_TIMEZONE", "UTC"
    )


settings = Settings()
