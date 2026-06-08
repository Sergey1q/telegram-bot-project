"""Авторизация для админ-панели."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from bot.config import config

security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Проверка логина и пароля администратора."""
    is_username_correct = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        config.admin_username.encode("utf-8")
    )
    is_password_correct = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        config.admin_password.encode("utf-8")
    )
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials
