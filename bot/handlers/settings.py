"""
Обработчики настроек и конфигурации бота
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import Messages
from bot.keyboards.inline import (
    get_settings_keyboard, get_experience_keyboard,
    get_employment_keyboard, get_schedule_keyboard, get_area_selection_keyboard
)
from bot.states.states import SettingsStates
from database.repository import db_repository
from hh_api.auth import auth_manager

router = Router()


@router.message(Command("settings"))
async def settings_handler(message: Message, state: FSMContext) -> None:
    """Обработчик команды /settings — показывает и меняет настройки поиска"""

    user_id = message.from_user.id

    # 1) Попробовать получить текущие настройки
    current = await db_repository.get_user_settings(user_id)
    # Формируем HTML-текст текущих настроек
    if current:
        html = (
            "<b>⚙️ Ваши текущие настройки поиска:</b>\n\n"
            f"• <b>Ключевые слова:</b> {current.get('keywords', '—')}\n"
            f"• <b>Регион:</b> {current.get('area_name', '—')} (ID={current.get('area_id', '—')})\n"
            f"• <b>Зарплата:</b> {current.get('min_salary', '—')}–{current.get('max_salary', '—')} {current.get('currency', '')}\n"
            f"• <b>Опыт:</b> {current.get('experience', '—')}\n"
            f"• <b>Тип занятости:</b> {current.get('employment_type', '—')}\n"
            f"• <b>График:</b> {current.get('schedule', '—')}\n"
            f"• <b>Исключить компании:</b> {current.get('exclude_companies', '—')}\n"
            f"• <b>Исключить слова:</b> {current.get('exclude_keywords', '—')}\n"
            f"• <b>Мин. соответствие:</b> {current.get('min_match_score', 60)}%\n"
            f"• <b>Шаблон письма:</b> {current.get('cover_letter_template', '—')}\n\n"
            "Чтобы изменить настройки, введите новые значения по очереди."
        )
    else:
        html = "<b>⚙️ У вас ещё нет сохранённых настроек.</b>\nНачнём настройку."

    # Отправляем HTML-сообщение
    await message.answer(html, parse_mode="HTML")

    # 2) Запускаем FSM-диалог
    await state.clear()
    await state.set_state(SettingsStates.waiting_keywords)
    await message.answer("Введите ключевые слова для поиска вакансий:")
    logger.info(f"Начало настройки поиска для user={user_id}")



@router.callback_query(F.data == "settings")
async def settings_callback(callback: CallbackQuery) -> None:
    """Callback для показа настроек"""
    await settings_handler(callback.message)
    await callback.answer()


@router.callback_query(F.data == "set_keywords")
async def set_keywords_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Настройка ключевых слов"""

    await callback.message.answer(
        "🔍 **Настройка ключевых слов**\n\n"
        "Введите ключевые слова и навыки через запятую.\n"
        "Например: Python, Django, REST API, PostgreSQL, Git\n\n"
        "Эти слова будут использоваться для поиска подходящих вакансий."
    )

    await state.set_state(SettingsStates.waiting_keywords)
    await callback.answer()


@router.message(SettingsStates.waiting_keywords)
async def process_keywords(message: Message, state: FSMContext) -> None:
    """Обработка ввода ключевых слов"""

    keywords = message.text.strip()
    user_id = message.from_user.id

    # FIX: НЕ очищаем состояние, чтобы сохранить данные для сохранения
    # просто обновляем новое значение
    await state.update_data(keywords=keywords)

    await message.answer(
        f"✅ Ключевые слова сохранены: {keywords}\n\n"
        "Теперь настройте другие параметры или сохраните настройки.",
        reply_markup=get_settings_keyboard()
    )

    # НЕ вызываем await state.clear() - состояние остаётся!


@router.callback_query(F.data == "set_area")
async def set_area_callback(callback: CallbackQuery) -> None:
    """Настройка региона"""

    keyboard = get_area_selection_keyboard()
    await callback.message.answer(
        "📍 **Выберите регион работы:**",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("area:"))
