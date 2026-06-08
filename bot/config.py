"""Конфигурация бота."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    """Настройки бота."""
    token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: list = None
    
    def __post_init__(self):
        if self.admin_ids is None:
            admin_str = os.getenv("ADMIN_IDS", "")
            self.admin_ids = [int(x.strip()) for x in admin_str.split(",") if x.strip()]
    
    # База данных
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///bot_assistant.db")
    
    # Платежи Telegram Stars
    stars_enabled: bool = os.getenv("STARS_ENABLED", "true").lower() == "true"
    stars_wallet: str = os.getenv("STARS_WALLET", "")  # Для вывода звёзд
    
    # Админ-панель
    admin_url: str = os.getenv("ADMIN_URL", "http://localhost:8000")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")

config = BotConfig()
