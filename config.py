"""
Конфигурация приложения HH Bot для Windows 10 + Python 3.12
Поддерживает работу с переменными окружения и настройками по умолчанию.
"""

import os
import sys
from pathlib import Path
from typing import Optional

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

    # База данных
    DATABASE_URL: str = config('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/hh_bot.db')

    # Настройки логирования
    LOG_LEVEL: str = config('LOG_LEVEL', default='INFO')
    LOG_FILE: str = config('LOG_FILE', default=str(BASE_DIR / 'hh_bot.log'))
    LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"

    # Настройки автоотклика
    MAX_RESPONSES_PER_DAY: int = config('MAX_RESPONSES_PER_DAY', default=200, cast=int)
    RESPONSE_DELAY_SECONDS: int = config('RESPONSE_DELAY_SECONDS', default=30, cast=int)
    AUTO_RESPONSE_ENABLED: bool = config('AUTO_RESPONSE_ENABLED', default=False, cast=bool)

    # Настройки поиска вакансий
    DEFAULT_SEARCH_PERIOD_DAYS: int = config('DEFAULT_SEARCH_PERIOD_DAYS', default=3, cast=int)
    MAX_VACANCIES_PER_SEARCH: int = config('MAX_VACANCIES_PER_SEARCH', default=100, cast=int)
    SEARCH_DELAY_SECONDS: int = config('SEARCH_DELAY_SECONDS', default=60, cast=int)

    # Windows-специфичные настройки
    WINDOWS_EVENT_LOG_ENABLED: bool = config('WINDOWS_EVENT_LOG_ENABLED', default=False, cast=bool)

    # Пути для Windows (используем pathlib для кроссплатформенности)
    DATA_DIR: Path = BASE_DIR / 'data'
    LOGS_DIR: Path = BASE_DIR / 'logs'
    TEMP_DIR: Path = BASE_DIR / 'temp'

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

        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN не задан")

        if not cls.HH_CLIENT_ID:
            errors.append("HH_CLIENT_ID не задан")

        if not cls.HH_CLIENT_SECRET:
            errors.append("HH_CLIENT_SECRET не задан")

        # Проверяем права на запись в директории
        try:
            test_file = cls.DATA_DIR / 'test_write.tmp'
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError):
            errors.append(f"Нет прав на запись в директорию {cls.DATA_DIR}")

        return errors

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
            # Используем ProactorEventLoop для Windows
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