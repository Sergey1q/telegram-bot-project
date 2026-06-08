"""FastAPI админ-панель."""
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import RedirectResponse
import secrets

from bot.config import config
from admin_panel.dependencies import templates, get_db

app = FastAPI(
    title="Админ-панель Telegram-бота",
    description="Управление ботом, пользователями и заявками",
    version="2.0.0",
)

# Статические файлы
app.mount("/static", StaticFiles(directory="admin_panel/static"), name="static")

# Авторизация
security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Проверка логина/пароля."""
    is_correct = (
        secrets.compare_digest(credentials.username.encode("utf-8"), config.admin_username.encode("utf-8")) and
        secrets.compare_digest(credentials.password.encode("utf-8"), config.admin_password.encode("utf-8"))
    )
    if not is_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

# Импортируем роутеры ПОСЛЕ создания app и verify_credentials
from admin_panel.routers import dashboard, appointments, users, services, broadcast

# Подключаем роутеры
app.include_router(dashboard.router, dependencies=[Depends(verify_credentials)])
app.include_router(appointments.router, dependencies=[Depends(verify_credentials)])
app.include_router(users.router, dependencies=[Depends(verify_credentials)])
app.include_router(services.router, dependencies=[Depends(verify_credentials)])
app.include_router(broadcast.router, dependencies=[Depends(verify_credentials)])

@app.get("/login")
async def login_page(request: Request):
    """Страница входа."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/")
async def root():
    """Редирект на дашборд."""
    return RedirectResponse(url="/dashboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("admin_panel.main:app", host="0.0.0.0", port=8000, reload=True)
