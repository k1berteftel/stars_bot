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
from utils.transactions import check_user_premium, get_stars_price
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG, PaymentSG

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
    media = MediaAttachment(type=ContentType.PHOTO, path='medias/menu.png')
    return {
        'stars': formatted_stars,
        'usdt': formatted_usdt,
        'admin': admin,
        'media': media
    }


async def buy_choose(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data.clear()
    rate = clb.data.split('_')[0]
    dialog_manager.dialog_data['rate'] = rate
    if rate == 'ton':
        await dialog_manager.switch_to(startSG.choose_ton_method)
        return
    await dialog_manager.switch_to(state=startSG.pay_menu)


async def choose_ton_method(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    method = clb.data.split('_')[0]
    dialog_manager.dialog_data['ton_method'] = method
    if method == 'address':
        await dialog_manager.switch_to(startSG.get_ton_address)
        return
    await dialog_manager.switch_to(startSG.pay_menu)


async def get_ton_address(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    dialog_manager.dialog_data['username'] = text
    await dialog_manager.switch_to(startSG.pay_menu)


async def pay_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    rate = dialog_manager.dialog_data.get('rate')
    username = dialog_manager.dialog_data.get('username')
    not_address = True
    if not username:
        username = '@' + event_from_user.username
        dialog_manager.dialog_data['username'] = username
    if rate == 'stars':
        text = (f'<b><tg-emoji emoji-id="5897920748101571572">🌟</tg-emoji>Покупка Telegram Stars</b>\n - Получатель: {username}\n\n'
                f'<em>Чтобы установить кол-во звезд для покупки <b>введите кол-во звезд текстом<tg-emoji emoji-id="5470177992950946662">👇</tg-emoji> '
                f'(от 50 до 25000)</b></em>')
        buttons = [
            ('50', '50'),
            ('100', '100'),
            ('500', '500'),
            ('1000', '1000')
        ]
    elif rate == 'premium':
        text = (f'<b><tg-emoji emoji-id="6190484269513586305">🌟</tg-emoji>Покупка Telegram Premium</b>\n - Получатель: {username}\n\n'
                f'<em>Чтобы продолжить выберите внизу тариф подписки<tg-emoji emoji-id="5470177992950946662">👇</tg-emoji></em>')
        buttons = [
            ('3 месяца', '3'),
            ('6 месяцев', '6'),
            ('12 месяцев', '12')
        ]
    else:
        ton_method = dialog_manager.dialog_data.get('ton_method')
        if ton_method == 'username':
            text = (f'<b>Покупка TON</b>\n - Получатель: {username}\n\n'
                    f'<em>Чтобы продолжить введите кол-во TON для приобретения<tg-emoji emoji-id="5470177992950946662">👇</tg-emoji></em>')
        else:
            text = (f'<b>Покупка TON</b>\n - Адрес получателя: {username}\n\n'
                    f'<em>Чтобы продолжить введите кол-во TON для приобретения<tg-emoji emoji-id="5470177992950946662">👇</tg-emoji></em>')
            not_address = False
        buttons = []
    return {
        'text': text,
        'items': buttons,
        'username': username,
        'not_address': not_address
    }


async def get_currency_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    rate = dialog_manager.dialog_data.get('rate')
    if rate == 'stars':
        try:
            currency = int(text)
        except Exception:
            await msg.delete()
            await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Кол-во звезд должно быть числом, пожалуйста попробуйте снова')
            return
        if not (50 <= currency < 25000):
            await msg.delete()
            await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Кол-во звезд должно быть быть не меньше 50 и не больше 25000')
            return
        dialog_manager.dialog_data['currency'] = currency
        await dialog_manager.switch_to(startSG.get_promo)
        return
    elif rate == 'ton':
        try:
            currency = float(text)
        except Exception:
            await msg.delete()
            await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Кол-во TON должно быть числом, пожалуйста попробуйте снова')
            return
    await msg.delete()
    await dialog_manager.switch_to(startSG.pay_menu)


async def pay_menu_selector(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data['currency'] = int(item_id)
    rate = dialog_manager.dialog_data.get('rate')
    if rate == 'stars':
        await dialog_manager.switch_to(startSG.get_promo)
        return
    rate = dialog_manager.dialog_data.get('rate')
    username = dialog_manager.dialog_data.get('username')
    currency = dialog_manager.dialog_data.get('currency')

    if rate == 'premium':
        if not await check_user_premium(username, currency):
            await clb.message.answer(
                '<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>У данного пользователя уже есть подписка, пожалуйста выберите другого получателя')
            return
    start_data = {'rate': rate, 'username': username, 'currency': currency}
    await dialog_manager.start(PaymentSG.menu, data=start_data)


async def get_promo(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    promo = await session.check_promo(msg.from_user.id, text)
    if not promo:
        await msg.answer('<tg-emoji emoji-id="5435857806936777022">😔</tg-emoji>К сожалению такого промокода не было найдено или же вы уже вводили его')
        return
    await msg.answer('<tg-emoji emoji-id="5456432998092133477">✅</tg-emoji>Промокод был успешно активирован')
    dialog_manager.dialog_data['promo'] = promo.percent
    rate = dialog_manager.dialog_data.get('rate')
    username = dialog_manager.dialog_data.get('username')
    currency = dialog_manager.dialog_data.get('currency')
    start_data = {'rate': rate, 'username': username, 'currency': currency, 'promo': promo.percent}
    await dialog_manager.start(PaymentSG.menu, data=start_data)


async def skip_promo(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    rate = dialog_manager.dialog_data.get('rate')
    username = dialog_manager.dialog_data.get('username')
    currency = dialog_manager.dialog_data.get('currency')
    start_data = {'rate': rate, 'username': username, 'currency': currency}
    await dialog_manager.start(PaymentSG.menu, data=start_data)


async def get_username(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    rate = dialog_manager.dialog_data.get('rate')
    import re
    username = text.strip()
    match = re.match(r"^@?([a-zA-Z0-9_]{5,32})$", username)
    if not match:
        await msg.delete()
        await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Юзернейм должен быть в формате "@username", пожалуйста попробуйте снова')
        return
    if rate == 'premium':
        if not await check_user_premium(username, 3):
            await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>У данного пользователя уже есть подписка, пожалуйста выберите кого-нибудь другого')
            return
    dialog_manager.dialog_data['username'] = username
    await dialog_manager.switch_to(startSG.pay_menu)


async def ref_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(event_from_user.id)
    text = (f'<b><tg-emoji emoji-id="5377548235709619284">🤑</tg-emoji> Партнерская программа</b>\n\nПриглашайте людей и получайте по 15% от их навсегда\n\n'
            f'<b>Ваша партнерская ссылка:\n</b>t.me/TrustStarsBot?start={event_from_user.id}\n\n<b>Статистика вашей партнерки:</b>'
            f'\n\t- Рефералов: {user.refs}\n\t- Баланс: {user.earn} ₽\n\n<em>С данного баланса вы можете приобретать '
            f'продаваемую нами продукцию.</em>')
    return {
        'text': text,
        'url': f'http://t.me/share/url?url=https://t.me/TrustStarsBot?start={event_from_user.id}'
    }


async def get_derive_amount_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    if user.earn < 100:
        await clb.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Сумма для вывода от 100 ₽ или более .')
        return
    await dialog_manager.switch_to(startSG.get_derive_amount)


async def get_derive_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        amount = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Сумма для вывода должна быть числом, пожалуйста попробуйте снова')
        return
    if amount < 100:
        await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Сумма для вывода не может быть меньше 50')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    msg_user = await session.get_user(msg.from_user.id)
    if amount > msg_user.earn:
        await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Сумма для вывода должна быть не больше той что сейчас у вас')
        return
    username = msg.from_user.username
    if not username:
        await msg.answer(text='<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Чтобы с вами могли связаться для выплаты, '
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
    await msg.answer('<tg-emoji emoji-id="5456432998092133477">✅</tg-emoji>Заявка на вывод средств была успешно отправлена')
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(startSG.ref_menu)


async def profile_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(event_from_user.id)
    text = (f'<b><tg-emoji emoji-id="5467730450002746997">🔍</tg-emoji> Ваш профиль</b>\n\n<blockquote>🆔 Telegram ID: {user.user_id}\n<tg-emoji emoji-id="5224257782013769471">💰</tg-emoji> Реферальный баланс: {user.earn} ₽'
            f'\n<tg-emoji emoji-id="5463289097336405244">⭐</tg-emoji> Куплено звёзд вами: {user.buys}</blockquote>')
    return {
        'text': text
    }
