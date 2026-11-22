
import logging

from config import settings

log = logging.getLogger(__name__)


async def notify_admins(context, message):

    for admin_id in settings.admin_ids:

        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="HTML"
            )

        except Exception:
            log.exception(
                "Admin notification failed for %s",
                admin_id
            )
