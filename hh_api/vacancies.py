"""
Работа с вакансиями через HH API
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from hh_api.client import hh_client
from config import Config


class VacancyManager:
    """Менеджер для работы с вакансиями"""

    def __init__(self):
        self.client = hh_client

    async def search_vacancies(
            self,
            keywords: Optional[str] = None,
            area_id: Optional[str] = None,
            salary: Optional[int] = None,
            experience: Optional[str] = None,
            employment: Optional[str] = None,
            schedule: Optional[str] = None,
            page: int = 0,
            per_page: int = 100
    ) -> Dict[str, Any]:
        """Поиск вакансий с фильтрами"""

        search_params = {
            'page': page,
            'per_page': min(per_page, Config.MAX_VACANCIES_PER_SEARCH),
            'period': Config.DEFAULT_SEARCH_PERIOD_DAYS
        }

        # Добавляем параметры фильтрации
        if keywords:
            search_params['text'] = keywords

        if area_id and area_id != 'remote':
            search_params['area'] = area_id
        elif area_id == 'remote':
            search_params['schedule'] = 'remote'

        if salary:
            search_params['salary'] = salary

        if experience:
            search_params['experience'] = experience

        if employment:
            search_params['employment'] = employment

        if schedule and area_id != 'remote':
            search_params['schedule'] = schedule

        # Дополнительные фильтры
        search_params['only_with_salary'] = 'false'  # Включать вакансии без указания зарплаты
        search_params['currency'] = 'RUR'  # Валюта зарплаты

        logger.info(f"Поиск вакансий с параметрами: {search_params}")

        try:
            result = await self.client.search_vacancies(**search_params)

            found_count = result.get('found', 0)
            items_count = len(result.get('items', []))

            logger.info(f"Найдено {found_count} вакансий, получено {items_count}")

            return result

        except Exception as e:
            logger.error(f"Ошибка поиска вакансий: {e}")
            raise

    async def get_vacancy_details(self, vacancy_id: str) -> Dict[str, Any]:
        """Получение подробной информации о вакансии"""

        try:
            vacancy = await self.client.get_vacancy_by_id(vacancy_id)
            logger.info(f"Получена детальная информация о вакансии {vacancy_id}")
            return vacancy

        except Exception as e:
            logger.error(f"Ошибка получения вакансии {vacancy_id}: {e}")
            raise

    async def get_suitable_vacancies(
            self,
            search_params: Dict[str, Any],
            exclude_companies: Optional[str] = None,
            exclude_keywords: Optional[str] = None,
            max_pages: int = 5
    ) -> List[Dict[str, Any]]:
        """Получение всех подходящих вакансий с учетом исключений"""

        all_vacancies = []

        # Подготавливаем списки исключений
        excluded_companies = []
        excluded_keywords = []

        if exclude_companies:
            excluded_companies = [comp.strip().lower() for comp in exclude_companies.split(',')]

        if exclude_keywords:
            excluded_keywords = [kw.strip().lower() for kw in exclude_keywords.split(',')]

        # Поиск по страницам
        for page in range(max_pages):
            try:
                search_params['page'] = page
                result = await self.search_vacancies(**search_params)

                vacancies = result.get('items', [])

                if not vacancies:
                    break  # Больше вакансий нет

                # Фильтруем вакансии
                for vacancy in vacancies:
                    if self._should_exclude_vacancy(
                            vacancy,
                            excluded_companies,
                            excluded_keywords
                    ):
                        continue

                    all_vacancies.append(vacancy)

                # Если получили меньше вакансий чем запрашивали, значит это последняя страница
                if len(vacancies) < search_params.get('per_page', 100):
                    break

            except Exception as e:
                logger.error(f"Ошибка получения страницы {page}: {e}")
                break

        logger.info(f"Получено {len(all_vacancies)} подходящих вакансий")
        return all_vacancies

    def _should_exclude_vacancy(
            self,
            vacancy: Dict[str, Any],
            excluded_companies: List[str],
            excluded_keywords: List[str]
    ) -> bool:
        """Проверка нужно ли исключить вакансию"""

        # Получаем текст для проверки
        vacancy_title = vacancy.get('name', '').lower()
        employer_name = vacancy.get('employer', {}).get('name', '').lower()

        # Проверяем исключенные компании
        for excluded_company in excluded_companies:
            if excluded_company in employer_name:
                logger.debug(f"Исключаем вакансию из-за компании: {employer_name}")
                return True

        # Проверяем исключенные ключевые слова
        for excluded_keyword in excluded_keywords:
            if excluded_keyword in vacancy_title:
                logger.debug(f"Исключаем вакансию из-за ключевого слова: {excluded_keyword}")
                return True

        return False

    async def get_vacancy_requirements(self, vacancy_id: str) -> Dict[str, Any]:
        """Извлечение требований из вакансии для анализа соответствия"""

        try:
            vacancy = await self.get_vacancy_details(vacancy_id)

            # Извлекаем ключевые навыки
            key_skills = []
            if vacancy.get('key_skills'):
                key_skills = [skill.get('name', '') for skill in vacancy['key_skills']]

            # Извлекаем требования из описания
            description = vacancy.get('description', '')

            # Информация об опыте
            experience = vacancy.get('experience', {})

            # Зарплата
            salary = vacancy.get('salary', {})

            return {
                'key_skills': key_skills,
                'description': description,
                'experience': experience,
                'salary': salary,
                'employment': vacancy.get('employment', {}),
                'schedule': vacancy.get('schedule', {})
            }

        except Exception as e:
            logger.error(f"Ошибка извлечения требований из вакансии {vacancy_id}: {e}")
            return {}


# Глобальный экземпляр менеджера вакансий
vacancy_manager = VacancyManager()