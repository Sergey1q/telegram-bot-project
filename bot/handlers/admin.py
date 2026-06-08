"""Административные обработчики."""
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
from datetime import datetime
import pandas as pd
import os

from bot.database import (
    AsyncSessionLocal, User, Appointment, Service,
    AppointmentStatus, Payment, Broadcast, Feedback
)
from bot.keyboards import (
    admin_menu_keyboard, main_menu_keyboard,
    admin_appointments_keyboard, appointment_detail_keyboard
)
from bot.config import config

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка на администратора."""
    return user_id in config.admin_ids


# ============ ГЛАВНОЕ АДМИН-МЕНЮ ============

@router.message(F.text == "📋 Заявки")
async def admin_appointments(message: types.Message):
    """Список всех заявок."""
    if not is_admin(message.from_user.id):
        return
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment).order_by(Appointment.created_at.desc())
        )
        appointments = result.scalars().all()
    
    if not appointments:
        await message.answer("📭 Заявок пока нет.")
        return
    
    status_counts = {"new": 0, "confirmed": 0, "completed": 0, "cancelled": 0}
    for app in appointments:
        status = app.status.value if hasattr(app.status, 'value') else str(app.status)
        if status in status_counts:
            status_counts[status] += 1
    
    text = (
        f"📋 <b>ЗАЯВКИ</b>\n"
        f"Всего: <b>{len(appointments)}</b>\n"
        f"Новых: {status_counts.get('new', 0)} | Подтверждено: {status_counts.get('confirmed', 0)}\n"
        f"Выполнено: {status_counts.get('completed', 0)} | Отменено: {status_counts.get('cancelled', 0)}\n"
        f"{'─' * 30}\n"
    )
    
    status_emoji = {"new": "🆕", "confirmed": "✅", "completed": "✔️", "cancelled": "❌"}
    for app in appointments[-10:]:
        status = app.status.value if hasattr(app.status, 'value') else str(app.status)
        text += (
            f"{status_emoji.get(status, '')} <b>#{app.id}</b> {app.client_name}\n"
            f"   {app.service_name} | {app.appointment_date} {app.appointment_time}\n"
            f"   Тел: {app.client_phone} | {'Оплачено' if app.is_paid else 'Не оплачено'}\n"
        )
    
    await message.answer(text, reply_markup=admin_appointments_keyboard(appointments), parse_mode="HTML")


# ============ ДЕТАЛИ ЗАЯВКИ ============

@router.callback_query(F.data.startswith("app_"))
async def appointment_detail(callback: types.CallbackQuery):
    """Детали конкретной заявки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    appointment_id = int(callback.data.replace("app_", ""))
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
        app = result.scalar_one_or_none()
    
    if not app:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return
    
    status = app.status.value if hasattr(app.status, 'value') else str(app.status)
    status_emoji = {"new": "🆕", "confirmed": "✅", "completed": "✔️", "cancelled": "❌"}
    
    text = (
        f"📋 <b>ЗАЯВКА #{app.id}</b>\n\n"
        f"Статус: {status_emoji.get(status, '')} <b>{status}</b>\n"
        f"Услуга: <b>{app.service_name}</b>\n"
        f"Клиент: <b>{app.client_name}</b>\n"
        f"Телефон: <b>{app.client_phone}</b>\n"
        f"Email: {app.client_email or 'Не указан'}\n"
        f"Дата: <b>{app.appointment_date}</b>\n"
        f"Время: <b>{app.appointment_time}</b>\n"
        f"Стоимость: <b>{app.price:.0f}₽</b>\n"
        f"Оплата: {'✅ ' + (app.payment_method or '') if app.is_paid else '❌ Не оплачено'}\n"
        f"Комментарий: {app.comment or 'Нет'}\n"
        f"Создана: {app.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    await callback.message.edit_text(text, reply_markup=appointment_detail_keyboard(app.id, app.is_paid), parse_mode="HTML")
    await callback.answer()


# ============ ИЗМЕНЕНИЕ СТАТУСА ЗАЯВКИ ============

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_appointment(callback: types.CallbackQuery):
    """Подтвердить заявку."""
    if not is_admin(callback.from_user.id):
        return
    
    appointment_id = int(callback.data.replace("confirm_", ""))
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
        app = result.scalar_one_or_none()
        if app:
            app.status = AppointmentStatus.CONFIRMED
            app.updated_at = datetime.now()
            await db.commit()
    
    await callback.answer("✅ Подтверждено!")
    # Обновляем детали заявки
    await appointment_detail(callback)


@router.callback_query(F.data.startswith("complete_"))
async def complete_appointment(callback: types.CallbackQuery):
    """Завершить заявку."""
    if not is_admin(callback.from_user.id):
        return
    
    appointment_id = int(callback.data.replace("complete_", ""))
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
        app = result.scalar_one_or_none()
        if app:
            app.status = AppointmentStatus.COMPLETED
            app.updated_at = datetime.now()
            await db.commit()
    
    await callback.answer("✔️ Выполнено!")
    await appointment_detail(callback)


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_appointment_admin(callback: types.CallbackQuery):
    """Отменить заявку (админ)."""
    if not is_admin(callback.from_user.id):
        return
    
    appointment_id = int(callback.data.replace("cancel_", ""))
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
        app = result.scalar_one_or_none()
        if app:
            app.status = AppointmentStatus.CANCELLED
            app.updated_at = datetime.now()
            await db.commit()
    
    await callback.answer("❌ Отменено!")
    await appointment_detail(callback)


# ============ ЭКСПОРТ В EXCEL ============

@router.callback_query(F.data == "export_appointments")
async def export_appointments_excel(callback: types.CallbackQuery):
    """Экспорт заявок в Excel."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).order_by(Appointment.created_at.desc()))
        appointments = result.scalars().all()
    
    if not appointments:
        await callback.answer("Нет данных для экспорта!", show_alert=True)
        return
    
    # Формируем данные
    data = [{
        'ID': a.id,
        'Клиент': a.client_name,
        'Телефон': a.client_phone,
        'Email': a.client_email or '',
        'Услуга': a.service_name,
        'Дата': a.appointment_date,
        'Время': a.appointment_time,
        'Цена': a.price,
        'Оплачено': 'Да' if a.is_paid else 'Нет',
        'Способ оплаты': a.payment_method or '',
        'Статус': a.status.value if hasattr(a.status, 'value') else str(a.status),
        'Комментарий': a.comment or '',
        'Создана': a.created_at.strftime('%Y-%m-%d %H:%M'),
    } for a in appointments]
    
    df = pd.DataFrame(data)
    filename = f"appointments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Заявки', index=False)
    
    # Отправляем файл
    await callback.message.answer_document(
        types.FSInputFile(filename),
        caption=f"📊 Заявки ({len(appointments)} шт.)"
    )
    
    # Удаляем файл после отправки
    try:
        os.remove(filename)
    except:
        pass
    
    await callback.answer("✅ Экспортировано!")


# ============ НАЗАД К СПИСКУ ЗАЯВОК ============

@router.callback_query(F.data == "back_to_appointments")
async def back_to_appointments_list(callback: types.CallbackQuery):
    """Возврат к списку заявок."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment).order_by(Appointment.created_at.desc())
        )
        appointments = result.scalars().all()
    
    if not appointments:
        await callback.message.edit_text("📭 Заявок пока нет.")
        await callback.answer()
        return
    
    text = f"📋 <b>ЗАЯВКИ</b> (всего: {len(appointments)})\n{'─' * 30}\n"
    status_emoji = {"new": "🆕", "confirmed": "✅", "completed": "✔️", "cancelled": "❌"}
    
    for app in appointments[-10:]:
        status = app.status.value if hasattr(app.status, 'value') else str(app.status)
        text += (
            f"{status_emoji.get(status, '')} <b>#{app.id}</b> {app.client_name}\n"
            f"   {app.service_name} | {app.appointment_date}\n"
        )
    
    await callback.message.edit_text(text, reply_markup=admin_appointments_keyboard(appointments), parse_mode="HTML")
    await callback.answer()


