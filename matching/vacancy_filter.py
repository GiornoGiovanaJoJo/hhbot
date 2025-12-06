"""
Фильтр вакансий для откликов
Отсеивает вакансии с тестами и другими проблемами
"""

from typing import List, Dict, Any
from loguru import logger


class VacancyFilter:
    """Фильтр для вакансий"""

    # Признаки ненужных вакансий
    SKIP_KEYWORDS = [
        'test', 'тест',  # тесты
        'qa', 'qc',  # тестирование
        'qa engineer', 'qa specialist',
    ]

    @staticmethod
    def has_test_requirement(vacancy: Dict[str, Any]) -> bool:
        """Проверяет, требует ли вакансия прохождение теста"""
        
        # Проверяем по названию
        vacancy_name = vacancy.get('name', '').lower()
        for keyword in VacancyFilter.SKIP_KEYWORDS:
            if keyword.lower() in vacancy_name:
                logger.info(f"📱 Вакансия {vacancy.get('id')} скопирована - найден ключ '{keyword}' в названии")
                return True
        
        # Проверяем по описанию
        description = vacancy.get('description', '').lower() if vacancy.get('description') else ''
        if 'test' in description or 'тест' in description:
            # Проверяем, это именно требование теста, а не обычное дополнение
            test_indicators = ['must pass', 'должны пройти', 'test assignment', 'test task']
            for indicator in test_indicators:
                if indicator in description:
                    logger.info(f"📱 Вакансия {vacancy.get('id')} скопирована - требуется тест")
                    return True
        
        return False

    @staticmethod
    def is_archived(vacancy: Dict[str, Any]) -> bool:
        """Проверяет, закрыта ли вакансия"""
        return vacancy.get('archived', False)

    @staticmethod
    def is_valid(vacancy: Dict[str, Any]) -> bool:
        """Проверяет, валидна ли вакансия для отклика"""
        # Проверяем к тем, что бы скипнуть
        if VacancyFilter.has_test_requirement(vacancy):
            logger.debug(f"🙐 Вакансия {vacancy.get('id')} требует тест - пропускаем")
            return False
        
        if VacancyFilter.is_archived(vacancy):
            logger.debug(f"📋 Вакансия {vacancy.get('id')} архивирована - пропускаем")
            return False
        
        # Проверяем ID
        if not vacancy.get('id'):
            logger.debug("⚠️ Вакансия без ID - пропускаем")
            return False
        
        return True

    @staticmethod
    def filter_vacancies(vacancies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Отсеивает ненужные вакансии"""
        filtered = [v for v in vacancies if VacancyFilter.is_valid(v)]
        
        skipped = len(vacancies) - len(filtered)
        if skipped > 0:
            logger.info(f"📱 Пропущено {skipped} вакансий (тесты, архив, и т.d.)")
        
        return filtered


vacancy_filter = VacancyFilter()
