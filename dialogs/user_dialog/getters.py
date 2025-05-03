from aiogram import Bot
from aiogram.types import CallbackQuery, User, Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.schedulers import check_payment, stop_check_payment
from utils.payment import get_crypto_payment_data, get_yookassa_payment_data
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG


config: Config = load_config()


async def start_getter(event_from_user: User, **kwargs):
    admin = False
    if event_from_user.id in config.bot.admin_ids:
        admin = True
    return {'admin': admin}


async def payment_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    bot: Bot = dialog_manager.middleware_data.get('bot')
    amount = dialog_manager.dialog_data.get('amount')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    job = scheduler.get_job(f'payment_{event_from_user.id}')
    crypto_url = dialog_manager.dialog_data.get('crypto_url')
    yookassa_url = dialog_manager.dialog_data.get('yookassa_url')
    if not job:
        #yookassa_payment = await get_yookassa_payment_data(amount)
        crypto_payment = await get_crypto_payment_data(amount)
        #dialog_manager.dialog_data['yookassa_url'] = yookassa_payment.get('url')
        dialog_manager.dialog_data['yookassa_url'] = crypto_payment.get('url')
        dialog_manager.dialog_data['crypto_url'] = crypto_payment.get('url')
        crypto_url = crypto_payment.get('url')
        #yookassa_url = yookassa_payment.get('url')
        yookassa_url = crypto_payment.get('url')
        username = dialog_manager.dialog_data.get('username')
        if not username:
            username = '@' + event_from_user.username
        if not event_from_user.username:
            await bot.send_message(
                chat_id=event_from_user.id,
                text='❗️Чтобы покупать звезды, пожалуйста поставьте на свой аккаунт юзернейм себе юзернейм'
            )
            dialog_manager.dialog_data.clear()
            await dialog_manager.switch_to(startSG.start)
            return
        scheduler.add_job(
            check_payment,
            'interval',
            args=[bot, event_from_user.id, session, scheduler],
            kwargs={'card_id': crypto_payment.get('id'), 'invoice_id': crypto_payment.get('id'), 'username': username},  # yookassa_payment.get('id')
            id=f'payment_{event_from_user.id}',
            seconds=5
        )
        job = scheduler.get_job(f'stop_payment_{event_from_user.id}')
        if not job:
            scheduler.add_job(
                stop_check_payment,
                'interval',
                args=[event_from_user.id, scheduler],
                id=f'stop_payment_{event_from_user.id}',
                minutes=30
            )
    return {
        'crypto_link': crypto_url,
        'card_link': yookassa_url
    }


async def close_payment(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    job = scheduler.get_job(f'payment_{clb.from_user.id}')
    if job:
        job.remove()
    dialog_manager.dialog_data.clear()
    await dialog_manager.done()
    await clb.message.delete()
    await dialog_manager.start(startSG.start, mode=StartMode.RESET_STACK)


async def get_stars_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Кол-во звезд должно быть числом, пожалуйста попробуйте снова')
        return
    if not (50 <= amount <= 1000000):
        await msg.answer('❗️Кол-во звезд должно быть больше 50 и меньше 1000000')
        return
    dialog_manager.dialog_data['amount'] = amount
    await dialog_manager.switch_to(startSG.get_promo)


async def get_promo(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    promo = await session.check_promo(msg.from_user.id, text)
    if not promo:
        await msg.answer('😔К сожалению такого промокода не было найдено или же вы уже вводили его')
    await msg.answer('✅Промокод был успешно активирован')
    amount = dialog_manager.dialog_data.get('amount')
    dialog_manager.dialog_data['amount'] = amount - (amount * promo.percent / 100)
    await dialog_manager.switch_to(startSG.payment_menu)


async def get_username(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    if not text.startswith('@'):
        await msg.answer('❗️Юзернейм должен начинаться со знака @')
        return
    # проверка пользователя на существование
    dialog_manager.dialog_data['username'] = text
    await dialog_manager.switch_to(startSG.get_stars_amount)


async def get_ref_amount_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    if user.earn < 100:
        await clb.answer('❗️Сумма для покупки звезд через партнерские начисления должна быть 100 или более руб.')
        return
    await dialog_manager.switch_to(startSG.get_stars_amount)


async def ref_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(event_from_user.id)
    text = (f'<b>👥 Партнерская программа</b>\n\nПриглашайте людей и получайте 15% от нашего дохода НАВСЕГДА\n\n'
            f'<b>Ваша партнерская ссылка:\n</b>t.me/TrustStarsBot?start={event_from_user.id}\n\n<b>Статистика вашей партнерки:</b>'
            f'\n\t- Рефералов: {user.refs}\n\t- Баланс: {user.earn} руб\n\n<b>Минимальная сумма выплаты - 100 руб</b>')
    return {
        'text': text,
        'url': f'http://t.me/share/url?url=https://t.me/TrustStarsBot?start={event_from_user.id}'
    }


async def get_derive_amount_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    if user.earn < 100:
        await clb.answer('❗️Сумма для вывода 100 или более руб.')
        return
    await dialog_manager.switch_to(startSG.get_derive_amount)


async def get_derive_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Сумма для вывода должна быть числом, пожалуйста попробуйте снова')
        return
    if amount < 50:
        await msg.answer('❗️Сумма для вывода не может быть меньше 50')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(msg.from_user.id)
    if amount > user.earn:
        await msg.answer('❗️Сумма для вывода должна быть не больше той что сейчас у вас')
        return
    dialog_manager.dialog_data['derive_amount'] = amount
    await dialog_manager.switch_to(startSG.get_card)


async def get_card(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    pass

