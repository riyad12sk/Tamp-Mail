# Tamp-Mail — নিরাপত্তা ও Dashboard নোট

এই রিপোজিটরিতে Telegram bot code এবং browser admin dashboard রয়েছে। Dashboard-এর নিরাপত্তা ও কনফিগারেশন আলাদা করে যাচাই করা উচিত।

## গোপন তথ্য

- বাস্তব Bot Token, Admin ID, database URL, password বা signing key GitHub-এ commit করবেন না।
- কোনো token chat, terminal history, log বা Git history-তে প্রকাশিত হলে BotFather থেকে সেটি revoke করে নতুন token ব্যবহার করুন।
- `.env` স্থানীয় মেশিনে রাখুন; `.gitignore` এটি commit হওয়া থেকে আটকায়।
- `.env.example`-এ কেবল placeholder আছে; সেটি কপি করে বাস্তব secret GitHub-এ commit করবেন না।

## Dashboard-এর প্রয়োজনীয় environment variables

- `DATABASE_URL`: PostgreSQL connection string
- `DASHBOARD_USERNAME`: Dashboard login username
- `DASHBOARD_PASSWORD`: দীর্ঘ ও অনন্য password
- `SECRET_KEY`: কমপক্ষে ৩২ অক্ষরের random signing secret
- `DASHBOARD_COOKIE_SECURE`: HTTPS deployment-এ `true`; local HTTP test-এ `false`

Dashboard startup-এর সময় প্রয়োজনীয় variable অনুপস্থিত থাকলে বা `SECRET_KEY` ছোট হলে startup বন্ধ হবে। Session cookie HTTP-only, SameSite=Lax এবং configurable Secure flag ব্যবহার করে। Login ও logout form-এ CSRF token আছে। Response-এ basic security headers এবং no-store cache policy দেওয়া হয়।

Login attempt limiter process-local এবং সীমিত আকারের; service restart হলে এর state reset হয়। এটি shared/distributed rate limiter নয় এবং upstream protection-এর বিকল্প নয়।

## Database সামঞ্জস্য

Dashboard যে `users`, `email_accounts`, `messages` এবং `activity_logs` table query করে, সেগুলোর সংজ্ঞা `database/db.py`-এর schema-তে রয়েছে। Dashboard চালানোর আগে নিশ্চিত করুন PostgreSQL-এ schema তৈরি হয়েছে এবং database user প্রয়োজনীয় read permission পেয়েছে।

## Health check

Dashboard-এর `/health` endpoint database connection-এ `SELECT 1` চালায়। সফল হলে `{"status":"ok"}` ফেরত দেয়; database unavailable হলে HTTP 503 ফেরত দেয়।

## Render সম্পর্কে সতর্কতা

বর্তমান `render.yaml`-এ একটি Telegram worker এবং একটি web dashboard service দুটোই সংজ্ঞায়িত আছে। Blueprint deploy করলে worker-টিও চালু হতে পারে। তাই শুধু Dashboard পরীক্ষা করতে চাইলে এই Blueprint deploy করবেন না; আগে worker-সহ সম্পূর্ণ architecture ও অনুমোদিত email-testing scope আলাদাভাবে পর্যালোচনা করতে হবে।

Render-এর service plan এবং PostgreSQL plan-এ খরচ হতে পারে। Deploy করার আগে Render dashboard-এ বর্তমান মূল্য ও resource availability যাচাই করুন।

## স্থানীয় Dashboard পরীক্ষা

Python environment-এ `requirements.txt` install করে প্রয়োজনীয় Dashboard environment variables সেট করুন। Local HTTP পরীক্ষার সময়:

```bash
DASHBOARD_COOKIE_SECURE=false
```

তারপর Dashboard চালু করুন:

```bash
uvicorn dashboard.app:app --host 127.0.0.1 --port 8000
```

Browser-এ `http://127.0.0.1:8000/health` খুলে health status দেখুন। Public deployment-এ HTTPS ব্যবহার করুন এবং `DASHBOARD_COOKIE_SECURE=true` রাখুন।
