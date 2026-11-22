import asyncio
import hashlib
import logging

from database.db import pool
from services.tempmail import client, TempMailError
from utils import esc, DIVIDER

log = logging.getLogger(__name__)


async def inbox_monitor(app):
    # Poll active mailboxes at the configured interval. For large deployments,
    # replace per-mailbox polling with a provider webhook or a queued scheduler.
    while True:
        try:
            accounts = await pool().fetch(
                """
                SELECT id,telegram_id,email,api_token FROM email_accounts
                WHERE is_active=TRUE ORDER BY id DESC LIMIT 100
                """
            )
            for account in accounts:
                try:
                    items = await client.messages(account["email"], account["api_token"])
                    for item in items[:10]:
                        ext_id = str(item.get("id") or item.get("message_id") or item.get("mail_id") or "")
                        if not ext_id:
                            ext_id = hashlib.sha256(
                                repr((item.get("from"), item.get("subject"), item.get("date"),
                                      item.get("body_text") or item.get("body"))).encode()
                            ).hexdigest()
                        status = await pool().execute(
                            """
                            INSERT INTO messages(account_id,external_id,sender,subject,body)
                            VALUES($1,$2,$3,$4,$5) ON CONFLICT(account_id,external_id) DO NOTHING
                            """,
                            account["id"], ext_id,
                            str(item.get("from", "Unknown"))[:500],
                            str(item.get("subject", "No subject"))[:500],
                            str(item.get("body_text") or item.get("body") or item.get("text") or "")[:12000],
                        )
                        if status.endswith(" 1"):
                            try:
                                await app.bot.send_message(
                                    chat_id=account["telegram_id"],
                                    text=(
                                        "📩 <b>নতুন মেইল এসেছে!</b>\n" + DIVIDER +
                                        f"\n👤 From: {esc(item.get('from', 'Unknown'))[:300]}"
                                        f"\n📌 Subject: {esc(item.get('subject', 'No subject'))[:300]}"
                                        f"\n📧 To: <code>{esc(account['email'])}</code>\n\n"
                                        "📥 ইনবক্স থেকে পুরো মেসেজটি পড়ুন।"
                                    ),
                                    parse_mode="HTML",
                                )
                            except Exception:
                                # User may have blocked the bot - don't let that
                                # stop the rest of this batch from processing.
                                log.warning("Could not notify user %s of new mail.", account["telegram_id"])
                except TempMailError as exc:
                    log.warning("Inbox poll failed for account %s: %s", account["id"], exc)
                await asyncio.sleep(0.2)
        except Exception:
            log.exception("Inbox monitor iteration failed")
        await asyncio.sleep(10)
