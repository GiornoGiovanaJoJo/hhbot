"""
FSM состояния для Telegram бота
"""

from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    """Состояния процесса авторизации"""
    waiting_callback_url = State()


class SettingsStates(StatesGroup):
    """Состояния настройки критериев поиска"""
    waiting_keywords = State()
    waiting_area = State()
    waiting_salary = State()
    waiting_experience = State()
    waiting_employment = State()
    waiting_schedule = State()
    waiting_exclude_companies = State()
    waiting_exclude_keywords = State()
    waiting_cover_letter_template = State()


class SearchStates(StatesGroup):
    """Состояния поиска вакансий"""
    searching = State()
    showing_results = State()
    confirming_response = State()


class ResumeStates(StatesGroup):
    """Состояния работы с резюме"""
    selecting_resume = State()
    waiting_resume_title = State()  # Добавьте эту строку
    editing_resume = State()


class AutoResponseStates(StatesGroup):
    """Состояния автоматических откликов"""
    configuring = State()
    running = State()
    paused = State()