"""
Планировщик задач для автоматических откликов
"""
import asyncio
from typing import Dict, Set, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config import Config
from database.repository import db_repository
from hh_api.client import hh_client
from hh_api.auth import auth_manager
from matching.analyzer import matcher

# Глобальные переменные для управления непрерывными автоответами
continuous_tasks = {}  # Словарь для хранения запущенных задач: {telegram_id: task}
error_statistics = {}  # Статистика ошибок по пользователям


class TaskScheduler:
    """Планировщик автоматических задач"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.active_users: Set[int] = set()
        self.is_running = False
        self.processed_vacancies: Set[str] = set()  # Кеш обработанных вакансий
        self.error_counts: Dict[int, Dict[str, int]] = {}  # Счетчики ошибок по пользователям

    async def start(self) -> None:
        """Запуск планировщика"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            await self._load_active_users()

            for user_id in self.active_users:
                await self.start_auto_responses(user_id)

            logger.info("Планировщик задач запущен")

    async def shutdown(self) -> None:
        """Остановка планировщика"""
        if self.is_running:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            self.active_users.clear()

            # Останавливаем все непрерывные задачи
            global continuous_tasks
            for telegram_id in list(continuous_tasks.keys()):
                await stop_continuous_auto_responses(telegram_id)

            # Очищаем статистику
            self.processed_vacancies.clear()
            self.error_counts.clear()

            logger.info("Планировщик задач остановлен")

    async def start_auto_responses(self, telegram_id: int) -> None:
        """Запуск автоматических откликов для пользователя"""
        logger.info(f"Автoотклики: запущена функция start_auto_responses для {telegram_id}")

        if telegram_id in self.active_users:
            logger.warning(f"Автоотклики для пользователя {telegram_id} уже запущены")
            return

        self.active_users.add(telegram_id)

        # Инициализируем счетчики ошибок для пользователя
        self.error_counts[telegram_id] = {
            'test_required': 0,
            'access_denied': 0,
            'already_applied': 0,
            'vacancy_archived': 0,
            'other_errors': 0
        }

        job_id = f"auto_response_{telegram_id}"
        self.scheduler.add_job(
            self._process_auto_responses,
            trigger=IntervalTrigger(minutes=5),  # Каждые 5 минут
            args=[telegram_id],
            id=job_id,
            replace_existing=True,
            max_instances=1
        )

        logger.info(f"Автоотклики запущены для пользователя {telegram_id}")

    async def stop_auto_responses(self, telegram_id: int) -> None:
        """Остановка автоматических откликов для пользователя"""
        if telegram_id not in self.active_users:
            logger.warning(f"Автоотклики для пользователя {telegram_id} не запущены")
            return

        self.active_users.discard(telegram_id)

        # Очищаем счетчики ошибок
        if telegram_id in self.error_counts:
            del self.error_counts[telegram_id]

        job_id = f"auto_response_{telegram_id}"
        try:
            self.scheduler.remove_job(job_id)
        except Exception as e:
            logger.error(f"Ошибка остановки задачи {job_id}: {e}")

        logger.info(f"Автоотклики остановлены для пользователя {telegram_id}")

    async def _process_auto_responses(self, telegram_id: int) -> None:
        """Обработка автоматических откликов для пользователя"""
        logger.info(f"Автoотклики: запущена функция _process_auto_responses для {telegram_id}")

        try:
            # Проверка предварительных условий
            if not await self._validate_user_conditions(telegram_id):
                return

            # Получаем настройки пользователя
            user_settings = await db_repository.get_user_settings(telegram_id)
            if not user_settings:
                logger.warning(f"Нет настроек для пользователя {telegram_id}")
                return

            # Получаем активное резюме
            active_resume = await db_repository.get_active_resume(telegram_id)
            if not active_resume:
                logger.warning(f"Нет активного резюме для пользователя {telegram_id}")
                return

            # Ищем подходящие вакансии
            suitable_vacancies = await self._find_suitable_vacancies(
                telegram_id, user_settings, active_resume
            )

            logger.info(f"Найдено подходящих вакансий: {len(suitable_vacancies)} для пользователя {telegram_id}")

            if not suitable_vacancies:
                logger.info(f"Подходящих новых вакансий не найдено для пользователя {telegram_id}")
                await self._send_no_vacancies_notification(telegram_id)
                return

            # Отправляем отклики
            responses_sent, errors_count = await self._send_responses(
                telegram_id, suitable_vacancies, active_resume, user_settings
            )

            logger.info(f"Отправлено {responses_sent} откликов, {errors_count} ошибок для пользователя {telegram_id}")

            # Отправляем итоговую статистику
            if errors_count > 0:
                await self._send_error_summary(telegram_id, responses_sent, errors_count, len(suitable_vacancies))

        except Exception as e:
            logger.error(f"Ошибка автоматических откликов для пользователя {telegram_id}: {e}")
            await self._send_critical_error_notification(telegram_id, str(e))

    async def _validate_user_conditions(self, telegram_id: int) -> bool:
        """Валидация условий для пользователя"""
        try:
            # Загружаем токены авторизации
            if not await auth_manager.is_authenticated():
                await auth_manager.load_tokens()

            if not await auth_manager.is_authenticated():
                logger.error(f"Пользователь {telegram_id} не авторизован в HH API")
                await self._send_auth_required_notification(telegram_id)
                return False

            # Проверяем что автoотклики все еще активны
            if not await db_repository.is_auto_response_active(telegram_id):
                await self.stop_auto_responses(telegram_id)
                return False

            # Проверяем дневной лимит
            today_count = await self._get_today_responses_count(telegram_id)
            max_responses = getattr(Config, 'MAX_RESPONSES_PER_DAY', 20)

            if today_count >= max_responses:
                logger.info(f"Достигнут дневной лимит ({max_responses}) для пользователя {telegram_id}")
                await self._send_limit_reached_notification(telegram_id, today_count, max_responses)
                return False

            return True

        except Exception as e:
            logger.error(f"Ошибка валидации условий для пользователя {telegram_id}: {e}")
            return False

    async def _find_suitable_vacancies(
        self,
        telegram_id: int,
        user_settings: Dict[str, Any],
        active_resume: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Поиск подходящих вакансий с улучшенной фильтрацией"""
        try:
            # Собираем параметры поиска
            search_params: Dict[str, Any] = {
                'text': user_settings.get('keywords'),
                'salary': user_settings.get('min_salary'),
                'experience': user_settings.get('experience'),
                'employment': user_settings.get('employment_type'),
                'schedule': user_settings.get('schedule'),
                'per_page': 50
            }

            # Добавляем area только если это число
            area_id = user_settings.get('area_id')
            if area_id and str(area_id).isdigit():
                search_params['area'] = int(area_id)

            # Удаляем пустые параметры
            search_params = {k: v for k, v in search_params.items() if v is not None}

            logger.info(f"Поиск вакансий с параметрами: {search_params}")

            # Поиск через HH API
            response = await hh_client.search_vacancies(**search_params)
            vacancies = response.get('items', [])

            logger.info(f"Найдено вакансий через API: {len(vacancies)}")

            if not vacancies:
                return []

            # Фильтруем уже обработанные вакансии
            new_vacancies = [v for v in vacancies if str(v['id']) not in self.processed_vacancies]
            logger.info(f"Новых необработанных вакансий: {len(new_vacancies)}")

            if not new_vacancies:
                return []

            # Получаем минимальный порог соответствия
            min_score = user_settings.get('min_match_score')
            if not isinstance(min_score, int):
                min_score = 60

            # Фильтруем по соответствию
            suitable_vacancies = matcher.filter_suitable_vacancies(
                active_resume, new_vacancies, min_score
            )

            logger.info(f"Прошло фильтр соответствия: {len(suitable_vacancies)}")

            # Исключаем вакансии на которые уже откликались
            final_vacancies = []
            for vacancy_data in suitable_vacancies:
                vacancy = vacancy_data['vacancy']
                vacancy_id = str(vacancy['id'])

                if not await self._is_response_exists(telegram_id, vacancy_id):
                    final_vacancies.append(vacancy_data)
                    # Добавляем в кеш обработанных
                    self.processed_vacancies.add(vacancy_id)
                    logger.info(f"Добавлена новая вакансия: {vacancy_id}")
                else:
                    logger.info(f"Пропущена вакансия (уже откликались): {vacancy_id}")

            logger.info(f"Финальных вакансий для отклика: {len(final_vacancies)}")
            return final_vacancies[:5]  # Максимум 5 вакансий за раз

        except Exception as e:
            logger.error(f"Ошибка поиска вакансий: {e}")
            return []

    async def _send_responses(
        self,
        telegram_id: int,
        suitable_vacancies: List[Dict[str, Any]],
        active_resume: Dict[str, Any],
        user_settings: Dict[str, Any]
    ) -> Tuple[int, int]:
        """Отправка откликов на подходящие вакансии с улучшенной обработкой ошибок"""
        responses_sent = 0
        errors_count = 0
        resume_id = str(active_resume.get('id'))

        for vacancy_data in suitable_vacancies:
            try:
                # Проверяем лимит еще раз
                today_count = await self._get_today_responses_count(telegram_id)
                max_responses = getattr(Config, 'MAX_RESPONSES_PER_DAY', 20)

                if today_count >= max_responses:
                    logger.info(f"Достигнут лимит откликов на сегодня: {max_responses}")
                    break

                vacancy = vacancy_data['vacancy']
                vacancy_id = str(vacancy['id'])
                match_analysis = vacancy_data['match_analysis']

                logger.info(f"Автoотклики: готовлюсь откликнуться на вакансию {vacancy_id}")

                # Генерируем сопроводительное письмо
                cover_letter = await self._generate_cover_letter(
                    vacancy, active_resume, user_settings.get('cover_letter_template')
                )

                # Отправляем отклик через HH API
                success, error_type = await self._send_single_response(
                    telegram_id, vacancy_id, resume_id, cover_letter, vacancy
                )

                if success:
                    # Сохраняем в БД
                    await self._save_response_to_db(
                        telegram_id, vacancy_id, cover_letter, match_analysis['overall_score']
                    )

                    responses_sent += 1
                    logger.info(f"Успешно отправлен отклик на вакансию {vacancy_id}")

                    # Отправляем уведомление в Telegram
                    await self._send_telegram_notification(telegram_id, vacancy, cover_letter)

                    # Задержка между откликами
                    delay = getattr(Config, 'RESPONSE_DELAY_SECONDS', 30)
                    await asyncio.sleep(delay)
                else:
                    errors_count += 1
                    # Увеличиваем счетчик конкретного типа ошибки
                    if telegram_id in self.error_counts:
                        self.error_counts[telegram_id][error_type] += 1
                    logger.warning(f"Не удалось отправить отклик на вакансию {vacancy_id}, тип ошибки: {error_type}")

            except Exception as e:
                errors_count += 1
                if telegram_id in self.error_counts:
                    self.error_counts[telegram_id]['other_errors'] += 1
                logger.error(f"Ошибка отправки отклика на вакансию {vacancy.get('id')}: {e}")
                continue

        return responses_sent, errors_count

    async def _send_single_response(
        self,
        telegram_id: int,
        vacancy_id: str,
        resume_id: str,
        cover_letter: str,
        vacancy: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Отправка одного отклика с классификацией ошибок"""
        try:
            logger.info(f"РЕАЛЬНАЯ отправка отклика на вакансию {vacancy_id}")

            # Реальный вызов API для отправки отклика
            result = await hh_client.send_response_to_vacancy(vacancy_id, resume_id, cover_letter)

            if result.get('success'):
                logger.info(f"✅ Отклик успешно отправлен на вакансию {vacancy_id}")
                return True, 'success'
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')

                # Классификация ошибок HeadHunter
                if "test_required" in error_msg.lower() or "must process test first" in error_msg.lower():
                    logger.warning(f"⚠️ Требуется тест для вакансии {vacancy_id}")
                    await self._handle_test_required_error(telegram_id, vacancy, error_msg)
                    return False, 'test_required'
                elif "403" in error_msg and "forbidden" in error_msg.lower():
                    logger.warning(f"⚠️ Нет доступа к вакансии {vacancy_id}")
                    await self._handle_access_denied_error(telegram_id, vacancy, error_msg)
                    return False, 'access_denied'
                elif "already_applied" in error_msg.lower():
                    logger.warning(f"⚠️ Уже откликались на вакансию {vacancy_id}")
                    return False, 'already_applied'
                elif "vacancy_archived" in error_msg.lower() or "vacancy_not_found" in error_msg.lower():
                    logger.warning(f"⚠️ Вакансия {vacancy_id} архивирована или не найдена")
                    return False, 'vacancy_archived'
                else:
                    logger.error(f"❌ Неизвестная ошибка отправки отклика: {error_msg}")
                    return False, 'other_errors'

        except Exception as e:
            logger.error(f"Критическая ошибка отправки отклика: {e}")
            return False, 'other_errors'

    async def _handle_test_required_error(
        self,
        telegram_id: int,
        vacancy: Dict[str, Any],
        error_msg: str
    ) -> None:
        """Обработка ошибки требования теста"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            vacancy_name = vacancy.get('name', 'Неизвестная позиция')
            company_name = vacancy.get('employer', {}).get('name', 'Неизвестная компания')
            vacancy_url = vacancy.get('alternate_url', '')

            message_text = (
                f"📝 <b>Требуется тест для отклика</b>\n\n"
                f"🎯 <b>{vacancy_name}</b>\n"
                f"🏢 {company_name}\n\n"
                f"⚠️ Работодатель требует сначала пройти тест.\n"
                f"🔗 <a href='{vacancy_url}'>Пройти тест и откликнуться вручную</a>\n\n"
                f"💡 Автоотклик пропущен, продолжаю поиск других вакансий."
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                disable_web_page_preview=True
            )

            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о тесте: {e}")

    async def _handle_access_denied_error(
        self,
        telegram_id: int,
        vacancy: Dict[str, Any],
        error_msg: str
    ) -> None:
        """Обработка ошибки доступа к вакансии"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            vacancy_name = vacancy.get('name', 'Неизвестная позиция')
            company_name = vacancy.get('employer', {}).get('name', 'Неизвестная компания')

            message_text = (
                f"🚫 <b>Нет доступа к вакансии</b>\n\n"
                f"🎯 <b>{vacancy_name}</b>\n"
                f"🏢 {company_name}\n\n"
                f"⚠️ Возможные причины:\n"
                f"• Вакансия имеет ограничения по доступу\n"
                f"• Требуется премиум аккаунт\n"
                f"• Географические ограничения\n\n"
                f"💡 Автоотклик пропущен, продолжаю поиск других вакансий."
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )

            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об ограничении доступа: {e}")

    async def _send_error_summary(
        self,
        telegram_id: int,
        responses_sent: int,
        errors_count: int,
        total_vacancies: int
    ) -> None:
        """Отправка сводки по ошибкам"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            error_stats = self.error_counts.get(telegram_id, {})

            error_details = []
            if error_stats.get('test_required', 0) > 0:
                error_details.append(f"📝 Требуется тест: {error_stats['test_required']}")
            if error_stats.get('access_denied', 0) > 0:
                error_details.append(f"🚫 Нет доступа: {error_stats['access_denied']}")
            if error_stats.get('already_applied', 0) > 0:
                error_details.append(f"🔄 Уже откликались: {error_stats['already_applied']}")
            if error_stats.get('vacancy_archived', 0) > 0:
                error_details.append(f"📦 Архивирована: {error_stats['vacancy_archived']}")
            if error_stats.get('other_errors', 0) > 0:
                error_details.append(f"❓ Прочие ошибки: {error_stats['other_errors']}")

            error_breakdown = "\n".join(error_details) if error_details else "Детализация недоступна"

            message_text = (
                f"📊 <b>Сводка по автооткликам</b>\n\n"
                f"✅ Успешных откликов: {responses_sent}\n"
                f"❌ Ошибок: {errors_count}\n"
                f"📝 Всего обработано: {total_vacancies}\n"
                f"📈 Успешность: {(responses_sent / total_vacancies * 100):.1f}%\n\n"
                f"📋 <b>Детализация ошибок:</b>\n"
                f"{error_breakdown}\n\n"
                f"🔄 Продолжаю поиск новых вакансий..."
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )

            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки сводки по ошибкам: {e}")

    async def _send_no_vacancies_notification(self, telegram_id: int) -> None:
        """Уведомление об отсутствии новых вакансий"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            message_text = (
                f"🔍 <b>Поиск вакансий завершен</b>\n\n"
                f"😔 Новых подходящих вакансий не найдено\n\n"
                f"💡 <b>Возможные причины:</b>\n"
                f"• Все найденные вакансии уже обработаны\n"
                f"• Критерии поиска слишком строгие\n"
                f"• На рынке мало новых вакансий\n\n"
                f"🔄 Продолжаю мониторинг..."
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )

            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об отсутствии вакансий: {e}")

    async def _send_limit_reached_notification(self, telegram_id: int, current_count: int, max_limit: int) -> None:
        """Уведомление о достижении дневного лимита"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            message_text = (
                f"🛑 <b>Достигнут дневной лимит</b>\n\n"
                f"📤 Отправлено откликов сегодня: {current_count}\n"
                f"📊 Максимальный лимит: {max_limit}\n\n"
                f"⏰ Автоотклики возобновятся завтра\n"
                f"⚙️ Лимит можно изменить в настройках"
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )

            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о лимите: {e}")

    async def _send_auth_required_notification(self, telegram_id: int) -> None:
        """Уведомление о необходимости авторизации"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            message_text = (
                f"🔐 <b>Требуется авторизация</b>\n\n"
                f"⚠️ Токен авторизации недействителен\n"
                f"🔑 Необходимо повторно авторизоваться\n\n"
                f"👉 Используйте команду /auth\n"
                f"🛑 Автоотклики приостановлены"
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )

            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об авторизации: {e}")

    async def _send_critical_error_notification(self, telegram_id: int, error_message: str) -> None:
        """Уведомление о критической ошибке"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            message_text = (
                f"💥 <b>Критическая ошибка</b>\n\n"
                f"❌ Ошибка: <code>{error_message[:300]}</code>\n\n"
                f"🔄 Попробую продолжить на следующей итерации\n"
                f"📞 Обратитесь в поддержку, если ошибка повторяется"
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )

            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о критической ошибке: {e}")

    async def _send_telegram_notification(self, telegram_id: int, vacancy: Dict[str, Any], cover_letter: str) -> None:
        """Отправка уведомления в Telegram"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            vacancy_name = vacancy.get('name', 'Неизвестная позиция')
            company_name = vacancy.get('employer', {}).get('name', 'Неизвестная компания')
            salary_info = ""

            if vacancy.get('salary'):
                salary = vacancy['salary']
                from_sal = salary.get('from')
                to_sal = salary.get('to')
                currency = salary.get('currency', 'RUR')

                if from_sal and to_sal:
                    salary_info = f"\n💰 Зарплата: {from_sal:,} - {to_sal:,} {currency}"
                elif from_sal:
                    salary_info = f"\n💰 Зарплата: от {from_sal:,} {currency}"
                elif to_sal:
                    salary_info = f"\n💰 Зарплата: до {to_sal:,} {currency}"

            area_name = vacancy.get('area', {}).get('name', '')
            area_info = f"\n📍 {area_name}" if area_name else ""

            vacancy_url = vacancy.get('alternate_url', '')
            url_info = f"\n🔗 <a href='{vacancy_url}'>Посмотреть вакансию</a>" if vacancy_url else ""

            # Получаем текущую статистику за день
            today_count = await self._get_today_responses_count(telegram_id)

            message_text = (
                f"🤖 <b>Автоотклик отправлен!</b>\n\n"
                f"🎯 <b>{vacancy_name}</b>\n"
                f"🏢 {company_name}"
                f"{salary_info}"
                f"{area_info}"
                f"{url_info}\n\n"
                f"📝 <b>Сопроводительное письмо:</b>\n"
                f"<i>{cover_letter}</i>\n\n"
                f"📊 <b>Статистика за сегодня:</b> {today_count} откликов"
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                disable_web_page_preview=True
            )

            # Закрываем сессию бота после отправки
            await bot.session.close()

        except Exception as tg_error:
            logger.error(f"Ошибка отправки уведомления в Telegram: {tg_error}")

    async def _generate_cover_letter(
        self,
        vacancy: Dict[str, Any],
        resume: Dict[str, Any],
        template: str = None
    ) -> str:
        """Генерация сопроводительного письма с улучшенными шаблонами"""
        vacancy_name = vacancy.get('name', '')
        company_name = vacancy.get('employer', {}).get('name', '')
        my_skills = ', '.join(resume.get('skill_set', [])[:5])

        if template:
            try:
                # Заменяем переменные в шаблоне
                cover_letter = template.format(
                    vacancy_name=vacancy_name,
                    company_name=company_name,
                    my_skills=my_skills
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Ошибка форматирования шаблона: {e}, использую стандартный")
                cover_letter = self._get_default_cover_letter(vacancy_name, company_name)
        else:
            cover_letter = self._get_default_cover_letter(vacancy_name, company_name)

        return cover_letter

    def _get_default_cover_letter(self, vacancy_name: str, company_name: str) -> str:
        """Получение стандартного сопроводительного письма"""
        templates = [
            f"Здравствуйте! Меня заинтересовала позиция {vacancy_name} в компании {company_name}. Готов обсудить детали сотрудничества.",
            f"Добрый день! Хотел бы рассмотреть возможность трудоустройства на позицию {vacancy_name} в {company_name}. Буду рад собеседованию.",
            f"Здравствуйте! Увидел вакансию {vacancy_name} и считаю, что мой опыт подходит для этой позиции. С радостью расскажу подробнее о себе.",
        ]

        # Выбираем случайный шаблон для разнообразия
        import random
        return random.choice(templates)

    async def _save_response_to_db(
        self,
        telegram_id: int,
        vacancy_id: str,
        cover_letter: str,
        match_score: int
    ) -> None:
        """Сохранение отклика в БД с дополнительными метаданными"""
        try:
            # Получаем internal user_id
            import aiosqlite
            async with aiosqlite.connect(db_repository.db_path) as db:
                cursor = await db.execute(
                    "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Пользователь {telegram_id} не найден")
                user_id = row[0]

                # Сохраняем отклик с дополнительными данными
                await db.execute("""
                    INSERT INTO responses (user_id, vacancy_id, cover_letter, match_score, source_type, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, vacancy_id, cover_letter, match_score, 'auto'))
                await db.commit()

                logger.info(f"Сохранена запись об отклике на {vacancy_id} с оценкой {match_score}")

        except Exception as e:
            logger.error(f"Ошибка сохранения отклика в БД: {e}")

    async def _is_response_exists(self, telegram_id: int, vacancy_id: str) -> bool:
        """Проверка существования отклика"""
        try:
            import aiosqlite
            async with aiosqlite.connect(db_repository.db_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM responses r
                    JOIN users u ON r.user_id = u.id
                    WHERE u.telegram_id = ? AND r.vacancy_id = ?
                """, (telegram_id, vacancy_id))
                row = await cursor.fetchone()
                return bool(row and row[0] > 0)
        except Exception as e:
            logger.error(f"Ошибка проверки существования отклика: {e}")
            return False

    async def _get_today_responses_count(self, telegram_id: int) -> int:
        """Получение количества откликов за сегодня"""
        try:
            import aiosqlite
            from datetime import date

            today = date.today().strftime('%Y-%m-%d')

            async with aiosqlite.connect(db_repository.db_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM responses r
                    JOIN users u ON r.user_id = u.id
                    WHERE u.telegram_id = ? AND DATE(r.created_at) = ?
                """, (telegram_id, today))
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Ошибка получения количества откликов: {e}")
            return 0

    async def _load_active_users(self) -> None:
        """Загрузка активных пользователей из БД"""
        try:
            import aiosqlite
            async with aiosqlite.connect(db_repository.db_path) as db:
                cursor = await db.execute("""
                    SELECT u.telegram_id FROM users u
                    JOIN search_settings s ON u.id = s.user_id
                    WHERE s.auto_response_enabled = 1
                """)
                rows = await cursor.fetchall()
                for row in rows:
                    self.active_users.add(row[0])

                logger.info(f"Загружено активных пользователей: {len(self.active_users)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки активных пользователей: {e}")

    def get_active_users_count(self) -> int:
        """Получение количества активных пользователей"""
        return len(self.active_users)

    def is_user_active(self, telegram_id: int) -> bool:
        """Проверка активности пользователя"""
        return telegram_id in self.active_users

    def get_error_statistics(self, telegram_id: int) -> Dict[str, int]:
        """Получение статистики ошибок для пользователя"""
        return self.error_counts.get(telegram_id, {})

    def clear_processed_cache(self) -> None:
        """Очистка кеша обработанных вакансий (вызывается раз в день)"""
        self.processed_vacancies.clear()
        logger.info("Кеш обработанных вакансий очищен")


# Глобальный экземпляр планировщика
task_scheduler = TaskScheduler()


# Функции для управления непрерывными автоответами
async def start_continuous_auto_responses(telegram_id: int) -> bool:
    """Запуск непрерывных автооткликов для пользователя"""
    global continuous_tasks

    # Проверяем, не запущена ли уже задача
    if telegram_id in continuous_tasks and not continuous_tasks[telegram_id].done():
        logger.warning(f"Непрерывные автоотклики для {telegram_id} уже запущены")
        return False

    # Запускаем задачу в фоне
    task = asyncio.create_task(run_auto_responses_continuously(telegram_id, 1))
    continuous_tasks[telegram_id] = task

    logger.info(f"Запущены непрерывные автоотклики для пользователя {telegram_id}")
    return True


async def stop_continuous_auto_responses(telegram_id: int) -> bool:
    """Остановка непрерывных автооткликов для пользователя"""
    global continuous_tasks

    if telegram_id not in continuous_tasks:
        logger.warning(f"Непрерывные автоотклики для {telegram_id} не найдены")
        return False

    task = continuous_tasks[telegram_id]
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    del continuous_tasks[telegram_id]
    logger.info(f"Остановлены непрерывные автоотклики для пользователя {telegram_id}")
    return True


def is_continuous_running(telegram_id: int) -> bool:
    """Проверка, запущены ли непрерывные автоотклики"""
    global continuous_tasks
    return telegram_id in continuous_tasks and not continuous_tasks[telegram_id].done()


async def run_auto_responses_continuously(telegram_id: int, interval_minutes: int = 1) -> None:
    """Функция для непрерывного запуска автооткликов"""
    from hh_api.auth import auth_manager

    # Загружаем токены один раз
    try:
        await auth_manager.load_tokens()
        logger.info(f"Токены загружены для непрерывного режима пользователя {telegram_id}")
    except Exception as e:
        logger.error(f"Ошибка загрузки токенов: {e}")
        return

    scheduler = TaskScheduler()

    # Отправляем уведомление о запуске
    try:
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode

        bot = Bot(
            token=Config.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        await bot.send_message(
            chat_id=telegram_id,
            text=(
                f"🟢 <b>Автоотклики запущены в непрерывном режиме</b>\n\n"
                f"⏰ Интервал: каждые {interval_minutes} мин\n"
                f"🔄 Режим: непрерывный\n"
                f"📊 Статус: активен\n"
                f"🛑 Для остановки используйте команду /autostart"
            )
        )
        await bot.session.close()
        logger.info(f"Отправлено уведомление о запуске непрерывного режима пользователю {telegram_id}")

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о запуске: {e}")

    logger.info(f"🚀 Запущен непрерывный режим автооткликов для пользователя {telegram_id}")
    logger.info(f"⏰ Интервал: {interval_minutes} минут")

    iteration = 0
    start_total_time = datetime.now()

    try:
        while True:
            iteration += 1
            start_time = asyncio.get_event_loop().time()

            logger.info(f"🔄 Итерация #{iteration} - запуск автооткликов для {telegram_id}")

            try:
                # Проверяем токены перед каждой итерацией
                if not await auth_manager.is_authenticated():
                    await auth_manager.load_tokens()

                # Выполняем автоотклики
                await scheduler._process_auto_responses(telegram_id)

                end_time = asyncio.get_event_loop().time()
                execution_time = end_time - start_time

                logger.info(f"✅ Итерация #{iteration} завершена за {execution_time:.2f}с")

            except Exception as e:
                logger.error(f"❌ Ошибка в итерации #{iteration}: {e}")

                # Отправляем уведомление об ошибке
                try:
                    bot = Bot(
                        token=Config.TELEGRAM_BOT_TOKEN,
                        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                    )

                    await bot.send_message(
                        chat_id=telegram_id,
                        text=(
                            f"⚠️ <b>Ошибка в автоотклике</b>\n\n"
                            f"🔢 Итерация: #{iteration}\n"
                            f"❌ Ошибка: <code>{str(e)[:200]}</code>\n"
                            f"🔄 Продолжаем работу..."
                        )
                    )
                    await bot.session.close()

                except Exception as notify_error:
                    logger.error(f"Не удалось отправить уведомление об ошибке: {notify_error}")

            # Отправляем статус каждые 10 итераций
            if iteration % 10 == 0:
                try:
                    bot = Bot(
                        token=Config.TELEGRAM_BOT_TOKEN,
                        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                    )

                    total_time = datetime.now() - start_total_time
                    hours, remainder = divmod(total_time.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)

                    # Получаем статистику ошибок
                    error_stats = scheduler.get_error_statistics(telegram_id)
                    total_errors = sum(error_stats.values())

                    await bot.send_message(
                        chat_id=telegram_id,
                        text=(
                            f"📊 <b>Расширенная статистика автооткликов</b>\n\n"
                            f"🔢 Итераций выполнено: {iteration}\n"
                            f"⏰ Интервал: {interval_minutes} мин\n"
                            f"🟢 Статус: работает\n"
                            f"⏱️ Время работы: {int(hours)}ч {int(minutes)}м\n"
                            f"❌ Всего ошибок: {total_errors}\n\n"
                            f"🔄 Продолжаю мониторинг вакансий..."
                        )
                    )
                    await bot.session.close()

                except Exception as status_error:
                    logger.error(f"Не удалось отправить статус: {status_error}")

            # Ждем до следующей итерации
            logger.info(f"⏳ Ожидание {interval_minutes} минут до следующей итерации...")
            await asyncio.sleep(interval_minutes * 60)

    except asyncio.CancelledError:
        logger.info(f"🛑 Получен сигнал остановки для пользователя {telegram_id}")

        # Отправляем уведомление об остановке
        try:
            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            total_time = datetime.now() - start_total_time
            hours, remainder = divmod(total_time.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)

            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"🔴 <b>Автоотклики остановлены</b>\n\n"
                    f"🔢 Всего итераций: {iteration}\n"
                    f"⏱️ Время работы: {int(hours)}ч {int(minutes)}м\n"
                    f"✅ Остановка: корректная"
                )
            )
            await bot.session.close()

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об остановке: {e}")

    except Exception as e:
        logger.error(f"💥 Критическая ошибка непрерывного режима: {e}")

        # Отправляем уведомление о критической ошибке
        try:
            bot = Bot(
                token=Config.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"💥 <b>Критическая ошибка автооткликов</b>\n\n"
                    f"❌ Ошибка: <code>{str(e)[:200]}</code>\n"
                    f"🔢 Итераций выполнено: {iteration}\n"
                    f"🛑 Автоотклики остановлены"
                )
            )
            await bot.session.close()

        except Exception as notify_error:
            logger.error(f"Не удалось отправить уведомление о критической ошибке: {notify_error}")

    finally:
        logger.info(f"🏁 Непрерывный режим автооткликов для пользователя {telegram_id} завершен")


# Функция для прямого запуска (для отладки)
async def run_auto_responses(telegram_id: int) -> None:
    """Функция для ручного запуска автооткликов (для отладки)"""
    from hh_api.auth import auth_manager

    # Загружаем токены
    try:
        await auth_manager.load_tokens()
        logger.info("Токены загружены для отладки")
    except Exception as e:
        logger.error(f"Ошибка загрузки токенов: {e}")
        return

    scheduler = TaskScheduler()
    await scheduler._process_auto_responses(telegram_id)


# Утилитные функции для управления планировщиком
async def get_scheduler_statistics() -> Dict[str, Any]:
    """Получение общей статистики планировщика"""
    return {
        'active_users': len(task_scheduler.active_users),
        'continuous_tasks': len(continuous_tasks),
        'processed_vacancies_cache': len(task_scheduler.processed_vacancies),
        'is_running': task_scheduler.is_running
    }


async def cleanup_daily_cache() -> None:
    """Ежедневная очистка кешей (запускается по расписанию)"""
    task_scheduler.clear_processed_cache()
    global error_statistics
    error_statistics.clear()
    logger.info("Выполнена ежедневная очистка кешей")
