"""Вспомогательные функции для бота."""
from datetime import datetime, timedelta
import re

def validate_phone(phone: str) -> bool:
    """Проверка формата телефона."""
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\+?\d{10,12}$', phone_clean))

def format_phone(phone: str) -> str:
    """Форматирование телефона в красивый вид."""
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    if len(phone_clean) == 11:
        return f"+7 ({phone_clean[1:4]}) {phone_clean[4:7]}-{phone_clean[7:9]}-{phone_clean[9:11]}"
    return phone

def parse_date(text: str) -> str:
    """Парсинг даты из текста (завтра, послезавтра, и т.д.)."""
    text = text.lower().strip()
    today = datetime.now()
    
    date_map = {
        "сегодня": today,
        "завтра": today + timedelta(days=1),
        "послезавтра": today + timedelta(days=2),
        "через неделю": today + timedelta(weeks=1),
    }
    
    if text in date_map:
        return date_map[text].strftime("%d.%m.%Y")
    
    # Если введена дата в формате ДД.ММ.ГГГГ
    if re.match(r'\d{2}\.\d{2}\.\d{4}', text):
        return text
    
    return text

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезает текст до нужной длины."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def get_status_emoji(status: str) -> str:
    """Возвращает эмодзи для статуса."""
    emoji_map = {
        "new": "🆕",
        "confirmed": "✅",
        "completed": "✔️",
        "cancelled": "❌",
        "pending": "⏳",
        "paid": "💰",
        "refunded": "↩️",
        "expired": "⏰",
    }
    return emoji_map.get(status, "❓")

def get_stars_price(rub_price: float) -> int:
    """Конвертирует рубли в Telegram Stars (примерный курс)."""
    return int(rub_price / 2)  # 1 звезда ≈ 2 рубля

def format_price(price: float) -> str:
    """Форматирует цену."""
    if price >= 1000:
        return f"{price/1000:.1f}K₽"
    return f"{price:.0f}₽"
