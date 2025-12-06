"""
Планировщик задач для автоматических откликов
"""
import asyncio
from typing import Dict, Set, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config import Config
from database.repository import db_repository
from hh_api.client import hh_client
from hh_api.auth import auth_manager
from matching.analyzer import matcher
from matching.vacancy_filter import vacancy_filter

# Глобальные переменные для управления непрерывными автоответами
continuous_tasks = {}


class TaskScheduler:
    """Планировщик автоматических задач"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.active_users: Set[int] = set()
        self.is_running = False
        self.user_vacancy_cache: Dict[int, Set[str]] = {}
        self.cache_timestamps: Dict[int, datetime] = {}
        self.cache_ttl_hours = 24
        self.error_counts: Dict[int, Dict[str, int]] = {}
        # FIX: Чёрный список вакансий, требующих тест
        self.blacklist_test_required: Set[str] = set()
        # Отслеживаем время последней попытки для каждой вакансии с тестом
        self.test_vacancy_attempts: Dict[str, int] = {}
        # FIX: Кеш для сопроводительного письма
        self._cover_letter_cache: Optional[str] = None
        self._cover_letter_cache_time: Optional[datetime] = None
        # Нижний порог скора для фильтрации
        self.default_min_score = 50  # Первоначальный порог достаточно низкий

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

            global continuous_tasks
            for telegram_id in list(continuous_tasks.keys()):
                await stop_continuous_auto_responses(telegram_id)

            self.user_vacancy_cache.clear()
            self.cache_timestamps.clear()
            self.error_counts.clear()
            self.blacklist_test_required.clear()
            self.test_vacancy_attempts.clear()

            logger.info("Планировщик задач остановлен")

    async def start_auto_responses(self, telegram_id: int) -> None:
        """Запуск автоматических откликов для пользователя"""
        logger.info(f"Автоотклики: запущена функция start_auto_responses для {telegram_id}")

        if telegram_id in self.active_users:
            logger.warning(f"Автоотклики для пользователя {telegram_id} уже запущены")
            return

        self.active_users.add(telegram_id)
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
            if not await self._validate_user_conditions(telegram_id):
                return

            user_settings = await db_repository.get_user_settings(telegram_id)
            if not user_settings:
                logger.warning(f"Нет настроек для пользователя {telegram_id}")
                return

            active_resume = await db_repository.get_active_resume(telegram_id)
            if not active_resume:
                logger.warning(f"Нет активного резюме для пользователя {telegram_id}")
                return

            # Получаем порог скора (или используем дефолт)
            min_score = user_settings.get('min_match_score')
            if not isinstance(min_score, int):
                min_score = self.default_min_score

            logger.info(f"🏗️ Использую нижний порог скора: {min_score}")

            suitable_vacancies = await self._find_suitable_vacancies(
                telegram_id, user_settings, active_resume, min_score
            )

            logger.info(f"Найдено подходящих вакансий: {len(suitable_vacancies)} для пользователя {telegram_id}")

            if not suitable_vacancies:
                logger.info(f"Подходящих новых вакансий не найдено для пользователя {telegram_id}")
                await self._send_no_vacancies_notification(telegram_id)
                return

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
            if today_count is None:
                logger.warning(f"today_count вернул None для пользователя {telegram_id}, используем 0")
                today_count = 0
            
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
        active_resume: Dict[str, Any],
        min_score: int = None
    ) -> List[Dict[str, Any]]:
        """Поиск подходящих вакансий"""
        try:
            # Если мин_скор не передан, используем дефолт
            if min_score is None:
                min_score = user_settings.get('min_match_score')
                if not isinstance(min_score, int):
                    min_score = self.default_min_score

            if self._is_cache_expired(telegram_id):
                logger.info(f"Кеш вакансий истек: очищаем для пользователя {telegram_id}")
                if telegram_id in self.user_vacancy_cache:
                    self.user_vacancy_cache[telegram_id].clear()
                self.cache_timestamps[telegram_id] = datetime.now()

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

            logger.info(f"🔍 Поиск вакансий с параметрами: {search_params}")

            response = await hh_client.search_vacancies(**search_params)
            vacancies = response.get('items', [])

            logger.info(f"Найдено вакансий через API: {len(vacancies)}")

            if not vacancies:
                return []

            # FIX: Отсеиваем вакансии с тестами ПО НАЗВАНИЮ
            vacancies = vacancy_filter.filter_vacancies(vacancies)
            logger.info(f"После фильтра (тесты, архив): {len(vacancies)} вакансий")

            if not vacancies:
                logger.warning(f"У всех вакансий по нашим критериям вид несовместимых с искомым")
                return []

            final_vacancies = []
            for vacancy_data in vacancies:
                vacancy = vacancy_data if isinstance(vacancy_data, dict) else {'id': vacancy_data}
                vacancy_id = str(vacancy.get('id'))

                # FIX: Пропускаем вакансии из чёрного списка
                if vacancy_id in self.blacklist_test_required:
                    logger.debug(f"⚫️ Вакансия {vacancy_id} в чёрном списке (требует тест) - пропускаем")
                    continue

                if not await self._is_response_exists(telegram_id, vacancy_id):
                    final_vacancies.append(vacancy_data)
                    logger.info(f"Новая вакансия: {vacancy_id}")

            logger.info(f"Вновь найдено вакансий: {len(final_vacancies)}")

            if not final_vacancies:
                return []

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
        """Отправка откликов"""
        responses_sent = 0
        errors_count = 0
        resume_id = str(active_resume.get('id'))

        try:
            for vacancy_data in suitable_vacancies:
                try:
                    today_count = await self._get_today_responses_count(telegram_id)
                    if today_count is None:
                        logger.warning(f"today_count вернул None в _send_responses для {telegram_id}, используем 0")
                        today_count = 0
                    
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
                        telegram_id, vacancy_id, resume_id, cover_letter, vacancy
                    )

                    if success:
                        await self._save_response_to_db(
                            telegram_id, vacancy_id, cover_letter, 
                            vacancy_data.get('match_analysis', {}).get('overall_score', 0) if isinstance(vacancy_data, dict) else 0
                        )

                        responses_sent += 1
                        logger.info(f"Успешно отправлен отклик на вакансию {vacancy_id}")

                        await self._send_telegram_notification(telegram_id, vacancy, cover_letter)

                        delay = getattr(Config, 'RESPONSE_DELAY_SECONDS', 30)
                        await asyncio.sleep(delay)
                    else:
                        errors_count += 1
                        
                        # FIX: Если тест требуется - добавляем в чёрный список
                        if error_type == 'test_required':
                            self.blacklist_test_required.add(vacancy_id)
                            logger.info(f"🚫 Вакансия {vacancy_id} требует тест, добавляем в чёрный список")
                        
                        if telegram_id in self.error_counts:
                            self.error_counts[telegram_id][error_type] += 1
                        logger.warning(f"Не удалось отправить отклик: {error_type}")

                except Exception as e:
                    errors_count += 1
                    if telegram_id in self.error_counts:
                        self.error_counts[telegram_id]['other_errors'] += 1
                    logger.error(f"Ошибка отправки: {e}")
                    continue

        except Exception as e:
            logger.error(f"Критичная ошибка в _send_responses: {e}")

        return responses_sent, errors_count

    async def _send_single_response(
        self,
        telegram_id: int,
        vacancy_id: str,
        resume_id: str,
        cover_letter: str,
        vacancy: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Отправка одного отклика"""
        try:
            logger.info(f"Отправка отклика на вакансию {vacancy_id}")

            result = await hh_client.send_response_to_vacancy(vacancy_id, resume_id, cover_letter)

            if result.get('success'):
                logger.info(f"✅ Отклик успешно отправлен на вакансию {vacancy_id}")
                return True, 'success'
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')

                if "test_required" in error_msg.lower() or "must process test" in error_msg.lower():
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

    async def _send_error_summary(self, telegram_id: int, responses_sent: int, errors_count: int, total_vacancies: int) -> None:
        """Отправка сводки ошибок"""
        pass

    async def _send_no_vacancies_notification(self, telegram_id: int) -> None:
        """Уведомление об отсутствии вакансий"""
        pass

    async def _send_limit_reached_notification(self, telegram_id: int, current_count: int, max_limit: int) -> None:
        """Уведомление о лимите"""
        pass

    async def _send_auth_required_notification(self, telegram_id: int) -> None:
        """Уведомление о реавторизации"""
        pass

    async def _send_critical_error_notification(self, telegram_id: int, error_message: str) -> None:
        """Уведомление о критической ошибке"""
        pass

    async def _send_telegram_notification(self, telegram_id: int, vacancy: Dict[str, Any], cover_letter: str) -> None:
        """Отправка уведомления в Telegram"""
        pass

    async def _generate_cover_letter(self, vacancy: Dict[str, Any], resume: Dict[str, Any], template: str = None) -> str:
        """Генерация сопроводительного письма"""
        # FIX: НА РЕАЛЬНО загружаем сопроводительное письмо
        try:
            # Пробуем тю путь что надо
            cover_letter_path = Path(template) if template else Path('config/cover_letter_template.txt')
            
            # Также пробуем абсолютные пути
            if not cover_letter_path.exists():
                cover_letter_path = Path('.') / 'config' / 'cover_letter_template.txt'
            
            if not cover_letter_path.exists():
                logger.error(f"Не найден шаблон сопроводительного письма по пути: {cover_letter_path}")
                return ""
            
            with open(cover_letter_path, 'r', encoding='utf-8') as f:
                cover_letter = f.read()
            
            logger.info(f"📘 Сопроводительное письмо загружено ({len(cover_letter)} символов)")
            return cover_letter
            
        except Exception as e:
            logger.error(f"Ошибка генерации сопроводительного письма: {e}")
            return ""

    async def _save_response_to_db(self, telegram_id: int, vacancy_id: str, cover_letter: str, match_score: int) -> None:
        """Сохранение отклика в БД"""
        pass

    async def _is_response_exists(self, telegram_id: int, vacancy_id: str) -> bool:
        """Проверка существования отклика"""
        pass

    async def _get_today_responses_count(self, telegram_id: int) -> Optional[int]:
        """Получение количества откликов за сегодня"""
        try:
            stats = await db_repository.get_today_stats(telegram_id)
            return stats.get('today_count', 0)
        except Exception as e:
            logger.error(f"Ошибка получения статистики тодая: {e}")
            return None

    async def _load_active_users(self) -> None:
        """Лоадинг активных пользователей из БД"""
        pass

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

    def get_blacklist_count(self) -> int:
        """Получение количества вакансий в чёрном списке"""
        return len(self.blacklist_test_required)

    def clear_blacklist(self) -> None:
        """Очистка чёрного списка вакансий"""
        self.blacklist_test_required.clear()
        self.test_vacancy_attempts.clear()
        logger.info("Чёрный список вакансий очищен")


