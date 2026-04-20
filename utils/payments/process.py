from typing import Literal
import asyncio
from asyncio import TimeoutError

from aiogram import Bot
from nats.js import JetStreamContext

from services.publisher import send_publisher_data
from utils.payments.create import check_crypto_payment, check_oxa_payment
from database.action_data_class import DataInteraction
from config_data.config import Config, load_config


config: Config = load_config()


async def wait_for_payment(
        payment_id,
        user_id: int,
        app_id,
        bot: Bot,
        session: DataInteraction,
        js: JetStreamContext,
        currency: int,
        rate: Literal['stars', 'premium'],
        payment_type: Literal['crypto', 'cryptoBot'],
        timeout: int = 60 * 15,
        check_interval: int = 6
):
    """
    Ожидает оплаты в фоне. Завершается при оплате или по таймауту.
    """
    try:
        await asyncio.wait_for(_poll_payment(payment_id, user_id, app_id, currency, js, bot, session, rate, payment_type, check_interval),
                               timeout=timeout)

    except TimeoutError:
        print(f"Платёж {payment_id} истёк (таймаут)")

    except Exception as e:
        print(f"Ошибка в фоновом ожидании платежа {payment_id}: {e}")


async def _poll_payment(payment_id, user_id: int, app_id, currency: int, js: JetStreamContext, bot: Bot, session: DataInteraction, rate: str, payment_type: str, interval: int):
    """
    Цикл опроса статуса платежа.
    Завершается, когда платёж оплачен.
    """
    while True:
        if payment_type == 'crypto':
            status = await check_oxa_payment(payment_id)
        else:
            status = await check_crypto_payment(payment_id)
        if status:
            await bot.send_message(
                chat_id=user_id,
                text='<tg-emoji emoji-id="5456432998092133477">✅</tg-emoji>Оплата прошла успешно'
            )
            await execute_rate(app_id, currency, rate, payment_type, js,  bot, session)
            break
        await asyncio.sleep(interval)


async def execute_rate(app_id, currency: int, rate: str, payment_type: str, js: JetStreamContext, bot: Bot, session: DataInteraction):
    application = await session.get_application(app_id)
    data = {
        'transfer_type': rate,
        'username': application.receiver,
        'currency': currency,
        'payment': payment_type,
        'app_id': application.uid_key
    }
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=data
    )
