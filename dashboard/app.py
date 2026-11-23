import hmac
import secrets
import time
from collections import defaultdict, deque

import asyncpg
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import settings

app = FastAPI(title="Temp Mail Admin")
templates = Jinja2Templates(directory="dashboard/templates")
pool = None
_login_attempts = defaultdict(deque)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300


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
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="tempmail_admin_session",
        max_age=60 * 60 * 8,
        same_site="lax",
        https_only=settings.dashboard_cookie_secure,
    )
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=3)


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


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


def login_limited(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = _login_attempts[ip]
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= MAX_ATTEMPTS:
        return True
    attempts.append(now)
    return False


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    users = await pool.fetchval("SELECT COUNT(*) FROM users")
    emails = await pool.fetchval("SELECT COUNT(*) FROM email_accounts")
    messages = await pool.fetchval("SELECT COUNT(*) FROM messages")
    recent = await pool.fetch("SELECT telegram_id,action,details,created_at FROM activity_logs ORDER BY id DESC LIMIT 20")
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
    return {"status": "ok"}
