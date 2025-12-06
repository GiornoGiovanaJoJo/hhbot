"""
HH API клиент для работы с HeadHunter API
Поддерживает OAuth2 авторизацию и работу от имени пользователя
"""

import asyncio
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import aiohttp
from loguru import logger

from config import Config, WindowsConfig


class HHApiClient:
    """Клиент для работы с HH API"""

    def __init__(self):
        self.base_url = Config.HH_API_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    async def __aenter__(self):
        await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _create_session(self) -> None:
        """Создание HTTP сессии с Windows-оптимизированными настройками"""

        connector_kwargs = {}

        # Windows-специфичные настройки для aiohttp
        if Config.WINDOWS_EVENT_LOG_ENABLED:
            connector_kwargs['limit'] = 10  # Ограничиваем количество соединений

        # SSL настройки для Windows
        ssl_context = None
        if WindowsConfig.SSL_CAFILE:
            import ssl
            ssl_context = ssl.create_default_context(cafile=WindowsConfig.SSL_CAFILE)

        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            **connector_kwargs
        )

        timeout = aiohttp.ClientTimeout(total=30)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

        )

    async def close(self) -> None:
        """Закрытие сессии"""
        if self.session:
            await self.session.close()

    def set_access_token(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """Установка токенов доступа"""
        self._access_token = access_token
        self._refresh_token = refresh_token

    def get_oauth_url(self) -> str:
        """Получение URL для OAuth2 авторизации"""
        params = {
            'response_type': 'code',
            'client_id': Config.HH_CLIENT_ID,
            'redirect_uri': Config.HH_REDIRECT_URI,
            'scope': 'resume'  # Права на работу с резюме
        }
        return f"{Config.HH_OAUTH_BASE_URL}/authorize?{urlencode(params)}"

    async def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """Обмен authorization code на access token"""

        if not self.session:
            await self._create_session()

        token_url = f"{Config.HH_OAUTH_BASE_URL}/token"

        data = {
            'grant_type': 'authorization_code',
            'client_id': Config.HH_CLIENT_ID,
            'client_secret': Config.HH_CLIENT_SECRET,
            'redirect_uri': Config.HH_REDIRECT_URI,
            'code': authorization_code
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        async with self.session.post(token_url, data=data, headers=headers) as response:
            if response.status == 200:
                token_data = await response.json()

                # Сохраняем токены
                self._access_token = token_data.get('access_token')
                self._refresh_token = token_data.get('refresh_token')

                logger.info("Успешно получен access token")
                return token_data
            else:
                error_text = await response.text()
                logger.error(f"Ошибка получения токена: {response.status} - {error_text}")
                raise Exception(f"Ошибка получения токена: {response.status}")

    async def refresh_access_token(self) -> Dict[str, Any]:
        """Обновление access token используя refresh token"""

        if not self._refresh_token:
            raise Exception("Refresh token не найден")

        if not self.session:
            await self._create_session()

        token_url = f"{Config.HH_OAUTH_BASE_URL}/token"

        data = {
            'grant_type': 'refresh_token',
            'client_id': Config.HH_CLIENT_ID,
            'client_secret': Config.HH_CLIENT_SECRET,
            'refresh_token': self._refresh_token
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        async with self.session.post(token_url, data=data, headers=headers) as response:
            if response.status == 200:
                token_data = await response.json()

                # Обновляем токены
                self._access_token = token_data.get('access_token')
                self._refresh_token = token_data.get('refresh_token')

                logger.info("Access token обновлен")
                return token_data
            else:
                error_text = await response.text()
                logger.error(f"Ошибка обновления токена: {response.status} - {error_text}")
                raise Exception(f"Ошибка обновления токена: {response.status}")

    async def _make_authenticated_request(
            self,
            method: str,
            endpoint: str,
            **kwargs
    ) -> Dict[str, Any]:
        """Выполнение аутентифицированного запроса к API"""

        if not self._access_token:
            raise Exception("Access token не найден. Необходима авторизация")

        if not self.session:
            await self._create_session()

        headers = kwargs.setdefault('headers', {})
        headers['Authorization'] = f'Bearer {self._access_token}'

        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.request(method, url, **kwargs) as response:

                # Обновление токена при 401
                if response.status == 401 and self._refresh_token:
                    await self.refresh_access_token()
                    headers['Authorization'] = f'Bearer {self._access_token}'
                    async with self.session.request(method, url, **kwargs) as retry_response:
                        if retry_response.status in (200, 201):
                            return await retry_response.json()
                        else:
                            error_text = await retry_response.text()
                            raise Exception(f"Ошибка API: {retry_response.status} - {error_text}")

                # Считаем 200 и 201 успешными
                if response.status in (200, 201):
                    # В 201 нередко нет JSON-тела, поэтому проверяем
                    text = await response.text()
                    try:
                        return await response.json()
                    except Exception:
                        return {}

                # Все остальные статусы — ошибки
                error_text = await response.text()
                raise Exception(f"Ошибка API: {response.status} - {error_text}")

        except aiohttp.ClientError as e:
            raise Exception(f"Ошибка соединения: {e}")

    async def get_user_info(self) -> Dict[str, Any]:
        """Получение информации о текущем пользователе"""
        return await self._make_authenticated_request('GET', '/me')

    async def get_user_resumes(self) -> List[Dict[str, Any]]:
        """Получение списка резюме пользователя"""
        response = await self._make_authenticated_request('GET', '/resumes/mine')
        return response.get('items', [])

    async def get_resume_by_id(self, resume_id: str) -> Dict[str, Any]:
        """Получение конкретного резюме по ID"""
        return await self._make_authenticated_request('GET', f'/resumes/{resume_id}')

    async def search_vacancies(self, **params) -> Dict[str, Any]:
        """Поиск вакансий с параметрами фильтрации"""

        # Добавляем параметры по умолчанию
        default_params = {
            'per_page': Config.MAX_VACANCIES_PER_SEARCH,
            'page': 0,
            'period': Config.DEFAULT_SEARCH_PERIOD_DAYS
        }

        # Объединяем с переданными параметрами
        search_params = {**default_params, **params}

        return await self._make_authenticated_request(
            'GET',
            '/vacancies',
            params=search_params
        )

    async def get_vacancy_by_id(self, vacancy_id: str) -> Dict[str, Any]:
        """Получение подробной информации о вакансии"""
        return await self._make_authenticated_request('GET', f'/vacancies/{vacancy_id}')

    async def respond_to_vacancy(
        self,
        vacancy_id: str,
        resume_id: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Отправка отклика на вакансию"""

        data = {
            'vacancy_id': vacancy_id,
            'resume_id': resume_id
        }

        if message:
            data['message'] = message

        return await self._make_authenticated_request(
            'POST',
            '/negotiations',
            json=data
        )

    async def get_negotiations(self, **params) -> Dict[str, Any]:
        """Получение списка откликов/переписки"""
        return await self._make_authenticated_request('GET', '/negotiations', params=params)

    async def get_negotiations_stats(self) -> Dict[str, Any]:
        """Получение статистики по откликам"""
        return await self._make_authenticated_request('GET', '/negotiations/statistics')

    async def send_response_to_vacancy(
            self,
            vacancy_id: str,
            resume_id: str,
            cover_letter: str
    ) -> Dict[str, Any]:
        """Отправка отклика на вакансию"""
        try:
            form = {
                'vacancy_id': vacancy_id,
                'resume_id': resume_id,
                'message': cover_letter
            }

            response = await self._make_authenticated_request(
                'POST',
                '/negotiations',
                data=form,  # form-data
                # не трогаем заголовок Content-Type, пусть aiohttp сам поставит multipart/form-data
            )

            logger.info(f"Отклик отправлен на вакансию {vacancy_id}")
            return {'success': True, 'response': response}

        except Exception as e:
            logger.error(f"Ошибка отправки отклика на вакансию {vacancy_id}: {e}")
            return {'success': False, 'error': str(e)}

    respond_to_vacancy = send_response_to_vacancy

# Глобальный экземпляр клиента
hh_client = HHApiClient()