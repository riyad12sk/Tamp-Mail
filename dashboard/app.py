import hmac
import secrets
import time

import asyncpg
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from database.db import init_db, close_db as close_bot_db

app = FastAPI(title="Temp Mail Admin")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key or "startup-validation-will-reject-this",
    session_cookie="tempmail_admin_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=True,
)
templates = Jinja2Templates(directory="dashboard/templates")
pool = None

# Per-process login throttling. For multi-instance deployments, move this
# counter to Redis or another shared rate-limit store.
_login_attempts = {}
_LOGIN_WINDOW = 300
_LOGIN_LIMIT = 5


def _csrf_token(request: Request):
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def _check_csrf(request: Request, supplied: str):
    expected = request.session.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def _login_locked(request: Request):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < _LOGIN_WINDOW]
    _login_attempts[key] = attempts
    return len(attempts) >= _LOGIN_LIMIT


def _record_failed_login(request: Request):
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < _LOGIN_WINDOW]
    attempts.append(now)
    _login_attempts[key] = attempts


@app.on_event("startup")
async def startup():
    global pool
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is missing")
    if len(settings.secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters")
    if not settings.admin_username or not settings.admin_password:
        raise RuntimeError("DASHBOARD_USERNAME and DASHBOARD_PASSWORD must be configured")
    await init_db()
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=3)


@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()
        pool = None
    await close_bot_db()


def logged_in(request: Request):
    return request.session.get("admin") is True


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    users = await pool.fetchval("SELECT COUNT(*) FROM users")
    emails = await pool.fetchval("SELECT COUNT(*) FROM email_accounts")
    messages = await pool.fetchval("SELECT COUNT(*) FROM messages")
    recent = await pool.fetch("SELECT telegram_id,action,details,created_at FROM activity_logs ORDER BY id DESC LIMIT 20")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "users": users, "emails": emails, "messages": messages,
         "recent": recent, "csrf_token": _csrf_token(request)},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "", "csrf_token": _csrf_token(request)}
    )


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    _check_csrf(request, csrf_token)
    if _login_locked(request):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Too many attempts. Try again in five minutes.",
             "csrf_token": _csrf_token(request)},
            status_code=429,
        )
    valid = (
        hmac.compare_digest(username, settings.admin_username)
        and hmac.compare_digest(password, settings.admin_password)
    )
    if valid:
        _login_attempts.pop(request.client.host if request.client else "unknown", None)
        request.session.clear()
        request.session["admin"] = True
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        return RedirectResponse("/", status_code=303)
    _record_failed_login(request)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid credentials", "csrf_token": _csrf_token(request)},
        status_code=401,
    )


@app.post("/logout")
async def logout(request: Request, csrf_token: str = Form(...)):
    _check_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/health")
async def health():
    if pool is None:
        raise HTTPException(status_code=503, detail="Database is not ready")
    try:
        await pool.fetchval("SELECT 1")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}
