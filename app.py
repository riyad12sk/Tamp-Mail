import asyncpg
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from config import settings

app = FastAPI(title="Temp Mail Admin")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key or "SET_A_LONG_SECRET_KEY_IN_RENDER")
templates = Jinja2Templates(directory="dashboard/templates")
pool = None

@app.on_event("startup")
async def startup():
    global pool
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is missing")
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=3)

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()

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
    return templates.TemplateResponse("index.html", {"request": request, "users": users, "emails": emails, "messages": messages, "recent": recent})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    import hmac
    if (hmac.compare_digest(username, settings.admin_username)
        and settings.admin_password
        and hmac.compare_digest(password, settings.admin_password)):
        request.session["admin"] = True
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"}, status_code=401)

@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

@app.get("/health")
async def health():
    return {"status": "ok"}
