"""Клавиатуры для бота."""
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,  # ← ВОТ ЭТОГО НЕ ХВАТАЛО
)
from sqlalchemy import select
from bot.database import AsyncSessionLocal, Service, Appointment


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню пользователя."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📅 Записаться"),
        KeyboardButton(text="💰 Калькулятор"),
    )
    builder.row(
        KeyboardButton(text="ℹ️ О компании"),
        KeyboardButton(text="📞 Контакты"),
    )
    builder.row(
        KeyboardButton(text="📝 Оставить отзыв"),
        KeyboardButton(text="⭐ Мой баланс"),
    )
    builder.row(
        KeyboardButton(text="❓ Помощь"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Меню администратора."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📋 Заявки"),
        KeyboardButton(text="📢 Рассылка"),
    )
    builder.row(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="👥 Пользователи"),
    )
    builder.row(
        KeyboardButton(text="➕ Добавить услугу"),
        KeyboardButton(text="🔗 Админ-панель"),
    )
    builder.row(
        KeyboardButton(text="🔙 Обычное меню"),
    )
    return builder.as_markup(resize_keyboard=True)


async def services_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора услуги."""
    builder = InlineKeyboardBuilder()
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Service).filter(Service.is_active == True)
        )
        services = result.scalars().all()
    
    if services:
        for service in services:
            price_text = f"{service.price_rub:.0f}₽" if service.price_rub > 0 else f"{service.price_stars}⭐"
            builder.row(InlineKeyboardButton(
                text=f"{service.name} — {price_text}",
                callback_data=f"service_{service.id}"
            ))
    else:
        # Услуги по умолчанию
        default_services = [
            ("💻 Консультация IT", 1500, 60, 750),
            ("🔧 Настройка ПО", 2000, 90, 1000),
            ("📊 Анализ данных", 3000, 120, 1500),
            ("🤖 Разработка бота", 5000, 180, 2500),
        ]
        for name, price_rub, duration, price_stars in default_services:
            builder.row(InlineKeyboardButton(
                text=f"{name} — {price_rub}₽ / {price_stars}⭐",
                callback_data=f"service_default_{name}_{price_rub}_{price_stars}"
            ))
    
    builder.row(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_appointment"))
    return builder.as_markup()


def admin_appointments_keyboard(appointments: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком заявок."""
    builder = InlineKeyboardBuilder()
    
    status_emoji = {
        "new": "🆕",
        "confirmed": "✅",
        "completed": "✔️",
        "cancelled": "❌",
    }
    
    for app in appointments[-10:]:
        status = app.status.value if hasattr(app.status, 'value') else app.status
        emoji = status_emoji.get(status, "")
        builder.row(InlineKeyboardButton(
            text=f"{emoji} {app.client_name} | {app.service_name} | {app.appointment_date}",
            callback_data=f"app_{app.id}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="📤 Экспорт в Excel", callback_data="export_appointments"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin"),
    )
    return builder.as_markup()


def appointment_detail_keyboard(appointment_id: int, is_paid: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для управления конкретной заявкой."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{appointment_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="✔️ Выполнено", callback_data=f"complete_{appointment_id}"),
    )
    
    if not is_paid:
        builder.row(InlineKeyboardButton(
            text="💳 Оплатить звёздами ⭐",
            callback_data=f"pay_stars_{appointment_id}_500"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙 К списку", callback_data="back_to_appointments"))
    return builder.as_markup()
