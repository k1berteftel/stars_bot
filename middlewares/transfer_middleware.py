import logging
from typing import Any, Awaitable, Callable, Dict
from cachetools import TTLCache

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.action_data_class import DataInteraction

logger = logging.getLogger(__name__)


class TransferObjectsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:

        user: User = data.get('event_from_user')

        if user is None:
            return await handler(event, data)

        sessions: async_sessionmaker = data.get('_session')
        scheduler: AsyncIOScheduler = data.get('_scheduler')

        cache: TTLCache = data.get('cache')
        users = cache.get('users')
        if not users:
            db = DataInteraction(sessions)
            users = [user.id for user in await db.get_block_users()]
            cache['users'] = users
        if user.id in users:
            return

        interaction = DataInteraction(sessions)
        data['session'] = interaction
        data['scheduler'] = scheduler
        return await handler(event, data)