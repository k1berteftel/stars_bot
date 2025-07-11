import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.types import TelegramObject, User
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from keyboards.keyboard import get_sub_keyboard
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config

config: Config = load_config()
logger = logging.getLogger(__name__)


channel_id = -1002664163050


class RemindMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get('event_from_user')

        if user is None:
            return await handler(event, data)
        bot: Bot = data.get('bot')
        #"""
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user.id)
        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
            keyboard = await get_sub_keyboard()
            await bot.send_message(
                chat_id=user.id,
                text='Чтобы продолжить пользоваться ботом пожалуйста подпишитесь на <b>наш канал</b>',
                reply_markup=keyboard
            )
            return
        #"""
        session: DataInteraction = data.get('session')
        await session.set_activity(user_id=user.id)

        result = await handler(event, data)
        return result
