from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from loguru import logger

# Импорт именно экземпляра, а не класса!
from database.repository import db_repository

class AuthMiddleware(BaseMiddleware):
    """Middleware для логирования активности пользователей"""

    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        if isinstance(event, Message):
            action = f"message: {event.text[:50] if event.text else 'media'}"
        else:
            action = f"callback: {event.data}"

        try:
            # Используем метод экземпляра db_repository
            await db_repository.log_activity(
                telegram_id=user_id,
                action=action,
                details=(
                    f"chat_id: {event.chat.id}"
                    if hasattr(event, "chat") else "no chat"
                )
            )
        except ValueError:
            # Пользователь еще не в БД — игнорируем
            pass
        except Exception as e:
            logger.warning(f"Ошибка логирования активности: {e}")

        return await handler(event, data)
