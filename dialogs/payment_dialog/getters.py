import asyncio

from aiogram import Bot
from aiogram.types import CallbackQuery, User, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from nats.js import JetStreamContext

from utils.payments.create import (get_oxa_payment_data, get_crypto_payment_data,
                                           get_platega_sbp, get_paypear_sbp, _get_usdt_rub)
from utils.payments.process import wait_for_payment
from utils.transactions import get_stars_price
from utils.text_utils import send_application_log
from services.publisher import send_publisher_data
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG, PaymentSG


config: Config = load_config()


premium_usdt = {
    3: 12,
    6: 16,
    12: 29
}


async def polling_app_status(app_id: int, session: DataInteraction, bot: Bot, timeout: int = 60 * 20):
    async def check_app_status(app_id: int, session: DataInteraction):
        while True:
            application = await session.get_application(app_id)
            if application.status != 1:
                return
            await asyncio.sleep(30)
    try:
        await asyncio.wait_for(check_app_status(app_id, session), timeout=timeout)
    except TimeoutError:
        await session.update_application(app_id, 0)
    except Exception:
        await session.update_application(app_id, 0)


async def menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    if dialog_manager.start_data:
        dialog_manager.dialog_data.update(dialog_manager.start_data)
        dialog_manager.start_data.clear()
    bot: Bot = dialog_manager.middleware_data.get('bot')
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    rate = dialog_manager.dialog_data.get('rate')
    username = dialog_manager.dialog_data.get('username')
    currency = dialog_manager.dialog_data.get('currency')
    promo = dialog_manager.dialog_data.get('promo')
    prices = await session.get_prices()
    usdt_rub = await _get_usdt_rub()
    if rate == 'deleted_gift':
        amount = currency
        usdt = round(amount / usdt_rub, 2)
        gift_name = dialog_manager.dialog_data.get('gift')
        text = (f'<blockquote> - <b>Номер заказа:</b> <code>{{app_id}}</code>\n - Получатель: {username}\n'
                f' - Подарок: {gift_name}\n - Сумма к оплате: {amount}₽ ({usdt}$)</blockquote>')
        currency = int(dialog_manager.dialog_data.get('gift_id'))
    elif rate == 'stars':
        usdt = await get_stars_price(currency)
        if usdt is None:
            await dialog_manager.done()
            return
        amount = round((usdt * usdt_rub) / (1 - prices.stars_charge / 100), 2)
        if promo:
            amount = amount - (amount * promo / 100)
        usdt = round(amount / usdt_rub, 2)
        text = (f'<blockquote> - <b>Номер заказа:</b> <code>{{app_id}}</code>\n - Получатель: {username}\n'
                f' - Количество звезд: {currency}\n - Сумма к оплате: {amount}₽ ({usdt}$)</blockquote>')
    else:
        usdt = premium_usdt[currency]
        amount = round((usdt * usdt_rub) / (1 - prices.premium_charge / 100), 2)
        usdt = round(amount / (usdt_rub), 2)
        text = (f'<blockquote> - <b>Номер заказа:</b> <code>{{app_id}}</code>\n - Получатель: {username}\n'
                f' - Подписка на: {currency} (месяцы)\n - Сумма к оплате: {amount}₽ ({usdt}$)</blockquote>')
    app_id = dialog_manager.dialog_data.get('app_id')
    if not app_id:
        application = await session.add_application(event_from_user.id, username, currency, amount, usdt, rate)
        app_id = application.uid_key
        dialog_manager.dialog_data['app_id'] = app_id
    text = text.format(app_id=app_id)

    check_task = None
    task_name = f'check_app_{event_from_user.id}'
    for task in asyncio.all_tasks():
        if task.get_name() == task_name:
            check_task = task
            break
    if not check_task:
        check_task = asyncio.create_task(polling_app_status(app_id, session, bot))
        check_task.set_name(task_name)

    return {'text': text}


