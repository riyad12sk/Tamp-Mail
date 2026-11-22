import asyncio
import logging
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from config import settings
from database.db import init_db, close_db
from handlers.start import start, language, menu_callback, help_command
from handlers.email import generate_email, my_emails, delete_email, choose_delete
from handlers.inbox import inbox, view_message, refresh_inbox
from handlers.profile import profile, statistics
from handlers.admin import admin_command, admin_callback
from services.monitor import inbox_monitor

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)

async def post_init(app: Application):
    await init_db()
    app.create_task(inbox_monitor(app))
    log.info("Database ready; inbox monitor started.")

async def post_shutdown(app: Application):
    await close_db()

def main():
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is missing. Set it in Render Environment Variables.")
    app = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("stats", statistics))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(menu|lang):"))
    app.add_handler(CallbackQueryHandler(generate_email, pattern=r"^email:generate$"))
    app.add_handler(CallbackQueryHandler(my_emails, pattern=r"^email:list$"))
    app.add_handler(CallbackQueryHandler(choose_delete, pattern=r"^email:delete:list$"))
    app.add_handler(CallbackQueryHandler(delete_email, pattern=r"^email:delete:"))
    app.add_handler(CallbackQueryHandler(inbox, pattern=r"^(inbox:|refresh:)"))
    app.add_handler(CallbackQueryHandler(view_message, pattern=r"^message:"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^admin:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_command))
    log.info("Starting Telegram bot polling.")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
