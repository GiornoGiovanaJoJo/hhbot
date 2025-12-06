"""
Основной файл запуска HH Bot
Инициализация бота, настройка middleware, обработчиков и запуск.
Оптимизировано для Windows 10 + Python 3.12
"""

import asyncio
import sys
import signal
import os
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramError
from loguru import logger

from config import Config, WindowsConfig, Messages
from database.repository import DatabaseRepository
from bot.handlers import main as main_handlers, settings as settings_handlers
from bot.middlewares.auth import AuthMiddleware
from utils.logger import setup_logger
from utils.scheduler import task_scheduler
from hh_api.client import HHApiClient

# Глобальные переменные для управления жизненным циклом
_shutdown_event: Optional[asyncio.Event] = None
bot_instance: Optional[Bot] = None
dp_instance: Optional[Dispatcher] = None

async def create_bot() -> tuple[Bot, Dispatcher]:
    """Создание и настройка бота"""

    # Проверка конфигурации
    config_errors = Config.validate_config()
    if config_errors:
        logger.error(f"Ошибки конфигурации: {', '.join(config_errors)}")
        raise ValueError(f"Некорректная конфигурация: {', '.join(config_errors)}")

    # Инициализация бота с новым синтаксисом aiogram 3.7+
    bot_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN, default=bot_properties)

    # Инициализация хранилища FSM в зависимости от конфигурации
    if Config.FSM_STORAGE_TYPE == 'redis':
        try:
            from redis.asyncio import Redis
            from aiogram.fsm.storage.redis import RedisStorage
            
            redis = Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                password=Config.REDIS_PASSWORD,
                decode_responses=True
            )
            storage = RedisStorage(redis=redis)
            logger.info("🔴 Redis хранилище инициализировано")
        except ImportError:
            logger.warning("⚠️ Redis модуль не установлен, использую вместо Memory")
            from aiogram.fsm.storage.memory import MemoryStorage
            storage = MemoryStorage()
    else:
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
        logger.warning("⚠️ Используется MemoryStorage - состояния будут потеряны при перезагрузке!")

    dp = Dispatcher(storage=storage)

    # Подключение middleware
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Регистрация обработчиков
    dp.include_router(main_handlers.router)
    dp.include_router(settings_handlers.router)

    logger.info("🤖 Бот инициализирован успешно")
    return bot, dp


