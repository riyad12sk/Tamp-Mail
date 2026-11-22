
import html
from datetime import datetime, timezone

from telegram.constants import ParseMode
from telegram.error import BadRequest


DIVIDER = "━━━━━━━━━━━━━━━━━━"


def esc(value):
    if value is None:
        return ""

    return html.escape(str(value), quote=True)


def fmt_time(value):

    if not value:
        return "-"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return value

    if not isinstance(value, datetime):
        return str(value)

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).strftime(
        "%d %b %Y, %H:%M UTC"
    )


async def safe_edit(query, text, reply_markup=None):

    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

    except BadRequest as exc:

        if "Message is not modified" not in str(exc):
            raise
