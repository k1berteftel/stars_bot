import datetime
import json

from aiogram import Bot
from fastapi import APIRouter, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.build import PostgresBuild
from database.action_data_class import DataInteraction
from utils.transactions import transfer_stars
from config_data.config import load_config, Config


config: Config = load_config()

router = APIRouter()

database = PostgresBuild(config.db.dns)
sessions = database.session()

scheduler: AsyncIOScheduler = AsyncIOScheduler()
scheduler.start()


@router.post("/payment")
async def ping(response: Request):
    print(response.__dict__)
    print(await response.json())
    data = await response.json()
    session = DataInteraction(sessions)
    print(data)
    user_id = int(data['orderId'])
    application = await session.get_last_application(user_id)
    print(application.__dict__)
    if application.status in [0, 2, 3]:
        return "OK"
    if data['transactionStatus'] == 'Paid':
        status = await transfer_stars(application.receiver, application.amount)
        bot = Bot(token=config.bot.token)
        if not status:
            await bot.send_message(
                chat_id=user_id,
                text='🚨Во время начисления звезд что-то пошло не так, пожалуйста обратитесь в поддержку'
            )
            await session.update_application(application.uid_key, 3, 'card')
            job = scheduler.get_job(f'payment_{user_id}')
            if job:
                job.remove()
            stop_job = scheduler.get_job(f'stop_payment_{user_id}')
            if stop_job:
                stop_job.remove()
            return "OK"
        await bot.send_message(
            chat_id=user_id,
            text='✅Оплата была успешно совершенна, звезды были отправлены на счет'
        )
        job = scheduler.get_job(f'payment_{user_id}')
        if job:
            job.remove()
        stop_job = scheduler.get_job(f'stop_payment_{user_id}')
        if stop_job:
            stop_job.remove()
        await session.update_application(application.uid_key, status=2, payment='card')
    return "OK"
