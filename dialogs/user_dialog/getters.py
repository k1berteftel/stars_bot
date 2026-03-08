import asyncio
import os

from aiogram import Bot
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import CallbackQuery, User, Message, ContentType, FSInputFile
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nats.js import JetStreamContext

from services.publisher import send_publisher_data
from utils.tables import get_table
from utils.schedulers import check_payment, stop_check_payment
from utils.payment import get_crypto_payment_data, get_oxa_payment_data, get_freekassa_sbp, get_freekassa_card
from utils.payment import _get_ton_usdt, _get_usdt_rub
from utils.transactions import check_user_premium, get_stars_price
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG

config: Config = load_config()

premium_usdt = {
    3: 12,
    6: 16,
    12: 29
}


async def start_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    admin = False
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admins = [user.user_id for user in await session.get_admins()]
    admins.extend(config.bot.admin_ids)
    static = await session.get_statistics()
    try:
        usdt = await get_stars_price(static.buys)
    except Exception:
        usdt = round(static.buys * 0.015, 2)

    formatted_stars = f"{static.buys:,}".replace(",", " ")
    formatted_usdt = f"{usdt:,}".replace(",", " ")

    if event_from_user.id in admins:
        admin = True
    media = MediaAttachment(type=ContentType.PHOTO, path='medias/new_menu.jpg')
    return {
        'stars': formatted_stars,
        'usdt': formatted_usdt,
        'admin': admin,
        'media': media
    }


async def rules_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    text = (
        '<b>Политика использования</b>\nЦель магазина: Магазин предоставляет услуги по продаже звезд в Telegram.\n\n'
        'Правила использования: Пользователи обязаны соблюдать все применимые законы и правила платформ,'
        ' на которых они используют купленные звезды. Запрещены попытки обмана, мошенничество и другие '
        'недопустимые действия.\n\nПрием платежей: Мы принимаем платежи через указанные методы, '
        'обеспечивая безопасность и конфиденциальность ваших данных.\n\nОбязательства магазина:'
        ' Магазин обязуется предоставить вам купленные звезды после успешной оплаты.\n\nОтветственность '
        'пользователя: Вы несете ответственность за предоставление правильной информации при заказе услуги.'
        ' Пользователи должны предоставить корректные данные для успешного выполнения заказа.\n\nЗапрещенные'
        ' действия: Запрещены действия, направленные на мошенничество, включая попытки '
        'возврата средств после получения услуги.\n\n<b>Политика возврата</b>\nУсловия возврата: Вы можете '
        'запросить возврат средств, если не получили звезд. Нужны скрины оплаты и главной страницы бота.\n\n'
        'Процедура возврата: Для запроса возврата, свяжитесь с нашей службой поддержки по указанным '
        'контактным данным. Мы рассмотрим ваш запрос и произведем возврат средств на вашу карту/кошелек.\n\n'
        'Сроки возврата: Вы получите средства в течение 3 рабочих дней.\n\n<b>Политика конфиденциальности</b>\n'
        'Сбор информации: Мы можем собирать определенную информацию от пользователей для обработки заказов '
        'и улучшения сервиса.\n\nИспользование информации: Мы обеспечиваем безопасное и конфиденциальное '
        'хранение ваших данных. Информация будет использована исключительно для обработки заказов и '
        'обратной связи с вами.\n\nРазглашение информации: Мы не раскроем вашу информацию третьим '
        'лицам, за исключением случаев, предусмотренных законом или в случаях, когда это необходимо '
        'для выполнения заказа (например, передача информации платежным системам).\n\nСогласие пользователя: '
        'Используя наши услуги, вы соглашаетесь с нашей политикой конфиденциальности.')
    return {'text': text}


