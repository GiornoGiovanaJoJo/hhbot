"""
Система логирования для Windows 10
"""

import sys
from pathlib import Path
from loguru import logger

from config import Config, WindowsConfig


def setup_logger() -> None:
    """Настройка логирования для Windows"""

    # Удаляем стандартный handler
    logger.remove()

    # Консольный вывод с цветами
    logger.add(
        sys.stdout,
        format=Config.LOG_FORMAT,
        level=Config.LOG_LEVEL,
        colorize=True,
        catch=True
    )

    # Файловое логирование
    log_file = Config.LOGS_DIR / "hh_bot.log"
    logger.add(
        log_file,
        format=Config.LOG_FORMAT,
        level=Config.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        catch=True
    )

    # Отдельный файл для ошибок
    error_log_file = Config.LOGS_DIR / "errors.log"
    logger.add(
        error_log_file,
        format=Config.LOG_FORMAT,
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        catch=True
    )

    # Windows Event Log (если включен)
    if Config.WINDOWS_EVENT_LOG_ENABLED and sys.platform == 'win32':
        try:
            import win32evtlog
            import win32evtlogutil

            # Настройка Windows Event Log
            logger.add(
                WindowsEventLogHandler(),
                format="{time} | {level} | {message}",
                level="WARNING",
                catch=True
            )
        except ImportError:
            logger.warning("pywin32 не найден, Windows Event Log отключен")

    logger.info(f"Логирование настроено: уровень {Config.LOG_LEVEL}")


class WindowsEventLogHandler:
    """Handler для записи в Windows Event Log"""

    def __init__(self):
        self.source = "HH_AutoBot"

    def write(self, message: str) -> None:
        """Запись сообщения в Event Log"""
        try:
            import win32evtlogutil
            win32evtlogutil.ReportEvent(
                self.source,
                1,  # Event ID
                strings=[message]
            )
        except Exception as e:
            # Не логируем ошибки Event Log чтобы избежать рекурсии
            pass


def get_logger(name: str):
    """Получение именованного логгера"""
    return logger.bind(name=name)


# Настройка при импорте
if not logger._core.handlers:
    setup_logger()