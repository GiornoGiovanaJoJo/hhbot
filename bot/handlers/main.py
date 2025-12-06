"""
Основные обработчики команд Telegram бота
"""

import asyncio
from typing import Optional, Union

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger

from config import Messages, Config
from hh_api.auth import auth_manager
from hh_api.client import hh_client
from matching.analyzer import matcher
from database.repository import db_repository
from bot.keyboards.inline import (
    get_auth_keyboard,
    get_main_menu_keyboard
)
from bot.states.states import AuthStates, SettingsStates, ResumeStates
from utils.scheduler import (
    task_scheduler,
    start_continuous_auto_responses,
    stop_continuous_auto_responses,
    is_continuous_running
)

router = Router()


@router.message(ResumeStates.waiting_resume_title)
async def process_resume_selection(message: Message, state: FSMContext) -> None:
    """Обработка ввода названия резюме"""
    user_input = message.text.strip()
    user_id = message.from_user.id

    data = await state.get_data()
    available = data.get('available_resumes', [])
    if not available:
        await message.answer("❌ Список резюме не найден. Попробуйте /profile.")
        await state.clear()
        return

    # Логирование
    logger.info(f"Ввод резюме: '{user_input}'")
    for i, r in enumerate(available):
        logger.info(f"{i}: {r.get('title')} (ID={r.get('id')})")

    selected = next(
        (r for r in available if r.get('title','').strip().lower()==user_input.lower()),
        None
    )
    if not selected:
        titles = "\n".join(f"{i+1}. '{r.get('title')}'" for i,r in enumerate(available))
        await message.answer(
            f"❌ Не найдено '{user_input}'.\n\n📝 Варианты:\n{titles}\n\n"
            "Введите точное название:"
        )
        return

    resume_id = str(selected['id'])
    logger.info(f"Установка активного резюме user={user_id} id={resume_id}")
    ok = await db_repository.set_active_resume(user_id, resume_id)
    if ok:
        await message.answer(
            f"✅ Резюме '{selected['title']}' установлено активным!",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Резюме {resume_id} активировано для {user_id}")
    else:
        await message.answer("❌ Не удалось активировать. Повторите ввод.")
        logger.error(f"set_active_resume=False for user={user_id} id={resume_id}")

    await state.clear()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    """/start"""
    await state.clear()
    uid = message.from_user.id
    await db_repository.create_or_update_user(
        telegram_id=uid,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    welcome_text = (
        f"👋 Добро пожаловать, {message.from_user.first_name}!\n\n"
        f"🤖 Я HH Bot - помощник для автоматических откликов на вакансии HeadHunter.\n\n"
        f"🚀 Что я умею:\n"
        f"• 🔍 Автоматический поиск подходящих вакансий\n"
        f"• 📤 Отправка откликов по вашим критериям\n"
        f"• 📊 Аналитика и статистика откликов\n"
        f"• ⚙️ Гибкие настройки поиска\n\n"
        f"📱 Используйте /help для списка команд"
    )

    if await auth_manager.is_authenticated():
        await message.answer("🎉 С возвращением!", reply_markup=get_main_menu_keyboard())
    else:
        await message.answer(welcome_text, reply_markup=get_auth_keyboard())
    logger.info(f"Start by user={uid}")


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """/help"""
    help_text = (
        "📚 <b>Доступные команды:</b>\n\n"
        "🔐 <b>Авторизация:</b>\n"
        "• /auth - Авторизация в HeadHunter\n"
        "• /profile - Просмотр профиля и резюме\n\n"
        "⚙️ <b>Настройки:</b>\n"
        "• /settings - Настройка критериев поиска\n"
        "• /search - Поиск вакансий по критериям\n\n"
        "🤖 <b>Автоотклики:</b>\n"
        "• /autostart - Управление непрерывными автоответами\n"
        "• /auto_start - Запуск стандартных автооткликов\n"
        "• /auto_stop - Остановка автооткликов\n\n"
        "📊 <b>Статистика:</b>\n"
        "• /status - Текущий статус бота\n"
        "• /stats - Общая статистика откликов\n"
        "• /responses - История откликов\n\n"
        "❓ <b>Помощь:</b>\n"
        "• /help - Это сообщение\n"
        "• /about - О боте"
    )
    await message.answer(help_text)
    logger.info(f"Help by user={message.from_user.id}")


@router.message(Command("about"))
async def about_handler(message: Message) -> None:
    """/about"""
    about_text = (
        "ℹ️ <b>О HH Bot</b>\n\n"
        "🤖 <b>Версия:</b> 1.0\n"
        "👨‍💻 <b>Разработчик:</b> HH Bot Team\n"
        "🌐 <b>Платформа:</b> HeadHunter API\n\n"
        "📈 <b>Возможности:</b>\n"
        "• Автоматический поиск вакансий\n"
        "• Умная фильтрация по критериям\n"
        "• Персонализированные сопроводительные письма\n"
        "• Детальная аналитика\n"
        "• Уведомления в реальном времени\n\n"
        "🔒 <b>Безопасность:</b>\n"
        "• Все данные защищены\n"
        "• Используется официальный API HH\n"
        "• Соблюдение лимитов сервиса\n\n"
        "📞 <b>Поддержка:</b> @support_bot"
    )
    await message.answer(about_text)


@router.message(Command("auth"))
async def auth_handler(message: Message, state: FSMContext) -> None:
    """/auth"""
    if await auth_manager.is_authenticated():
        await message.answer("✅ Вы уже авторизованы")
        return
    url = await auth_manager.start_oauth_flow()
    await message.answer(
        f"🔑 <b>Авторизация в HeadHunter</b>\n\n"
        f"1. Перейдите по ссылке: {url}\n"
        f"2. Войдите в свой аккаунт HH\n"
        f"3. Разрешите доступ к вашему профилю\n"
        f"4. Скопируйте полную ссылку из адресной строки\n"
        f"5. Отправьте её мне\n\n"
        f"⚠️ Ссылка должна начинаться с: http://localhost:8000/auth/callback"
    )
    await state.set_state(AuthStates.waiting_callback_url)
    logger.info(f"Auth start for user={message.from_user.id}")


@router.message(AuthStates.waiting_callback_url)
async def auth_callback_handler(message: Message, state: FSMContext) -> None:
    """Обработчик callback URL после авторизации"""

    callback_url = message.text.strip()
    if not callback_url.startswith("http://localhost:8000/auth/callback"):
        await message.answer("❌ Неправильный URL. Убедитесь, что ссылка начинается с http://localhost:8000/auth/callback")
        return

    try:
        await message.answer("🔄 Обрабатываю авторизацию...")

        # 1) Завершаем OAuth flow, получаем токены
        await auth_manager.complete_oauth_flow(callback_url)

        # 2) Запрашиваем профиль и резюме через API
        user_info = await hh_client.get_user_info()
        resumes = await hh_client.get_user_resumes()

        # 3) Сохраняем всё в БД
        user_id = message.from_user.id
        await db_repository.save_hh_profile(user_id, user_info, resumes)
        logger.info(f"Сохранено резюме в БД: {len(resumes)}")

        # 4) Отвечаем пользователю
        await message.answer(
            f"🎉 <b>Авторизация успешна!</b>\n\n"
            f"👤 Привет, {user_info.get('first_name','пользователь')}!\n"
            f"📝 Найдено резюме: {len(resumes)}\n"
            f"📧 Email: {user_info.get('email', 'не указан')}\n\n"
            f"✅ Теперь вы можете:\n"
            f"• Настроить критерии поиска (/settings)\n"
            f"• Выбрать активное резюме (/profile)\n"
            f"• Запустить автоотклики (/autostart)",
            reply_markup=get_main_menu_keyboard()
        )

        await state.clear()
        logger.info(f"Авторизация завершена для user_id={user_id}")

    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        await message.answer(f"❌ <b>Ошибка авторизации</b>\n\nДетали: {e}")


@router.message(Command("profile"))
async def profile_handler(message: Message, state: FSMContext) -> None:
    """/profile"""
    if not await auth_manager.is_authenticated():
        await message.answer(Messages.AUTH_REQUIRED)
        return
    profile = await auth_manager.get_user_profile()
    if not profile:
        await message.answer("❌ Не удалось получить профиль")
        return
    user, resumes = profile['user_info'], profile['resumes']

    # Получаем информацию об активном резюме
    active_resume = await db_repository.get_active_resume(message.from_user.id)
    active_title = active_resume.get('title') if active_resume else 'не выбрано'

    text = (
        f"👤 <b>Профиль HeadHunter</b>\n\n"
        f"🔹 Имя: {user.get('first_name','')} {user.get('last_name','')}\n"
        f"📧 Email: {user.get('email','—')}\n"
        f"🌐 Сайт: {user.get('site_url', '—')}\n\n"
        f"📝 <b>Резюме ({len(resumes)}):</b>\n"
        f"✅ Активное: {active_title}\n\n"
        f"📋 <b>Доступные резюме:</b>"
    )
    await message.answer(text)

    if resumes:
        titles = "\n".join(f"• {r['title']}" for r in resumes)
        await message.answer(
            f"{titles}\n\n"
            "💡 Введите точное название резюме для активации:"
        )
        await state.set_state(ResumeStates.waiting_resume_title)
        await state.update_data(available_resumes=resumes)
    logger.info(f"Profile shown for user={message.from_user.id}")


@router.message(Command("search"))
async def search_handler(message: Message) -> None:
    """/search"""
    if not await auth_manager.is_authenticated():
        await message.answer(Messages.AUTH_REQUIRED)
        return

    uid = message.from_user.id
    settings = await db_repository.get_user_settings(uid)
    if not settings:
        await message.answer("⚙️ Сначала настройте критерии поиска: /settings")
        return

    resume = await db_repository.get_active_resume(uid)
    if not resume:
        await message.answer("📝 Сначала выберите активное резюме: /profile")
        return

    await message.answer("🔍 Ищу подходящие вакансии...")

    # Собираем параметры поиска
    search_params: dict = {
        'text': settings.get('keywords'),
        'salary': settings.get('min_salary'),
        'experience': settings.get('experience'),
        'employment': settings.get('employment_type'),
        'schedule': settings.get('schedule'),
        'per_page': 50
    }

    area_id = settings.get('area_id')
    if area_id and str(area_id).isdigit():
        search_params['area'] = int(area_id)

    # Удаляем пустые параметры
    search_params = {k: v for k, v in search_params.items() if v is not None}

    try:
        resp = await hh_client.search_vacancies(**search_params)
    except Exception as e:
        logger.error(f"Ошибка API запроса: {e}")
        await message.answer(f"❌ Ошибка поиска вакансий: {e}")
        return

    vacs = resp.get('items', [])
    if not vacs:
        await message.answer("😔 По вашим критериям вакансии не найдены")
        return

    # Фильтруем по соответствию
    min_score = settings.get('min_match_score')
    if not isinstance(min_score, int):
        min_score = 60

    suited = matcher.filter_suitable_vacancies(resume, vacs, min_score)
    if not suited:
        await message.answer(f"⚠️ Нет вакансий с соответствием выше {min_score}%")
        return

    await message.answer(f"✅ <b>Найдено подходящих вакансий: {len(suited)}</b>\n\nПоказываю первые 5:")

    for i, vdata in enumerate(suited[:5], 1):
        v = vdata['vacancy']
        a = vdata['match_analysis']

        salary_info = ""
        if v.get('salary'):
            salary = v['salary']
            from_sal = salary.get('from')
            to_sal = salary.get('to')
            currency = salary.get('currency', 'RUR')

            if from_sal and to_sal:
                salary_info = f"💰 {from_sal:,} - {to_sal:,} {currency}\n"
            elif from_sal:
                salary_info = f"💰 от {from_sal:,} {currency}\n"
            elif to_sal:
                salary_info = f"💰 до {to_sal:,} {currency}\n"

        text = (
            f"<b>{i}. {v.get('name','')}</b>\n"
            f"🏢 {v.get('employer', {}).get('name','')}\n"
            f"📍 {v.get('area', {}).get('name','')}\n"
            f"{salary_info}"
            f"📈 Соответствие: {a.get('overall_score',0)}%\n"
        )

        if v.get('alternate_url'):
            text += f"🔗 <a href='{v['alternate_url']}'>Подробнее</a>\n"

        await message.answer(text, disable_web_page_preview=True)
        await asyncio.sleep(0.5)


@router.message(Command("autostart"))
async def autostart_handler(message: Message) -> None:
    """Управление непрерывными автоответами"""
    telegram_id = message.from_user.id

    if not await auth_manager.is_authenticated():
        await message.answer("🔐 Сначала авторизуйтесь: /auth")
        return

    # Проверяем настройки
    settings = await db_repository.get_user_settings(telegram_id)
    resume = await db_repository.get_active_resume(telegram_id)

    if not settings or not resume:
        await message.answer(
            "⚠️ <b>Требуется настройка</b>\n\n"
            "Для работы автооткликов необходимо:\n"
            "• 🔧 Настроить критерии поиска (/settings)\n"
            "• 📝 Выбрать активное резюме (/profile)\n\n"
            "После настройки вернитесь к этой команде."
        )
        return

    # Проверяем статус
    is_running = is_continuous_running(telegram_id)

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🟢 Запустить автоотклики" if not is_running else "🔴 Остановить автоотклики",
                callback_data=f"continuous_{'stop' if is_running else 'start'}:{telegram_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Проверить статус",
                callback_data=f"continuous_status:{telegram_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки поиска",
                callback_data="settings_menu"
            )
        ]
    ])

    status_text = "🟢 Запущены" if is_running else "🔴 Остановлены"

    await message.answer(
        f"🤖 <b>Управление непрерывными автоответами</b>\n\n"
        f"👤 Пользователь: {message.from_user.first_name}\n"
        f"🆔 ID: <code>{telegram_id}</code>\n"
        f"📊 Статус: {status_text}\n" 
        f"⏰ Интервал: 1 минута\n"
        f"🎯 Критерии: {settings.get('keywords', 'не указаны')}\n"
        f"📝 Резюме: {resume.get('title', 'не выбрано')}\n\n"
        f"💡 Используйте кнопки ниже для управления:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("continuous_start:"))
async def callback_start_continuous(callback: CallbackQuery) -> None:
    """Запуск непрерывных автооткликов"""
    telegram_id = int(callback.data.split(":")[1])

    # Проверяем права доступа
    if callback.from_user.id != telegram_id:
        await callback.answer("❌ У вас нет прав для управления этими автоответами", show_alert=True)
        return

    try:
        # Запускаем автоотклики
        success = await start_continuous_auto_responses(telegram_id)

        if success:
            # Обновляем клавиатуру
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔴 Остановить автоотклики",
                        callback_data=f"continuous_stop:{telegram_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Проверить статус",
                        callback_data=f"continuous_status:{telegram_id}"
                    )
                ]
            ])

            await callback.message.edit_text(
                f"🟢 <b>Непрерывные автоответы запущены!</b>\n\n"
                f"👤 Пользователь: {callback.from_user.first_name}\n"
                f"🆔 ID: <code>{telegram_id}</code>\n"
                f"📊 Статус: 🟢 Активны\n"
                f"⏰ Интервал: 1 минута\n\n"
                f"🔄 Автоотклики будут отправляться каждую минуту\n"
                f"📨 Вы будете получать уведомления о каждом отклике\n"
                f"📊 Статистика каждые 10 итераций\n\n"
                f"💡 Используйте кнопку ниже для остановки:",
                reply_markup=keyboard
            )

            await callback.answer("✅ Автоотклики запущены успешно!")

        else:
            await callback.answer("⚠️ Автоотклики уже запущены", show_alert=True)

    except Exception as e:
        await callback.answer(f"❌ Ошибка запуска: {str(e)[:100]}", show_alert=True)


