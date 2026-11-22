# TempMailBot — Advanced Edition

GitHub + Render deployment-এর জন্য প্রস্তুত Python Telegram bot ও browser admin dashboard।

## গুরুত্বপূর্ণ নিরাপত্তা
- আগের চ্যাটে প্রকাশিত Telegram Bot Token-টি BotFather থেকে revoke করে নতুন token নিন।
- `.env` কখনো GitHub-এ upload করবেন না।
- Bot token, PostgreSQL URL, dashboard password এবং SECRET_KEY শুধু Render-এর Environment Variables-এ রাখুন।
- অজানা/অননুমোদিত সাইটে এই বটের inbox ব্যবহার করবেন না। Temp email-এ গুরুত্বপূর্ণ বা ব্যক্তিগত তথ্য গ্রহণ করবেন না।

## GitHub-এ Upload
এই ZIP extract করে এর ভেতরের সব ফাইল `Tamp-Mail` repository-র root-এ upload করুন। `.env` upload করবেন না।

## Render Deployment
`render.yaml` Blueprint ব্যবহার করে deploy করুন। Render Dashboard-এ New > Blueprint এবং GitHub repository নির্বাচন করুন।
Blueprint-এর Database plan ও service plan আপনার Render account-এর বর্তমান pricing/availability অনুযায়ী নির্বাচন করুন। `starter` worker/web paid plan; free plan-এ always-on background worker পাওয়া যায় না।

Environment Variables:
- `BOT_TOKEN`: BotFather থেকে নতুন token
- `ADMIN_IDS`: আপনার Telegram numeric user ID; একাধিক হলে comma-separated
- `DASHBOARD_USERNAME`: dashboard login username
- `DASHBOARD_PASSWORD`: শক্তিশালী, অনন্য password
- `SECRET_KEY`: দীর্ঘ random secret
- `DATABASE_URL`: Render PostgreSQL connection string (Blueprint auto-link করে)

## Deploy-এর পরে
1. Worker logs-এ `Starting Telegram bot polling` দেখুন।
2. Bot-এ `/start` পাঠান।
3. `/admin` দিয়ে Telegram admin summary দেখুন।
4. Web service URL খুলে dashboard login করুন।
5. `/health` endpoint-এ `{"status":"ok"}` পাওয়া উচিত।

## Temp Mail provider caveat
এই project-এ আপনার দেওয়া `api.internal.temp-mail.io` API pattern adapter হিসেবে রাখা হয়েছে। এটি internal/unofficial endpoint হতে পারে; availability, authentication, message schema বা service terms বদলাতে পারে। Production launch-এর আগে provider-এর অনুমোদিত ও প্রকাশিত API documentation/terms যাচাই করুন। API unavailable হলে `TEMPMAIL_API_BASE`-এ documented provider endpoint বসিয়ে `services/tempmail.py`-এর request/response mapping সেই অনুযায়ী পরিবর্তন করতে হবে।

## Feature notes
- 10-second polling is a requested interval; the monitor polls active inboxes sequentially and is suitable only for small test deployments. Many mailboxes can create high API traffic and provider rate-limit issues.
- Delete deactivates the address inside this bot. It does not claim to delete the remote provider mailbox because the supplied API flow does not document a remote-delete endpoint.
- Admin web dashboard is password-protected and uses session cookies. Use HTTPS (Render provides it), a strong password and a unique SECRET_KEY.
- The database schema is initialized automatically at service startup.
- Email content is untrusted input. Do not open links or attachments from unknown senders.

## Local development (optional)
Install requirements, set environment variables, then run `python main.py`. Dashboard: `uvicorn dashboard.app:app --host 0.0.0.0 --port 8000`.
