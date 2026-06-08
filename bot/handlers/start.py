"""Обработчик команды /start."""
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from datetime import datetime

from bot.database import AsyncSessionLocal, User, UserRole
from bot.keyboards import main_menu_keyboard, admin_menu_keyboard
from bot.config import config

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Регистрация пользователя."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).filter(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                role=UserRole.ADMIN if message.from_user.id in config.admin_ids else UserRole.USER,
            )
            db.add(user)
            await db.commit()
        
        # Обновляем last_active
        user.last_active = datetime.now()
        await db.commit()
    
    # Определяем меню
    if message.from_user.id in config.admin_ids:
        keyboard = admin_menu_keyboard()
        role = "администратора"
    else:
        keyboard = main_menu_keyboard()
        role = "пользователя"
    
    welcome = (
        f"👋 <b>Добро пожаловать, {message.from_user.full_name}!</b>\n\n"
        f"Вы вошли как <b>{role}</b>.\n\n"
        "📅 Запись на услуги\n"
        "💰 Оплата через Telegram Stars ⭐\n"
        "📊 Статистика и отчёты\n"
        "📢 Рассылки (админ)\n\n"
        "Выберите действие в меню 👇"
    )
    
    await message.answer(welcome, reply_markup=keyboard, parse_mode="HTML")

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Вход в админ-панель через веб."""
    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Доступ запрещён.")
        return
    
    await message.answer(
        f"🔗 <b>Админ-панель:</b> {config.admin_url}\n"
        f"Логин: <code>{config.admin_username}</code>\n"
        f"Пароль: <code>{config.admin_password}</code>",
        parse_mode="HTML"
    )