@router.callback_query(F.data.startswith("continuous_stop:"))
async def callback_stop_continuous(callback: CallbackQuery) -> None:
    """Остановка непрерывных автооткликов"""
    telegram_id = int(callback.data.split(":")[1])

    # Проверяем права доступа
    if callback.from_user.id != telegram_id:
        await callback.answer("❌ У вас нет прав для управления этими автоответами", show_alert=True)
        return

    try:
        # Останавливаем автоотклики
        success = await stop_continuous_auto_responses(telegram_id)

        if success:
            # Обновляем клавиатуру
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🟢 Запустить автоотклики",
                        callback_data=f"continuous_start:{telegram_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Проверить статус",
                        callback_data=f"continuous_status:{telegram_id}"
                    )
                ]
            ])

            await callback.message.edit_text(
                f"🔴 <b>Непрерывные автоответы остановлены</b>\n\n"
                f"👤 Пользователь: {callback.from_user.first_name}\n"
                f"🆔 ID: <code>{telegram_id}</code>\n"
                f"📊 Статус: 🔴 Неактивны\n\n"
                f"✅ Автоотклики корректно остановлены\n"
                f"📈 Вся статистика сохранена\n\n"
                f"💡 Используйте кнопку ниже для повторного запуска:",
                reply_markup=keyboard
            )

            await callback.answer("✅ Автоотклики остановлены!")

        else:
            await callback.answer("⚠️ Автоотклики уже остановлены", show_alert=True)

    except Exception as e:
        await callback.answer(f"❌ Ошибка остановки: {str(e)[:100]}", show_alert=True)


