"""
ГОТОВЫЙ БОТ ДЛЯ САЛОНА КРАСОТЫ
Запуск: python bot/beauty_salon_bot.py
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
import pandas as pd

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8798079377:AAGst33-TDokl3-GERdRsgWieSzbfXgQ2UE"
ADMIN_IDS = [6327993240]  # Замените на ваш ID

# ============ БАЗА ДАННЫХ ============
engine = create_engine("sqlite:///beauty_salon.db", echo=False)

class Base(DeclarativeBase):
    pass

class Appointment(Base):
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String(100))
    client_phone: Mapped[str] = mapped_column(String(20))
    service: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column(Float)
    date: Mapped[str] = mapped_column(String(20))
    time: Mapped[str] = mapped_column(String(10))
    comment: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Новая")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

# ============ УСЛУГИ САЛОНА ============
SERVICES = {
    "💇 Стрижка женская": 1500,
    "💇 Стрижка мужская": 800,
    "💅 Маникюр": 1200,
    "💅 Маникюр + покрытие": 2000,
    "💆 Окрашивание": 3000,
    "💆 Мелирование": 4000,
    "💄 Макияж": 1500,
    "💄 Макияж вечерний": 2500,
    "🧖 Чистка лица": 1800,
    "🧖 Массаж лица": 1200,
    "💪 Массаж спины": 2000,
    "💪 Массаж общий": 3500,
    "👰 Свадебный пакет": 8000,
}

# ============ СОСТОЯНИЯ ============
class AppointmentState(StatesGroup):
    choosing_service = State()
    entering_name = State()
    entering_phone = State()
    entering_date = State()
    entering_time = State()
    entering_comment = State()

# ============ КЛАВИАТУРЫ ============
def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📅 Записаться"))
    builder.row(KeyboardButton(text="💅 Услуги и цены"), KeyboardButton(text="📞 Контакты"))
    builder.row(KeyboardButton(text="ℹ️ О салоне"), KeyboardButton(text="⭐ Отзывы"))
    return builder.as_markup(resize_keyboard=True)

def services_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name, price in SERVICES.items():
        builder.row(InlineKeyboardButton(
            text=f"{name} — {price}₽",
            callback_data=f"book_{name}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_booking"))
    return builder.as_markup()

# ============ ОБРАБОТЧИКИ ============
router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome = (
        "🌸 <b>Добро пожаловать в салон красоты «Лаванда»!</b>\n\n"
        "Мы работаем с 2020 года и делаем девушек ещё красивее!\n\n"
        "📅 <b>Записаться онлайн</b> — нажмите кнопку ниже\n"
        "💅 <b>Все услуги и цены</b> — в меню\n"
        "📞 <b>Телефон:</b> +7 (999) 123-45-67\n\n"
        "Выберите действие 👇"
    )
    await message.answer(welcome, reply_markup=main_menu(), parse_mode="HTML")

@router.message(F.text == "📅 Записаться")
async def start_booking(message: types.Message, state: FSMContext):
    await state.set_state(AppointmentState.choosing_service)
    await message.answer("💅 Выберите услугу:", reply_markup=services_menu())

@router.callback_query(F.data.startswith("book_"))
async def choose_service(callback: types.CallbackQuery, state: FSMContext):
    service_name = callback.data.replace("book_", "")
    price = SERVICES.get(service_name, 0)
    
    await state.update_data(service=service_name, price=price)
    await state.set_state(AppointmentState.entering_name)
    
    await callback.message.edit_text(
        f"✅ Услуга: <b>{service_name}</b> — <b>{price}₽</b>\n\n"
        "Введите ваше имя:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_booking")
async def cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu())

@router.message(AppointmentState.entering_name)
async def enter_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Имя должно содержать минимум 2 символа.")
        return
    
    await state.update_data(client_name=name)
    await state.set_state(AppointmentState.entering_phone)
    await message.answer("📱 Введите номер телефона:\nНапример: +79001234567")

@router.message(AppointmentState.entering_phone)
async def enter_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    
    await state.update_data(client_phone=phone)
    await state.set_state(AppointmentState.entering_date)
    await message.answer(
        "📅 Введите желаемую дату:\n"
        "Например: 25.06.2026 или завтра"
    )

@router.message(AppointmentState.entering_date)
async def enter_date(message: types.Message, state: FSMContext):
    date_text = message.text.strip()
    if date_text.lower() == "завтра":
        date_text = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    elif date_text.lower() == "послезавтра":
        date_text = (datetime.now() + timedelta(days=2)).strftime("%d.%m.%Y")
    
    await state.update_data(date=date_text)
    await state.set_state(AppointmentState.entering_time)
    await message.answer("⏰ Введите удобное время:\nНапример: 14:00")

@router.message(AppointmentState.entering_time)
async def enter_time(message: types.Message, state: FSMContext):
    time_text = message.text.strip().replace('.', ':')
    
    await state.update_data(time=time_text)
    await state.set_state(AppointmentState.entering_comment)
    await message.answer(
        "💬 Комментарий (необязательно):\n"
        "Напишите /skip чтобы пропустить"
    )

@router.message(AppointmentState.entering_comment)
async def save_appointment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text if message.text != "/skip" else ""
    
    with Session(engine) as db:
        appointment = Appointment(
            client_name=data['client_name'],
            client_phone=data['client_phone'],
            service=data['service'],
            price=data['price'],
            date=data['date'],
            time=data['time'],
            comment=comment,
        )
        db.add(appointment)
        db.commit()
    
    await state.clear()
    
    text = (
        "✅ <b>ЗАПИСЬ ПОДТВЕРЖДЕНА!</b>\n\n"
        f"Услуга: <b>{data['service']}</b>\n"
        f"Стоимость: <b>{data['price']}₽</b>\n"
        f"Дата: <b>{data['date']}</b>\n"
        f"Время: <b>{data['time']}</b>\n"
        f"Имя: <b>{data['client_name']}</b>\n"
        f"Телефон: <b>{data['client_phone']}</b>\n"
    )
    if comment:
        text += f"Комментарий: {comment}\n"
    
    text += "\n🌸 Ждём вас! Отличного настроения!"
    
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")
    
    # Уведомление админу
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"🆕 <b>НОВАЯ ЗАПИСЬ</b>\n"
                f"Клиент: {data['client_name']}\n"
                f"Телефон: {data['client_phone']}\n"
                f"Услуга: {data['service']}\n"
                f"Дата: {data['date']} в {data['time']}",
                parse_mode="HTML"
            )
        except:
            pass

@router.message(F.text == "💅 Услуги и цены")
async def show_services(message: types.Message):
    text = "💅 <b>УСЛУГИ И ЦЕНЫ</b>\n\n"
    for name, price in SERVICES.items():
        text += f"{name}: <b>{price}₽</b>\n"
    
    text += "\n📅 Для записи нажмите «Записаться»"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📞 Контакты")
async def show_contacts(message: types.Message):
    await message.answer(
        "📞 <b>КОНТАКТЫ</b>\n\n"
        "🏠 Адрес: г. Москва, ул. Цветочная, 15\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "📧 Email: lavanda@beauty.ru\n"
        "🕐 Пн-Сб: 10:00–20:00\n"
        "🕐 Вс: 11:00–18:00\n\n"
        "Мы рядом с метро Цветочная!",
        parse_mode="HTML"
    )

@router.message(F.text == "ℹ️ О салоне")
async def show_about(message: types.Message):
    await message.answer(
        "🌸 <b>САЛОН КРАСОТЫ «ЛАВАНДА»</b>\n\n"
        "Мы работаем с 2020 года.\n"
        "Более 1000 довольных клиенток!\n\n"
        "✨ Только качественные материалы\n"
        "✨ Опытные мастера\n"
        "✨ Уютная атмосфера\n"
        "✨ Кофе и чай бесплатно\n\n"
        "Приходите — будем рады! 💕",
        parse_mode="HTML"
    )

@router.message(F.text == "⭐ Отзывы")
async def show_reviews(message: types.Message):
    await message.answer(
        "⭐ <b>ОТЗЫВЫ НАШИХ КЛИЕНТОВ</b>\n\n"
        "🌟 «Лучший салон! Хожу только сюда уже 2 года» — Анна\n"
        "🌟 «Маникюр держится 3 недели!» — Екатерина\n"
        "🌟 «Очень приятная атмосфера и мастера» — Мария\n"
        "🌟 «Свадебный макияж — это просто сказка!» — Ольга\n\n"
        "❤️ Будем рады вашему отзыву!",
        parse_mode="HTML"
    )

# ============ АДМИН-МЕНЮ ============
@router.message(F.text == "Админ2")
async def admin_menu(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён.")
        return
    
    with Session(engine) as db:
        appointments = db.query(Appointment).order_by(Appointment.created_at.desc()).all()
    
    if not appointments:
        await message.answer("📭 Записей пока нет.")
        return
    
    text = f"📋 <b>ЗАПИСИ (всего: {len(appointments)})</b>\n{'─' * 30}\n"
    for app in appointments[:10]:
        text += (
            f"<b>#{app.id}</b> {app.client_name} | {app.date} {app.time}\n"
            f"  {app.service} — {app.price}₽\n"
            f"  📱 {app.client_phone}\n"
        )
    
    # Экспорт в Excel
    data = [{
        'ID': a.id,
        'Клиент': a.client_name,
        'Телефон': a.client_phone,
        'Услуга': a.service,
        'Цена': a.price,
        'Дата': a.date,
        'Время': a.time,
        'Комментарий': a.comment or '',
        'Статус': a.status,
        'Дата создания': a.created_at.strftime('%Y-%m-%d %H:%M'),
    } for a in appointments]
    
    df = pd.DataFrame(data)
    filename = "beauty_appointments.xlsx"
    df.to_excel(filename, index=False)
    
    await message.answer(text, parse_mode="HTML")
    await message.answer_document(types.FSInputFile(filename), caption="📊 Все записи")
    
    import os
    try:
        os.remove(filename)
    except:
        pass

# ============ ЗАПУСК ============
async def main():
    logging.basicConfig(level=logging.INFO)
    
    if BOT_TOKEN == "ВАШ_ТОКЕН":
        print("❌ Укажите токен бота!")
        return
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    print("🌸 Бот салона красоты запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
