import asyncio
import logging
import os
import sys
import inspect
import pytz
import datetime
import traceback
from cachetools import TTLCache

import uvicorn

from redis.asyncio import Redis
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent
from aiogram.filters import ExceptionTypeFilter
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram_dialog import setup_dialogs
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState, OutdatedIntent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.router import router
from storage.nats_storage import NatsStorage
from utils.nats_connect import connect_to_nats
from utils.start_utils import start_schedulers
from services.start_consumer import start_transfer_consumer
from database.build import PostgresBuild
from database.model import Base
from database.action_data_class import setup_database, DataInteraction
from database.cache import CacheManager
from config_data.config import load_config, Config
from handlers.user_handlers import user_router
from dialogs import get_dialogs
from middlewares import TransferObjectsMiddleware, RemindMiddleware


timezone = pytz.timezone('Europe/Moscow')
datetime.datetime.now(timezone)

module_path = inspect.getfile(inspect.currentframe())
module_dir = os.path.realpath(os.path.dirname(module_path))


format = '[{asctime}] #{levelname:8} {filename}:' \
         '{lineno} - {name} - {message}'

LOG_FILE = 'errors.log'

logging.basicConfig(
    level=logging.DEBUG,
    format=format,
    style='{',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)


def log_exception(exc_type, exc_value, exc_traceback):
    """
    Функция для записи исключения в лог
    """
    # Исключаем стандартные KeyboardInterrupt и SystemExit
    if issubclass(exc_type, KeyboardInterrupt):
        return

    # Получаем traceback как строку
    exc_info = exc_type, exc_value, exc_traceback
    exc_str = ''.join(traceback.format_exception(*exc_info))

    # Логируем в файл
    logging.error(f"Необработанное исключение:\n{exc_str}")


async def on_unknown_intent(event: ErrorEvent, **kwargs):
    """Обработка устаревших inline-кнопок после перезапуска бота."""
    logger.warning(f'Unknown intent: {event.exception}')
    if event.update.callback_query:
        await event.update.callback_query.answer(
            '⚠️ Бот был перезапущен. Нажмите /start, чтобы начать заново.',
            show_alert=True,
        )


async def on_unknown_state(event: ErrorEvent, **kwargs):
    """Обработка неизвестного состояния диалога."""
    logger.warning(f'Unknown state: {event.exception}')
    if event.update.callback_query:
        await event.update.callback_query.answer(
            '⚠️ Бот был обновлён. Нажмите /start, чтобы начать заново.',
            show_alert=True,
        )


def _register_dialog_error_handlers(dp: Dispatcher):
    """Регистрация обработчиков ошибок aiogram-dialog на диспетчере."""
    dp.errors.register(on_unknown_intent, ExceptionTypeFilter(UnknownIntent))
    dp.errors.register(on_unknown_intent, ExceptionTypeFilter(OutdatedIntent))
    dp.errors.register(on_unknown_state, ExceptionTypeFilter(UnknownState))


sys.excepthook = log_exception

logger = logging.getLogger(__name__)

config: Config = load_config()


async def main():
    database = PostgresBuild(config.db.dns)
    #await database.drop_tables(Base)
    await database.create_tables(Base)
    session = database.session()
    await setup_database(session)

    scheduler: AsyncIOScheduler = AsyncIOScheduler()
    scheduler.start()

    redis = Redis(password=config.redis.password)
    cache_manager = CacheManager(redis)

    db = DataInteraction(session, cache_manager)

    await db.update_earn(user_id=8005178596, earn=300)

    await start_schedulers(scheduler, db)

    """
    apps = await db.get_user_applications(7686062583)
    applications = [f'{app.__dict__}\n' for app in apps]
    with open('user_apps.txt', 'a+', encoding='utf-8') as file:
        file.writelines(applications)
    return
    """

    nc, js = await connect_to_nats(servers=config.nats.servers)
    storage: NatsStorage = await NatsStorage(nc=nc, js=js).create_storage()

    bot = Bot(token=config.bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    cache = TTLCache(
        maxsize=1000,
        ttl=60 * 60 * 3
    )

    # подключаем роутеры
    dp.include_routers(user_router, *get_dialogs())

    # подключаем middleware
    dp.update.middleware(TransferObjectsMiddleware())
    dp.callback_query.middleware(RemindMiddleware())
    _register_dialog_error_handlers(dp)

    # запуск
    await bot.delete_webhook(drop_pending_updates=True)
    setup_dialogs(dp)

    logger.info('Bot start polling')

    app = FastAPI()
    app.include_router(router)
    app.state.nc = nc
    app.state.js = js
    app.state.scheduler = scheduler
    app.state.session = db

    uvicorn_config = uvicorn.Config(app, host='0.0.0.0', port=8000, log_level="info")  # ssl_keyfile='ssl/key.pem', ssl_certfile='ssl/cert.pem'
    server = uvicorn.Server(uvicorn_config)

    aiogram_task = asyncio.create_task(dp.start_polling(bot, _session=session, _scheduler=scheduler, js=js, cache=cache, cache_manager=cache_manager))
    uvicorn_task = asyncio.create_task(server.serve())
    consumer_task = asyncio.create_task(start_transfer_consumer(
        nc=nc,
        js=js,
        cache_manager=cache_manager,
        scheduler=scheduler,
        bot=bot,
        subject=config.consumer.subject,
        stream=config.consumer.stream,
        durable_name=config.consumer.durable_name
    ))

    try:
        await asyncio.gather(aiogram_task, uvicorn_task, consumer_task)
    except Exception as e:
        logger.exception(e)
    finally:
        await nc.close()
        logger.info('Connection closed')


if __name__ == "__main__":
    asyncio.run(main())