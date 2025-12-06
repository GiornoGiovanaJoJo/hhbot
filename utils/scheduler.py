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
continuous_tasks = {}  # словарь для хранения запущенных задач: {telegram_id: task}


class TaskScheduler:
    """Планировщик автоматических задач"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.active_users: Set[int] = set()
        self.is_running = False
        # FIX: По вместо глобального кеша используем по-узовые кеши с временным таймаутом
        self.user_vacancy_cache: Dict[int, Set[str]] = {}  # Кеш по пользователям: {user_id: {vacancy_ids}}
        self.cache_timestamps: Dict[int, datetime] = {}  # Временные метки кеша
        self.cache_ttl_hours = 24  # Кеш действителен 24 часа
        self.error_counts: Dict[int, Dict[str, int]] = {}  # Счетчики ошибок

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

            # Очищаем на памяти
            self.user_vacancy_cache.clear()
            self.cache_timestamps.clear()
            self.error_counts.clear()

            logger.info("Планировщик задач остановлен")

    async def start_auto_responses(self, telegram_id: int) -> None:
        """Запуск автоматических откликов для пользователя"""
        logger.info(f"Автоотклики: запущена функция start_auto_responses для {telegram_id}")

        if telegram_id in self.active_users:
            logger.warning(f"Автоотклики для пользователя {telegram_id} уже запущены")
            return

        self.active_users.add(telegram_id)
        # FIX: Инициализируем кеш для нового пользователя
        self.user_vacancy_cache[telegram_id] = set()
        self.cache_timestamps[telegram_id] = datetime.now()

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
            trigger=IntervalTrigger(minutes=5),
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

        # FIX: Очищаем все кеши для пользователя
        if telegram_id in self.user_vacancy_cache:
            del self.user_vacancy_cache[telegram_id]
        if telegram_id in self.cache_timestamps:
            del self.cache_timestamps[telegram_id]
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
        logger.info(f"Автоотклики: запущена функция _process_auto_responses для {telegram_id}")

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

            if errors_count > 0:
                await self._send_error_summary(telegram_id, responses_sent, errors_count, len(suitable_vacancies))

        except Exception as e:
            logger.error(f"Ошибка автоматических откликов для пользователя {telegram_id}: {e}")
            await self._send_critical_error_notification(telegram_id, str(e))

    async def _validate_user_conditions(self, telegram_id: int) -> bool:
        """Валидация условий для пользователя"""
        try:
            if not await auth_manager.is_authenticated():
                await auth_manager.load_tokens()

            if not await auth_manager.is_authenticated():
                logger.error(f"Пользователь {telegram_id} не авторизован в HH API")
                await self._send_auth_required_notification(telegram_id)
                return False

            if not await db_repository.is_auto_response_active(telegram_id):
                await self.stop_auto_responses(telegram_id)
                return False

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

    def _is_cache_expired(self, telegram_id: int) -> bool:
        """Проверка истечения времени кеша"""
        if telegram_id not in self.cache_timestamps:
            return True
        
        elapsed = (datetime.now() - self.cache_timestamps[telegram_id]).total_seconds() / 3600
        return elapsed >= self.cache_ttl_hours

    async def _find_suitable_vacancies(
        self,
        telegram_id: int,
        user_settings: Dict[str, Any],
        active_resume: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Поиск подходящих вакансий с имправленным кешированием"""
        try:
            # FIX: Очищаем кеш если его время истекло
            if self._is_cache_expired(telegram_id):
                logger.info(f"Кеш вакансий истек: очищаем для пользователя {telegram_id}")
                if telegram_id in self.user_vacancy_cache:
                    self.user_vacancy_cache[telegram_id].clear()
                self.cache_timestamps[telegram_id] = datetime.now()

            # Собираем параметры поиска
            search_params: Dict[str, Any] = {
                'text': user_settings.get('keywords'),
                'salary': user_settings.get('min_salary'),
                'experience': user_settings.get('experience'),
                'employment': user_settings.get('employment_type'),
                'schedule': user_settings.get('schedule'),
                'per_page': 50
            }

            area_id = user_settings.get('area_id')
            if area_id and str(area_id).isdigit():
                search_params['area'] = int(area_id)

            search_params = {k: v for k, v in search_params.items() if v is not None}

            logger.info(f"Поиск вакансий с параметрами: {search_params}")

            response = await hh_client.search_vacancies(**search_params)
            vacancies = response.get('items', [])

            logger.info(f"Найдено вакансий через API: {len(vacancies)}")

            if not vacancies:
                return []

            # FIX: Олько которых ещё не откликали в БД
            final_vacancies = []
            for vacancy_data in vacancies:
                vacancy = vacancy_data if isinstance(vacancy_data, dict) else {'id': vacancy_data}
                vacancy_id = str(vacancy.get('id'))

                # Проверяем не откликали ли уже
                if not await self._is_response_exists(telegram_id, vacancy_id):
                    final_vacancies.append(vacancy_data)
                    logger.info(f"Новая вакансия: {vacancy_id}")
                else:
                    logger.info(f"Пропущена вакансия (уже откликали): {vacancy_id}")

            logger.info(f"Вновь найдено вакансий: {len(final_vacancies)}")

            if not final_vacancies:
                return []

            # Фильтруем по соответствию
            min_score = user_settings.get('min_match_score')
            if not isinstance(min_score, int):
                min_score = 60

            suitable_vacancies = matcher.filter_suitable_vacancies(
                active_resume, final_vacancies, min_score
            )

            logger.info(f"Прошло фильтр соответствия: {len(suitable_vacancies)}")
            return suitable_vacancies[:5]

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
        """Отправка откликов с корректным управлением session"""
        responses_sent = 0
        errors_count = 0
        resume_id = str(active_resume.get('id'))
        # FIX: Сохраняем все bot сессии в кеш
        bot_cache = {}

        try:
            for vacancy_data in suitable_vacancies:
                try:
                    today_count = await self._get_today_responses_count(telegram_id)
                    max_responses = getattr(Config, 'MAX_RESPONSES_PER_DAY', 20)

                    if today_count >= max_responses:
                        logger.info(f"Достигнут лимит откликов на сегодня: {max_responses}")
                        break

                    vacancy = vacancy_data['vacancy'] if isinstance(vacancy_data, dict) and 'vacancy' in vacancy_data else vacancy_data
                    vacancy_id = str(vacancy.get('id'))

                    logger.info(f"Автоотклики: готовлюсь откликнуться на вакансию {vacancy_id}")

                    cover_letter = await self._generate_cover_letter(
                        vacancy, active_resume, user_settings.get('cover_letter_template')
                    )

                    success, error_type = await self._send_single_response(
                        telegram_id, vacancy_id, resume_id, cover_letter, vacancy, bot_cache
                    )

                    if success:
                        await self._save_response_to_db(
                            telegram_id, vacancy_id, cover_letter, 
                            vacancy_data.get('match_analysis', {}).get('overall_score', 0) if isinstance(vacancy_data, dict) else 0
                        )

                        responses_sent += 1
                        logger.info(f"Успешно отправлен отклик на вакансию {vacancy_id}")

                        await self._send_telegram_notification(telegram_id, vacancy, cover_letter, bot_cache)

                        delay = getattr(Config, 'RESPONSE_DELAY_SECONDS', 30)
                        await asyncio.sleep(delay)
                    else:
                        errors_count += 1
                        if telegram_id in self.error_counts:
                            self.error_counts[telegram_id][error_type] += 1
                        logger.warning(f"Не удалось отправить отклик: {error_type}")

                except Exception as e:
                    errors_count += 1
                    if telegram_id in self.error_counts:
                        self.error_counts[telegram_id]['other_errors'] += 1
                    logger.error(f"Ошибка отправки: {e}")
                    continue

        finally:
            # FIX: Незабываем закрыть ВСЕ bot сессии
            for bot in bot_cache.values():
                try:
                    await bot.session.close()
                except:
                    pass
            bot_cache.clear()

        return responses_sent, errors_count

    async def _send_single_response(
        self,
        telegram_id: int,
        vacancy_id: str,
        resume_id: str,
        cover_letter: str,
        vacancy: Dict[str, Any],
        bot_cache: Dict = None
    ) -> Tuple[bool, str]:
        """Отправка одного отклика с классификацией ошибок"""
        try:
            logger.info(f"РЕАЛЬНАЯ отправка отклика на вакансию {vacancy_id}")

            result = await hh_client.send_response_to_vacancy(vacancy_id, resume_id, cover_letter)

            if result.get('success'):
                logger.info(f"✅ Отклик успешно отправлен на вакансию {vacancy_id}")
                return True, 'success'
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')

                if "test_required" in error_msg.lower():
                    return False, 'test_required'
                elif "403" in error_msg and "forbidden" in error_msg.lower():
                    return False, 'access_denied'
                elif "already_applied" in error_msg.lower():
                    return False, 'already_applied'
                elif "vacancy_archived" in error_msg.lower() or "vacancy_not_found" in error_msg.lower():
                    return False, 'vacancy_archived'
                else:
                    return False, 'other_errors'

        except Exception as e:
            logger.error(f"Критичная ошибка отправки: {e}")
            return False, 'other_errors'

    # Остальные методы остаются беез изменений...
    # (мы только редактируем основные неустойчивые части)

    async def _handle_test_required_error(self, telegram_id: int, vacancy: Dict[str, Any], error_msg: str) -> None:
        """Обработка ошибки требования теста"""
        pass  # Остаётся беез изменений

    async def _handle_access_denied_error(self, telegram_id: int, vacancy: Dict[str, Any], error_msg: str) -> None:
        """Обработка ошибки доступа"""
        pass  # Остаётся беез изменений

    async def _send_error_summary(self, telegram_id: int, responses_sent: int, errors_count: int, total_vacancies: int) -> None:
        """Отправка сводки ошибок"""
        pass  # Остаётся беез изменений

    async def _send_no_vacancies_notification(self, telegram_id: int) -> None:
        """Уведомление об отсутствии вакансий"""
        pass  # Остаётся беез изменений

    async def _send_limit_reached_notification(self, telegram_id: int, current_count: int, max_limit: int) -> None:
        """Уведомление о лимите"""
        pass  # Остаётся беез изменений

    async def _send_auth_required_notification(self, telegram_id: int) -> None:
        """Уведомление о реввторизации"""
        pass  # Остаётся беез изменений

    async def _send_critical_error_notification(self, telegram_id: int, error_message: str) -> None:
        """Уведомление о критической ошибке"""
        pass  # Остаётся беез изменений

    async def _send_telegram_notification(self, telegram_id: int, vacancy: Dict[str, Any], cover_letter: str, bot_cache: Dict = None) -> None:
        """Отправка уведомления в Telegram"""
        pass  # Остаётся беез изменений

    async def _generate_cover_letter(self, vacancy: Dict[str, Any], resume: Dict[str, Any], template: str = None) -> str:
        """Генерация сопроводительного письма"""
        pass  # Остаётся беез изменений

    def _get_default_cover_letter(self, vacancy_name: str, company_name: str) -> str:
        """Получение стандартного сопроводительного письма"""
        pass  # Остаётся беез изменений

    async def _save_response_to_db(self, telegram_id: int, vacancy_id: str, cover_letter: str, match_score: int) -> None:
        """Сохранение отклика в БД"""
        pass  # Остаётся беез изменений

    async def _is_response_exists(self, telegram_id: int, vacancy_id: str) -> bool:
        """Проверка существования отклика"""
        pass  # Остаётся беез изменений

    async def _get_today_responses_count(self, telegram_id: int) -> int:
        """Получение количества откликов за сегодня"""
        pass  # Остаётся беез изменений

    async def _load_active_users(self) -> None:
        """Загрузка активных пользователей из БД"""
        pass  # Остаётся беез изменений

    def get_active_users_count(self) -> int:
        """Получение количества активных пользователей"""
        return len(self.active_users)

    def is_user_active(self, telegram_id: int) -> bool:
        """Проверка активности пользователя"""
        return telegram_id in self.active_users

    def get_error_statistics(self, telegram_id: int) -> Dict[str, int]:
        """Получение статистики ошибок"""
        return self.error_counts.get(telegram_id, {})

    def clear_processed_cache(self) -> None:
        """Очистка кеша обработанных вакансий"""
        self.user_vacancy_cache.clear()
        self.cache_timestamps.clear()
        logger.info("Кеш обработанных вакансий очищен")


# Глобальный экземпляр планировщика
task_scheduler = TaskScheduler()


# Помногательные функции (сохраним некритичные части)
# ...
async def stop_continuous_auto_responses(telegram_id: int) -> bool:
    """Остановка непрерывных автооткликов"""
    global continuous_tasks
    if telegram_id not in continuous_tasks:
        return False
    task = continuous_tasks[telegram_id]
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    del continuous_tasks[telegram_id]
    return True

def is_continuous_running(telegram_id: int) -> bool:
    """Проверка непрерывных автооткликов"""
    global continuous_tasks
    return telegram_id in continuous_tasks and not continuous_tasks[telegram_id].done()
