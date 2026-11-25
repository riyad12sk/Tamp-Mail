import logging
import time

from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import settings
from database.db import init_db, close_db, is_blocked

from handlers.start import start, menu_callback, help_command
from handlers.email import generate_email, my_emails, delete_email, choose_delete
from handlers.inbox import inbox, view_message
from handlers.profile import profile, statistics
from handlers.admin import (
    admin_command,
    admin_callback,
    broadcast_command,
    block_user_command,
    unblock_user_command,
)

from services.monitor import inbox_monitor


# ==============================
# LOGGING CONFIGURATION
# ==============================

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

log = logging.getLogger(__name__)


# ==============================
# BLOCK FILTER - runs before every other handler (group=-1)
# ==============================

async def block_filter(update, context):
    uid = update.effective_user.id if update.effective_user else None
    if uid is None:
        return
    try:
        blocked = await is_blocked(uid)
    except Exception:
        # DB not ready / transient error - never lock users out because of it.
        return
    if blocked:
        if update.callback_query:
            await update.callback_query.answer("🚫 আপনাকে এই বটে ব্লক করা হয়েছে।", show_alert=True)
        elif update.message:
            await update.message.reply_text("🚫 আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে।")
        raise ApplicationHandlerStop()


# ==============================
# APPLICATION STARTUP
# ==============================

async def post_init(app: Application):
    try:
        await init_db()

        app.create_task(
            inbox_monitor(app),
            name="inbox-monitor"
        )

        log.info(
            "Database ready. Inbox monitor started."
        )

    except Exception:
        log.exception("Application startup failed.")
        raise


# ==============================
# APPLICATION SHUTDOWN
# ==============================

async def post_shutdown(app: Application):
    try:
        await close_db()
        log.info("Database connection closed.")

    except Exception:
        log.exception("Database shutdown error.")


# ==============================
# ERROR HANDLER
# ==============================

async def error_handler(update, context):
    log.error(
        "Telegram update error:",
        exc_info=context.error
    )


# ==============================
# BUILD APPLICATION
# ==============================

def build_app() -> Application:

    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN is missing. "
            "Set it in Render Environment Variables."
        )

    app = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # --------------------------
    # BLOCK FILTER (must be first - its own group)
    # --------------------------

    app.add_handler(MessageHandler(filters.ALL, block_filter), group=-1)
    app.add_handler(CallbackQueryHandler(block_filter), group=-1)

    # --------------------------
    # COMMAND HANDLERS
    # --------------------------

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("stats", statistics))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("block", block_user_command))
    app.add_handler(CommandHandler("unblock", unblock_user_command))

    # --------------------------
    # MENU & LANGUAGE
    # --------------------------

    app.add_handler(
        CallbackQueryHandler(
            menu_callback,
            pattern=r"^(menu|lang):"
        )
    )

    # --------------------------
    # EMAIL HANDLERS
    # --------------------------

    app.add_handler(
        CallbackQueryHandler(
            generate_email,
            pattern=r"^email:generate$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            my_emails,
            pattern=r"^email:list$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            choose_delete,
            pattern=r"^email:delete:list$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            delete_email,
            pattern=r"^email:delete:"
        )
    )

    # --------------------------
    # INBOX & REFRESH HANDLERS
    # --------------------------

    app.add_handler(
        CallbackQueryHandler(
            inbox,
            pattern=r"^(inbox:|refresh:)"
        )
    )

    # --------------------------
    # MESSAGE VIEW HANDLER
    # --------------------------

    app.add_handler(
        CallbackQueryHandler(
            view_message,
            pattern=r"^message:"
        )
    )

    # --------------------------
    # ADMIN HANDLER
    # --------------------------

    app.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^admin:"
        )
    )

    # --------------------------
    # TEXT MESSAGE HANDLER
    # --------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            help_command
        )
    )

    # --------------------------
    # ERROR HANDLER
    # --------------------------

    app.add_error_handler(error_handler)

    return app


# ==============================
# MAIN ENTRY POINT - WITH AUTO-RECOVERY
# ==============================

def main():
    """
    Builds and runs the bot. python-telegram-bot's run_polling() already
    retries transient network errors on its own. This outer loop is an
    extra safety net: if polling ever exits because of a genuinely
    unexpected, unhandled error, it rebuilds the Application and starts
    again after a short delay - instead of letting the whole worker
    process die and wait for Render to notice and restart it. A clean,
    intentional stop (e.g. Render sending SIGTERM during a deploy) makes
    run_polling() return normally, which simply ends the loop.
    """
    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN is missing. Set it in Render Environment Variables."
        )

    backoff = 5
    while True:
        try:
            app = build_app()
            log.info("Starting Telegram bot polling.")
            app.run_polling(
                allowed_updates=[
                    "message",
                    "callback_query",
                ],
                drop_pending_updates=False,
            )
            break
        except Exception:
            log.exception(
                "Bot crashed unexpectedly. Restarting in %s seconds.",
                backoff,
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    main()