async def payment_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    bot: Bot = dialog_manager.middleware_data.get('bot')
    buy = dialog_manager.dialog_data.get('buy')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    job = scheduler.get_job(f'payment_{event_from_user.id}')
    crypto_url = dialog_manager.dialog_data.get('crypto_url')
    sbp_url = dialog_manager.dialog_data.get('sbp_url')
    #oxa_url = dialog_manager.dialog_data.get('oxa_url')
    card_url = dialog_manager.dialog_data.get('card_url')
    prices = await session.get_prices()
    usdt_rub = await _get_usdt_rub()
    username = dialog_manager.dialog_data.get('username')
    if buy == 'stars':
        currency = dialog_manager.dialog_data.get('amount')
        usdt = await get_stars_price(currency)
        print(usdt, usdt_rub)
        return
        promo = dialog_manager.dialog_data.get('promo')
        amount = round((usdt * usdt_rub) / (1 - prices.stars_charge / 100), 2)
        if promo:
            amount = amount - (amount * promo / 100)
        usdt = round(amount / usdt_rub, 2)
        text = (f'<b>Номер заказа</b>: <code>{{uid_key}}</code>\n\n<b>Сумма к оплате</b>: <code>{amount}₽ ({usdt}$)</code>\n'
                f'<b>Вы покупаете</b>: <code>{currency} звезд</code>\n<b>Получатель</b>: <code>{username}</code>\n')
    elif buy == 'premium':
        currency = dialog_manager.dialog_data.get('months')
        usdt = premium_usdt[currency]
        amount = round((usdt * usdt_rub) / (1 - prices.premium_charge / 100), 2)
        usdt = round(amount / (usdt_rub), 2)
        text = (f'<b>Номер заказа</b>: <code>{{uid_key}}</code>\n\n<b>Сумма к оплате</b>: <code>{amount}₽ ({usdt}$)</code>\n'
                f'<b>Вы покупаете</b>: <code>Premium на {currency} месяца(ев)</code>\n<b>Получатель</b>: <code>{username}</code>\n')
    else:
        currency = dialog_manager.dialog_data.get('amount')
        ton_usdt = await _get_ton_usdt()
        usdt = currency * ton_usdt
        amount = round(((usdt * usdt_rub) / (1 - prices.ton_charge / 100)), 2)
        usdt = round(amount / (usdt_rub), 2)
        text = (f'<b>Номер заказа</b>: <code>{{uid_key}}</code>\n\n<b>Сумма к оплате</b>: <code>{amount}₽ ({usdt}$)</code>\n'
                f'<b>Вы покупаете</b>: <code>{currency} TON</code>\n<b>Получатель</b>: <code>{username}</code>\n')
    app_id = dialog_manager.dialog_data.get('app_id')
    if app_id:
        text = text.format(uid_key=app_id)
        application = await session.get_application(app_id)
    if not job or not app_id:
        application = await session.add_application(event_from_user.id, username, currency, int(amount), usdt, buy)
        app_id = application.uid_key
        text = text.format(uid_key=app_id)
        dialog_manager.dialog_data['app_id'] = app_id
        sbp_payment = await get_freekassa_sbp(event_from_user.id, amount, app_id)
        crypto_payment = await get_crypto_payment_data(usdt)
        # oxa_payment = await get_oxa_payment_data(usdt)
        card_payment = await get_freekassa_card(event_from_user.id, amount, app_id)
        dialog_manager.dialog_data['sbp_url'] = sbp_payment.get('url')
        dialog_manager.dialog_data['crypto_url'] = crypto_payment.get('url')
#         dialog_manager.dialog_data['oxa_url'] = oxa_payment.get('url')
        dialog_manager.dialog_data['card_url'] = card_payment.get('url')
        crypto_url = crypto_payment.get('url')
        sbp_url = sbp_payment.get('url')