task_scheduler = TaskScheduler()


async def start_continuous_auto_responses(telegram_id: int) -> bool:
    """Запуск непрерывных автоответов"""
    global continuous_tasks

    if telegram_id in continuous_tasks and not continuous_tasks[telegram_id].done():
        logger.warning(f"Непрерывные автоотклики уже запущены для {telegram_id}")
        return False

    logger.info(f"Запуск непрерывных автоответов для {telegram_id}")

    task = asyncio.create_task(_continuous_auto_responses_loop(telegram_id))
    continuous_tasks[telegram_id] = task

    logger.info(f"Непрерывные автоотклики запущены для {telegram_id}")
    return True


async def _continuous_auto_responses_loop(telegram_id: int) -> None:
    """Основной цикл непрерывных автоответов"""
    logger.info(f"Цикл непрерывных откликов начался для {telegram_id}")

    iteration = 0
    error_count = 0
    max_consecutive_errors = 5

    try:
        while True:
            iteration += 1
            logger.info(f"Итерация {iteration} непрерывных откликов для {telegram_id}")

            try:
                if not await task_scheduler._validate_user_conditions(telegram_id):
                    logger.warning(f"Условия не пройдены, остановка непрерывных откликов для {telegram_id}")
                    break

                user_settings = await db_repository.get_user_settings(telegram_id)
                active_resume = await db_repository.get_active_resume(telegram_id)

                if not user_settings or not active_resume:
                    logger.warning(f"Нет настроек или резюме для {telegram_id}")
                    break

                suitable_vacancies = await task_scheduler._find_suitable_vacancies(
                    telegram_id, user_settings, active_resume
                )

                if suitable_vacancies:
                    responses_sent, errors_count = await task_scheduler._send_responses(
                        telegram_id, suitable_vacancies, active_resume, user_settings
                    )

                    logger.info(
                        f"Непрерывные отклики итерация {iteration}: "
                        f"отправлено {responses_sent}, ошибок {errors_count}"
                    )

                    if iteration % 10 == 0:
                        total_today = await task_scheduler._get_today_responses_count(telegram_id)
                        logger.info(f"Статистика за сегодня: {total_today} откликов для {telegram_id}")

                    error_count = 0
                else:
                    logger.info(f"Нет новых подходящих вакансий для {telegram_id}")

                await asyncio.sleep(60)

            except asyncio.CancelledError:
                logger.info(f"Непрерывные автоотклики отменены для {telegram_id}")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Ошибка в цикле непрерывных откликов для {telegram_id}: {e}")

                if error_count >= max_consecutive_errors:
                    logger.error(
                        f"Превышено максимальное количество ошибок ({max_consecutive_errors}), "
                        f"остановка для {telegram_id}"
                    )
                    await task_scheduler._send_critical_error_notification(
                        telegram_id,
                        f"Слишком много ошибок в непрерывных автоответах. Автоотклики остановлены."
                    )
                    break

                await asyncio.sleep(60)

    finally:
        logger.info(f"Цикл непрерывных откликов завершился для {telegram_id}")
        if telegram_id in continuous_tasks:
            del continuous_tasks[telegram_id]


async def stop_continuous_auto_responses(telegram_id: int) -> None:
    """Остановка непрерывных автоответов"""
    global continuous_tasks

    if telegram_id not in continuous_tasks:
        logger.warning(f"Непрерывные автоответы не запущены для {telegram_id}")
        return

    task = continuous_tasks[telegram_id]
    if not task.done():
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

    logger.info(f"Непрерывные автоответы остановлены для {telegram_id}")
