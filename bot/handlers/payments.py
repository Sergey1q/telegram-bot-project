"""Обработчики платежей через Telegram Stars."""
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery
from sqlalchemy import select
from datetime import datetime
import json
import logging

from bot.database import AsyncSessionLocal, Payment, PaymentStatus, User, Appointment, AppointmentStatus
from bot.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Флаг для тестового режима (без реальных платежей)
TEST_MODE = True  # Поставьте False для реальных платежей


@router.callback_query(F.data.startswith("pay_stars_"))
async def send_stars_invoice(callback: types.CallbackQuery, bot: Bot):
    """Отправляет счёт на оплату или проводит тестовую оплату."""
    parts = callback.data.split("_")
    appointment_id = int(parts[2])
    amount = int(parts[3])
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
        appointment = result.scalar_one_or_none()
        
        if not appointment:
            await callback.answer("❌ Заявка не найдена!", show_alert=True)
            return
        
        if TEST_MODE:
            # ТЕСТОВЫЙ РЕЖИМ — сразу подтверждаем оплату
            payment = Payment(
                user_id=callback.from_user.id,
                appointment_id=appointment_id,
                amount_stars=amount,
                amount_rub=amount * 2,
                description=f"Оплата услуги: {appointment.service_name} (ТЕСТ)",
                payload=json.dumps({"appointment_id": appointment_id, "user_id": callback.from_user.id}),
                status=PaymentStatus.PAID,
                paid_at=datetime.now(),
            )
            db.add(payment)
            
            # Обновляем заявку
            appointment.is_paid = True
            appointment.payment_method = "stars_test"
            appointment.status = AppointmentStatus.CONFIRMED
            
            # Начисляем кешбэк
            result = await db.execute(select(User).filter(User.telegram_id == callback.from_user.id))
            user = result.scalar_one_or_none()
            if user:
                cashback = int(amount * 0.05)
                user.stars_balance += cashback
                user.total_spent += amount
            
            await db.commit()
            
            text = (
                "🎉 <b>ОПЛАТА УСПЕШНА! (ТЕСТОВЫЙ РЕЖИМ)</b>\n\n"
                f"Услуга: <b>{appointment.service_name}</b>\n"
                f"Сумма: <b>{amount} ⭐</b>\n"
                f"Дата: {appointment.appointment_date} в {appointment.appointment_time}\n\n"
                f"💰 Кешбэк: <b>+{cashback if user else 0} ⭐</b>\n"
                f"Баланс: <b>{user.stars_balance if user else 0} ⭐</b>\n\n"
                "✅ Заявка подтверждена! Мы свяжемся с вами."
            )
            
            await callback.message.edit_text(text, parse_mode="HTML")
            await callback.answer("✅ Тестовая оплата прошла успешно!")
            
            # Уведомление админам
            from bot.config import config
            for admin_id in config.admin_ids:
                try:
                    await bot.send_message(
                        admin_id,
                        f"💰 <b>ТЕСТОВЫЙ ПЛАТЁЖ</b>\n"
                        f"От: {callback.from_user.full_name}\n"
                        f"Сумма: {amount} ⭐\n"
                        f"Услуга: {appointment.service_name}\n"
                        f"Заявка #{appointment_id}",
                        parse_mode="HTML"
                    )
                except:
                    pass
        else:
            # РЕАЛЬНЫЙ РЕЖИМ — отправляем счёт Telegram Stars
            # ВАЖНО: для реальных платежей нужно:
            # 1. Подключить бота к Telegram Stars в @BotFather
            # 2. Иметь достаточный баланс звёзд
            
            payment = Payment(
                user_id=callback.from_user.id,
                appointment_id=appointment_id,
                amount_stars=amount,
                amount_rub=amount * 2,
                description=f"Оплата услуги: {appointment.service_name}",
                payload=json.dumps({"appointment_id": appointment_id, "user_id": callback.from_user.id}),
            )
            db.add(payment)
            await db.commit()
            
            try:
                prices = [LabeledPrice(
                    label=f"Оплата {appointment.service_name}",
                    amount=amount
                )]
                
                await bot.send_invoice(
                    chat_id=callback.from_user.id,
                    title="Оплата услуги",
                    description=f"Услуга: {appointment.service_name}\nДата: {appointment.appointment_date}\nВремя: {appointment.appointment_time}",
                    payload=f"appointment_{appointment_id}",
                    provider_token="",  # Пусто для Telegram Stars
                    currency="XTR",
                    prices=prices,
                    start_parameter=f"pay_{appointment_id}",
                )
                await callback.answer("✅ Счёт отправлен!")
            except Exception as e:
                logger.error(f"Ошибка отправки счёта: {e}")
                await callback.answer("❌ Ошибка отправки счёта. Попробуйте позже.", show_alert=True)


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Подтверждает возможность оплаты."""
    logger.info(f"Pre-checkout query: {pre_checkout_query.id}")
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    """Обрабатывает успешный платёж."""
    payment_info = message.successful_payment
    
    logger.info(f"Успешный платёж: {payment_info.telegram_payment_charge_id}, сумма: {payment_info.total_amount}")
    
    try:
        # Извлекаем ID заявки
        payload = payment_info.invoice_payload
        appointment_id = int(payload.replace("appointment_", ""))
    except:
        appointment_id = 0
    
    async with AsyncSessionLocal() as db:
        # Обновляем платёж
        result = await db.execute(
            select(Payment).filter(
                Payment.user_id == message.from_user.id,
                Payment.status == PaymentStatus.PENDING
            )
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            payment.status = PaymentStatus.PAID
            payment.telegram_payment_id = payment_info.telegram_payment_charge_id
            payment.paid_at = datetime.now()
        
        # Обновляем заявку
        if appointment_id:
            result = await db.execute(select(Appointment).filter(Appointment.id == appointment_id))
            appointment = result.scalar_one_or_none()
            if appointment:
                appointment.is_paid = True
                appointment.payment_method = "stars"
                appointment.status = AppointmentStatus.CONFIRMED
        
        # Начисляем кешбэк
        result = await db.execute(select(User).filter(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        cashback = 0
        
        if user:
            cashback = int(payment_info.total_amount * 0.05)
            user.stars_balance += cashback
            user.total_spent += payment_info.total_amount
        
        await db.commit()
        
        text = (
            "🎉 <b>ОПЛАТА УСПЕШНА!</b>\n\n"
            f"Сумма: <b>{payment_info.total_amount} ⭐</b>\n"
            f"ID: <code>{payment_info.telegram_payment_charge_id}</code>\n"
            f"\n💰 Кешбэк: <b>+{cashback} ⭐</b>\n"
            f"Баланс: <b>{user.stars_balance if user else 0} ⭐</b>\n\n"
            "✅ Заявка подтверждена! Мы свяжемся с вами."
        )
        
        await message.answer(text, parse_mode="HTML")
        
        # Уведомление админам
        from bot.config import config
        for admin_id in config.admin_ids:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"💰 <b>НОВЫЙ ПЛАТЁЖ!</b>\n"
                    f"От: {message.from_user.full_name}\n"
                    f"Сумма: {payment_info.total_amount} ⭐\n"
                    f"ID: {payment_info.telegram_payment_charge_id}",
                    parse_mode="HTML"
                )
            except:
                pass


@router.message(Command("balance"))
async def check_balance(message: types.Message):
    """Проверка баланса звёзд."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).filter(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
    
    if user:
        text = (
            "💰 <b>ВАШ БАЛАНС</b>\n\n"
            f"⭐ Звёзд: <b>{user.stars_balance}</b>\n"
            f"💵 Всего потрачено: <b>{user.total_spent:.0f} ⭐</b>\n\n"
            "<i>Звёзды начисляются как кешбэк 5% с каждой оплаты.</i>"
        )
    else:
        text = "❌ Вы не зарегистрированы. Нажмите /start"
    
    await message.answer(text, parse_mode="HTML")
