"""
Inline клавиатуры для Telegram бота
"""

from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_auth_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для авторизации"""
    keyboard = [
        [InlineKeyboardButton(text="🔑 Авторизоваться в HH", callback_data="auth_start")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Основное меню"""
    keyboard = [
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ],
        [
            InlineKeyboardButton(text="🔍 Поиск вакансий", callback_data="search"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text="🤖 Запустить автоотклики", callback_data="auto_start"),
            InlineKeyboardButton(text="⏹️ Остановить автоотклики", callback_data="auto_stop")
        ],
        [
            InlineKeyboardButton(text="📈 Статус", callback_data="status"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_resume_selection_keyboard(resumes: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура выбора резюме"""
    keyboard = []

    for resume in resumes:
        resume_id = resume.get('id')
        title = resume.get('title', 'Без названия')
        status = resume.get('status', {}).get('name', '')

        # Ограничиваем длину названия
        if len(title) > 30:
            title = title[:27] + "..."

        button_text = f"📝 {title}"
        if status:
            button_text += f" ({status})"

        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"select_resume:{resume_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔍 Ключевые слова", callback_data="set_keywords"),
            InlineKeyboardButton(text="📍 Регион", callback_data="set_area")
        ],
        [
            InlineKeyboardButton(text="💰 Зарплата", callback_data="set_salary"),
            InlineKeyboardButton(text="⏰ Опыт работы", callback_data="set_experience")
        ],
        [
            InlineKeyboardButton(text="💼 Тип занятости", callback_data="set_employment"),
            InlineKeyboardButton(text="🕐 График работы", callback_data="set_schedule")
        ],
        [
            InlineKeyboardButton(text="🚫 Исключения", callback_data="set_exclusions"),
            InlineKeyboardButton(text="📝 Шаблон письма", callback_data="set_cover_letter")
        ],
        [
            InlineKeyboardButton(text="💾 Сохранить настройки", callback_data="save_settings"),
            InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_experience_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора опыта работы"""
    keyboard = [
        [InlineKeyboardButton(text="Без опыта", callback_data="exp:noExperience")],
        [InlineKeyboardButton(text="От 1 года до 3 лет", callback_data="exp:between1And3")],
        [InlineKeyboardButton(text="От 3 до 6 лет", callback_data="exp:between3And6")],
        [InlineKeyboardButton(text="Более 6 лет", callback_data="exp:moreThan6")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_employment_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа занятости"""
    keyboard = [
        [InlineKeyboardButton(text="Полная занятость", callback_data="emp:full")],
        [InlineKeyboardButton(text="Частичная занятость", callback_data="emp:part")],
        [InlineKeyboardButton(text="Проектная работа", callback_data="emp:project")],
        [InlineKeyboardButton(text="Стажировка", callback_data="emp:probation")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора графика работы"""
    keyboard = [
        [InlineKeyboardButton(text="Полный день", callback_data="sch:fullDay")],
        [InlineKeyboardButton(text="Сменный график", callback_data="sch:shift")],
        [InlineKeyboardButton(text="Гибкий график", callback_data="sch:flexible")],
        [InlineKeyboardButton(text="Удаленная работа", callback_data="sch:remote")],
        [InlineKeyboardButton(text="Вахтовый метод", callback_data="sch:flyInFlyOut")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_vacancy_action_keyboard(vacancy_id: str) -> InlineKeyboardMarkup:
    """Клавиатура действий с вакансией"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Откликнуться", callback_data=f"respond:{vacancy_id}"),
            InlineKeyboardButton(text="👁️ Подробнее", callback_data=f"details:{vacancy_id}")
        ],
        [
            InlineKeyboardButton(text="🚫 Пропустить", callback_data=f"skip:{vacancy_id}"),
            InlineKeyboardButton(text="⬅️ Назад к поиску", callback_data="back_to_search")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{item_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel:{action}:{item_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура статистики"""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 Общая статистика", callback_data="stats_general"),
            InlineKeyboardButton(text="📅 За сегодня", callback_data="stats_today")
        ],
        [
            InlineKeyboardButton(text="📈 За неделю", callback_data="stats_week"),
            InlineKeyboardButton(text="📆 За месяц", callback_data="stats_month")
        ],
        [
            InlineKeyboardButton(text="📝 История откликов", callback_data="response_history"),
            InlineKeyboardButton(text="📨 Приглашения", callback_data="invitations")
        ],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_auto_response_keyboard(is_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления автооткликами"""
    keyboard = []

    if is_active:
        keyboard.append([
            InlineKeyboardButton(text="⏹️ Остановить", callback_data="auto_stop"),
            InlineKeyboardButton(text="⏸️ Пауза", callback_data="auto_pause")
        ])
        keyboard.append([
            InlineKeyboardButton(text="📊 Статистика", callback_data="auto_stats"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="auto_settings")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="▶️ Запустить", callback_data="auto_start"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="auto_settings")
        ])

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_area_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора региона (популярные города)"""
    keyboard = [
        [
            InlineKeyboardButton(text="🏙️ Москва", callback_data="area:1"),
            InlineKeyboardButton(text="🏛️ Санкт-Петербург", callback_data="area:2")
        ],
        [
            InlineKeyboardButton(text="🏢 Новосибирск", callback_data="area:4"),
            InlineKeyboardButton(text="🏬 Екатеринбург", callback_data="area:3")
        ],
        [
            InlineKeyboardButton(text="🏘️ Нижний Новгород", callback_data="area:66"),
            InlineKeyboardButton(text="🌐 Удаленная работа", callback_data="area:remote")
        ],
        [
            InlineKeyboardButton(text="📝 Указать другой", callback_data="area_custom"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)