@router.callback_query(F.data.startswith("continuous_status:"))
async def callback_status_continuous(callback: CallbackQuery) -> None:
    """Проверка статуса непрерывных автооткликов"""
    telegram_id = int(callback.data.split(":")[1])

    # Проверяем права доступа
    if callback.from_user.id != telegram_id:
        await callback.answer("❌ У вас нет прав для просмотра этой информации", show_alert=True)
        return

    is_running = is_continuous_running(telegram_id)
    status_text = "🟢 Активны" if is_running else "🔴 Неактивны"

    # Получаем дополнительную информацию
    settings = await db_repository.get_user_settings(telegram_id)
    resume = await db_repository.get_active_resume(telegram_id)
    today_stats = await db_repository.get_today_stats(telegram_id)

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🟢 Запустить автоотклики" if not is_running else "🔴 Остановить автоотклики",
                callback_data=f"continuous_{'stop' if is_running else 'start'}:{telegram_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Обновить статус",
                callback_data=f"continuous_status:{telegram_id}"
            )
        ]
    ])

    await callback.message.edit_text(
        f"📊 <b>Детальный статус автоответов</b>\n\n"
        f"👤 Пользователь: {callback.from_user.first_name}\n"
        f"🆔 ID: <code>{telegram_id}</code>\n"
        f"📊 Статус: {status_text}\n"
        f"⏰ Интервал: 1 минута\n\n"
        f"⚙️ <b>Настройки:</b>\n"
        f"🔍 Ключевые слова: {settings.get('keywords', 'не указаны') if settings else 'не настроены'}\n"
        f"📝 Активное резюме: {resume.get('title', 'не выбрано') if resume else 'не выбрано'}\n\n"
        f"📈 <b>Сегодня:</b>\n"
        f"📤 Откликов: {today_stats.get('responses', 0) if today_stats else 0}\n"
        f"🔍 Поисков: {today_stats.get('searches', 0) if today_stats else 0}\n\n"
        f"{'🔄 Автоотклики отправляются каждую минуту' if is_running else '⏸️ Автоотклики приостановлены'}\n\n"
        f"💡 Используйте кнопки для управления:",
        reply_markup=keyboard
    )

    await callback.answer("📊 Статус обновлен")


