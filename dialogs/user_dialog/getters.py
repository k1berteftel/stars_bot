import os

from aiogram import Bot
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import CallbackQuery, User, Message, ContentType, FSInputFile
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.transactions import transfer_stars
from utils.tables import get_table
from utils.schedulers import check_payment, stop_check_payment
from utils.payment import get_crypto_payment_data, get_oxa_payment_data, _get_usdt_rub, get_wata_card_data, get_p2p_sbp, get_wata_sbp_data
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG


config: Config = load_config()


async def start_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    admin = False
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admins = [user.user_id for user in await session.get_admins()]
    admins.extend(config.bot.admin_ids)
    if event_from_user.id in admins:
        admin = True
    media = MediaId(file_id='AgACAgIAAxkBAAIBQGgaN21XHo8C0ui8X_vXVD_1dp9BAAJg8DEb9dvQSFW59oxus4LOAQADAgADeAADNgQ')
    media = MediaAttachment(type=ContentType.PHOTO, file_id=media)
    return {'admin': admin,
            'media': media}


async def rules_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    text = ('<b>Политика использования</b>\nЦель магазина: Магазин предоставляет услуги по продаже звезд в Telegram.\n\n'
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
    stars = dialog_manager.dialog_data.get('amount')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    job = scheduler.get_job(f'payment_{event_from_user.id}')
    crypto_url = dialog_manager.dialog_data.get('crypto_url')
    sbp_url = dialog_manager.dialog_data.get('sbp_url')
    oxa_url = dialog_manager.dialog_data.get('oxa_url')
    card_url = dialog_manager.dialog_data.get('card_url')
    prices = await session.get_prices()
    promo = dialog_manager.dialog_data.get('promo')
    amount = int(round((stars * 1.21) / (1 - prices.charge / 100)))
    if promo:
        amount = amount - (amount * promo / 100)
    usdt = round(amount / (78), 2)  # await _get_usdt_rub() - перестал отображаться курс
    username = dialog_manager.dialog_data.get('username')
    if not username:
        username = event_from_user.username
    if not event_from_user.username and username:
        await bot.send_message(
            chat_id=event_from_user.id,
            text='❗️Чтобы покупать звезды, пожалуйста поставьте на свой аккаунт юзернейм'
        )
        dialog_manager.dialog_data.clear()
        await dialog_manager.switch_to(startSG.start)
        return
    app_id = dialog_manager.dialog_data.get('app_id')
    if app_id:
        application = await session.get_application(app_id)
    if not job or not app_id:
        sbp_payment = await get_p2p_sbp(amount)  # после фикса заменить
        crypto_payment = await get_crypto_payment_data(usdt)
        oxa_payment = await get_oxa_payment_data(usdt)
        #card_payment = await get_wata_card_data(event_from_user.id, amount)
        dialog_manager.dialog_data['sbp_url'] = sbp_payment.get('url')
        dialog_manager.dialog_data['crypto_url'] = crypto_payment.get('url')
        dialog_manager.dialog_data['oxa_url'] = oxa_payment.get('url')
        #dialog_manager.dialog_data['card_url'] = card_payment.get('url')
        crypto_url = crypto_payment.get('url')
        sbp_url = sbp_payment.get('url')
        oxa_url = oxa_payment.get('url')
        #card_url = card_payment.get('url')
        application = await session.add_application(event_from_user.id, username, stars, amount, usdt)
        dialog_manager.dialog_data['app_id'] = app_id
        dialog_manager.dialog_data['uid_key'] = application.uid_key
        job = scheduler.get_job(job_id=f'payment_{event_from_user.id}')
        if job:
            job.remove()
        scheduler.add_job(
            check_payment,
            'interval',
            args=[bot, event_from_user.id, application.uid_key, session, scheduler],
            kwargs={
                'invoice_id': crypto_payment.get('id'), 'track_id': oxa_payment.get('id'),
                'username': username, 'stars': stars, 'card_id': sbp_payment.get('id'),
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
        'crypto_link': crypto_url,
        'oxa_link': oxa_url,
        'sbp_link': sbp_url,
        #'card_link': card_url,
        'uid_key': application.uid_key,
        'rub': float(amount),
        'usdt': usdt,
        'amount': stars,
        'username': username
    }


async def close_payment(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    application = await session.get_application(dialog_manager.dialog_data.get('uid_key'))
    if application.status != 2:
        await session.update_application(dialog_manager.dialog_data.get('uid_key'), 0, None)
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


async def get_stars_amount(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
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
    await dialog_manager.switch_to(startSG.get_stars_amount)


async def get_ref_amount_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    #if user.earn < 100:
        #await clb.answer('❗️Сумма для покупки звезд через партнерские начисления должна быть 100 или более руб.')
        #return
    await dialog_manager.switch_to(startSG.get_stars_amount)


async def ref_menu_getter(event_from_user: User, dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(event_from_user.id)
    text = (f'<b>👥 Партнерская программа</b>\n\nПриглашайте людей и получайте по 3⭐️ за '
            f'каждого приглашенного и по 2⭐️ за каждого приглашенного вашим рефералом\n\n'
            f'<b>Ваша партнерская ссылка:\n</b>t.me/TrustStarsBot?start={event_from_user.id}\n\n<b>Статистика вашей партнерки:</b>'
            f'\n\t- Рефералов: {user.refs}\n\t- Баланс: {user.earn} ⭐️\n\n<b>Минимальная сумма выплаты - 100 ⭐️</b>')
    return {
        'text': text,
        'url': f'http://t.me/share/url?url=https://t.me/TrustStarsBot?start={event_from_user.id}'
    }


async def get_derive_amount_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    user = await session.get_user(clb.from_user.id)
    if user.earn < 100:
        await clb.answer('❗️Сумма для вывода 100 звезд или более .')
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
    msg_user = await session.get_user(msg.from_user.id)
    if amount > msg_user.earn:
        await msg.answer('❗️Сумма для вывода должна быть не больше той что сейчас у вас')
        return
    username = msg.from_user.username
    if not username:
        await msg.answer(text='❗️Чтобы получить звезды, пожалуйста поставьте на свой аккаунт юзернейм')
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
            f'\n - Общий баланс: {msg_user.earn}⭐️\n - <b>Сумма для вывода</b>: {amount}⭐️')
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

