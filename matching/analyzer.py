"""
Анализ соответствия резюме и вакансий
Фильтрация по опыту, навыкам и другим критериям
"""

import re
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timedelta

from loguru import logger

from config import Config


class ResumeVacancyMatcher:
    """Анализатор соответствия резюме и вакансий"""

    def __init__(self):
        self.stopwords = {
            'и', 'в', 'на', 'с', 'по', 'для', 'или', 'а', 'но', 'от', 'до',
            'при', 'без', 'под', 'над', 'о', 'об', 'за', 'перед', 'после',
            'work', 'experience', 'skills', 'the', 'and', 'or', 'in', 'at',
            'with', 'for', 'from', 'to', 'of'
        }

    def extract_skills_from_text(self, text: str) -> Set[str]:
        """Извлечение навыков из текста"""
        if not text:
            return set()

        # Приводим к нижнему регистру
        text_lower = text.lower()

        # Удаляем знаки препинания и разбиваем на слова
        words = re.findall(r'\b\w+\b', text_lower)

        # Убираем стоп-слова и короткие слова
        skills = {
            word for word in words
            if len(word) >= 2 and word not in self.stopwords
        }

        # Поиск составных навыков (например, "machine learning", "data science")
        compound_skills = set()
        text_normalized = re.sub(r'[^\w\s]', ' ', text_lower)

        # Паттерны для поиска технических навыков
        tech_patterns = [
            r'\b(?:python|java|javascript|c\+\+|c#|php|ruby|go|rust|kotlin)\b',
            r'\b(?:sql|mysql|postgresql|mongodb|redis|elasticsearch)\b',
            r'\b(?:react|vue|angular|django|flask|spring|laravel)\b',
            r'\b(?:docker|kubernetes|aws|azure|gcp|linux|windows)\b',
            r'\b(?:git|svn|jenkins|gitlab|github)\b',
            r'\b(?:machine learning|data science|deep learning|ai)\b',
            r'\b(?:photoshop|illustrator|figma|sketch)\b'
        ]

        for pattern in tech_patterns:
            matches = re.findall(pattern, text_normalized)
            compound_skills.update(matches)

        return skills.union(compound_skills)

    def calculate_experience_years(self, experience_data: List[Dict[str, Any]]) -> float:
        """Расчет общего опыта работы в годах"""
        total_months = 0

        for exp in experience_data:
            start_str = exp.get('start')
            end_str = exp.get('end')

            if not start_str:
                continue

            try:
                start_date = datetime.strptime(start_str, '%Y-%m-%d')

                if end_str:
                    end_date = datetime.strptime(end_str, '%Y-%m-%d')
                else:
                    end_date = datetime.now()  # Текущее место работы

                # Рассчитываем разность в месяцах
                months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                total_months += months_diff

            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка парсинга даты опыта: {e}")
                continue

        return round(total_months / 12, 1)

    def extract_salary_range(self, salary_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Извлечение информации о зарплате"""
        if not salary_data:
            return {'min': None, 'max': None, 'currency': None}

        return {
            'min': salary_data.get('from'),
            'max': salary_data.get('to'),
            'currency': salary_data.get('currency')
        }

    def match_experience_level(
        self,
        resume_experience: float,
        vacancy_experience: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Сопоставление уровня опыта"""

        vacancy_exp_id = vacancy_experience.get('id', '')
        vacancy_exp_name = vacancy_experience.get('name', '')

        # Маппинг уровней опыта HH
        experience_mapping = {
            'noExperience': {'min': 0, 'max': 0},
            'between1And3': {'min': 1, 'max': 3},
            'between3And6': {'min': 3, 'max': 6},
            'moreThan6': {'min': 6, 'max': float('inf')}
        }

        required_range = experience_mapping.get(vacancy_exp_id, {'min': 0, 'max': 0})

        matches = (
            resume_experience >= required_range['min'] and
            resume_experience <= required_range['max']
        )

        return {
            'matches': matches,
            'resume_years': resume_experience,
            'required_min': required_range['min'],
            'required_max': required_range['max'],
            'vacancy_requirement': vacancy_exp_name
        }

    def calculate_skills_match(
        self,
        resume_skills: Set[str],
        vacancy_skills: Set[str]
    ) -> Dict[str, Any]:
        """Расчет совпадения навыков"""

        if not vacancy_skills:
            return {
                'match_percentage': 100,  # Если навыки не указаны, считаем что подходит
                'matched_skills': set(),
                'missing_skills': set(),
                'total_required': 0
            }

        matched_skills = resume_skills.intersection(vacancy_skills)
        missing_skills = vacancy_skills - resume_skills

        match_percentage = (len(matched_skills) / len(vacancy_skills)) * 100 if vacancy_skills else 100

        return {
            'match_percentage': round(match_percentage, 1),
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'total_required': len(vacancy_skills)
        }

    def analyze_vacancy_match(
        self,
        resume_data: Dict[str, Any],
        vacancy_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Полный анализ соответствия резюме и вакансии"""

        # Извлекаем навыки из резюме
        resume_text = ' '.join([
            resume_data.get('title', ''),
            resume_data.get('skills', ''),
            ' '.join([exp.get('position', '') + ' ' + exp.get('description', '')
                     for exp in resume_data.get('experience', [])])
        ])
        resume_skills = self.extract_skills_from_text(resume_text)

        # Извлекаем навыки из вакансии
        vacancy_text = ' '.join([
            vacancy_data.get('name', ''),
            vacancy_data.get('description', ''),
            ' '.join([skill.get('name', '') for skill in vacancy_data.get('key_skills', [])])
        ])
        vacancy_skills = self.extract_skills_from_text(vacancy_text)

        # Рассчитываем опыт
        resume_experience = self.calculate_experience_years(resume_data.get('experience', []))

        # Анализ опыта
        experience_match = self.match_experience_level(
            resume_experience,
            vacancy_data.get('experience', {})
        )

        # Анализ навыков
        skills_match = self.calculate_skills_match(resume_skills, vacancy_skills)

        # Анализ зарплаты
        resume_salary = self.extract_salary_range(resume_data.get('salary'))
        vacancy_salary = self.extract_salary_range(vacancy_data.get('salary'))

        salary_match = self._analyze_salary_compatibility(resume_salary, vacancy_salary)

        # Общий скор соответствия
        overall_score = self._calculate_overall_score(
            experience_match['matches'],
            skills_match['match_percentage'],
            salary_match['compatible']
        )

        return {
            'overall_score': overall_score,
            'experience': experience_match,
            'skills': skills_match,
            'salary': salary_match,
            'vacancy_info': {
                'id': vacancy_data.get('id'),
                'name': vacancy_data.get('name'),
                'employer': vacancy_data.get('employer', {}).get('name'),
                'area': vacancy_data.get('area', {}).get('name'),
                'url': vacancy_data.get('alternate_url')
            }
        }

    def _analyze_salary_compatibility(
        self,
        resume_salary: Dict[str, Any],
        vacancy_salary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Анализ совместимости зарплатных ожиданий"""

        # Если зарплата не указана в одном из источников
        if not resume_salary['min'] and not vacancy_salary['min']:
            return {'compatible': True, 'reason': 'Зарплата не указана'}

        if not resume_salary['min']:
            return {'compatible': True, 'reason': 'Зарплата в резюме не указана'}

        if not vacancy_salary['min']:
            return {'compatible': True, 'reason': 'Зарплата в вакансии не указана'}

        # Сравниваем валюты
        if resume_salary['currency'] != vacancy_salary['currency']:
            return {'compatible': True, 'reason': 'Разные валюты, сравнение затруднено'}

        # Проверяем пересечение диапазонов
        resume_min = resume_salary['min'] or 0
        resume_max = resume_salary['max'] or resume_min * 1.5

        vacancy_min = vacancy_salary['min'] or 0
        vacancy_max = vacancy_salary['max'] or vacancy_min * 1.5

        # Есть ли пересечение диапазонов
        compatible = (
            resume_min <= vacancy_max and
            resume_max >= vacancy_min
        )

        return {
            'compatible': compatible,
            'resume_range': f"{resume_min}-{resume_max} {resume_salary['currency']}",
            'vacancy_range': f"{vacancy_min}-{vacancy_max} {vacancy_salary['currency']}",
            'reason': 'Совпадает' if compatible else 'Не совпадает'
        }

    def _calculate_overall_score(
        self,
        experience_matches: bool,
        skills_percentage: float,
        salary_compatible: bool
    ) -> int:
        """Расчет общего скора соответствия (0-100)
        
        Логика расчета:
        - Опыт работы: 40% (должен совпадать требованиям)
        - Навыки: 50% (процент совпадения)
        - Зарплата: 10% (должна быть совместима)
        """

        score = 0

        # Опыт работы (40% от общего скора)
        if experience_matches:
            score += 40
        else:
            # Даже если опыт не совпадает, даем 20 очков (50% от 40)
            score += 20

        # Навыки (50% от общего скора)
        # Минимум 30% навыков для прохождения фильтра
        if skills_percentage >= 30:
            score += (skills_percentage * 0.5)
        else:
            score += (skills_percentage * 0.3)  # Менее щадящий расчет

        # Зарплата (10% от общего скора)
        if salary_compatible:
            score += 10

        return min(100, round(score))

    def filter_suitable_vacancies(
        self,
        resume_data: Dict[str, Any],
        vacancies: List[Dict[str, Any]],
        min_score: int = 60
    ) -> List[Dict[str, Any]]:
        """Фильтрация подходящих вакансий"""

        suitable_vacancies = []
        analysis_results = []  # Для логирования

        logger.info(f"📊 Начало анализа {len(vacancies)} вакансий (мин. скор: {min_score})")

        for vacancy in vacancies:
            try:
                match_result = self.analyze_vacancy_match(resume_data, vacancy)
                vacancy_id = vacancy.get('id', 'unknown')
                overall_score = match_result['overall_score']
                
                analysis_results.append({
                    'id': vacancy_id,
                    'name': vacancy.get('name', ''),
                    'score': overall_score
                })

                if overall_score >= min_score:
                    suitable_vacancies.append({
                        'vacancy': vacancy,
                        'match_analysis': match_result
                    })
                    logger.debug(
                        f"✅ Вакансия {vacancy_id} подходит! Скор: {overall_score} "
                        f"(Опыт: {match_result['experience']['matches']}, "
                        f"Навыки: {match_result['skills']['match_percentage']}%)"
                    )
                else:
                    logger.debug(
                        f"❌ Вакансия {vacancy_id} не подходит. Скор: {overall_score} "
                        f"(нужен {min_score}+) "
                        f"[Опыт: {match_result['experience']['matches']}, "
                        f"Навыки: {match_result['skills']['match_percentage']}%]"
                    )

            except Exception as e:
                vacancy_id = vacancy.get('id', 'unknown')
                logger.error(f"⚠️ Ошибка анализа вакансии {vacancy_id}: {e}")
                continue

        # Логирование статистики
        scores = [r['score'] for r in analysis_results]
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score_actual = min(scores)
            logger.info(
                f"📈 Статистика анализа: "
                f"Подходит: {len(suitable_vacancies)}/{len(vacancies)}, "
                f"Средний скор: {avg_score:.1f}, "
                f"Диапазон: {min_score_actual:.0f}-{max_score:.0f}"
            )

            # Логируем топ 5 вакансий
            top_vacancies = sorted(analysis_results, key=lambda x: x['score'], reverse=True)[:5]
            if top_vacancies:
                logger.info("🏆 Топ-5 вакансий по скору:")
                for i, v in enumerate(top_vacancies, 1):
                    logger.info(f"  {i}. [{v['score']}] {v['name'][:50]}")

        # Сортируем по убыванию скора соответствия
        suitable_vacancies.sort(
            key=lambda x: x['match_analysis']['overall_score'],
            reverse=True
        )

        return suitable_vacancies


# Глобальный экземпляр анализатора
matcher = ResumeVacancyMatcher()