#        oxa_url = oxa_payment.get('url')
        card_url = card_payment.get('url')
        job = scheduler.get_job(job_id=f'payment_{event_from_user.id}')
        if job:
            job.remove()
        js: JetStreamContext = dialog_manager.middleware_data.get('js')
        scheduler.add_job(
            check_payment,
            'interval',
            args=[js, event_from_user.id, application.uid_key, buy, scheduler],
            kwargs={
                'invoice_id': crypto_payment.get('id'), #'track_id': oxa_payment.get('id'),
                'username': username,
                'currency': currency,
                'order_id': sbp_payment.get('order_id')
            },
            id=f'payment_{event_from_user.id}',
            seconds=15
        )
        job = scheduler.get_job(f'stop_payment_{event_from_user.id}')
        if not job:
            scheduler.add_job(
                stop_check_payment,
                'interval',
                args=[event_from_user.id, application.uid_key, session, scheduler],
                id=f'stop_payment_{event_from_user.id}',
                minutes=30
            )
    return {
        'text': text,
        'crypto_link': crypto_url,
        #'oxa_link': oxa_url,
        'sbp_link': sbp_url,
        'card_link': card_url,
    }


async def close_payment(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    application = await session.get_application(dialog_manager.dialog_data.get('app_id'))
    if application.status != 2:
        await session.update_application(dialog_manager.dialog_data.get('app_id'), 0, None)
    job = scheduler.get_job(f'payment_{clb.from_user.id}')
    if job:
        job.remove()
    dialog_manager.dialog_data.clear()
    await dialog_manager.done()
    try:
        await clb.message.delete()
    except Exception:
        ...
    await dialog_manager.start(startSG.start, mode=StartMode.RESET_STACK)


async def from_balance_buy(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    js: JetStreamContext = dialog_manager.middleware_data.get('js')
    buy = dialog_manager.dialog_data.get('buy')
    user = await session.get_user(clb.from_user.id)
    prices = await session.get_prices()
    usdt_rub = await _get_usdt_rub()
    if buy == 'stars':
        currency = dialog_manager.dialog_data.get('amount')
        usdt = await get_stars_price(currency)
        promo = dialog_manager.dialog_data.get('promo')
        amount = int(round((usdt * usdt_rub) / (1 - prices.stars_charge / 100)))
        if promo:
            amount = amount - (amount * promo / 100)
    elif buy == 'premium':
        currency = dialog_manager.dialog_data.get('months')
        usdt = premium_usdt[currency]
        amount = int(round((usdt * usdt_rub) / (1 - prices.premium_charge / 100)))
    else:
        currency = dialog_manager.dialog_data.get('amount')
        ton_usdt = await _get_ton_usdt()
        usdt = currency * ton_usdt
        amount = int(round(((usdt * usdt_rub) / (1 - prices.ton_charge / 100))))

    if user.earn < amount:
        await clb.answer('❗️На вашем партнерском балансе недостаточно средств для оплаты покупки"')
        return
    app_id = dialog_manager.dialog_data.get('app_id')
    username = dialog_manager.dialog_data.get('username')
    transfer_data = {
        'transfer_type': buy,
        'username': username,
        'currency': currency,
        'payment': 'referral',
        'app_id': app_id
    }
    await send_publisher_data(
        js=js,
        subject=config.consumer.subject,
        data=transfer_data
    )
    job = scheduler.get_job(f'payment_{clb.from_user.id}')
    if job:
        job.remove()
    stop_job = scheduler.get_job(f'stop_payment_{clb.from_user.id}')
    if stop_job:
        stop_job.remove()
    await session.update_earn(clb.from_user.id, -amount)
    await clb.answer('✅Оплата с реферального баланса прошла успешно, пожалуйста ожидайте пополнения')


async def buy_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    buy = clb.data.split('_')[0]
    dialog_manager.dialog_data.clear()
    dialog_manager.dialog_data['buy'] = buy
    if buy == 'ton':
        await dialog_manager.switch_to(startSG.ton_receipt_menu)
        return
    await dialog_manager.switch_to(startSG.get_username)


async def get_username_getter(dialog_manager: DialogManager, **kwargs):
    buy = dialog_manager.dialog_data.get('buy')
    if buy == 'ton':
        text = 'TON'
    elif buy == 'premium':
        text = 'Премиум'
    else:
        text = 'Звезды'
    return {'present': text}


async def get_stars_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    # await msg.answer('На данный момент в боте ведутся <b>технические работы</b>, приносим свои извинения🙏   ')
    # await dialog_manager.switch_to(startSG.start)
    # return
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Кол-во звезд должно быть числом, пожалуйста попробуйте снова')
        return
    if not (50 <= amount <= 100000):
        await msg.answer('❗️Кол-во звезд должно быть больше 50 и меньше 1000000')
        return
    dialog_manager.dialog_data['amount'] = amount
    await dialog_manager.switch_to(startSG.get_promo)


async def premium_rate_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    months = int(clb.data.split('_')[0])
    dialog_manager.dialog_data['months'] = months
    await dialog_manager.switch_to(startSG.payment_menu)


async def get_ton_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Кол-во TON должно быть числом, пожалуйста попробуйте снова')
        return
    if not (1 <= amount < 100):
        await msg.answer('❗️Кол-во TON должно быть больше 1 и меньше 100')
        return
    dialog_manager.dialog_data['amount'] = amount
    await dialog_manager.switch_to(startSG.payment_menu)


async def get_rate_amount_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    username = dialog_manager.dialog_data.get('username')
    address = dialog_manager.dialog_data.get('address')
    buy = dialog_manager.dialog_data.get('buy')
    if buy in ['stars', 'premium']:
        return {
            'username': username,
            'address': False
        }
    else:
        if address:
            return {
                'username': False,
                'address': address
            }
        else:
            return {
                'username': username,
                'address': False
            }


async def get_promo(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    promo = await session.check_promo(msg.from_user.id, text)
    if not promo:
        await msg.answer('😔К сожалению такого промокода не было найдено или же вы уже вводили его')
        return
    await msg.answer('✅Промокод был успешно активирован')
    dialog_manager.dialog_data['promo'] = promo.percent
    await dialog_manager.switch_to(startSG.payment_menu)


async def get_username(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    if not text.startswith('@'):
        await msg.answer('❗️Юзернейм должен начинаться со знака @')
        return
    # проверка пользователя на существование
    dialog_manager.dialog_data['username'] = text
    buy = dialog_manager.dialog_data.get('buy')
    if buy == 'stars':
        await dialog_manager.switch_to(startSG.get_stars_amount)
    elif buy == 'premium':
        status = await check_user_premium(text, 12)
        if not status:
            await msg.answer('❗️У данного пользователя уже есть Премиум, пожалуйста попробуйте кого-нибудь еще')
            return
        await dialog_manager.switch_to(startSG.get_premium_rate)
    else:
        await dialog_manager.switch_to(startSG.get_ton_amount)


async def skip_get_username(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    username = clb.from_user.username
    if not username:
        await clb.message.answer('❗️Чтобы совершать покупки, пожалуйста поставьте на свой аккаунт юзернейм')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    if user.username != username:
        await session.update_username(clb.from_user.id, username)
    dialog_manager.dialog_data['username'] = username
    buy = dialog_manager.dialog_data.get('buy')
    if buy == 'stars':
        await dialog_manager.switch_to(startSG.get_stars_amount)
    elif buy == 'premium':
        status = await check_user_premium(username, 12)
        if not status:
            await clb.message.answer('❗️У вас уже есть Премиум, пожалуйста попробуйте кого-нибудь еще')
            return
        await dialog_manager.switch_to(startSG.get_premium_rate)
    else:
        await dialog_manager.switch_to(startSG.get_ton_amount)


async def get_ref_amount_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    # if user.earn < 100:
    # await clb.answer('❗️Сумма для покупки звезд через партнерские начисления должна быть 100 или более руб.')
    # return
    await dialog_manager.switch_to(startSG.get_stars_amount)


async def ref_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(event_from_user.id)
    text = (f'<b>👥 Партнерская программа</b>\n\nПриглашайте людей и получайте по 15% от их навсегда\n\n'
            f'<b>Ваша партнерская ссылка:\n</b>t.me/TrustStarsBot?start={event_from_user.id}\n\n<b>Статистика вашей партнерки:</b>'
            f'\n\t- Рефералов: {user.refs}\n\t- Баланс: {user.earn} ₽\n\n<b>С данного баланса вы можете приобретать '
            f'продаваемую нами продукцию или же просто вывести заработанные средства себе на карту. '
            f'Минимальная сумма выплаты - 100 ₽</b>')
    return {
        'text': text,
        'url': f'http://t.me/share/url?url=https://t.me/TrustStarsBot?start={event_from_user.id}'
    }


async def get_derive_amount_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    if user.earn < 100:
        await clb.answer('❗️Сумма для вывода от 100 ₽ или более .')
        return
    await dialog_manager.switch_to(startSG.get_derive_amount)


async def get_derive_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('❗️Сумма для вывода должна быть числом, пожалуйста попробуйте снова')
        return
    if amount < 100:
        await msg.answer('❗️Сумма для вывода не может быть меньше 50')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    msg_user = await session.get_user(msg.from_user.id)
    if amount > msg_user.earn:
        await msg.answer('❗️Сумма для вывода должна быть не больше той что сейчас у вас')
        return
    username = msg.from_user.username
    if not username:
        await msg.answer(text='❗️Чтобы с вами могли связаться для выплаты, '
                              'пожалуйста поставьте на свой аккаунт юзернейм')
        return
    ref_users = await session.get_ref_users(msg.from_user.id)
    users = []
    for user in ref_users:
        users.append(
            [
                user.user_id,
                user.name,
                '@' + user.username if user.username else '-',
                user.refs,
                user.entry.strftime('%d-%m-%Y %H:%M')
            ]
        )
    users.insert(0, ['User Id', 'Никнейм', 'Юзернейм', 'Рефералы', 'Первый запуск'])
    table_1 = get_table(users, 'Рефералы')
    sub_users = []
    sub_ref_users = await session.get_sub_ref_users(msg.from_user.id)
    for user in sub_ref_users:
        sub_users.append(
            [
                user.user_id,
                user.name,
                '@' + user.username if user.username else '-',
                user.refs,
                user.entry.strftime('%d-%m-%Y %H:%M')
            ]
        )
    sub_users.insert(0, ['User Id', 'Никнейм', 'Юзернейм', 'Рефералы', 'Первый запуск'])
    table_2 = get_table(sub_users, 'Рефералы 2')
    text = (f'<b>Заявка на вывод средств</b>\n\nДанные о пользователе:\n'
            f'- Никнейм: {msg_user.name}\n - Username: @{msg_user.username}'
            f'\n - Telegram Id: {msg.from_user.id}\n - Рефералы: {msg_user.refs}\n - Рефералы 2: {msg_user.sub_refs}'
            f'\n - Общий баланс: {msg_user.earn} ️₽\n - <b>Сумма для вывода</b>: {amount} ₽')
    builder = MediaGroupBuilder(caption=text)
    builder.add_document(FSInputFile(path=table_1))
    builder.add_document(FSInputFile(path=table_2))
    await msg.bot.send_media_group(
        media=builder.build(),
        chat_id=config.bot.admin_ids[0],
    )
    try:
        os.remove(table_1)
        os.remove(table_2)
    except Exception:
        ...
    await session.update_earn(msg.from_user.id, -amount)
    await msg.answer('✅Заявка на вывод средств была успешно отправлена')
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(startSG.ref_menu)


async def profile_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(event_from_user.id)
    text = (f'<b>👤 Ваш профиль</b>\n\n<blockquote>🆔 Telegram ID: {user.user_id}\n💰 Реферальный баланс: {user.earn} ₽'
            f'\n⭐ Куплено звёзд вами: {user.buys}</blockquote>')
    return {
        'text': text
    }
