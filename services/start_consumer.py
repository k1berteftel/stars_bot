import logging

from aiogram import Bot
from services.consumer import TransactionConsumer

from nats.aio.client import Client
from nats.js.client import JetStreamContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


async def start_transfer_consumer(
    nc: Client,
    js: JetStreamContext,
    scheduler: AsyncIOScheduler,
    bot: Bot,
    subject: str,
    stream: str,
    durable_name: str
) -> None:
    consumer = TransactionConsumer(
        nc=nc,
        js=js,
        scheduler=scheduler,
        bot=bot,
        subject=subject,
        stream=stream,
        durable_name=durable_name
    )
    logger.info('Start AI message consumer')
    await consumer.start()