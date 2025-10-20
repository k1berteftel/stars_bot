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

from utils.transactions import transfer_stars, transfer_ton, transfer_premium
from database.action_data_class import DataInteraction
from database.build import PostgresBuild
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
            scheduler: AsyncIOScheduler,
            bot: Bot,
            subject: str,
            stream: str,
            durable_name: str
    ) -> None:
        self.nc = nc
        self.js = js
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
        self.cache = TTLCache(
            maxsize=1000,
            ttl=60 * 60 * 3
        )
        logger.info('start TransactionConsumer')

    async def on_message(self, message: Msg):
        data = json.loads(message.data.decode())
        logger.info('Success get message')
        print(data)
        buy = data.get('transfer_type')
        username = data.get('username')
        currency = data.get('currency')
        payment = data.get('payment')
        app_id = data.get('app_id')
        if app_id in self.cache.keys():
            await message.ack()
            return
        self.cache[app_id] = True
        session: DataInteraction = DataInteraction(sessions)
        application = await session.get_application(app_id)
        user_id = application.user_id
        try:
            if buy == 'stars':
                status = await transfer_stars(username, currency)
            elif buy == 'premium':
                status = await transfer_premium(username, currency)
            else:
                status = await transfer_ton(username, currency)
            if not status:
                if application.status != 2:
                    await session.update_application(app_id, 3, payment)
                job = self.scheduler.get_job(f'payment_{user_id}')
                if job:
                    job.remove()
                stop_job = self.scheduler.get_job(f'stop_payment_{user_id}')
                if stop_job:
                    stop_job.remove()
                raise Exception
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text='✅Оплата была успешно совершенна, звезды были отправлены на счет'
                )
            except Exception:
                ...
            #print(self.scheduler)
            job = self.scheduler.get_job(f'payment_{user_id}')
            if job:
                job.remove()
            stop_job = self.scheduler.get_job(f'stop_payment_{user_id}')
            if stop_job:
                stop_job.remove()
            if application.status != 2:
                await session.update_application(app_id, 2, payment)
            await session.add_payment()
            if buy == 'stars':
                await session.update_buys(user_id, currency)
        except Exception as err:
            try:
                if self.counter.get(user_id) and self.counter.get(user_id) > 3:
                    del self.counter[user_id]
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=(f'🚨Во время начисления звезд что-то пошло не так, пожалуйста '
                              f'обратитесь в поддержку(№ заказа: <code>{app_id}</code>)')
                    )
                    return
                if self.counter.get(user_id):
                    self.counter[user_id] += 1
                else:
                    self.counter[user_id] = 1
                await message.nak(15)
            except Exception:
                ...
        finally:
            await message.ack()

    async def unsubscribe(self) -> None:
        if self.stream_sub:
            await self.stream_sub.unsubscribe()
            logger.info('Consumer unsubscribed')