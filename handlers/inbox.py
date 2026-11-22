import hashlib

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.db import pool, get_user
from services.tempmail import client, TempMailError
from keyboards.buttons import TEXT, back_menu
from utils import esc, fmt_time, safe_edit, DIVIDER


async def _lang(uid):
    row = await get_user(uid)
    return row["language"] if row else "en"


async def _account(uid, account_id=None):
    if account_id:
        return await pool().fetchrow(
            "SELECT * FROM email_accounts WHERE id=$1 AND telegram_id=$2 AND is_active=TRUE", account_id, uid
        )
    return await pool().fetchrow(
        "SELECT * FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE ORDER BY id DESC LIMIT 1", uid
    )


async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    is_refresh = q.data.startswith("refresh:")
    await q.answer("🔄 রিফ্রেশ হচ্ছে..." if is_refresh else None)
    lang = await _lang(q.from_user.id)
    t = TEXT.get(lang, TEXT["en"])

    parts = q.data.split(":")
    if parts[0] == "refresh":
        account_id = int(parts[1])
    else:
        account_id = int(parts[2]) if len(parts) > 2 and parts[1] == "account" else None

    account = await _account(q.from_user.id, account_id)
    if not account:
        empty = "📭 আগে একটি ইমেইল তৈরি করুন।" if lang == "bn" else "📭 Generate an email address first."
        await safe_edit(q, empty, reply_markup=back_menu(lang))
        return

    try:
        remote = await client.messages(account["email"], account["api_token"])
        for item in remote[:10]:
            ext_id = str(item.get("id") or item.get("message_id") or item.get("mail_id") or "")
            if not ext_id:
                ext_id = hashlib.sha256(
                    repr((item.get("from"), item.get("subject"), item.get("date"),
                          item.get("body_text") or item.get("body"))).encode()
                ).hexdigest()
            await pool().execute(
                """
                INSERT INTO messages(account_id,external_id,sender,subject,body)
                VALUES($1,$2,$3,$4,$5) ON CONFLICT(account_id,external_id) DO NOTHING
                """,
                account["id"], ext_id,
                str(item.get("from", "Unknown"))[:500],
                str(item.get("subject", "No subject"))[:500],
                str(item.get("body_text") or item.get("body") or item.get("text") or "")[:12000],
            )

        rows = await pool().fetch(
            "SELECT id,sender,subject,received_at FROM messages WHERE account_id=$1 ORDER BY id DESC LIMIT 10",
            account["id"],
        )
        header = f"📥 <b>Inbox</b>\n{DIVIDER}\n📧 <code>{esc(account['email'])}</code>"
        refresh_btn = [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{account['id']}")]
        back_btn = [InlineKeyboardButton(t["back"], callback_data="menu:home")]

        if not rows:
            empty = "📭 <b>ইনবক্স খালি</b>" if lang == "bn" else "📭 <b>Inbox is empty</b>"
            await safe_edit(
                q,
                f"{empty}\n{DIVIDER}\n📧 <code>{esc(account['email'])}</code>",
                reply_markup=InlineKeyboardMarkup([refresh_btn, back_btn]),
            )
            return

        buttons = [
            [InlineKeyboardButton(f"✉️ {str(r['subject'] or 'No subject')[:45]}", callback_data=f"message:{r['id']}")]
            for r in rows
        ]
        buttons.append(refresh_btn)
        buttons.append(back_btn)
        await safe_edit(q, header, reply_markup=InlineKeyboardMarkup(buttons))
    except TempMailError as exc:
        err = f"⚠️ প্রোভাইডার এরর: {esc(exc)}" if lang == "bn" else f"⚠️ Inbox provider error: {esc(exc)}"
        await safe_edit(q, err, reply_markup=back_menu(lang))


async def view_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = await _lang(q.from_user.id)

    try:
        mid = int(q.data.split(":")[1])
    except ValueError:
        await safe_edit(q, "⚠️ ভুল মেসেজ আইডি।" if lang == "bn" else "⚠️ Invalid message.", reply_markup=back_menu(lang))
        return

    row = await pool().fetchrow(
        """
        SELECT m.*, e.email FROM messages m JOIN email_accounts e ON e.id=m.account_id
        WHERE m.id=$1 AND e.telegram_id=$2
        """,
        mid, q.from_user.id,
    )
    if not row:
        await safe_edit(q, "⚠️ মেসেজটি পাওয়া যায়নি।" if lang == "bn" else "⚠️ Message not found.", reply_markup=back_menu(lang))
        return

    no_body = "(কোনো টেক্সট পাওয়া যায়নি)" if lang == "bn" else "(No text body available)"
    body = esc((row["body"] or "")[:3500]) or no_body
    text = (
        "✉️ <b>Message</b>\n" + DIVIDER +
        f"\n👤 From: {esc(row['sender'] or 'Unknown')}"
        f"\n📌 Subject: {esc(row['subject'] or 'No subject')}"
        f"\n📧 To: <code>{esc(row['email'])}</code>"
        f"\n🕒 {fmt_time(row['received_at'])}\n" + DIVIDER +
        f"\n\n{body}"
    )
    await safe_edit(q, text, reply_markup=back_menu(lang))
