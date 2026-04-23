from aiogram import Bot

from database.action_data_class import DataInteraction


channel_id = -1003970166132


async def send_application_log(app_id: int, session: DataInteraction, bot: Bot):
    application = await session.get_application(app_id)
    user = await session.get_user(application.user_id)
    statuses = {
        0: 'Не оплачен',
        1: 'В процессе выполнения',
        2: 'Оплачен',
        3: 'Ошибка выполнения'
    }
    payments = {
        None: 'Не оплачен',
        'sbp': 'СБП',
        'card': 'Карта',
        'crypto': 'Крипта (Oxa pay)',
        'crypto_bot': 'Криптобот',
        'referral': 'С баланса'
    }
    types = {
        'stars': 'Покупка звезд',
        None: 'Покупка звезд',
        'premium': 'Покупка премиум',
        'ton': 'Покупка TON',
        'deleted_gift': 'Удаленный подарок'
    }
    amount_text = {
        'stars': '⭐️',
        None: '⭐️',
        'premium': 'месяцев',
        'ton': 'TON',
        'deleted_gift': 'ID подарка'
    }
    transaction = None
    if application.tx_hash:
        transaction = f'https://tonviewer.com/transaction/{application.tx_hash}'

    text = (f'<b>Тип заказа</b>: {types.get(application.type)}\n'
            f'<b>Номер заказа</b>: {application.uid_key}\n<b>Создал</b>: {application.user_id} (@{user.username})'
            f'\n<b>Получатель</b>: {application.receiver}\n<b>Сумма</b>: {application.amount} {amount_text.get(application.type)}\n'
            f'<b>Стоимость</b>: {float(application.rub)}₽ ({application.usdt}$)\n<b>Статус заказа</b>: {statuses[application.status]}'
            f'\n<b>Метод оплаты</b>: {payments[application.payment]}{f"\n<b>Транзакция</b>: {transaction}" if transaction else ""}'
            f'\n<b>Дата создания</b>: {application.create.strftime("%Y-%m-%d %H:%M:%S")}')

    try:
        await bot.send_message(
            chat_id=channel_id,
            text=text
        )
    except Exception:
        ...