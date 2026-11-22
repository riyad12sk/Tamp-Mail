import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import pool, log_action
from services.tempmail import client, TempMailError

async def _account(uid, account_id=None):
    if account_id:
        return await pool().fetchrow("SELECT * FROM email_accounts WHERE id=$1 AND telegram_id=$2 AND is_active=TRUE", account_id, uid)
    return await pool().fetchrow("SELECT * FROM email_accounts WHERE telegram_id=$1 AND is_active=TRUE ORDER BY id DESC LIMIT 1", uid)

async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = q.data.split(":")
    if parts[0] == "refresh":
        account_id = int(parts[1])
    else:
        account_id = int(parts[2]) if len(parts) > 2 and parts[1] == "account" else None
    account = await _account(q.from_user.id, account_id)
    if not account:
        await q.message.reply_text("Generate an email address first.")
        return
    try:
        remote = await client.messages(account["email"], account["api_token"])
        for item in remote[:10]:
            ext_id = str(item.get("id") or item.get("message_id") or item.get("mail_id") or "")
            if not ext_id:
                ext_id = hashlib.sha256(repr((item.get("from"), item.get("subject"), item.get("date"), item.get("body_text") or item.get("body"))).encode()).hexdigest()
            await pool().execute("""
              INSERT INTO messages(account_id,external_id,sender,subject,body)
              VALUES($1,$2,$3,$4,$5) ON CONFLICT(account_id,external_id) DO NOTHING
            """, account["id"], ext_id, str(item.get("from","Unknown"))[:500],
                 str(item.get("subject","No subject"))[:500],
                 str(item.get("body_text") or item.get("body") or item.get("text") or "")[:12000])
        rows = await pool().fetch("SELECT id,sender,subject,received_at FROM messages WHERE account_id=$1 ORDER BY id DESC LIMIT 10", account["id"])
        if not rows:
            await q.message.reply_text(f"📭 Inbox empty for {account['email']}.")
            return
        buttons = [[InlineKeyboardButton(f"✉️ {str(r['subject'])[:45]}", callback_data=f"message:{r['id']}")] for r in rows]
        buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{account['id']}")])
        await q.message.reply_text(f"📥 Inbox: {account['email']}", reply_markup=InlineKeyboardMarkup(buttons))
    except TempMailError as exc:
        await q.message.reply_text(f"Inbox provider error: {exc}")

async def view_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        mid = int(q.data.split(":")[1])
    except ValueError:
        await q.message.reply_text("Invalid message.")
        return
    row = await pool().fetchrow("""
      SELECT m.*, e.email FROM messages m JOIN email_accounts e ON e.id=m.account_id
      WHERE m.id=$1 AND e.telegram_id=$2
    """, mid, q.from_user.id)
    if not row:
        await q.message.reply_text("Message not found.")
        return
    body = row["body"] or "(No text body available)"
    body = body[:3500]
    text = f"From: {row['sender'] or 'Unknown'}\\nSubject: {row['subject'] or 'No subject'}\\nTo: {row['email']}\\n\\n{body}"
    await q.message.reply_text(text)
