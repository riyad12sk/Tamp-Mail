from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import settings
from database.db import pool, log_action
from services.tempmail import client, TempMailError
from keyboards.buttons import main_menu

async def generate_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Generating..." if q else None)
    uid = q.from_user.id
    count = await pool().fetchval("SELECT COUNT(*) FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE", uid)
    if count >= settings.max_emails_per_user:
        await q.message.reply_text(f"Limit reached. Maximum active emails: {settings.max_emails_per_user}.")
        return
    try:
        email, token = await client.create()
        await pool().execute(
          "INSERT INTO email_accounts(telegram_id,email,api_token) VALUES($1,$2,$3) ON CONFLICT DO NOTHING",
          uid, email, token
        )
        await log_action(uid, "email_created", email)
        await q.message.reply_text(f"✉️ *Your temporary email*\\n`{email}`\\n\\nUse My inbox to check incoming messages.",
                                   parse_mode="Markdown", reply_markup=main_menu())
    except TempMailError as exc:
        await q.message.reply_text(f"Could not create email: {exc}")

async def my_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    rows = await pool().fetch("SELECT id,email,created_at FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE ORDER BY id DESC", uid)
    if not rows:
        await q.message.reply_text("You have no active email addresses yet.")
        return
    buttons = [[InlineKeyboardButton(f"📧 {r['email']}", callback_data=f"inbox:account:{r['id']}")] for r in rows]
    await q.message.reply_text("Your active email addresses:", reply_markup=InlineKeyboardMarkup(buttons))

async def choose_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rows = await pool().fetch("SELECT id,email FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE", q.from_user.id)
    if not rows:
        await q.message.reply_text("No active email to archive.")
        return
    buttons = [[InlineKeyboardButton(f"🗑 {r['email']}", callback_data=f"email:delete:{r['id']}")] for r in rows]
    await q.message.reply_text("Choose an address to deactivate:", reply_markup=InlineKeyboardMarkup(buttons))

async def delete_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        account_id = int(q.data.split(":")[2])
    except (ValueError, IndexError):
        await q.message.reply_text("Invalid email selection.")
        return
    result = await pool().execute("UPDATE email_accounts SET is_active=FALSE WHERE id=$1 AND telegram_id=$2 AND is_active=TRUE", account_id, q.from_user.id)
    await log_action(q.from_user.id, "email_deactivated", str(account_id))
    await q.message.reply_text("Email deactivated in this bot. The provider may retain the mailbox; remote deletion is not guaranteed.")
