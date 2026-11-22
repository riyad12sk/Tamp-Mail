from telegram import Update
from telegram.ext import ContextTypes
from database.db import pool, log_action
from keyboards.buttons import TEXT, main_menu, language_menu

async def ensure_user(update):
    u = update.effective_user
    await pool().execute("""
      INSERT INTO users(telegram_id, username, first_name)
      VALUES($1,$2,$3)
      ON CONFLICT(telegram_id) DO UPDATE SET username=EXCLUDED.username,
      first_name=EXCLUDED.first_name, last_seen=NOW()
    """, u.id, u.username, u.first_name)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update)
    lang = await pool().fetchval("SELECT language FROM users WHERE telegram_id=$1", update.effective_user.id)
    t = TEXT.get(lang, TEXT["en"])
    await update.message.reply_text(t["welcome"] + "\n\n" + t["choose"], reply_markup=main_menu(lang), parse_mode="Markdown")
    await log_action(update.effective_user.id, "start")

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = await pool().fetchval("SELECT language FROM users WHERE telegram_id=$1", uid) or "en"
    if q.data.startswith("lang:"):
        lang = q.data.split(":")[1]
        await pool().execute("UPDATE users SET language=$1 WHERE telegram_id=$2", lang, uid)
        await q.edit_message_text(TEXT[lang]["welcome"] + "\n\n" + TEXT[lang]["choose"],
                                  reply_markup=main_menu(lang), parse_mode="Markdown")
        return
    action = q.data.split(":")[1]
    if action == "home":
        await q.edit_message_text(TEXT[lang]["choose"], reply_markup=main_menu(lang))
    elif action == "language":
        await q.edit_message_text("Choose your language / ভাষা নির্বাচন করুন:", reply_markup=language_menu())
    elif action == "profile":
        from handlers.profile import profile
        await profile(update, context, from_callback=True)
    elif action == "stats":
        from handlers.profile import statistics
        await statistics(update, context, from_callback=True)
    elif action == "help":
        await q.edit_message_text("Use Generate email to create an inbox. Open My inbox to view messages.\\n\\nনতুন ইমেইল তৈরি করতে Generate email চাপুন।", reply_markup=main_menu(lang))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = "en"
    if update.effective_user:
        lang = await pool().fetchval("SELECT language FROM users WHERE telegram_id=$1", update.effective_user.id) or "en"
    await update.effective_message.reply_text(TEXT[lang]["help"] + ": Generate an address, then check its inbox.")
