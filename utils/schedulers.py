import asyncio
from aiogram import Bot
from aiogram import Bot
from aiogram_dialog import DialogManager
from aiogram.types import InlineKeyboardMarkup, Message
from datetime import datetime, timedelta

from .payment import check_crypto_payment, check_yookassa_payment
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.action_data_class import DataInteraction


async def check_payment(bot: Bot, user_id: int, session: DataInteraction, scheduler: AsyncIOScheduler, **kwargs):
    invoice_id = kwargs.get('invoice_id')
    card_id = kwargs.get('card_id')
    if await check_crypto_payment(invoice_id) or await check_yookassa_payment(card_id):
        # Отправить токены
        username = kwargs.get('username')
        await bot.send_message(
            chat_id=user_id,
            text='Оплата была успешно совершенна, звезды были отправлены на счет'
        )
        job = scheduler.get_job(f'payment_{user_id}')
        if job:
            job.remove()
        stop_job = scheduler.get_job(f'stop_payment_{user_id}')
        if stop_job:
            stop_job.remove()
        return
    return


async def stop_check_payment(user_id: int, scheduler: AsyncIOScheduler):
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

