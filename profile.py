from telegram import Update
from telegram.ext import ContextTypes
from database.db import pool

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    uid = update.effective_user.id
    row = await pool().fetchrow("SELECT first_name,username,created_at,language FROM users WHERE telegram_id=$1", uid)
    count = await pool().fetchval("SELECT COUNT(*) FROM email_accounts WHERE telegram_id=$1", uid)
    text = f"👤 Profile\\nName: {row['first_name'] or '-'}\\nUsername: @{row['username'] or '-'}\\nEmails created: {count}\\nLanguage: {row['language']}"
    if from_callback:
        await update.callback_query.message.reply_text(text)
    else:
        await update.effective_message.reply_text(text)

async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    uid = update.effective_user.id
    emails = await pool().fetchval("SELECT COUNT(*) FROM email_accounts WHERE telegram_id=$1", uid)
    messages = await pool().fetchval("""SELECT COUNT(*) FROM messages m JOIN email_accounts e ON e.id=m.account_id WHERE e.telegram_id=$1""", uid)
    text = f"📊 Your statistics\\nEmails generated: {emails}\\nMessages received: {messages}"
    if from_callback:
        await update.callback_query.message.reply_text(text)
    else:
        await update.effective_message.reply_text(text)