@router.message(Command("auto_start"))
async def auto_start_handler(message: Message) -> None:
    """Запуск стандартных автоматических откликов (каждые 5 минут)"""

    if not await auth_manager.is_authenticated():
        await message.answer(Messages.AUTH_REQUIRED)
        return

    user_id = message.from_user.id

    # Проверяем настройки
    user_settings = await db_repository.get_user_settings(user_id)
    active_resume = await db_repository.get_active_resume(user_id)

    if not user_settings or not active_resume:
        await message.answer(
            "⚙️ Для автоматических откликов необходимо:\n"
            "1. Настроить критерии поиска (/settings)\n"
            "2. Выбрать активное резюме (/profile)"
        )
        return

    # Проверяем, не запущены ли уже автоотклики
    if await db_repository.is_auto_response_active(user_id):
        await message.answer("⚠️ Стандартные автоотклики уже запущены")
        return

    # Запускаем автоотклики
    await db_repository.set_auto_response_status(user_id, True)

    # Запускаем фоновую задачу
    await task_scheduler.start_auto_responses(user_id)

    await message.answer(
        "✅ <b>Стандартные автоотклики запущены!</b>\n\n"
        "⏰ Интервал: каждые 5 минут\n"
        "🔄 Для непрерывного режима используйте /autostart"
    )
    logger.info(f"Стандартные автоотклики запущены для пользователя {user_id}")


