"""Универсальные обработчики (подключаются ПОСЛЕДНИМИ)."""
from aiogram import Router, types

router = Router()


@router.callback_query()
async def any_callback(callback: types.CallbackQuery):
    """Любой необработанный callback — просто закрываем."""
    await callback.answer()


@router.message()
async def any_message(message: types.Message):
    """Любое необработанное сообщение."""
    await message.answer(
        "👇 Используйте кнопки меню:\n"
        "Если меню скрылось — нажмите /start"
    )
