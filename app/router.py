import datetime
import json
import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import APIRouter, Request, Form, HTTPException, status
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aioplatega import CallbackPayload

from nats.js import JetStreamContext

from services.publisher import send_publisher_data
from database.action_data_class import DataInteraction
from utils.transactions import transfer_stars, transfer_ton, transfer_premium
from config_data.config import load_config, Config


config: Config = load_config()

router = APIRouter()


ALLOWED_IPS: list[str] = [
    "158.160.85.101"
]


@router.post("/payments/paypear")
async def paypear_callback(request: Request):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP {client_ip} is not allowed"
        )
    session: DataInteraction = request.app.state.session
    scheduler: AsyncIOScheduler = request.app.state.scheduler
    js: JetStreamContext = request.app.state.js

    data = await request.json()
    if not data['event'] == 'payment.confirmed' or not data['object'].get('paid'):
        return "OK"

    app_id = int(data['object']['metadata'].get('app_id'))
    application = await session.get_application(app_id)

    payment = 'sbp'

    data = {
        'transfer_type': application.type,
        'username': application.receiver,
        'currency': application.amount,
        'payments': payment,
        'app_id': application.uid_key
    }
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=data
    )
    name = f'process_payment_{application.user_id}'
    for task in asyncio.all_tasks():
        if task.get_name() == name:
            task.cancel()
    return "OK"


@router.post('/payments/platega')
async def platega_callback(request: Request):
    headers = request.headers
    merchant_id = headers.get('X-MerchantId')
    secret_key = headers.get('X-Secret')
    if not merchant_id or not secret_key or (merchant_id != config.platega.merchant_id or secret_key != config.platega.secret_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"X-MerchantId or X-Secret is not allowed"
        )

    try:
        payload = CallbackPayload.model_validate(await request.json())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Payload is not allowed"
        )

    if payload.status != "CONFIRMED":
        return "OK"

    session: DataInteraction = request.app.state.session
    scheduler: AsyncIOScheduler = request.app.state.scheduler
    js: JetStreamContext = request.app.state.js

    app_id = int(payload.payload)
    application = await session.get_application(app_id)

    if payload.payment_method == 2:
        payment = 'sbp'
    else:
        payment = 'card'

    data = {
        'transfer_type': application.type,
        'username': application.receiver,
        'currency': application.amount,
        'payments': payment,
        'app_id': application.uid_key
    }
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=data
    )
    name = f'process_payment_{application.user_id}'
    for task in asyncio.all_tasks():
        if task.get_name() == name:
            task.cancel()
    return "OK"
