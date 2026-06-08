"""Обработчики отзывов, информационных сообщений и калькулятора."""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from bot.database import AsyncSessionLocal, Feedback, User
from bot.keyboards import main_menu_keyboard, admin_menu_keyboard, services_keyboard
from bot.config import config

router = Router()


class FeedbackState(StatesGroup):
    entering_rating = State()
    entering_text = State()


# ============ КАЛЬКУЛЯТОР ============

@router.message(F.text == "💰 Калькулятор")
async def calculator(message: types.Message):
    """Калькулятор стоимости услуг."""
    keyboard = await services_keyboard()
    await message.answer(
        "💰 <b>КАЛЬКУЛЯТОР СТОИМОСТИ</b>\n\n"
        "Выберите услугу для расчёта стоимости.\n"
        "Вы увидите цену в рублях и Telegram Stars ⭐",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ============ ОТЗЫВЫ ============

@router.message(F.text == "📝 Оставить отзыв")
async def start_feedback(message: types.Message, state: FSMContext):
    """Начало сбора отзыва."""
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(types.InlineKeyboardButton(
            text="⭐" * i,
            callback_data=f"rating_{i}"
        ))
    builder.adjust(5)
    
    await state.set_state(FeedbackState.entering_rating)
    await message.answer("Оцените качество услуг от 1 до 5:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("rating_"))
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    """Обработка рейтинга."""
    rating = int(callback.data.replace("rating_", ""))
    await state.update_data(rating=rating)
    await state.set_state(FeedbackState.entering_text)
    
    await callback.message.edit_text(
        f"Рейтинг: {'⭐' * rating}\n\n"
        "Напишите ваш отзыв (текст):"
    )
    await callback.answer()


@router.message(FeedbackState.entering_text)
async def save_feedback(message: types.Message, state: FSMContext):
    """Сохранение отзыва."""
    data = await state.get_data()
    rating = data.get('rating', 5)
    text = message.text.strip()
    
    if len(text) < 5:
        await message.answer("❌ Отзыв должен содержать минимум 5 символов.")
        return
    
    async with AsyncSessionLocal() as db:
        feedback = Feedback(
            user_id=message.from_user.id,
            text=text,
            rating=rating,
        )
        db.add(feedback)
        await db.commit()
    
    await state.clear()
    
    await message.answer(
        f"❤️ <b>Спасибо за отзыв!</b>\n"
        f"Ваша оценка: {'⭐' * rating}\n\n"
        "Мы обязательно его учтём.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    
    # Уведомление админам
    for admin_id in config.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f"📝 <b>НОВЫЙ ОТЗЫВ</b>\n"
                f"От: {message.from_user.full_name}\n"
                f"Рейтинг: {'⭐' * rating}\n"
                f"Текст: {text}",
                parse_mode="HTML"
            )
        except:
            pass


# ============ ИНФОРМАЦИЯ ============

@router.message(F.text == "❓ Помощь")
@router.message(Command("help"))
async def help_message(message: types.Message):
    """Помощь."""
    text = (
        "❓ <b>ПОМОЩЬ</b>\n\n"
        "📅 <b>Записаться</b> — запись на услугу\n"
        "💰 <b>Калькулятор</b> — расчёт стоимости\n"
        "⭐ <b>Мой баланс</b> — баланс звёзд\n"
        "📝 <b>Оставить отзыв</b> — оценить работу\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "/balance — баланс звёзд\n"
        "/help — эта справка"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "⭐ Мой баланс")
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


@router.message(F.text == "ℹ️ О компании")
async def about(message: types.Message):
    """Информация о компании."""
    await message.answer(
        "🏢 <b>IT-Решения</b>\n\n"
        "Профессиональная разработка ПО и консультации.\n\n"
        "✅ Более 100 проектов\n"
        "✅ 5 лет на рынке\n"
        "✅ Команда экспертов\n\n"
        "Свяжитесь с нами для консультации!",
        parse_mode="HTML"
    )


@router.message(F.text == "📞 Контакты")
async def contacts(message: types.Message):
    """Контакты."""
    await message.answer(
        "📞 <b>КОНТАКТЫ</b>\n\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "📧 Email: info@example.com\n"
        "🌐 Сайт: example.com\n\n"
        "🕐 Пн-Пт: 9:00–18:00\n"
        "Сб-Вс: выходной",
        parse_mode="HTML"
    )


# ============ ВОЗВРАТ В МЕНЮ ============

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery):
    """Возврат в админ-меню."""
    await callback.message.answer("Админ-меню:", reply_markup=admin_menu_keyboard())
    await callback.answer()
