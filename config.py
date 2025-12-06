"""
Конфигурация приложения HH Bot для Windows 10 + Python 3.12
Поддерживает работу с переменными окружения и настройками по умолчанию.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from decouple import config

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Основная конфигурация приложения"""

    # Telegram Bot настройки
    TELEGRAM_BOT_TOKEN: str = config('TELEGRAM_BOT_TOKEN', default='')

    # HeadHunter API настройки
    HH_CLIENT_ID: str = config('HH_CLIENT_ID', default='')
    HH_CLIENT_SECRET: str = config('HH_CLIENT_SECRET', default='')
    HH_REDIRECT_URI: str = config('HH_REDIRECT_URI', default='http://localhost:8000/auth/callback')
    HH_API_BASE_URL: str = 'https://api.hh.ru'
    HH_OAUTH_BASE_URL: str = 'https://hh.ru/oauth'

    # Хранилище FSM состояния (Redis или Memory)
    FSM_STORAGE_TYPE: str = config('FSM_STORAGE_TYPE', default='memory')  # 'redis' или 'memory'
    REDIS_HOST: str = config('REDIS_HOST', default='localhost')
    REDIS_PORT: int = config('REDIS_PORT', default=6379, cast=int)
    REDIS_DB: int = config('REDIS_DB', default=0, cast=int)
    REDIS_PASSWORD: Optional[str] = config('REDIS_PASSWORD', default=None)

    # База данных
    DATABASE_URL: str = config('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/hh_bot.db')

    # Настройки логирования
    LOG_LEVEL: str = config('LOG_LEVEL', default='INFO')
    LOG_FILE: str = config('LOG_FILE', default=str(BASE_DIR / 'hh_bot.log'))
    LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    LOG_ROTATION: str = config('LOG_ROTATION', default='100 MB')
    LOG_RETENTION: str = config('LOG_RETENTION', default='10 days')

    # Настройки автоотклика
    MAX_RESPONSES_PER_DAY: int = config('MAX_RESPONSES_PER_DAY', default=200, cast=int)
    RESPONSE_DELAY_SECONDS: int = config('RESPONSE_DELAY_SECONDS', default=30, cast=int)
    AUTO_RESPONSE_ENABLED: bool = config('AUTO_RESPONSE_ENABLED', default=False, cast=bool)

    # Настройки поиска вакансий
    DEFAULT_SEARCH_PERIOD_DAYS: int = config('DEFAULT_SEARCH_PERIOD_DAYS', default=3, cast=int)
    MAX_VACANCIES_PER_SEARCH: int = config('MAX_VACANCIES_PER_SEARCH', default=100, cast=int)
    SEARCH_DELAY_SECONDS: int = config('SEARCH_DELAY_SECONDS', default=60, cast=int)

    # Настройки API клиента
    API_REQUEST_TIMEOUT: int = config('API_REQUEST_TIMEOUT', default=30, cast=int)
    API_RETRY_ATTEMPTS: int = config('API_RETRY_ATTEMPTS', default=3, cast=int)
    API_RETRY_DELAY_SECONDS: int = config('API_RETRY_DELAY_SECONDS', default=5, cast=int)

    # Windows-специфичные настройки
    WINDOWS_EVENT_LOG_ENABLED: bool = config('WINDOWS_EVENT_LOG_ENABLED', default=False, cast=bool)

    # Пути для Windows (используем pathlib для кроссплатформенности)
    DATA_DIR: Path = BASE_DIR / 'data'
    LOGS_DIR: Path = BASE_DIR / 'logs'
    TEMP_DIR: Path = BASE_DIR / 'temp'

    # Admin ID для отправки уведомлений
    ADMIN_CHAT_ID: Optional[int] = config('ADMIN_CHAT_ID', default=None, cast=lambda x: int(x) if x else None)

    @classmethod
    def setup_directories(cls) -> None:
        """Создает необходимые директории если их нет"""
        directories = [cls.DATA_DIR, cls.LOGS_DIR, cls.TEMP_DIR]
        for directory in directories:
            directory.mkdir(exist_ok=True, parents=True)

    @classmethod
    def validate_config(cls) -> list[str]:
        """Валидация конфигурации, возвращает список ошибок"""
        errors = []
        warnings = []

        # Критические проверки
        if not cls.TELEGRAM_BOT_TOKEN or cls.TELEGRAM_BOT_TOKEN == '':
            errors.append("🔢 TELEGRAM_BOT_TOKEN не задан")
        elif len(cls.TELEGRAM_BOT_TOKEN) < 30:
            warnings.append("⚠️ TELEGRAM_BOT_TOKEN может быть некорректнюя (топкен слишком короткий)")

        if not cls.HH_CLIENT_ID or cls.HH_CLIENT_ID == '':
            errors.append("🔢 HH_CLIENT_ID не задан")
        
        if not cls.HH_CLIENT_SECRET or cls.HH_CLIENT_SECRET == '':
            errors.append("🔢 HH_CLIENT_SECRET не задан")

        # Валидация URL
        try:
            parsed = urlparse(cls.HH_REDIRECT_URI)
            if not parsed.scheme or not parsed.netloc:
                errors.append(f"🔢 HH_REDIRECT_URI некорректный URL: {cls.HH_REDIRECT_URI}")
        except Exception as e:
            errors.append(f"🔢 HH_REDIRECT_URI невалидный: {e}")

        # Проверка Redis конфигурации если используется
        if cls.FSM_STORAGE_TYPE == 'redis':
            if cls.REDIS_PORT < 1 or cls.REDIS_PORT > 65535:
                errors.append(f"🔢 REDIS_PORT некорректный: {cls.REDIS_PORT} (должен быть 1-65535)")
            if cls.REDIS_DB < 0 or cls.REDIS_DB > 15:
                errors.append(f"🔢 REDIS_DB должен быть между 0 и 15: {cls.REDIS_DB}")
            if not cls.REDIS_HOST:
                errors.append("🔢 REDIS_HOST не задан")

        # Проверяем права на запись в директории
        try:
            test_file = cls.DATA_DIR / 'test_write.tmp'
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError) as e:
            errors.append(f"🔢 Нет прав на запись в {cls.DATA_DIR}: {e}")

        # Проверка числовых параметров
        if cls.MAX_RESPONSES_PER_DAY <= 0:
            errors.append(f"🔢 MAX_RESPONSES_PER_DAY должен быть > 0: {cls.MAX_RESPONSES_PER_DAY}")
        
        if cls.API_REQUEST_TIMEOUT <= 0:
            errors.append(f"🔢 API_REQUEST_TIMEOUT должен быть > 0: {cls.API_REQUEST_TIMEOUT}")

        if cls.API_RETRY_ATTEMPTS < 0:
            errors.append(f"🔢 API_RETRY_ATTEMPTS должен быть >= 0: {cls.API_RETRY_ATTEMPTS}")

        # Необязательные параметры
        if not cls.ADMIN_CHAT_ID:
            warnings.append("⚠️ ADMIN_CHAT_ID не настроен (админ-уведомления деактивированы)")

        # Выводим предупреждения
        if warnings:
            for warning in warnings:
                print(f"{warning}")

        return errors

    @classmethod
    def get_masked_secret(cls, secret: str, show_chars: int = 4) -> str:
        """Скрывает секрет для безопасного логирования"""
        if not secret or len(secret) <= show_chars * 2:
            return '***'
        return secret[:show_chars] + '*' * (len(secret) - show_chars * 2) + secret[-show_chars:]