async def process_area_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора региона"""

    area_data = callback.data.split(":")
    area_id = area_data[1]

    area_names = {
        "1": "Москва",
        "2": "Санкт-Петербург",
        "3": "Екатеринбург",
        "4": "Новосибирск",
        "66": "Нижний Новгород",
        "remote": "Удаленная работа"
    }

    area_name = area_names.get(area_id, "Другой регион")

    # FIX: обновляем данные БЕЗ clear()
    await state.update_data(area_id=area_id, area_name=area_name)

    await callback.message.answer(
        f"✅ Регион установлен: {area_name}",
        reply_markup=get_settings_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "area_custom")
async def set_custom_area(callback: CallbackQuery, state: FSMContext) -> None:
    """Ввод кастомного региона"""

    await callback.message.answer(
        "📍 Введите название города или региона:\n"
        "Например: Казань, Ростов-на-Дону, Краснодар"
    )

    await state.set_state(SettingsStates.waiting_area)
    await callback.answer()


@router.message(SettingsStates.waiting_area)
async def process_custom_area(message: Message, state: FSMContext) -> None:
    """Обработка кастомного региона"""

    area_name = message.text.strip()

    # В реальном приложении здесь был бы поиск по HH API справочнику регионов
    # FIX: обновляем данные БЕЗ clear()
    await state.update_data(area_name=area_name, area_id=None)

    await message.answer(
        f"✅ Регион установлен: {area_name}\n\n"
        "💡 При поиске вакансий бот попытается найти соответствующий регион в базе HH.",
        reply_markup=get_settings_keyboard()
    )

    # НЕ очищаем состояние!


@router.callback_query(F.data == "set_salary")
async def set_salary_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Настройка зарплаты"""

    await callback.message.answer(
        "💰 **Настройка зарплатных ожиданий**\n\n"
        "Введите минимальную желаемую зарплату в рублях.\n"
        "Например: 100000\n\n"
        "Вакансии с зарплатой ниже этой суммы будут исключены из поиска."
    )

    await state.set_state(SettingsStates.waiting_salary)
    await callback.answer()


@router.message(SettingsStates.waiting_salary)
async def process_salary(message: Message, state: FSMContext) -> None:
    """Обработка ввода зарплаты"""

    try:
        salary = int(message.text.strip())

        if salary < 0:
            await message.answer("❌ Зарплата не может быть отрицательной. Попробуйте еще раз.")
            return

        # FIX: обновляем данные БЕЗ clear()
        await state.update_data(min_salary=salary)

        await message.answer(
            f"✅ Минимальная зарплата установлена: {salary:,} руб.",
            reply_markup=get_settings_keyboard()
        )

        # НЕ очищаем состояние!

    except ValueError:
        await message.answer(
            "❌ Неправильный формат. Введите число.\n"
            "Например: 100000"
        )


