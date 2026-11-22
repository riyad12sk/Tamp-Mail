from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import settings
from database.db import pool

def is_admin(uid):
    return uid in settings.admin_ids

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("Access denied.")
        return
    users = await pool().fetchval("SELECT COUNT(*) FROM users")
    emails = await pool().fetchval("SELECT COUNT(*) FROM email_accounts")
    messages = await pool().fetchval("SELECT COUNT(*) FROM messages")
    await update.effective_message.reply_text(
      f"🛡 Admin Dashboard\\nUsers: {users}\\nEmails: {emails}\\nMessages: {messages}",
      reply_markup=InlineKeyboardMarkup([
       [InlineKeyboardButton("Recent activity", callback_data="admin:activity")]
      ])
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        await q.message.reply_text("Access denied.")
        return
    if q.data == "admin:activity":
        rows = await pool().fetch("SELECT telegram_id,action,details,created_at FROM activity_logs ORDER BY id DESC LIMIT 10")
        text = "Recent activity:\\n" + "\\n".join(f"{r['telegram_id']} | {r['action']} | {r['details'] or ''}" for r in rows)
        await q.message.reply_text(text[:3500] or "No activity yet.")
