"""
Отправка откликов на вакансии через HH API
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from typing import List, Dict, Any
from hh_api.client import hh_client
from config import Config
from database.repository import db_repository


class ResponseManager:
    """Менеджер для отправки откликов на вакансии"""

    def __init__(self):
        self.client = hh_client

    async def send_response(
            self,
            telegram_id: int,
            vacancy_id: str,
            resume_id: str,
            cover_letter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Отправка отклика на вакансию"""

        try:
            # Проверяем не откликались ли уже на эту вакансию
            if await db_repository.is_response_exists(telegram_id, vacancy_id):
                raise ValueError("Отклик на эту вакансию уже был отправлен")

            # Проверяем дневной лимит
            today_count = await db_repository.get_today_responses_count(telegram_id)
            if today_count >= Config.MAX_RESPONSES_PER_DAY:
                raise ValueError(f"Достигнут дневной лимит откликов ({Config.MAX_RESPONSES_PER_DAY})")

            # Отправляем отклик через HH API
            response_result = await self.client.respond_to_vacancy(
                vacancy_id=vacancy_id,
                resume_id=resume_id,
                message=cover_letter
            )

            logger.info(f"Отклик отправлен: vacancy_id={vacancy_id}, resume_id={resume_id}")

            return {
                'success': True,
                'response_id': response_result.get('id'),
                'status': response_result.get('state', {}).get('name', 'отправлен'),
                'sent_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Ошибка отправки отклика на вакансию {vacancy_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def generate_cover_letter(
            self,
            vacancy_data: Dict[str, Any],
            resume_data: Dict[str, Any],
            template: Optional[str] = None
    ) -> str:
        """Генерация персонализированного сопроводительного письма"""

        # Дефолтный шаблон если не задан
        if not template:
            template = (
                "Здравствуйте! Меня заинтересовала позиция {vacancy_name} в компании {company_name}. "
                "Мой опыт работы включает: {my_skills}. "
                "Буду рад обсудить возможности сотрудничества."
            )

        # Извлекаем данные для подстановки
        vacancy_name = vacancy_data.get('name', 'данная позиция')
        company_name = vacancy_data.get('employer', {}).get('name', 'вашей компании')

        # Извлекаем навыки из резюме
        my_skills = self._extract_skills_from_resume(resume_data)

        # Подставляем переменные
        try:
            cover_letter = template.format(
                vacancy_name=vacancy_name,
                company_name=company_name,
                my_skills=my_skills
            )
        except KeyError as e:
            logger.warning(f"Неизвестная переменная в шаблоне: {e}")
            # Используем шаблон как есть
            cover_letter = template

        # Ограничиваем длину письма (HH имеет лимиты)
        if len(cover_letter) > 2000:
            cover_letter = cover_letter[:1997] + "..."

        return cover_letter

    def _extract_skills_from_resume(self, resume_data: Dict[str, Any]) -> str:
        """Извлечение навыков из резюме для письма"""

        skills = []

        # Навыки из поля skills
        if resume_data.get('skills'):
            skills_text = resume_data['skills']
            # Берем первые несколько навыков
            skills_list = [s.strip() for s in skills_text.split(',')[:5]]
            skills.extend(skills_list)

        # Навыки из опыта работы
        if resume_data.get('experience'):
            for exp in resume_data['experience'][:2]:  # Берем последние 2 места работы
                position = exp.get('position', '')
                if position:
                    skills.append(position)

        # Форматируем для письма
        if skills:
            return ', '.join(skills[:4])  # Максимум 4 навыка
        else:
            return "разнообразные навыки и опыт работы"

    async def get_response_status(self, negotiation_id: str) -> Dict[str, Any]:
        """Получение статуса отклика"""

        try:
            negotiations = await self.client.get_negotiations()

            # Ищем нужный отклик
            for negotiation in negotiations.get('items', []):
                if negotiation.get('id') == negotiation_id:
                    return {
                        'id': negotiation.get('id'),
                        'status': negotiation.get('state', {}).get('name'),
                        'vacancy_name': negotiation.get('vacancy', {}).get('name'),
                        'employer_name': negotiation.get('vacancy', {}).get('employer', {}).get('name'),
                        'created_at': negotiation.get('created_at'),
                        'updated_at': negotiation.get('updated_at')
                    }

            return {'error': 'Отклик не найден'}

        except Exception as e:
            logger.error(f"Ошибка получения статуса отклика {negotiation_id}: {e}")
            return {'error': str(e)}

    async def get_all_responses(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение всех откликов пользователя"""

        try:
            negotiations = await self.client.get_negotiations(per_page=limit)

            responses = []
            for negotiation in negotiations.get('items', []):
                response_data = {
                    'id': negotiation.get('id'),
                    'status': negotiation.get('state', {}).get('name'),
                    'vacancy_id': negotiation.get('vacancy', {}).get('id'),
                    'vacancy_name': negotiation.get('vacancy', {}).get('name'),
                    'employer_name': negotiation.get('vacancy', {}).get('employer', {}).get('name'),
                    'created_at': negotiation.get('created_at'),
                    'updated_at': negotiation.get('updated_at'),
                    'messages_count': len(negotiation.get('messages', []))
                }
                responses.append(response_data)

            return responses

        except Exception as e:
            logger.error(f"Ошибка получения откликов: {e}")
            return []

    async def get_response_statistics(self) -> Dict[str, Any]:
        """Получение статистики откликов"""

        try:
            stats = await self.client.get_negotiations_stats()

            return {
                'total_responses': stats.get('counters', {}).get('total', 0),
                'pending_responses': stats.get('counters', {}).get('pending', 0),
                'viewed_responses': stats.get('counters', {}).get('viewed', 0),
                'invited_responses': stats.get('counters', {}).get('invited', 0)
            }

        except Exception as e:
            logger.error(f"Ошибка получения статистики откликов: {e}")
            return {}


# Глобальный экземпляр менеджера откликов
response_manager = ResponseManager()