@router.callback_query(F.data == "set_experience")
async def set_experience_callback(callback: CallbackQuery) -> None:
    """Настройка опыта работы"""

    keyboard = get_experience_keyboard()
    await callback.message.answer(
        "⏰ **Выберите ваш уровень опыта:**",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exp:"))
async def process_experience(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора опыта"""

    exp_id = callback.data.split(":")[1]

    exp_names = {
        "noExperience": "Без опыта",
        "between1And3": "От 1 года до 3 лет",
        "between3And6": "От 3 до 6 лет",
        "moreThan6": "Более 6 лет"
    }

    exp_name = exp_names.get(exp_id, exp_id)

    # FIX: обновляем данные БЕЗ clear()
    await state.update_data(experience=exp_id)

    await callback.message.answer(
        f"✅ Опыт работы установлен: {exp_name}",
        reply_markup=get_settings_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "set_employment")
async def set_employment_callback(callback: CallbackQuery) -> None:
    """Настройка типа занятости"""

    keyboard = get_employment_keyboard()
    await callback.message.answer(
        "💼 **Выберите тип занятости:**",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("emp:"))
async def process_employment(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка типа занятости"""

    emp_id = callback.data.split(":")[1]

    emp_names = {
        "full": "Полная занятость",
        "part": "Частичная занятость",
        "project": "Проектная работа",
        "probation": "Стажировка"
    }

    emp_name = emp_names.get(emp_id, emp_id)

    # FIX: обновляем данные БЕЗ clear()
    await state.update_data(employment_type=emp_id)

    await callback.message.answer(
        f"✅ Тип занятости установлен: {emp_name}",
        reply_markup=get_settings_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "set_schedule")
async def set_schedule_callback(callback: CallbackQuery) -> None:
    """Настройка графика работы"""

    keyboard = get_schedule_keyboard()
    await callback.message.answer(
        "🕐 **Выберите график работы:**",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sch:"))
async def process_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка графика работы"""

    sch_id = callback.data.split(":")[1]

    sch_names = {
        "fullDay": "Полный день",
        "shift": "Сменный график",
        "flexible": "Гибкий график",
        "remote": "Удаленная работа",
        "flyInFlyOut": "Вахтовый метод"
    }

    sch_name = sch_names.get(sch_id, sch_id)

    # FIX: обновляем данные БЕЗ clear()
    await state.update_data(schedule=sch_id)

    await callback.message.answer(
        f"✅ График работы установлен: {sch_name}",
        reply_markup=get_settings_keyboard()
    )

    await callback.answer()


@router.callback_query(F.data == "set_exclusions")
async def set_exclusions_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Настройка исключений"""

    await callback.message.answer(
        "🚫 **Настройка исключений**\n\n"
        "Введите через запятую компании или ключевые слова, которые нужно исключить из поиска.\n"
        "Например: Газпром, МТС, аутсорс, фриланс\n\n"
        "Вакансии с этими словами в названии или описании будут пропущены."
    )

    await state.set_state(SettingsStates.waiting_exclude_keywords)
    await callback.answer()


@router.message(SettingsStates.waiting_exclude_keywords)
async def process_exclusions(message: Message, state: FSMContext) -> None:
    """Обработка исключений"""

    exclusions = message.text.strip()

    # FIX: обновляем данные БЕЗ clear()
    await state.update_data(exclude_keywords=exclusions)

    await message.answer(
        f"✅ Исключения установлены: {exclusions}",
        reply_markup=get_settings_keyboard()
    )

    # НЕ очищаем состояние!


@router.callback_query(F.data == "set_cover_letter")
async def set_cover_letter_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Настройка шаблона сопроводительного письма"""

    await callback.message.answer(
        "📝 **Шаблон сопроводительного письма**\n\n"
        "Введите шаблон письма для откликов. Вы можете использовать переменные:\n"
        "- {vacancy_name} - название вакансии\n"
        "- {company_name} - название компании\n"
        "- {my_skills} - ваши навыки\n\n"
        "Пример:\n"
        "Здравствуйте! Меня заинтересовала позиция {vacancy_name} в компании {company_name}. "
        "Мой опыт включает: {my_skills}. Готов обсудить детали сотрудничества."
    )

    await state.set_state(SettingsStates.waiting_cover_letter_template)
    await callback.answer()


@router.message(SettingsStates.waiting_cover_letter_template)
async def process_cover_letter(message: Message, state: FSMContext) -> None:
    """Обработка шаблона письма"""

    template = message.text.strip()

    # FIX: обновляем данные БЕЗ clear()
    await state.update_data(cover_letter_template=template)

    await message.answer(
        "✅ Шаблон сопроводительного письма сохранен",
        reply_markup=get_settings_keyboard()
    )

    # НЕ очищаем состояние!


@router.callback_query(F.data == "save_settings")
async def save_settings_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохранение всех настроек"""

    user_id = callback.from_user.id
    data = await state.get_data()  # Получаем все накопленные данные
    await callback.answer()

    logger.info(f"🔍 Попытка сохранения настроек для user={user_id}")
    logger.info(f"📦 Данные в состоянии: {data}")

    # FIX: Оставляем в data только ключи с непустыми значениями
    filtered = {k: v for k, v in data.items() if v is not None and v != ""}

    logger.info(f"✅ Отфильтрованные данные: {filtered}")

    if not filtered:
        # Если пользователь не ввёл ни одного нового значения — просим его заполнить
        logger.warning(f"⚠️ Нет новых данных для сохранения у user={user_id}")
        await callback.message.answer(
            "❌ Нет данных для сохранения. Сначала введите хотя бы одно новое значение через кнопки или ответы."
        )
        return

    try:
        # Берём старые настройки (или пустой словарь)
        current = await db_repository.get_user_settings(user_id) or {}
        logger.info(f"📖 Текущие настройки в БД: {current}")

        # Обновляем только те поля, которые пользователь ввёл
        updated = {**current, **filtered}
        logger.info(f"🔄 Объединённые настройки: {updated}")

        # Сохраняем в БД
        await db_repository.save_user_settings(user_id, updated)
        logger.info(f"✅ Настройки сохранены для user={user_id}")

        # Лог и ответ пользователю
        saved = await db_repository.get_user_settings(user_id)
        logger.info(f"📝 Верификация: Сохранённые настройки в БД: {saved}")

        await callback.message.answer(
            "<b>✅ Настройки сохранены успешно!</b>\n\n"
            "Теперь вы можете:\n"
            "• Выполнить поиск вакансий (/search)\n"
            "• Запустить автоматические отклики (/auto_start)",
            parse_mode="HTML"
        )

        # ТОЛЬКО ТЕПЕРЬ очищаем состояние (после сохранения)
        await state.clear()

    except Exception as e:
        logger.error(f"❌ Ошибка сохранения настроек для user={user_id}: {e}")
        await callback.message.answer(
            f"❌ Ошибка при сохранении настроек: {e}"
        )