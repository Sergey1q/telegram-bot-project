"""Главный файл бота."""
import sys
import asyncio
import logging

# ============ ПАТЧ ДЛЯ PYTHON 3.13 + AIOGRAM 3.x ============
if sys.version_info >= (3, 13):
    import builtins
    import functools
    
    # Сохраняем оригинальный partial
    _original_callable = builtins.callable
    
    def _patched_callable(obj):
        """Усиленная проверка callable."""
        try:
            return _original_callable(obj)
        except TypeError:
            return False
    
    builtins.callable = _patched_callable
    
    # Патчим partial для безопасной работы
    _original_partial = functools.partial
    
    class SafePartial(functools.partial):
        def __new__(cls, func, /, *args, **keywords):
            if not callable(func):
                raise TypeError(
                    f"the first argument must be callable, got {type(func).__name__}"
                )
            return super().__new__(cls, func, *args, **keywords)
    
    functools.partial = SafePartial

# ============ ОСНОВНОЙ КОД ============
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.handlers import start, appointments, payments, admin, feedback, common

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск бота."""
    if not config.token or config.token == "ВАШ_ТОКЕН_БОТА":
        logger.error("❌ Не указан токен бота!")
        return
    
    bot = Bot(token=config.token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.include_router(start.router)
    dp.include_router(appointments.router)
    dp.include_router(payments.router)
    dp.include_router(admin.router)
    dp.include_router(feedback.router)
    dp.include_router(common.router)
    
    logger.info("=" * 50)
    logger.info("🤖 БОТ ЗАПУЩЕН")
    logger.info(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    logger.info("=" * 50)
    
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
