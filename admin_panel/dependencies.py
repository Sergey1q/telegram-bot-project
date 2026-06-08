"""Зависимости для админ-панели."""
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from bot.database import sync_engine
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")

# Отключаем кеширование Jinja2 для избежания ошибок
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.auto_reload = True
templates.env.cache = {}  # Отключаем кеш

def get_db():
    """Получение сессии базы данных."""
    db = Session(sync_engine)
    try:
        yield db
    finally:
        db.close()
