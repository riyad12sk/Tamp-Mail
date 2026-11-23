import hmac
import logging
import secrets
import time
from collections import OrderedDict, deque

import asyncpg
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Tamp-Mail Admin")
templates = Jinja2Templates(directory="dashboard/templates")
pool = None

# This is a small, process-local guard for a single-admin dashboard.
# It is intentionally bounded so arbitrary client IPs cannot grow memory forever.
_login_attempts = OrderedDict()
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300
MAX_TRACKED_IPS = 1024


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="tempmail_admin_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=settings.dashboard_cookie_secure,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.on_event("startup")
async def startup():
    global pool
    missing = [
        name for name, value in (
            ("DATABASE_URL", settings.database_url),
            ("SECRET_KEY", settings.secret_key),
            ("DASHBOARD_USERNAME", settings.admin_username),
            ("DASHBOARD_PASSWORD", settings.admin_password),
        ) if not value
    ]
    if missing:
        raise RuntimeError("Missing required dashboard environment variables: " + ", ".join(missing))
    if len(settings.secret_key) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters.")
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=3)


@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool is not None:
        await pool.close()
        pool = None


def logged_in(request: Request):
    return request.session.get("admin") is True


def csrf_token(request: Request):
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def valid_csrf(request: Request, token: str):
    expected = request.session.get("csrf_token", "")
    return bool(expected and token and hmac.compare_digest(expected, token))


def _client_key(request: Request):
    # Do not trust X-Forwarded-For unless a trusted proxy is explicitly configured.
    return request.client.host if request.client else "unknown"


def login_limited(request: Request):
    key = _client_key(request)
    now = time.monotonic()
    attempts = _login_attempts.get(key)
    if attempts is None:
        attempts = deque()
        _login_attempts[key] = attempts
    _login_attempts.move_to_end(key)

    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()

    if len(attempts) >= MAX_ATTEMPTS:
        return True

    attempts.append(now)
    while len(_login_attempts) > MAX_TRACKED_IPS:
        _login_attempts.popitem(last=False)
    return False


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    if pool is None:
        return HTMLResponse("Dashboard database is unavailable.", status_code=503)
    try:
        users = await pool.fetchval("SELECT COUNT(*) FROM users")
        emails = await pool.fetchval("SELECT COUNT(*) FROM email_accounts")
        messages = await pool.fetchval("SELECT COUNT(*) FROM messages")
        recent = await pool.fetch(
            "SELECT telegram_id,action,details,created_at FROM activity_logs ORDER BY id DESC LIMIT 20"
        )
    except asyncpg.PostgresError:
        logger.exception("Dashboard database query failed")
        return HTMLResponse("Dashboard data is temporarily unavailable.", status_code=503)

    return templates.TemplateResponse("index.html", {
        "request": request, "users": users, "emails": emails,
        "messages": messages, "recent": recent, "csrf_token": csrf_token(request)
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request, "error": "", "csrf_token": csrf_token(request)
    })


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...),
                csrf: str = Form(...)):
    if not valid_csrf(request, csrf):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Invalid session. Refresh and try again.",
            "csrf_token": csrf_token(request)
        }, status_code=403)

    if login_limited(request):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Too many attempts. Wait five minutes.",
            "csrf_token": csrf_token(request)
        }, status_code=429)

    if (hmac.compare_digest(username, settings.admin_username)
            and hmac.compare_digest(password, settings.admin_password)):
        _login_attempts.pop(_client_key(request), None)
        request.session.clear()
        request.session["admin"] = True
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse("login.html", {
        "request": request, "error": "Invalid credentials.",
        "csrf_token": csrf_token(request)
    }, status_code=401)


@app.post("/logout")
async def logout(request: Request, csrf: str = Form(...)):
    if not logged_in(request) or not valid_csrf(request, csrf):
        return RedirectResponse("/login", status_code=303)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/health")
async def health():
    if pool is None:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    try:
        await pool.fetchval("SELECT 1")
    except Exception:
        logger.exception("Dashboard health check failed")
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok"}