async def initialize_database() -> None:
    """Инициализация базы данных"""
    try:
        db = DatabaseRepository()
        await db.init_database()
        logger.info("📄 База данных инициализирована")

        try:
            import aiosqlite
            async with aiosqlite.connect(db.db_path) as conn:
                cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = await cursor.fetchall()
                logger.info(f"📊 Найдено таблиц в БД: {len(tables)}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось проверить таблицы БД: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise


async def initialize_hh_client() -> None:
    """Инициализация HH API клиента"""
    try:
        hh_client = HHApiClient()
        logger.info("🔗 HH API клиент инициализирован")

        if not Config.HH_CLIENT_ID or not Config.HH_CLIENT_SECRET:
            logger.warning("⚠️ HH API не настроен полностью")
        else:
            logger.info("✅ HH API конфигурация корректна")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации HH API: {e}")
        raise

async def start_scheduler() -> None:
    """Запуск планировщика задач"""
    try:
        await task_scheduler.start()
        active_count = task_scheduler.get_active_users_count()
        logger.info(f"⏰ Планировщик задач запущен")
        logger.info(f"὆5 Активных пользователей для автооткликов: {active_count}")

        if active_count > 0:
            logger.info("🔄 Автоматические отклики активированы")
        else:
            logger.info("🔄 Автоматические отклики в режиме ожидания")

    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")
        raise

async def send_startup_notification(bot: Bot) -> None:
    """Отправка уведомления о запуске"""
    try:
        bot_info = await bot.get_me()
        logger.info(f"🤖 Бот @{bot_info.username} готов к работе!")

        if hasattr(Config, 'ADMIN_CHAT_ID') and Config.ADMIN_CHAT_ID:
            try:
                active_count = task_scheduler.get_active_users_count()
                startup_message = (
                    f"🟢 <b>HH Bot запущен!</b>\n\n"
                    f"🤖 Бот: @{bot_info.username}\n"
                    f"👤 ID бота: <code>{bot_info.id}</code>\n"
                    f"👥 Активных пользователей: {active_count}\n"
                    f"⏰ Планировщик: работает\n"
                    f"🐍 Python: {sys.version.split()[0]}\n"
                    f"🖥️ Платформа: {sys.platform}"
                )

                await bot.send_message(
                    chat_id=Config.ADMIN_CHAT_ID,
                    text=startup_message
                )
                logger.info("📨 Уведомление админу отправлено")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить уведомление админу: {e}")

    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о боте: {e}")

async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота"""
    try:
        logger.info("🚀 Выполняем процедуры запуска...")

        await initialize_database()
        await initialize_hh_client()
        await start_scheduler()
        await send_startup_notification(bot)

        logger.info("✅ Все системы запущены успешно!")

    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске: {e}")
        raise

async def send_shutdown_notification(bot: Bot) -> None:
    """Отправка уведомления об остановке"""
    try:
        if hasattr(Config, 'ADMIN_CHAT_ID') and Config.ADMIN_CHAT_ID:
            try:
                shutdown_message = (
                    f"🔴 <b>HH Bot остановлен</b>\n\n"
                    f"⏹️ Планировщик: остановлен\n"
                    f"📱 Автоотклики: приостановлены"
                )

                await bot.send_message(
                    chat_id=Config.ADMIN_CHAT_ID,
                    text=shutdown_message
                )
                logger.info("📨 Уведомление об остановке отправлено")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить уведомление об остановке: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления об остановке: {e}")

async def cleanup_scheduler() -> None:
    """Очистка планировщика"""
    try:
        logger.info("⏰ Останавливаем планировщик...")
        await task_scheduler.shutdown()
        logger.info("✅ Планировщик остановлен корректно")
    except Exception as e:
        logger.error(f"❌ Ошибка остановки планировщика: {e}")

async def cleanup_bot_session(bot: Bot) -> None:
    """Очистка сессии бота"""
    try:
        logger.info("🔌 Закрываем сессию бота...")
        await bot.session.close()
        logger.info("✅ Сессия бота закрыта")
    except Exception as e:
        logger.error(f"❌ Ошибка закрытия сессии бота: {e}")

async def on_shutdown(bot: Bot) -> None:
    """действия при остановке бота"""
    try:
        logger.info("🛑 Начинаем корректное завершение...")

        await send_shutdown_notification(bot)
        await cleanup_scheduler()
        await cleanup_bot_session(bot)

        logger.info("✅ Все системы остановлены корректно")

    except Exception as e:
        logger.error(f"💥 Ошибка при остановке: {e}")
    finally:
        logger.info("🔴 Процедура завершения завершена")

def setup_signal_handlers(shutdown_event: asyncio.Event) -> None:
    """Настройка обработчиков сигналов для корректного завершения"""
    def signal_handler(signum, frame):
        logger.info(f"🛑 Получен сигнал {signum}, начинаем корректное завершение...")
        shutdown_event.set()

    if sys.platform != 'win32':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def main() -> None:
    """Основная функция запуска с retry-логикой"""
    global bot_instance, dp_instance, _shutdown_event

    try:
        setup_logger()
        logger.info("📝 Логирование настроено")

        _shutdown_event = asyncio.Event()
        setup_signal_handlers(_shutdown_event)

        logger.info("⚙️ Создаем экземпляры бота и диспетчера...")
        bot, dp = await create_bot()
        bot_instance, dp_instance = bot, dp

        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        logger.info("📡 Запускаем polling с retry-логикой...")
        logger.info("🎯 Бот готов принимать сообщения!")

        retry_count = 0
        max_retries = 5
        retry_delay = 5

        while True:
            try:
                await dp.start_polling(bot, skip_updates=True)
            except TelegramError as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.critical(f"💀 Не удалось переподключиться после {max_retries} попыток")
                    raise
                
                logger.error(f"❌ Ошибка Telegram API (попытка {retry_count}/{max_retries}): {e}")
                logger.info(f"⏳ Ожидание {retry_delay:.1f} секунд...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 60)
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.critical(f"💀 Непредвиденная ошибка: {e}")
                    raise
                
                logger.error(f"❌ Ошибка (попытка {retry_count}/{max_retries}): {e}")
                logger.info(f"⏳ Ожидание {retry_delay:.1f} секунд...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 60)

    except KeyboardInterrupt:
        logger.info("⚠️ Получен сигнал прерывания (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise
    finally:
        logger.info("🏁 Завершение основной функции...")

def run_bot() -> None:
    """Точка входа для запуска бота"""

    if sys.platform == 'win32':
        logger.info("🖥️ Применяем оптимизации для Windows...")

        WindowsConfig.setup_windows_asyncio()

        if sys.version_info >= (3, 8):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            logger.info("🔧 Установлена WindowsProactorEventLoopPolicy")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("🔄 Event loop создан и установлен")

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Получено прерывание от пользователя")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка выполнения: {e}")
        raise
    finally:
        logger.info("🧹 Очистка event loop...")
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.info(f"⏳ Отменяем {len(pending)} оставшихся задач...")
                for task in pending:
                    task.cancel()

                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            loop.close()
            logger.info("✅ Event loop закрыт корректно")
        except Exception as e:
            logger.error(f"💥 Ошибка при закрытии event loop: {e}")

def check_environment() -> bool:
    """Проверка переменных окружения"""
    errors = []
    warnings = []

    if not Config.TELEGRAM_BOT_TOKEN:
        errors.append("❌ TELEGRAM_BOT_TOKEN не задан!")

    if not Config.HH_CLIENT_ID:
        errors.append("❌ HH_CLIENT_ID не задан!")

    if not Config.HH_CLIENT_SECRET:
        errors.append("❌ HH_CLIENT_SECRET не задан!")

    if not hasattr(Config, 'ADMIN_CHAT_ID') or not Config.ADMIN_CHAT_ID:
        warnings.append("⚠️ ADMIN_CHAT_ID не настроен")

    if warnings:
        print("Предупреждения:")
        print("\n".join(warnings))
        print()

    if errors:
        print("Критические ошибки:")
        print("\n".join(errors))
        print("💡 Создайте файл .env на основе .env.example")
        print("💡 Виныте новые ключи острежения на https://dev.hh.ru")
        return False

    print("✅ Проверка окружения пройдена")
    return True

def print_startup_info() -> None:
    """Вывод информации о запуске"""
    print("🤖 HH Bot v1.0 - Автоматические отклики на вакансии HeadHunter")
    print("=" * 80)
    print(f"🖥️  Платформа: {sys.platform}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Рабочая директория: {Path.cwd()}")
    print(f"🔧 Event Loop Policy: {asyncio.get_event_loop_policy().__class__.__name__}")
    print(f"📆 Aiogram: 3.7+")
    print(f"⚙️  Оптимизация: Redis" if Config.FSM_STORAGE_TYPE == 'redis' else f"⚙️  Оптимизация: Memory (WARNING)")
    print("=" * 80)
    print("🚀 Подготовка к запуску...")
    print()


if __name__ == "__main__":
    print_startup_info()

    if not check_environment():
        sys.exit(1)

    try:
        logger.info("🎐 Инициализация HH Bot...")
        run_bot()
    except KeyboardInterrupt:
        logger.info("⚠️ Начали работу прервана")
        print("\n👋 До свидания!")
    except Exception as e:
        logger.critical(f"💠 Фатальная ошибка: {e}")
        print(f"\n💠 Критическая ошибка: {e}")
        print("📁 Посмотрите логи для получения подробной информации")
        sys.exit(1)
    finally:
        print("\n🏁 Программа завершена")
