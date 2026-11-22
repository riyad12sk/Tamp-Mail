import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import settings
from database.db import pool, all_user_ids, set_blocked, user_count
from utils import esc, fmt_time, safe_edit, DIVIDER


def is_admin(uid) -> bool:
    return uid in settings.admin_ids


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("🚫 Access denied.")
        return

    users = await user_count()
    emails = await pool().fetchval("SELECT COUNT(*) FROM email_accounts")
    active = await pool().fetchval("SELECT COUNT(*) FROM email_accounts WHERE is_active=TRUE")
    messages = await pool().fetchval("SELECT COUNT(*) FROM messages")

    text = (
        "🛡 <b>Admin Dashboard</b>\n" + DIVIDER +
        f"\n👥 Users: <b>{users}</b>"
        f"\n✉️ Total emails: <b>{emails}</b> (active: {active})"
        f"\n📨 Messages: <b>{messages}</b>\n" + DIVIDER +
        "\n\n<b>Admin commands</b>"
        "\n• <code>/broadcast &lt;message&gt;</code> — সব ইউজারকে পাঠান"
        "\n• <code>/block &lt;telegram_id&gt;</code>"
        "\n• <code>/unblock &lt;telegram_id&gt;</code>"
    )
    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📜 Recent activity", callback_data="admin:activity")]]
        ),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        await q.message.reply_text("🚫 Access denied.")
        return

    if q.data == "admin:activity":
        rows = await pool().fetch(
            "SELECT telegram_id,action,details,created_at FROM activity_logs ORDER BY id DESC LIMIT 10"
        )
        if rows:
            lines = [
                f"• <code>{r['telegram_id']}</code> — {esc(r['action'])} "
                f"{esc(r['details'] or '')} ({fmt_time(r['created_at'])})"
                for r in rows
            ]
            body = "\n".join(lines)
        else:
            body = "কোনো কার্যকলাপ নেই।"
        text = "📜 <b>Recent activity</b>\n" + DIVIDER + "\n" + body
        await safe_edit(q, text[:4000])


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("🚫 Access denied.")
        return

    raw = update.message.text or ""
    _, _, message = raw.partition(" ")
    message = message.strip()
    if not message:
        await update.effective_message.reply_text(
            "✏️ ব্যবহার:\n<code>/broadcast আপনার ঘোষণা এখানে লিখুন</code>\n\n"
            "HTML ফরম্যাট (&lt;b&gt;, &lt;i&gt;) সাপোর্ট করে।",
            parse_mode="HTML",
        )
        return

    ids = await all_user_ids()
    status = await update.effective_message.reply_text(f"📣 {len(ids)} জন ইউজারকে পাঠানো হচ্ছে...")
    sent, failed = 0, 0
    for uid in ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text="📢 <b>নতুন ঘোষণা</b>\n" + DIVIDER + f"\n{message}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ Broadcast সম্পন্ন।\nসফল: {sent}\nব্যর্থ (ব্লকড/ডিঅ্যাক্টিভেটেড): {failed}")


async def block_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("🚫 Access denied.")
        return
    args = context.args
    if not args or not args[0].isdigit():
        await update.effective_message.reply_text("ব্যবহার: /block <telegram_id>")
        return
    await set_blocked(int(args[0]), True)
    await update.effective_message.reply_text(f"🚫 ইউজার <code>{args[0]}</code> ব্লক করা হয়েছে।", parse_mode="HTML")


async def unblock_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("🚫 Access denied.")
        return
    args = context.args
    if not args or not args[0].isdigit():
        await update.effective_message.reply_text("ব্যবহার: /unblock <telegram_id>")
        return
    await set_blocked(int(args[0]), False)
    await update.effective_message.reply_text(f"✅ ইউজার <code>{args[0]}</code> আনব্লক করা হয়েছে।", parse_mode="HTML")