async def payment_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    js: JetStreamContext = dialog_manager.middleware_data.get('js')
    payment_type = clb.data.split('_')[0]
    app_id = dialog_manager.dialog_data.get('app_id')
    rate = dialog_manager.dialog_data.get('rate')
    currency = dialog_manager.dialog_data.get('currency')
    username = dialog_manager.dialog_data.get('username')
    promo = dialog_manager.dialog_data.get('promo')
    prices = await session.get_prices()
    usdt_rub = await _get_usdt_rub()
    if rate == 'deleted_gift':
        amount = currency
        usdt = round(amount / usdt_rub, 2)
        currency = int(dialog_manager.dialog_data.get('gift_id'))
    elif rate == 'stars':
        usdt = await get_stars_price(currency)
        amount = round((usdt * usdt_rub) / (1 - prices.stars_charge / 100), 2)
        if promo:
            amount = amount - (amount * promo / 100)
        usdt = round(amount / usdt_rub, 2)
    else:
        usdt = premium_usdt[currency]
        amount = round((usdt * usdt_rub) / (1 - prices.premium_charge / 100), 2)
        usdt = round(amount / (usdt_rub), 2)

    if payment_type == 'card':
        pass
        # payment = await get_freekassa_card(clb.from_user.id, amount, app_id)
    elif payment_type == 'sbp1':
        payment = await get_paypear_sbp(amount, app_id)
    elif payment_type == 'sbp2':
        payment = await get_platega_sbp(amount, app_id, clb.from_user.id)
    elif payment_type == 'crypto':
        payment = await get_oxa_payment_data(amount)
        task = asyncio.create_task(
            wait_for_payment(
                payment_id=payment.get('id'),
                user_id=clb.from_user.id,
                app_id=app_id,
                bot=clb.bot,
                session=session,
                js=js,
                currency=currency,
                rate=rate,
                payment_type='crypto',
            )
        )
        for active_task in asyncio.all_tasks():
            if active_task.get_name() == f'process_payment_{clb.from_user.id}':
                active_task.cancel()
        task.set_name(f'process_payment_{clb.from_user.id}')
    else:
        payment = await get_crypto_payment_data(amount)
        task = asyncio.create_task(
            wait_for_payment(
                payment_id=payment.get('id'),
                user_id=clb.from_user.id,
                app_id=app_id,
                bot=clb.bot,
                session=session,
                js=js,
                currency=currency,
                rate=rate,
                payment_type='cryptoBot',
            )
        )
        for active_task in asyncio.all_tasks():
            if active_task.get_name() == f'process_payment_{clb.from_user.id}':
                active_task.cancel()
        task.set_name(f'process_payment_{clb.from_user.id}')
    dialog_manager.dialog_data['url'] = payment.get('url')
    dialog_manager.dialog_data['amount'] = amount
    dialog_manager.dialog_data['usdt'] = usdt
    await dialog_manager.switch_to(PaymentSG.process_payment)


async def from_balance(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    js: JetStreamContext = dialog_manager.middleware_data.get('js')
    app_id = dialog_manager.dialog_data.get('app_id')
    rate = dialog_manager.dialog_data.get('rate')
    currency = dialog_manager.dialog_data.get('currency')
    username = dialog_manager.dialog_data.get('username')
    promo = dialog_manager.dialog_data.get('promo')
    user = await session.get_user(clb.from_user.id)
    prices = await session.get_prices()
    usdt_rub = await _get_usdt_rub()
    if rate == 'deleted_gift':
        amount = currency
        usdt = round(amount / usdt_rub, 2)
        currency = int(dialog_manager.dialog_data.get('gift_id'))
    elif rate == 'stars':
        usdt = await get_stars_price(currency)
        amount = int(round((usdt * usdt_rub) / (1 - prices.stars_charge / 100)))
        if promo:
            amount = amount - (amount * promo / 100)
    else:
        usdt = premium_usdt[currency]
        amount = int(round((usdt * usdt_rub) / (1 - prices.premium_charge / 100)))

    if user.earn < amount:
        await clb.answer('❗️На вашем партнерском балансе недостаточно средств для оплаты покупки"')
        return

    transfer_data = {
        'transfer_type': rate,
        'username': username,
        'currency': currency,
        'payments': 'referral',
        'app_id': app_id
    }
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=transfer_data
    )

    name = f'process_payment_{clb.from_user.id}'
    for task in asyncio.all_tasks():
        if task.get_name() == name:
            task.cancel()

    await session.update_earn(clb.from_user.id, -amount)
    await clb.answer('✅Оплата с реферального баланса прошла успешно, пожалуйста ожидайте транзакцию')


async def process_payment_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    amount = dialog_manager.dialog_data.get('amount')
    usdt = dialog_manager.dialog_data.get('usdt')
    url = dialog_manager.dialog_data.get('url')
    app_id = dialog_manager.dialog_data.get('app_id')
    text = f'<blockquote> - Сумма к оплате: {amount}₽ ({usdt}$)</blockquote>\n<b> - Номер заказа: {app_id}</b>'
    return {
        'text': text,
        'url': url
    }


async def close_payment(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    name = f'process_payment_{clb.from_user.id}'
    for task in asyncio.all_tasks():
        if task.get_name() == name:
            task.cancel()
    await dialog_manager.switch_to(PaymentSG.menu)
