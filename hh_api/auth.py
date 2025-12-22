"""
OAuth2 авторизация для HH API
Управление токенами доступа и процессом авторизации
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import webbrowser
from urllib.parse import urlparse, parse_qs

from loguru import logger
from cryptography.fernet import Fernet

from config import Config
from hh_api.client import hh_client
from aiohttp import web
import asyncio


async def start_callback_server():
    """Запускает простой локальный сервер для OAuth callback"""
    app = web.Application()

    async def callback_handler(request):
        code = request.rel_url.query.get('code')
        if code:
            # Сохраните code в файл или переменную окружения
            with open('auth_code.txt', 'w') as f:
                f.write(code)
            return web.Response(text="✅ Авторизация успешна! Закройте это окно.")
        return web.Response(text="❌ Ошибка авторизации", status=400)

    app.router.add_get('/auth/callback', callback_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8000)
    await site.start()
    print("✅ Callback server started on http://localhost:8000")
    return runner


class HHAuthManager:
    """Менеджер авторизации HH API"""

    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """Получение или создание ключа шифрования для токенов"""
        key_file = Config.DATA_DIR / 'encryption.key'

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key

    def encrypt_token(self, token: str) -> str:
        """Шифрование токена"""
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """Расшифровка токена"""
        return self.fernet.decrypt(encrypted_token.encode()).decode()

    async def start_oauth_flow(self) -> str:
        """Запуск процесса OAuth2 авторизации"""

        # Получаем URL для авторизации
        oauth_url = hh_client.get_oauth_url()

        logger.info("Запуск процесса OAuth2 авторизации")
        logger.info(f"URL для авторизации: {oauth_url}")

        return oauth_url

    async def complete_oauth_flow(self, callback_url: str) -> Dict[str, Any]:
        """Завершение процесса OAuth2 авторизации"""

        # Извлекаем authorization code из callback URL
        parsed_url = urlparse(callback_url)
        query_params = parse_qs(parsed_url.query)

        if 'code' not in query_params:
            raise ValueError("Authorization code не найден в callback URL")

        authorization_code = query_params['code'][0]

        # Обмениваем code на токены
        token_data = await hh_client.exchange_code_for_token(authorization_code)

        # Шифруем и сохраняем токены
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 3600)

        if access_token:
            await self.save_tokens(access_token, refresh_token, expires_in)
            hh_client.set_access_token(access_token, refresh_token)

            logger.info("OAuth2 авторизация завершена успешно")
            return token_data
        else:
            raise Exception("Access token не получен")

    async def save_tokens(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600
    ) -> None:
        """Сохранение токенов в зашифрованном виде"""

        token_data = {
            'access_token': self.encrypt_token(access_token),
            'refresh_token': self.encrypt_token(refresh_token) if refresh_token else None,
            'expires_at': (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
            'created_at': datetime.now().isoformat()
        }

        tokens_file = Config.DATA_DIR / 'hh_tokens.json'

        with open(tokens_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)

        logger.info("Токены сохранены")

    async def load_tokens(self) -> Optional[Dict[str, Any]]:
        """Загрузка сохраненных токенов"""

        tokens_file = Config.DATA_DIR / 'hh_tokens.json'

        if not tokens_file.exists():
            return None

        try:
            with open(tokens_file, 'r', encoding='utf-8') as f:
                encrypted_data = json.load(f)

            # Расшифровываем токены
            access_token = self.decrypt_token(encrypted_data['access_token'])
            refresh_token = None
            if encrypted_data.get('refresh_token'):
                refresh_token = self.decrypt_token(encrypted_data['refresh_token'])

            # Проверяем срок действия
            expires_at = datetime.fromisoformat(encrypted_data['expires_at'])

            if datetime.now() >= expires_at:
                logger.warning("Access token истек")
                if refresh_token:
                    # Пытаемся обновить токен
                    return await self.refresh_token(refresh_token)
                else:
                    return None

            # Устанавливаем токены в клиент
            hh_client.set_access_token(access_token, refresh_token)

            logger.info("Токены загружены успешно")
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': expires_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Ошибка загрузки токенов: {e}")
            return None

    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Обновление access token"""

        try:
            hh_client.set_access_token('', refresh_token)
            token_data = await hh_client.refresh_access_token()

            # Сохраняем новые токены
            access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token', refresh_token)
            expires_in = token_data.get('expires_in', 3600)

            await self.save_tokens(access_token, new_refresh_token, expires_in)

            logger.info("Токен обновлен успешно")
            return token_data

        except Exception as e:
            logger.error(f"Ошибка обновления токена: {e}")
            return None

    async def is_authenticated(self) -> bool:
        """Проверка аутентификации пользователя"""

        tokens = await self.load_tokens()
        if not tokens:
            return False

        try:
            # Проверяем токен запросом к API
            await hh_client.get_user_info()
            return True
        except Exception as e:
            logger.error(f"Токен недействителен: {e}")
            return False

    async def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Получение профиля пользователя"""

        if not await self.is_authenticated():
            return None

        try:
            user_info = await hh_client.get_user_info()
            resumes = await hh_client.get_user_resumes()

            return {
                'user_info': user_info,
                'resumes': resumes
            }
        except Exception as e:
            logger.error(f"Ошибка получения профиля: {e}")
            return None

    async def logout(self) -> None:
        """Выход из аккаунта (удаление токенов)"""

        tokens_file = Config.DATA_DIR / 'hh_tokens.json'

        if tokens_file.exists():
            tokens_file.unlink()

        # Очищаем токены в клиенте
        hh_client.set_access_token('', '')

        logger.info("Выход из аккаунта выполнен")


# Глобальный экземпляр менеджера авторизации
auth_manager = HHAuthManager()