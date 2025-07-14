import datetime
import json

from aiogram import Bot
from fastapi import APIRouter, Request, Form
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.build import PostgresBuild
from database.action_data_class import DataInteraction
from utils.transactions import transfer_stars, transfer_ton, transfer_premium
from config_data.config import load_config, Config


config: Config = load_config()

router = APIRouter()

database = PostgresBuild(config.db.dns)
sessions = database.session()


@router.post("/payment")
async def ping(response: Request, us_userId: str | int = Form(...), CUR_ID: str | int = Form(...)):
    user_id = int(us_userId)
    session = DataInteraction(sessions)
    application = await session.get_last_application(user_id)
    if application.status in [0, 2, 3]:
        return "OK"
    trans_type = int(CUR_ID)
    if application.type == 'stars':
        status = await transfer_stars(application.receiver, application.amount)
    elif application.type == 'premium':
        status = await transfer_premium(application.receiver, application.amount)
    else:
        status = await transfer_ton(application.receiver, application.amount)
    payment = ''
    if trans_type == 36:
        payment = 'card'
    if trans_type == 44:
        payment = 'sbp'
    bot = Bot(token=config.bot.token)
    if not status:
        await bot.send_message(
            chat_id=user_id,
            text=f'🚨Во время начисления звезд что-то пошло не так, пожалуйста '
                 f'обратитесь в поддержку(№ заказа: <code>{application.uid_key}</code>)'
        )
        await session.update_application(application.uid_key, 3, payment)
        return "OK"
    await bot.send_message(
        chat_id=user_id,
        text='✅Оплата была успешно совершенна, звезды были отправлены на счет'
    )
    await session.update_application(application.uid_key, status=2, payment=payment)
    await session.add_payment()
    await session.update_buys(user_id, application.amount)
    return "OK"
