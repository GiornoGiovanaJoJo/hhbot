"""
Фильтры для отбора подходящих вакансий
"""

from typing import Dict, Any, List, Optional, Set
import re
from loguru import logger


class VacancyFilters:
    """Система фильтров для отбора вакансий"""

    def __init__(self):
        self.spam_keywords = {
            'млм', 'сетевой маркетинг', 'амвей', 'гербалайф', 'эйвон',
            'орифлэйм', 'форевер', 'нутрилайт', 'тяньши', 'парфюм лидер',
            'работа на дому', 'дополнительный доход', 'подработка студентам',
            'фриланс', 'удаленно без опыта', 'легкий заработок'
        }

        self.suspicious_patterns = [
            r'от \d+\s*тыс\.?\s*руб\.?\s*в\s*день',
            r'доход\s+до\s+\d+\s*тыс',
            r'без\s+вложений',
            r'свободный\s+график.*дом',
            r'подработка.*\d+\s*часов?'
        ]

    def filter_by_salary(
            self,
            vacancy: Dict[str, Any],
            min_salary: Optional[int] = None
    ) -> bool:
        """Фильтр по зарплате"""

        if not min_salary:
            return True

        salary = vacancy.get('salary')
        if not salary:
            return True  # Пропускаем вакансии без указания зарплаты

        salary_from = salary.get('from')
        salary_to = salary.get('to')

        # Если указана только верхняя граница, используем её
        if salary_from is None and salary_to:
            return salary_to >= min_salary

        # Если указана только нижняя граница или обе, используем нижнюю
        if salary_from:
            return salary_from >= min_salary

        return True

    def filter_by_experience(
            self,
            vacancy: Dict[str, Any],
            user_experience: Optional[str] = None
    ) -> bool:
        """Фильтр по опыту работы"""

        if not user_experience:
            return True

        vacancy_exp = vacancy.get('experience', {}).get('id')
        if not vacancy_exp:
            return True

        # Маппинг пользовательского опыта на требования вакансии
        experience_compatibility = {
            'noExperience': ['noExperience'],
            'between1And3': ['noExperience', 'between1And3'],
            'between3And6': ['noExperience', 'between1And3', 'between3And6'],
            'moreThan6': ['noExperience', 'between1And3', 'between3And6', 'moreThan6']
        }

        compatible_levels = experience_compatibility.get(user_experience, [])
        return vacancy_exp in compatible_levels

    def filter_by_employment_type(
            self,
            vacancy: Dict[str, Any],
            desired_employment: Optional[str] = None
    ) -> bool:
        """Фильтр по типу занятости"""

        if not desired_employment:
            return True

        vacancy_employment = vacancy.get('employment', {}).get('id')
        if not vacancy_employment:
            return True

        return vacancy_employment == desired_employment

    def filter_by_schedule(
            self,
            vacancy: Dict[str, Any],
            desired_schedule: Optional[str] = None
    ) -> bool:
        """Фильтр по графику работы"""

        if not desired_schedule:
            return True

        vacancy_schedule = vacancy.get('schedule', {}).get('id')
        if not vacancy_schedule:
            return True

        return vacancy_schedule == desired_schedule

    def filter_spam_vacancies(self, vacancy: Dict[str, Any]) -> bool:
        """Фильтр спам-вакансий"""

        vacancy_name = vacancy.get('name', '').lower()
        employer_name = vacancy.get('employer', {}).get('name', '').lower()

        # Проверяем спам-ключевые слова
        combined_text = f"{vacancy_name} {employer_name}"

        for spam_word in self.spam_keywords:
            if spam_word in combined_text:
                logger.debug(f"Отфильтрована спам-вакансия по слову '{spam_word}': {vacancy_name}")
                return False

        # Проверяем подозрительные паттерны
        for pattern in self.suspicious_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                logger.debug(f"Отфильтрована подозрительная вакансия по паттерну: {vacancy_name}")
                return False

        return True

    def filter_by_company_blacklist(
            self,
            vacancy: Dict[str, Any],
            blacklisted_companies: Optional[List[str]] = None
    ) -> bool:
        """Фильтр по черному списку компаний"""

        if not blacklisted_companies:
            return True

        employer_name = vacancy.get('employer', {}).get('name', '').lower()

        for blacklisted in blacklisted_companies:
            if blacklisted.lower() in employer_name:
                logger.debug(f"Отфильтрована вакансия из черного списка: {employer_name}")
                return False

        return True

    def filter_by_keywords_blacklist(
            self,
            vacancy: Dict[str, Any],
            blacklisted_keywords: Optional[List[str]] = None
    ) -> bool:
        """Фильтр по черному списку ключевых слов"""

        if not blacklisted_keywords:
            return True

        vacancy_name = vacancy.get('name', '').lower()

        for keyword in blacklisted_keywords:
            if keyword.lower() in vacancy_name:
                logger.debug(f"Отфильтрована вакансия по ключевому слову '{keyword}': {vacancy_name}")
                return False

        return True

    def filter_by_location(
            self,
            vacancy: Dict[str, Any],
            desired_areas: Optional[List[str]] = None
    ) -> bool:
        """Фильтр по локации"""

        if not desired_areas:
            return True

        vacancy_area = vacancy.get('area', {}).get('name', '').lower()

        for area in desired_areas:
            if area.lower() in vacancy_area:
                return True

        return False

    def apply_all_filters(
            self,
            vacancies: List[Dict[str, Any]],
            filters_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Применение всех фильтров к списку вакансий"""

        filtered_vacancies = []

        for vacancy in vacancies:
            # Проверяем каждый фильтр
            if not self.filter_spam_vacancies(vacancy):
                continue

            if not self.filter_by_salary(vacancy, filters_config.get('min_salary')):
                continue

            if not self.filter_by_experience(vacancy, filters_config.get('experience')):
                continue

            if not self.filter_by_employment_type(vacancy, filters_config.get('employment_type')):
                continue

            if not self.filter_by_schedule(vacancy, filters_config.get('schedule')):
                continue

            # Черные списки
            blacklisted_companies = filters_config.get('exclude_companies', '').split(',') if filters_config.get(
                'exclude_companies') else None
            if not self.filter_by_company_blacklist(vacancy, blacklisted_companies):
                continue

            blacklisted_keywords = filters_config.get('exclude_keywords', '').split(',') if filters_config.get(
                'exclude_keywords') else None
            if not self.filter_by_keywords_blacklist(vacancy, blacklisted_keywords):
                continue

            # Вакансия прошла все фильтры
            filtered_vacancies.append(vacancy)

        logger.info(f"Фильтры: {len(vacancies)} -> {len(filtered_vacancies)} вакансий")
        return filtered_vacancies

    def get_rejection_reason(
            self,
            vacancy: Dict[str, Any],
            filters_config: Dict[str, Any]
    ) -> Optional[str]:
        """Получение причины отклонения вакансии"""

        if not self.filter_spam_vacancies(vacancy):
            return "Спам-вакансия"

        if not self.filter_by_salary(vacancy, filters_config.get('min_salary')):
            return f"Зарплата ниже {filters_config.get('min_salary')}"

        if not self.filter_by_experience(vacancy, filters_config.get('experience')):
            return "Несоответствие по опыту"

        if not self.filter_by_employment_type(vacancy, filters_config.get('employment_type')):
            return "Несоответствие по типу занятости"

        if not self.filter_by_schedule(vacancy, filters_config.get('schedule')):
            return "Несоответствие по графику работы"

        blacklisted_companies = filters_config.get('exclude_companies', '').split(',') if filters_config.get(
            'exclude_companies') else None
        if not self.filter_by_company_blacklist(vacancy, blacklisted_companies):
            return "Компания в черном списке"

        blacklisted_keywords = filters_config.get('exclude_keywords', '').split(',') if filters_config.get(
            'exclude_keywords') else None
        if not self.filter_by_keywords_blacklist(vacancy, blacklisted_keywords):
            return "Ключевое слово в черном списке"

        return None


# Глобальный экземпляр фильтров
vacancy_filters = VacancyFilters()