class WindowsConfig:
    """Windows-специфичные настройки"""

    # Настройки asyncio для Windows
    USE_PROACTOR_EVENT_LOOP: bool = True

    # Настройки SSL для Windows
    SSL_VERIFY: bool = True
    SSL_CAFILE: Optional[str] = None  # Путь к CA файлу если нужно

    # Кодировка для Windows
    DEFAULT_ENCODING: str = 'utf-8'

    @staticmethod
    def setup_windows_asyncio():
        """Настройка asyncio для корректной работы на Windows"""
        if sys.platform == 'win32':
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

class Messages:
    """Сообщения бота на русском языке"""

    # Приветствие и помощь
    START_MESSAGE = """
👋 Привет! Я бот для автоматических откликов на вакансии HeadHunter.

Чтобы начать, нужно:
1. Авторизоваться в HeadHunter API
2. Настроить критерии поиска вакансий
3. Запустить автоматический поиск и отклики

Используйте /help для просмотра всех команд.
    """

    HELP_MESSAGE = """
🤖 Доступные команды:

/start - Запуск бота
/help - Помощь по командам
/auth - Авторизация в HeadHunter
/profile - Просмотр профиля и резюме
/settings - Настройки поиска вакансий
/search - Поиск подходящих вакансий
/auto_start - Запустить автоотклики
/auto_stop - Остановить автоотклики
/status - Статус работы бота
/stats - Статистика откликов

📊 Статистика и мониторинг:
/today - Статистика за сегодня
/history - История откликов
    """

    # Авторизация
    AUTH_REQUIRED = "❌ Для использования этой функции необходима авторизация в HeadHunter."
    AUTH_SUCCESS = "✅ Успешная авторизация в HeadHunter!"
    AUTH_ERROR = "❌ Ошибка авторизации. Попробуйте еще раз."

    # Автоотклики
    AUTO_STARTED = "🚀 Автоматические отклики запущены!"
    AUTO_STOPPED = "⏹️ Автоматические отклики остановлены."
    AUTO_ALREADY_RUNNING = "ℹ️ Автоотклики уже запущены."
    AUTO_NOT_RUNNING = "ℹ️ Автоотклики не запущены."

    # Лимиты
    DAILY_LIMIT_REACHED = "⚠️ Достигнут дневной лимит откликов (200). Попробуйте завтра."

    # Ошибки
    ERROR_OCCURRED = "❌ Произошла ошибка: {error}"
    CONFIG_ERROR = "❌ Ошибка конфигурации: {errors}"

    # Успех
    VACANCY_FOUND = "✅ Найдено {count} подходящих вакансий"
    RESPONSE_SENT = "✅ Отклик на вакансию '{title}' отправлен"

# Инициализация конфигурации при импорте
config_instance = Config()
windows_config = WindowsConfig()

# Создаем директории при импорте
config_instance.setup_directories()

# Настраиваем Windows asyncio
windows_config.setup_windows_asyncio()