@router.message(Command("auto_stop"))
async def auto_stop_handler(message: Message) -> None:
    """Остановка автоматических откликов"""

    user_id = message.from_user.id

    # Останавливаем стандартные автоотклики
    standard_stopped = False
    if await db_repository.is_auto_response_active(user_id):
        await db_repository.set_auto_response_status(user_id, False)
        await task_scheduler.stop_auto_responses(user_id)
        standard_stopped = True

    # Останавливаем непрерывные автоотклики
    continuous_stopped = False
    if is_continuous_running(user_id):
        await stop_continuous_auto_responses(user_id)
        continuous_stopped = True

    if standard_stopped or continuous_stopped:
        stopped_types = []
        if standard_stopped:
            stopped_types.append("стандартные")
        if continuous_stopped:
            stopped_types.append("непрерывные")

        await message.answer(
            f"✅ <b>Автоотклики остановлены</b>\n\n"
            f"🛑 Остановлены: {', '.join(stopped_types)}\n"
            f"📊 Вся статистика сохранена"
        )
        logger.info(f"Автоотклики остановлены для пользователя {user_id}")
    else:
        await message.answer("ℹ️ Автоотклики не были запущены")


@router.message(Command("status"))
async def status_handler(message: Message) -> None:
    """Статус работы бота"""

    user_id = message.from_user.id

    # Проверяем авторизацию
    is_auth = await auth_manager.is_authenticated()

    # Проверяем автоотклики
    standard_active = await db_repository.is_auto_response_active(user_id)
    continuous_active = is_continuous_running(user_id)

    # Статистика за сегодня
    today_stats = await db_repository.get_today_stats(user_id)

    status_text = f"📊 <b>Статус бота</b>\n\n"
    status_text += f"🔐 Авторизация HH: {'✅ Активна' if is_auth else '❌ Требуется'}\n"
    status_text += f"🤖 Стандартные автоотклики: {'🟢 Активны' if standard_active else '🔴 Неактивны'}\n"
    status_text += f"⚡ Непрерывные автоотклики: {'🟢 Активны' if continuous_active else '🔴 Неактивны'}\n\n"
    status_text += f"📈 <b>Статистика за сегодня:</b>\n"
    status_text += f"🔍 Поисков: {today_stats.get('searches', 0) if today_stats else 0}\n"
    status_text += f"📤 Откликов: {today_stats.get('responses', 0) if today_stats else 0}\n"
    status_text += f"📨 Приглашений: {today_stats.get('invitations', 0) if today_stats else 0}\n\n"
    status_text += f"⏰ Последняя активность: {today_stats.get('last_activity', 'никогда') if today_stats else 'никогда'}"

    await message.answer(status_text)


