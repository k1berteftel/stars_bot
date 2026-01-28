import asyncio
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram import Bot
from aiogram_dialog import DialogManager
from aiogram.types import InlineKeyboardMarkup, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nats.js import JetStreamContext

from .payment import check_crypto_payment, check_oxa_payment
from services.publisher import send_publisher_data
from database.action_data_class import DataInteraction
from config_data.config import Config, load_config


config: Config = load_config()


async def check_payment(js: JetStreamContext, user_id: int, app_id: int, buy: str, scheduler: AsyncIOScheduler, **kwargs):
    invoice_id = kwargs.get('invoice_id')
    #track_id = kwargs.get('track_id')
    card_id = kwargs.get('card_id')
    order_id = kwargs.get('order_id')
    crypto_bot = await check_crypto_payment(invoice_id)
    #crypto = await check_oxa_payment(track_id)
    if crypto_bot:# or crypto:
        username = kwargs.get('username')
        currency = kwargs.get('currency')
        payment = ''
        if crypto_bot:
            payment = 'crypto_bot'
        # if crypto:
        #     payment = 'crypto'
        transfer_data = {
            'transfer_type': buy,
            'username': username,
            'currency': currency,
            'payment': payment,
            'app_id': app_id
        }
        await send_publisher_data(
            js=js,
            subject=config.consumer.subject,
            data=transfer_data
        )
        job = scheduler.get_job(f'payment_{user_id}')
        if job:
            job.remove()
        stop_job = scheduler.get_job(f'stop_payment_{user_id}')
        if stop_job:
            stop_job.remove()
    return


async def stop_check_payment(user_id: int, app_id: int, session: DataInteraction, scheduler: AsyncIOScheduler):
    application = await session.get_application(app_id)
    if application.status != 2:
        await session.update_application(app_id, 0, None)
    job = scheduler.get_job(f'payment_{user_id}')
    if job:
        job.remove()
    job = scheduler.get_job(f'stop_payment_{user_id}')
    if job:
        job.remove()


async def send_messages(bot: Bot, session: DataInteraction, keyboard: InlineKeyboardMarkup|None, message: Message, **kwargs):
    users = await session.get_users()
    text = kwargs.get('text')
    caption = kwargs.get('caption')
    photo = kwargs.get('photo')
    video = kwargs.get('video')
    if text:
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user.user_id,
                    text=text.format(name=user.name),
                    reply_markup=keyboard
                )
                if user.active == 0:
                    await session.set_active(user.user_id, 1)
            except Exception as err:
                print(err)
                await session.set_active(user.user_id, 0)
    elif caption:
        if photo:
            for user in users:
                try:
                    await bot.send_photo(
                        chat_id=user.user_id,
                        photo=photo,
                        caption=caption.format(name=user.name),
                        reply_markup=keyboard
                    )
                    if user.active == 0:
                        await session.set_active(user.user_id, 1)
                except Exception as err:
                    print(err)
                    await session.set_active(user.user_id, 0)
        else:
            for user in users:
                try:
                    await bot.send_video(
                        chat_id=user.user_id,
                        video=video,
                        caption=caption.format(name=user.name),
                        reply_markup=keyboard
                    )
                    if user.active == 0:
                        await session.set_active(user.user_id, 1)
                except Exception as err:
                    print(err)
                    await session.set_active(user.user_id, 0)


async def clean_applications(session: DataInteraction):
    today = (datetime.today() - timedelta(days=3)).timestamp()
    for application in await session.get_applications():
        if application.create.timestamp() <= today:
            await session.del_application(application.uid_key)

