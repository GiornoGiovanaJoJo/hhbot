"""
Вспомогательные функции и утилиты
"""

import re
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger


def normalize_text(text: str) -> str:
    """Нормализация текста для анализа"""
    if not text:
        return ""

    # Убираем лишние пробелы и переводы строк
    normalized = re.sub(r'\s+', ' ', text.strip())

    # Убираем HTML теги если есть
    normalized = re.sub(r'<[^>]+>', '', normalized)

    return normalized


def extract_phone_numbers(text: str) -> List[str]:
    """Извлечение номеров телефонов из текста"""
    phone_pattern = r'[\+]?[1-9]?[\s\-\(\)]?[\d\s\-\(\)]{10,15}'
    phones = re.findall(phone_pattern, text)

    # Очищаем найденные номера
    clean_phones = []
    for phone in phones:
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        if len(clean_phone) >= 10:
            clean_phones.append(clean_phone)

    return clean_phones


def extract_emails(text: str) -> List[str]:
    """Извлечение email адресов из текста"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def generate_file_hash(file_path: Path) -> str:
    """Генерация хеша файла"""
    hash_md5 = hashlib.md5()

    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Ошибка генерации хеша для {file_path}: {e}")
        return ""


def format_currency(amount: Optional[int], currency: str = "RUR") -> str:
    """Форматирование валютных сумм"""
    if amount is None:
        return "не указана"

    # Форматируем с разделением тысяч
    formatted = f"{amount:,}".replace(",", " ")

    # Добавляем валюту
    currency_symbols = {
        "RUR": "₽",
        "USD": "$",
        "EUR": "€",
        "KZT": "₸",
        "UAH": "₴",
        "BYR": "Br"
    }

    symbol = currency_symbols.get(currency, currency)
    return f"{formatted} {symbol}"


def format_experience_years(years: float) -> str:
    """Форматирование опыта работы в годах"""
    if years == 0:
        return "без опыта"
    elif years < 1:
        months = int(years * 12)
        return f"{months} мес."
    elif years == 1:
        return "1 год"
    elif years < 5:
        return f"{years:.1f} года"
    else:
        return f"{years:.1f} лет"


def calculate_age(birth_date_str: str) -> Optional[int]:
    """Вычисление возраста по дате рождения"""
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
    except (ValueError, TypeError):
        return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезание текста до указанной длины"""
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def safe_get_nested(data: Dict[str, Any], keys: str, default: Any = None) -> Any:
    """Безопасное получение вложенных значений из словаря"""
    try:
        result = data
        for key in keys.split('.'):
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result
    except (KeyError, TypeError, AttributeError):
        return default


def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """Форматирование даты и времени"""
    if not dt:
        return "не указано"

    formats = {
        "full": "%d.%m.%Y %H:%M",
        "date": "%d.%m.%Y",
        "time": "%H:%M",
        "short": "%d.%m %H:%M"
    }

    return dt.strftime(formats.get(format_type, formats["full"]))


def parse_hh_date(date_str: str) -> Optional[datetime]:
    """Парсинг даты в формате HH API"""
    if not date_str:
        return None

    # Убираем timezone если есть
    clean_date = date_str.split('+')[0].split('T')

    try:
        if len(clean_date) == 2:
            # Дата и время
            return datetime.strptime(f"{clean_date[0]} {clean_date[1][:8]}", "%Y-%m-%d %H:%M:%S")
        else:
            # Только дата
            return datetime.strptime(clean_date[0], "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Не удалось распарсить дату: {date_str}")
        return None


def validate_url(url: str) -> bool:
    """Валидация URL"""
    url_pattern = re.compile(
        r'^https?://'  # http:// или https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # домен
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # порт
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return url_pattern.match(url) is not None


def clean_html_tags(text: str) -> str:
    """Очистка HTML тегов из текста"""
    if not text:
        return ""

    # Убираем HTML теги
    clean = re.sub(r'<[^>]+>', '', text)

    # Убираем HTML entities
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&quot;', '"')

    # Нормализуем пробелы
    clean = re.sub(r'\s+', ' ', clean).strip()

    return clean


def get_file_size_mb(file_path: Path) -> float:
    """Получение размера файла в мегабайтах"""
    try:
        size_bytes = file_path.stat().st_size
        return round(size_bytes / (1024 * 1024), 2)
    except Exception:
        return 0.0


def ensure_directory_exists(directory_path: Path) -> None:
    """Создание директории если она не существует"""
    try:
        directory_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Не удалось создать директорию {directory_path}: {e}")


def is_working_hours() -> bool:
    """Проверка рабочего времени (9:00 - 18:00 по МСК)"""
    now = datetime.now()
    return 9 <= now.hour < 18


def get_time_until_next_working_day() -> timedelta:
    """Время до начала следующего рабочего дня"""
    now = datetime.now()

    # Если сейчас рабочее время
    if is_working_hours() and now.weekday() < 5:
        return timedelta(0)

    # Ищем следующий рабочий день
    next_day = now + timedelta(days=1)
    next_day = next_day.replace(hour=9, minute=0, second=0, microsecond=0)

    # Если следующий день выходной, ищем понедельник
    while next_day.weekday() >= 5:  # Суббота (5) или воскресенье (6)
        next_day += timedelta(days=1)

    return next_day - now


def mask_sensitive_data(text: str, mask_char: str = "*") -> str:
    """Маскирование чувствительных данных в тексте"""
    if not text:
        return text

    # Маскируем email (оставляем первые 3 символа и домен)
    text = re.sub(
        r'([a-zA-Z0-9._%+-]{1,3})[a-zA-Z0-9._%+-]*(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'\1' + mask_char * 3 + r'\2',
        text
    )

    # Маскируем телефоны (оставляем последние 4 цифры)
    text = re.sub(
        r'(\+?[0-9\s\-\(\)]{7,})([0-9]{4})',
        lambda m: mask_char * (len(re.sub(r'[^\d]', '', m.group(1))) - 4) + m.group(2),
        text
    )

    return text