@router.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    """Общая статистика"""

    user_id = message.from_user.id
    stats = await db_repository.get_user_stats(user_id)

    stats_text = f"📊 <b>Общая статистика</b>\n\n"
    stats_text += f"📤 Всего откликов: {stats.get('total_responses', 0) if stats else 0}\n"
    stats_text += f"📨 Приглашений: {stats.get('total_invitations', 0) if stats else 0}\n"
    stats_text += f"✅ Успешных собеседований: {stats.get('successful_interviews', 0) if stats else 0}\n"
    stats_text += f"📈 Коэффициент отклика: {stats.get('response_rate', 0) if stats else 0}%\n\n"
    stats_text += f"🗓️ Активен с: {stats.get('registration_date', 'неизвестно') if stats else 'неизвестно'}\n"
    stats_text += f"⏰ Последний отклик: {stats.get('last_response', 'никогда') if stats else 'никогда'}"

    await message.answer(stats_text)


@router.message(Command("responses"))
async def responses_handler(message: Message) -> None:
    """История откликов"""
    user_id = message.from_user.id

    try:
        responses = await db_repository.get_user_responses(user_id, limit=10)

        if not responses:
            await message.answer("📝 История откликов пуста")
            return

        await message.answer(f"📋 <b>Последние {len(responses)} откликов:</b>\n")

        for i, response in enumerate(responses, 1):
            response_text = (
                f"<b>{i}. Вакансия #{response.get('vacancy_id', 'неизвестно')}</b>\n"
                f"📅 {response.get('created_at', 'неизвестно')}\n"
                f"📝 Письмо: {response.get('cover_letter', '')[:100]}...\n"
            )
            await message.answer(response_text)
            await asyncio.sleep(0.3)

    except Exception as e:
        logger.error(f"Ошибка получения истории откликов: {e}")
        await message.answer("❌ Ошибка получения истории откликов")
