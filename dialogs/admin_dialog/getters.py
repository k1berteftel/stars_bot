import os
import datetime

from aiogram import Bot
from aiogram.types import CallbackQuery, User, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput, MessageInput
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.tables import get_table
from utils.build_ids import get_random_id
from utils.schedulers import send_messages
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import startSG, adminSG


async def get_static(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    users = await session.get_users()
    active = 0
    entry = {
        'today': 0,
        'yesterday': 0,
        '2_day_ago': 0
    }
    activity = 0
    for user in users:
        if user.active:
            active += 1
        for day in range(0, 3):
            #print(user.entry.date(), (datetime.datetime.today() - datetime.timedelta(days=day)).date())
            if user.entry.date() == (datetime.datetime.today() - datetime.timedelta(days=day)).date():
                if day == 0:
                    entry['today'] = entry.get('today') + 1
                elif day == 1:
                    entry['yesterday'] = entry.get('yesterday') + 1
                else:
                    entry['2_day_ago'] = entry.get('2_day_ago') + 1
        if user.activity.timestamp() > (datetime.datetime.today() - datetime.timedelta(days=1)).timestamp():
            activity += 1
    statistic = await session.get_statistics()
    text = (f'<b>Статистика на {datetime.datetime.today().strftime("%d-%m-%Y")}</b>\n\nВсего пользователей: {len(users)}'
            f'\n - Активные пользователи(не заблокировали бота): {active}\n - Пользователей заблокировали '
            f'бота: {len(users) - active}\n - Провзаимодействовали с ботом за последние 24 часа: {activity}\n'
            f'Всего покупок: {statistic.payments}\n\n'
            f'<b>Прирост аудитории:</b>\n - За сегодня: +{entry.get("today")}\n - Вчера: +{entry.get("yesterday")}'
            f'\n - Позавчера: + {entry.get("2_day_ago")}')
    await clb.message.answer(text=text)


async def get_users_txt(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    users = await session.get_users()
    with open('users.txt', 'a+') as file:
        for user in users:
            file.write(f'{user.user_id}\n')
    await clb.message.answer_document(
        document=FSInputFile(path='users.txt')
    )
    try:
        os.remove('users.txt')
    except Exception:
        ...


async def get_ref_table(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    users = await session.get_users()
    table_users = []
    for user in users:
        if not user.earn and not user.buys:
            continue
        table_users.append(
            [
                user.user_id,
                user.name,
                '@' + user.username if user.username else '-',
                user.refs,
                user.sub_refs,
                user.earn,
                user.buys
            ]
        )
    table_users.insert(0, ['User Id', 'Никнейм', 'Юзернейм', 'Рефералы' 'Рефералы второй ступени', 'Заработок (Баланс)', 'Купил звезд'])
    table = get_table(table_users, 'refs_data')
    await clb.message.answer_document(FSInputFile(path=table))
    try:
        os.remove(table)
    except Exception:
        ...


async def get_app_uid(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        uid_key = int(text)
    except Exception:
        await msg.delete()
        await msg.answer('Номер заказа должен быть числом, пожалуйста попробуйте еще раз')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    application = await session.get_application(uid_key)
    if not application:
        await msg.answer('Заказа с таким номером не найдено')
        return
    dialog_manager.dialog_data['uid_key'] = application.uid_key
    await dialog_manager.switch_to(adminSG.application_menu)


async def application_menu_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    uid_key = dialog_manager.dialog_data.get('uid_key')
    application = await session.get_application(uid_key)
    user = await session.get_user(application.user_id)
    statuses = {
        0: 'Не оплачен',
        1: 'В процессе выполнения',
        2: 'Оплачен',
        3: 'Ошибка выполнения'
    }
    payments = {
        None: 'Не оплачен',
        'sbp': 'СБП (Wata)',
        'card': 'Карта (Wata)',
        'crypto': 'Крипта (Oxa pay)',
        'crypto_bot': 'Криптобот'
    }
    text = (f'<b>Номер заказа</b>: {application.uid_key}\n<b>Создал</b>: {application.user_id} (@{user.username})'
            f'\n<b>Получатель</b>: @{application.receiver}\n<b>Сумма</b>: {application.amount} звезд\n'
            f'<b>Стоимость</b>: {float(application.rub)}₽ ({application.usdt}$)\n<b>Статус заказа</b>: {statuses[application.status]}'
            f'\n<b>Статус оплаты</b>: {payments[application.payment]}'
            f'\n<b>Дата создания</b>: {application.create.strftime("%Y-%m-%d %H:%M:%S")}')
    return {'text': text}


async def charge_menu_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    prices = await session.get_prices()
    return {'charge': prices.charge}


async def get_charge(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        charge = int(text)
    except Exception:
        await msg.answer('Введите пожалуйста число (от 0 до 100')
        return
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.set_charge(charge)
    await dialog_manager.switch_to(adminSG.charge_menu)


async def deeplink_menu_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    links = await session.get_deeplinks()
    text = ''
    for link in links:
        text += f'https://t.me/TrustStarsBot?start={link.link}: {link.entry}\n'  # Получить ссылку на бота и поменять
    return {'links': text}


async def add_deeplink(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.add_deeplink(get_random_id())
    await dialog_manager.switch_to(adminSG.deeplink_menu)


async def del_deeplink(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.del_deeplink(item_id)
    await clb.answer('Ссылка была успешно удаленна')
    await dialog_manager.switch_to(adminSG.deeplink_menu)


async def del_deeplink_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    links = await session.get_deeplinks()
    buttons = []
    for link in links:
        buttons.append((f'{link.link}: {link.entry}', link.link))
    return {'items': buttons}


async def promo_menu_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    promos = await session.get_promos()
    text = ''
    for promo in promos:
        text += f'{promo.promo}: {promo.entry}/{promo.limit}, {promo.percent}%\n'  # Получить ссылку на бота и поменять
    return {'promos': text}


async def del_promo_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    promos = await session.get_promos()
    buttons = []
    for promo in promos:
        buttons.append((f'{promo.promo}: {promo.entry}/{promo.limit}', promo.id))
    return {'items': buttons}


async def del_promo(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.del_promo(int(item_id))
    await clb.answer('Промокод успешно удален')
    await dialog_manager.switch_to(adminSG.promos_menu)


async def get_promo(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    dialog_manager.dialog_data['promo'] = text
    await dialog_manager.switch_to(adminSG.get_limit)


async def get_limit(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        limit = int(text)
    except Exception:
        await msg.answer('Лимит вводов промокода должен быть числом')
        return
    dialog_manager.dialog_data['limit'] = limit
    await dialog_manager.switch_to(adminSG.get_percent)


async def get_percent(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        percent = int(text)
    except Exception:
        await msg.answer('Процент скидки промокода должен быть целым числом (от 0 до 100)')
        return
    promo = dialog_manager.dialog_data.get('promo')
    limit = dialog_manager.dialog_data.get('limit')
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.add_promo(
        promo=promo,
        limit=limit,
        percent=percent
    )
    await msg.answer('Промокод был успешно добавлен')
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(adminSG.promos_menu)


async def del_admin(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    await session.del_admin(int(item_id))
    await clb.answer('Админ был успешно удален')
    await dialog_manager.switch_to(adminSG.admin_menu)


async def admin_del_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admins = await session.get_admins()
    buttons = []
    for admin in admins:
        buttons.append((admin.name, admin.user_id))
    return {'items': buttons}


async def refresh_url(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    id: str = dialog_manager.dialog_data.get('link_id')
    dialog_manager.dialog_data.clear()
    await session.del_link(id)
    await dialog_manager.switch_to(adminSG.admin_add)


async def admin_add_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    id = get_random_id()
    dialog_manager.dialog_data['link_id'] = id
    await session.add_link(id)
    return {'id': id}


async def admin_menu_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    admins = await session.get_admins()
    text = ''
    for admin in admins:
        text += f'{admin.name}\n'
    return {'admins': text}


async def get_mail(msg: Message, widget: MessageInput, dialog_manager: DialogManager):
    if msg.text:
        dialog_manager.dialog_data['text'] = msg.text
    elif msg.photo:
        dialog_manager.dialog_data['photo'] = msg.photo[0].file_id
        dialog_manager.dialog_data['caption'] = msg.caption
    elif msg.video:
        dialog_manager.dialog_data['video'] = msg.video.file_id
        dialog_manager.dialog_data['caption'] = msg.caption
    else:
        await msg.answer('Что-то пошло не так, пожалуйста попробуйте снова')
    await dialog_manager.switch_to(adminSG.get_time)


async def get_time(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        time = datetime.datetime.strptime(text, '%H:%M %d.%m')
    except Exception as err:
        print(err)
        await msg.answer('Вы ввели данные не в том формате, пожалуйста попробуйте снова')
        return
    dialog_manager.dialog_data['time'] = text
    await dialog_manager.switch_to(adminSG.get_keyboard)


async def get_mail_keyboard(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    try:
        buttons = text.split('\n')
        keyboard: list[tuple] = [(i.split('-')[0], i.split('-')[1]) for i in buttons]
    except Exception as err:
        print(err)
        await msg.answer('Вы ввели данные не в том формате, пожалуйста попробуйте снова')
        return
    dialog_manager.dialog_data['keyboard'] = keyboard
    await dialog_manager.switch_to(adminSG.confirm_mail)


async def cancel_malling(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(adminSG.start)


async def start_malling(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    bot: Bot = dialog_manager.middleware_data.get('bot')
    scheduler: AsyncIOScheduler = dialog_manager.middleware_data.get('scheduler')
    time = dialog_manager.dialog_data.get('time')
    keyboard = dialog_manager.dialog_data.get('keyboard')
    if keyboard:
        keyboard = [InlineKeyboardButton(text=i[0], url=i[1]) for i in keyboard]
    users = await session.get_users()
    if not time:
        if dialog_manager.dialog_data.get('text'):
            text: str = dialog_manager.dialog_data.get('text')
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.user_id,
                        text=text.format(name=user.name),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None
                    )
                    if user.active == 0:
                        await session.set_active(user.user_id, 1)
                except Exception as err:
                    print(err)
                    await session.set_active(user.user_id, 0)
        elif dialog_manager.dialog_data.get('caption'):
            caption: str = dialog_manager.dialog_data.get('caption')
            if dialog_manager.dialog_data.get('photo'):
                for user in users:
                    try:
                        await bot.send_photo(
                            chat_id=user.user_id,
                            photo=dialog_manager.dialog_data.get('photo'),
                            caption=caption.format(name=user.name),
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None
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
                            video=dialog_manager.dialog_data.get('video'),
                            caption=caption.format(name=user.name),
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None
                        )
                        if user.active == 0:
                            await session.set_active(user.user_id, 1)
                    except Exception as err:
                        print(err)
                        await session.set_active(user.user_id, 0)
    else:
        date = datetime.datetime.strptime(time, '%H:%M %d.%m')
        scheduler.add_job(
            func=send_messages,
            args=[bot, session, InlineKeyboardMarkup(inline_keyboard=[keyboard]) if keyboard else None],
            kwargs={
                'text': dialog_manager.dialog_data.get('text'),
                'caption': dialog_manager.dialog_data.get('caption'),
                'photo': dialog_manager.dialog_data.get('photo'),
                'video': dialog_manager.dialog_data.get('video')
            },
            next_run_time=date
        )
    dialog_manager.dialog_data.clear()
    await dialog_manager.switch_to(adminSG.start)