# ============ СТАТИСТИКА ============

@router.message(F.text == "📊 Статистика")
async def admin_statistics(message: types.Message):
    """Статистика бота."""
    if not is_admin(message.from_user.id):
        return
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count(User.id)))
        total_users = result.scalar()
        
        result = await db.execute(
            select(func.count(User.id)).filter(
                User.registered_at >= datetime.now().replace(hour=0, minute=0, second=0)
            )
        )
        new_today = result.scalar()
        
        result = await db.execute(select(func.count(Appointment.id)))
        total_appointments = result.scalar()
        
        result = await db.execute(
            select(func.count(Appointment.id)).filter(Appointment.status == "new")
        )
        new_appointments = result.scalar()
        
        result = await db.execute(
            select(func.sum(Payment.amount_rub)).filter(Payment.status == "paid")
        )
        total_revenue = result.scalar() or 0
        
        result = await db.execute(select(func.count(Service.id)))
        total_services = result.scalar()
    
    text = (
        "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b> (+{new_today} сегодня)\n"
        f"📅 Заявок: <b>{total_appointments}</b> (новых: {new_appointments})\n"
        f"💰 Выручка: <b>{total_revenue:.0f}₽</b>\n"
        f"🔧 Услуг: <b>{total_services}</b>\n"
        f"📅 Дата: <b>{datetime.now().strftime('%d.%m.%Y %H:%M')}</b>"
    )
    
    await message.answer(text, parse_mode="HTML")


# ============ ССЫЛКА НА АДМИН-ПАНЕЛЬ ============

@router.message(F.text == "🔗 Админ-панель")
async def admin_panel_link(message: types.Message):
    """Ссылка на веб-админку."""
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        f"🔗 <b>Веб-панель управления:</b>\n{config.admin_url}\n\n"
        f"👤 Логин: <code>{config.admin_username}</code>\n"
        f"🔑 Пароль: <code>{config.admin_password}</code>",
        parse_mode="HTML"
    )


# ============ ПЕРЕКЛЮЧЕНИЕ МЕНЮ ============

@router.message(F.text == "🔙 Обычное меню")
async def switch_to_user_menu(message: types.Message):
    """Переключение в обычное меню."""
    await message.answer("Обычное меню:", reply_markup=main_menu_keyboard())
