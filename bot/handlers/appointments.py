"""Обработчики записи на услуги."""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from datetime import datetime, timedelta
import re

from bot.database import AsyncSessionLocal, Appointment, Service, AppointmentStatus
from bot.keyboards import services_keyboard, main_menu_keyboard
from bot.config import config

router = Router()

class AppointmentState(StatesGroup):
    choosing_service = State()
    entering_name = State()
    entering_phone = State()
    entering_date = State()
    entering_time = State()
    entering_comment = State()


@router.message(F.text == "📅 Записаться")
async def start_appointment(message: types.Message, state: FSMContext):
    """Начало записи на услугу."""
    await state.set_state(AppointmentState.choosing_service)
    keyboard = await services_keyboard()
    await message.answer("📅 Выберите услугу:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("service_"))
async def choose_service(callback: types.CallbackQuery, state: FSMContext):
    """Выбор услуги."""
    data = callback.data
    
    if data.startswith("service_default_"):
        # Услуга по умолчанию
        parts = data.replace("service_default_", "").rsplit("_", 2)
        service_name = parts[0]
        price_rub = float(parts[1])
        price_stars = int(parts[2])
        service_id = None
    else:
        # Услуга из БД
        try:
            service_id = int(data.replace("service_", ""))
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Service).filter(Service.id == service_id))
                service = result.scalar_one_or_none()
                if service:
                    service_name = service.name
                    price_rub = service.price_rub
                    price_stars = service.price_stars
                else:
                    await callback.answer("Услуга не найдена!", show_alert=True)
                    return
        except ValueError:
            return  # Не наш callback
    
    await state.update_data(
        service_id=service_id,
        service_name=service_name,
        price_rub=price_rub,
        price_stars=price_stars,
    )
    await state.set_state(AppointmentState.entering_name)
    
    await callback.message.edit_text(
        f"✅ Услуга: <b>{service_name}</b>\n"
        f"💰 Стоимость: <b>{price_rub:.0f}₽</b> или <b>{price_stars} ⭐</b>\n\n"
        "Введите ваше имя:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_appointment")
async def cancel_appointment_process(callback: types.CallbackQuery, state: FSMContext):
    """Отмена записи."""
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(AppointmentState.entering_name)
async def enter_name(message: types.Message, state: FSMContext):
    """Ввод имени."""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Имя должно содержать минимум 2 символа.")
        return
    
    await state.update_data(client_name=name)
    await state.set_state(AppointmentState.entering_phone)
    await message.answer("📱 Введите номер телефона:\nПример: +79001234567")


@router.message(AppointmentState.entering_phone)
async def enter_phone(message: types.Message, state: FSMContext):
    """Ввод телефона."""
    phone = message.text.strip()
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
    
    if not re.match(r'^\+?\d{10,12}$', phone_clean):
        await message.answer("❌ Неверный формат телефона. Попробуйте ещё раз:")
        return
    
    await state.update_data(client_phone=phone)
    await state.set_state(AppointmentState.entering_date)
    await message.answer(
        "📅 Введите желаемую дату:\n"
        "Примеры: 15.06.2026, завтра, 20 июня"
    )


@router.message(AppointmentState.entering_date)
async def enter_date(message: types.Message, state: FSMContext):
    """Ввод даты."""
    date_text = message.text.strip()
    
    # Обработка "завтра", "послезавтра"
    if date_text.lower() == "завтра":
        date_text = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    elif date_text.lower() == "послезавтра":
        date_text = (datetime.now() + timedelta(days=2)).strftime("%d.%m.%Y")
    
    await state.update_data(appointment_date=date_text)
    await state.set_state(AppointmentState.entering_time)
    await message.answer("⏰ Введите удобное время:\nПример: 14:00 или 14.00")


@router.message(AppointmentState.entering_time)
async def enter_time(message: types.Message, state: FSMContext):
    """Ввод времени."""
    time_text = message.text.strip().replace('.', ':')
    
    if not re.match(r'^\d{1,2}:\d{2}$', time_text):
        await message.answer("❌ Неверный формат времени. Пример: 14:00")
        return
    
    await state.update_data(appointment_time=time_text)
    await state.set_state(AppointmentState.entering_comment)
    await message.answer(
        "💬 Оставьте комментарий (необязательно):\n"
        "Напишите /skip чтобы пропустить"
    )


@router.message(AppointmentState.entering_comment)
async def save_appointment(message: types.Message, state: FSMContext):
    """Сохранение заявки."""
    data = await state.get_data()
    comment = message.text if message.text != "/skip" else ""
    
    async with AsyncSessionLocal() as db:
        appointment = Appointment(
            user_id=message.from_user.id,
            service_id=data.get('service_id'),
            service_name=data['service_name'],
            client_name=data['client_name'],
            client_phone=data['client_phone'],
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time'],
            comment=comment,
            price=data['price_rub'],
            status=AppointmentStatus.NEW,
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)
        
        appointment_id = appointment.id
    
    await state.clear()
    
    # Подтверждение
    text = (
        "✅ <b>ЗАЯВКА СОЗДАНА!</b>\n\n"
        f"Номер заявки: <b>#{appointment_id}</b>\n"
        f"Услуга: <b>{data['service_name']}</b>\n"
        f"Дата: <b>{data['appointment_date']}</b>\n"
        f"Время: <b>{data['appointment_time']}</b>\n"
        f"Имя: <b>{data['client_name']}</b>\n"
        f"Телефон: <b>{data['client_phone']}</b>\n"
        f"Стоимость: <b>{data['price_rub']:.0f}₽</b> / <b>{data['price_stars']}⭐</b>\n"
    )
    if comment:
        text += f"Комментарий: <i>{comment}</i>\n"
    
    text += "\n📞 Мы свяжемся с вами для подтверждения."
    
    # Клавиатура с оплатой
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"💳 Оплатить {data['price_stars']} ⭐",
        callback_data=f"pay_stars_{appointment_id}_{data['price_stars']}"
    ))
    builder.row(InlineKeyboardButton(
        text="🔙 В меню",
        callback_data="back_to_menu"
    ))
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    
    # Уведомление админам
    for admin_id in config.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f"🆕 <b>НОВАЯ ЗАЯВКА #{appointment_id}</b>\n"
                f"Услуга: {data['service_name']}\n"
                f"Клиент: {data['client_name']}\n"
                f"Телефон: {data['client_phone']}\n"
                f"Дата: {data['appointment_date']} в {data['appointment_time']}",
                parse_mode="HTML"
            )
        except:
            pass


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
@router.callback_query(F.data == "cancel_appointment")
async def cancel_appointment_process(callback: types.CallbackQuery, state: FSMContext):
    """Отмена записи."""
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
