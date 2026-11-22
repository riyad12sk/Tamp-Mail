from telegram import Update
from telegram.ext import ContextTypes

from database.db import pool, get_user
from keyboards.buttons import back_menu
from utils import esc, fmt_time, safe_edit, DIVIDER


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    uid = update.effective_user.id
    row = await get_user(uid)
    count = await pool().fetchval("SELECT COUNT(*) FROM email_accounts WHERE telegram_id=$1", uid)
    lang = row["language"] if row else "en"

    name = esc(row["first_name"]) if row and row["first_name"] else "-"
    username = f"@{esc(row['username'])}" if row and row["username"] else "-"
    joined = fmt_time(row["created_at"]) if row else "-"

    text = (
        "👤 <b>প্রোফাইল</b>\n" + DIVIDER +
        f"\n🆔 আইডি: <code>{uid}</code>"
        f"\n📛 নাম: {name}"
        f"\n🔗 ইউজারনেম: {username}"
        f"\n✉️ মোট ইমেইল তৈরি: <b>{count}</b>"
        f"\n🌐 ভাষা: {lang.upper()}"
        f"\n📅 যুক্ত হয়েছেন: {joined}"
    )

    if from_callback:
        await safe_edit(update.callback_query, text, reply_markup=back_menu(lang))
    else:
        await update.effective_message.reply_text(text, reply_markup=back_menu(lang), parse_mode="HTML")


async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    uid = update.effective_user.id
    row = await get_user(uid)
    lang = row["language"] if row else "en"
    emails = await pool().fetchval("SELECT COUNT(*) FROM email_accounts WHERE telegram_id=$1", uid)
    active = await pool().fetchval(
        "SELECT COUNT(*) FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE", uid
    )
    messages = await pool().fetchval(
        "SELECT COUNT(*) FROM messages m JOIN email_accounts e ON e.id=m.account_id WHERE e.telegram_id=$1", uid
    )

    text = (
        "📊 <b>পরিসংখ্যান</b>\n" + DIVIDER +
        f"\n✉️ মোট ইমেইল তৈরি: <b>{emails}</b>"
        f"\n🟢 সক্রিয় ইমেইল: <b>{active}</b>"
        f"\n📨 মোট মেসেজ গ্রহণ: <b>{messages}</b>"
    )

    if from_callback:
        await safe_edit(update.callback_query, text, reply_markup=back_menu(lang))
    else:
        await update.effective_message.reply_text(text, reply_markup=back_menu(lang), parse_mode="HTML")
