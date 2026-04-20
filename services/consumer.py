import logging
import datetime
import asyncio
import json

from aiogram import Bot

from cachetools import TTLCache

from nats.aio.client import Client
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import StreamConfig, StorageType, RetentionPolicy
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.transactions import transfer_stars, transfer_ton, transfer_premium, transfer_gift
from utils.text_utils import send_application_log
from database.action_data_class import DataInteraction
from database.build import PostgresBuild
from database.cache import CacheManager
from config_data.config import Config, load_config

config: Config = load_config()

database = PostgresBuild(config.db.dns)
sessions = database.session()


logger = logging.getLogger(__name__)


class TransactionConsumer:
    def __init__(
            self,
            nc: Client,
            js: JetStreamContext,
            cache_manager: CacheManager,
            scheduler: AsyncIOScheduler,
            bot: Bot,
            subject: str,
            stream: str,
            durable_name: str
    ) -> None:
        self.nc = nc
        self.js = js
        self.cache_manager = cache_manager
        self.scheduler = scheduler
        self.bot = bot
        self.subject = subject
        self.stream = stream
        self.durable_name = durable_name
        self.counter: dict[int, int] = {}

    async def start(self) -> None:
        try:
            await self.js.delete_stream(name=config.consumer.stream)
        except Exception:
            ...
        #"""
        stream_config = StreamConfig(
            name=config.consumer.stream,  # Название стрима
            subjects=[
                config.consumer.subject
            ],
            retention=RetentionPolicy.LIMITS,  # Политика удержания
            max_bytes=300 * 1024 * 1024,  # 300 MiB
            max_msg_size=10 * 1024 * 1024,  # 10 MiB
            storage=StorageType.FILE,  # Хранение сообщений на диске
            allow_direct=True,  # Разрешение получать сообщения без создания консьюмера
        )
        await self.js.add_stream(stream_config)
        self.stream_sub = await self.js.subscribe(
            subject=self.subject,
            stream=self.stream,
            cb=self.on_message,
            durable=self.durable_name,
            manual_ack=True
        )
        #"""
        logger.info('start TransactionConsumer')

    async def on_message(self, message: Msg):
        data = json.loads(message.data.decode())
        logger.info('Success get message')
        print(data)
        buy = data.get('transfer_type')
        username = data.get('username')
        currency = data.get('currency')
        payment = data.get('payments')
        app_id = data.get('app_id')
        session: DataInteraction = DataInteraction(sessions, self.cache_manager)
        application = await session.get_application(app_id)
        if application.status != 1:
            await message.ack()
            return
        user_id = application.user_id
        user = await session.get_user(user_id)
        try:
            if buy == 'deleted_gift':
                status = await transfer_gift(username, currency)
            elif buy == 'stars':
                status = await transfer_stars(username, currency)
            elif buy == 'premium':
                status = await transfer_premium(username, currency)
            else:
                status = await transfer_ton(username, currency)
            if not status:
                if application.status != 2:
                    await session.update_application(app_id, 3, payment)
                name = f'process_payment_{user_id}'
                for task in asyncio.all_tasks():
                    if task.get_name() == name:
                        task.cancel()
                raise Exception
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text='<tg-emoji emoji-id="5456432998092133477">✅</tg-emoji>Транзакция была успешно выполнена'
                )
            except Exception:
                ...
            name = f'process_payment_{user_id}'
            for task in asyncio.all_tasks():
                if task.get_name() == name:
                    task.cancel()
            await session.update_application(app_id, 2, payment)
            await session.add_payment()
            if buy == 'stars':
                await session.update_buys(user_id, currency)
                await session.add_buys(currency)
            await session.add_cashflow(int(application.rub))

            if user.referral:
                await session.update_earn(user.referral, int(application.rub * 0.15))

            if user.join:
                await session.update_deeplink_earn(user.join, int(application.rub))
        except Exception as err:
            logger.error(f'Error during execute application task: {err}')
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=(f'<tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji>Во время выполнения транзакции что-то пошло не так, пожалуйста '
                            f'обратитесь в поддержку(№ заказа: <code>{app_id}</code>)')
                )
            except Exception:
                ...
        finally:
            await send_application_log(app_id, session, self.bot)
            await message.ack()

    async def unsubscribe(self) -> None:
        if self.stream_sub:
            await self.stream_sub.unsubscribe()
            logger.info('Consumer unsubscribed')