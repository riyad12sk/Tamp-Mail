from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from database.db import upsert_user, get_user, set_language, log_action
from keyboards.buttons import TEXT, main_menu, language_menu
from services.notify import notify_admins
from utils import esc, fmt_time, safe_edit, DIVIDER


def _welcome_text(t, name, uid):
    return t["welcome_title"].format(name=name) + "\n" + DIVIDER + "\n" + t["welcome_body"].format(uid=uid)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    is_new = await upsert_user(u.id, u.username, u.first_name)
    row = await get_user(u.id)
    lang = row["language"] if row else "en"
    t = TEXT.get(lang, TEXT["en"])
    fallback_name = "বন্ধু" if lang == "bn" else "friend"
    name = esc(u.first_name or u.username or fallback_name)

    await update.message.reply_text(
        _welcome_text(t, name, u.id),
        reply_markup=main_menu(lang),
        parse_mode="HTML",
    )
    await log_action(u.id, "start")

    if is_new:
        uname = f"@{u.username}" if u.username else "—"
        await notify_admins(
            context,
            "🆕 <b>নতুন ইউজার বট ব্যবহার শুরু করেছেন</b>\n" + DIVIDER +
            f"\n👤 নাম: {esc(u.first_name or '-')}"
            f"\n🔗 ইউজারনেম: {esc(uname)}"
            f"\n🆔 আইডি: <code>{u.id}</code>"
            f"\n🕒 সময়: {fmt_time(datetime.now(timezone.utc))}"
            f"\n\n📣 আপডেট জানাতে <code>/broadcast</code> ব্যবহার করুন।",
        )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    row = await get_user(uid)
    lang = row["language"] if row else "en"

    if q.data.startswith("lang:"):
        lang = q.data.split(":")[1]
        await set_language(uid, lang)
        t = TEXT.get(lang, TEXT["en"])
        fallback_name = "বন্ধু" if lang == "bn" else "friend"
        name = esc(q.from_user.first_name or q.from_user.username or fallback_name)
        await safe_edit(q, _welcome_text(t, name, uid), reply_markup=main_menu(lang))
        return

    t = TEXT.get(lang, TEXT["en"])
    action = q.data.split(":")[1]

    if action == "home":
        await safe_edit(q, t["choose"], reply_markup=main_menu(lang))
    elif action == "language":
        await safe_edit(q, "🌐 ভাষা নির্বাচন করুন / Choose your language:", reply_markup=language_menu())
    elif action == "profile":
        from handlers.profile import profile
        await profile(update, context, from_callback=True)
    elif action == "stats":
        from handlers.profile import statistics
        await statistics(update, context, from_callback=True)
    elif action == "help":
        await safe_edit(q, t["help_text"], reply_markup=main_menu(lang))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = "en"
    if update.effective_user:
        row = await get_user(update.effective_user.id)
        lang = row["language"] if row else "en"
    t = TEXT.get(lang, TEXT["en"])
    await update.effective_message.reply_text(t["help_text"], reply_markup=main_menu(lang), parse_mode="HTML")
