from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import settings
from database.db import pool, get_user, log_action
from services.tempmail import client, TempMailError
from keyboards.buttons import TEXT, main_menu, back_menu
from utils import esc, safe_edit, DIVIDER


async def _lang(uid):
    row = await get_user(uid)
    return row["language"] if row else "en"


async def generate_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    lang = await _lang(uid)
    await q.answer("⏳ তৈরি হচ্ছে..." if lang == "bn" else "⏳ Generating...")

    count = await pool().fetchval(
        "SELECT COUNT(*) FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE", uid
    )
    if count >= settings.max_emails_per_user:
        msg = (
            f"⚠️ সর্বোচ্চ সীমায় পৌঁছে গেছেন। একসাথে সর্বোচ্চ {settings.max_emails_per_user}টি সক্রিয় ইমেইল রাখা যায়।"
            if lang == "bn"
            else f"⚠️ Limit reached. Maximum active emails allowed: {settings.max_emails_per_user}."
        )
        await q.message.reply_text(msg, reply_markup=back_menu(lang))
        return

    await context.bot.send_chat_action(chat_id=q.message.chat_id, action="typing")
    try:
        email, token = await client.create()
        await pool().execute(
            "INSERT INTO email_accounts(telegram_id,email,api_token) VALUES($1,$2,$3) ON CONFLICT DO NOTHING",
            uid, email, token,
        )
        await log_action(uid, "email_created", email)
        if lang == "bn":
            text = (
                "✅ <b>নতুন অস্থায়ী ইমেইল তৈরি হয়েছে</b>\n" + DIVIDER +
                f"\n📧 <code>{esc(email)}</code>\n\n"
                "ঠিকানাটিতে ট্যাপ করলেই কপি হয়ে যাবে।\n"
                "📥 <b>ইনবক্স</b> থেকে আসা মেসেজ দেখুন।"
            )
        else:
            text = (
                "✅ <b>New temporary email created</b>\n" + DIVIDER +
                f"\n📧 <code>{esc(email)}</code>\n\n"
                "Tap the address to copy it instantly.\n"
                "Check <b>My inbox</b> to read incoming mail."
            )
        await q.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu(lang))
    except TempMailError as exc:
        msg = f"❌ ইমেইল তৈরি করা যায়নি: {esc(exc)}" if lang == "bn" else f"❌ Could not create email: {esc(exc)}"
        await q.message.reply_text(msg, reply_markup=back_menu(lang))


async def my_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = await _lang(uid)
    t = TEXT.get(lang, TEXT["en"])
    rows = await pool().fetch(
        "SELECT id,email,created_at FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE ORDER BY id DESC",
        uid,
    )
    if not rows:
        empty = "📭 আপনার কোনো সক্রিয় ইমেইল নেই।" if lang == "bn" else "📭 You have no active email addresses yet."
        await safe_edit(q, empty, reply_markup=back_menu(lang))
        return
    buttons = [[InlineKeyboardButton(f"📧 {r['email']}", callback_data=f"inbox:account:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(t["back"], callback_data="menu:home")])
    title = "📬 <b>আপনার সক্রিয় ইমেইল ঠিকানাসমূহ</b>" if lang == "bn" else "📬 <b>Your active email addresses</b>"
    await safe_edit(q, title, reply_markup=InlineKeyboardMarkup(buttons))


async def choose_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = await _lang(q.from_user.id)
    t = TEXT.get(lang, TEXT["en"])
    rows = await pool().fetch(
        "SELECT id,email FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE", q.from_user.id
    )
    if not rows:
        empty = "📭 ডিলিট করার মতো কোনো সক্রিয় ইমেইল নেই।" if lang == "bn" else "📭 No active email to delete."
        await safe_edit(q, empty, reply_markup=back_menu(lang))
        return
    buttons = [[InlineKeyboardButton(f"🗑 {r['email']}", callback_data=f"email:delete:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(t["back"], callback_data="menu:home")])
    title = "🗑 <b>কোন ঠিকানাটি নিষ্ক্রিয় করতে চান?</b>" if lang == "bn" else "🗑 <b>Choose an address to deactivate</b>"
    await safe_edit(q, title, reply_markup=InlineKeyboardMarkup(buttons))


async def delete_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = await _lang(q.from_user.id)
    try:
        account_id = int(q.data.split(":")[2])
    except (ValueError, IndexError):
        await safe_edit(q, "⚠️ ভুল সিলেকশন।" if lang == "bn" else "⚠️ Invalid selection.", reply_markup=back_menu(lang))
        return
    await pool().execute(
        "UPDATE email_accounts SET is_active=FALSE WHERE id=$1 AND telegram_id=$2 AND is_active=TRUE",
        account_id, q.from_user.id,
    )
    await log_action(q.from_user.id, "email_deactivated", str(account_id))
    if lang == "bn":
        text = "✅ ইমেইল এই বটে নিষ্ক্রিয় করা হয়েছে।\n⚠️ প্রোভাইডার সাইডে মেইলবক্সটি মুছে যাওয়ার নিশ্চয়তা নেই।"
    else:
        text = "✅ Email deactivated in this bot.\n⚠️ The provider may still retain the mailbox."
    await safe_edit(q, text, reply_markup=back_menu(lang))
