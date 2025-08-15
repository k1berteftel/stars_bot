import datetime
import json

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import APIRouter, Request, Form
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nats.js import JetStreamContext

from services.publisher import send_publisher_data
from database.action_data_class import DataInteraction
from utils.transactions import transfer_stars, transfer_ton, transfer_premium
from config_data.config import load_config, Config


config: Config = load_config()

router = APIRouter()


@router.post("/payment")
async def ping(response: Request, us_userId: str | int = Form(...), CUR_ID: str | int = Form(...)):
    user_id = int(us_userId)
    session: DataInteraction = response.app.state.session
    scheduler: AsyncIOScheduler = response.app.state.scheduler
    js: JetStreamContext = response.app.state.js
    application = await session.get_last_application(user_id)
    if application.status in [0, 2, 3]:
        return "OK"
    trans_type = int(CUR_ID)
    payment = ''
    if trans_type == 36:
        payment = 'card'
    if trans_type == 44:
        payment = 'sbp'
    data = {
        'transfer_type': application.type,
        'username': application.receiver,
        'currency': application.amount,
        'payment': payment,
        'app_id': application.uid_key
    }
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=data
    )
    job = scheduler.get_job(f'payment_{user_id}')
    if job:
        job.remove()
    stop_job = scheduler.get_job(f'stop_payment_{user_id}')
    if stop_job:
        stop_job.remove()
    return "OK"
