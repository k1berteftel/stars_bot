import datetime
import json
import asyncio
import hmac
import hashlib

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import APIRouter, Request, Form, HTTPException, status
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aioplatega import CallbackPayload

from nats.js import JetStreamContext

from utils.log_utils import write_log
from services.publisher import send_publisher_data
from database.action_data_class import DataInteraction
from utils.transactions import transfer_stars, transfer_ton, transfer_premium
from config_data.config import load_config, Config


config: Config = load_config()

router = APIRouter()


ALLOWED_IPS: list[str] = [
    # paypear
    "158.160.85.101",
    # freekassa
    "168.119.157.136",
    "168.119.60.227",
    "178.154.197.79",
    "51.250.54.238"
]


def check_lava_signature(params: dict, check_signature: str):
    secret_key = config.lava.secret_key_1
    body = json.dumps(params)
    signature = hmac.new(secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
    return signature == check_signature


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
        'app_id': application.uid_key,
        'payment_id': str(payload.id)
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


@router.post('/payments/freekassa')
async def freekassa_callback(response: Request, intid: str | int = Form(...), us_userId: str | int = Form(...), CUR_ID: str | int = Form(...),
               us_appId: str | int = Form(...)):
    client_ip = response.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP {client_ip} is not allowed"
        )
    payment_id = int(intid)
    user_id = int(us_userId)
    session: DataInteraction = response.app.state.session
    scheduler: AsyncIOScheduler = response.app.state.scheduler
    js: JetStreamContext = response.app.state.js
    #write_log(f'Заказ номер {us_appId} был принят платежным хендлером freekassa\n')
    application = await session.get_application(int(us_appId))
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
        'payments': payment,
        'app_id': application.uid_key,
        'payment_id': payment_id
    }
    #write_log(f'Заказ номер {us_appId} отправляется в консьюмер\n')
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


@router.post('/payments/lava')
async def lava_callback(response: Request):
    raw_data = await response.body()
    try:
        data = json.loads(raw_data)
        print(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    headers = dict(response.headers)
    print(headers.items())
    # signature = headers.get('authorization')
    # if not check_lava_signature(data, signature):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Signature is not allowed"
    #     )
    session: DataInteraction = response.app.state.session
    scheduler: AsyncIOScheduler = response.app.state.scheduler
    js: JetStreamContext = response.app.state.js

    #write_log(f'Заказ номер {us_appId} был принят платежным хендлером lava\n')

    custom_fields = json.loads(data.get('custom_fields'))

    application = await session.get_application(int(custom_fields.get('app_id')))
    if application.status in [0, 2, 3]:
        return "OK"
    payment = 'card'
    trans_type = data.get('pay_service')
    if trans_type == 36:
        payment = 'card'
    if trans_type == 44:
        payment = 'sbp'
    data = {
        'transfer_type': application.type,
        'username': application.receiver,
        'currency': application.amount,
        'payments': payment,
        'app_id': application.uid_key
    }
    #write_log(f'Заказ номер {us_appId} отправляется в консьюмер\n')
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


