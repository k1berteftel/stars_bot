from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.user_dialog import getters

from states.state_groups import startSG, adminSG

user_dialog = Dialog(
    Window(
        DynamicMedia('media'),
        Const('<b>✨ Добро пожаловать!</b>\n\n'
              'Здесь можно приобрести Telegram звезды без верификации KYC и дешевле чем в приложении.'),
        Column(
            SwitchTo(Const('⭐️Купить звезды'), id='get_stars_amount_switcher', state=startSG.get_stars_amount),
            SwitchTo(Const('🎁Подарок другу'), id='get_username_switcher', state=startSG.get_username),
            SwitchTo(Const('👤Партнерская программа'), id='ref_menu_switcher', state=startSG.ref_menu),
            SwitchTo(Const('📋Правила'), id='rules_menu_switcher', state=startSG.rules_menu),
            Url(Const('🌠Наш канал'), id='channel_url', url=Const('https://t.me/TrustStarsNews')),
            Url(Const('📩Поддержка'), id='support_url', url=Const('https://t.me/TrustStarsHelp')),
            Start(Const('Админ панель'), id='admin', state=adminSG.start, when='admin')
        ),
        getter=getters.start_getter,
        state=startSG.start
    ),
    Window(
        Format('{text}'),
        SwitchTo(Const('🔙Назад'), id='back', state=startSG.start),
        getter=getters.rules_menu_getter,
        state=startSG.rules_menu
    ),
    Window(
        Const('⭐️Отправьте количество звезд, которое вы хотели бы приобрести <em>(минимум 50)</em>'),
        TextInput(
            id='get_stars_amount',
            on_success=getters.get_stars_amount
        ),
        SwitchTo(Const('🔙Назад'), id='back', state=startSG.start),
        state=startSG.get_stars_amount
    ),
    Window(
        Const('Введите промокод или нажмите "➡️Пропустить", чтобы продолжить покупку звезд'),
        TextInput(
            id='get_promo',
            on_success=getters.get_promo
        ),
        SwitchTo(Const('➡️Пропустить'), id='miss_promo', state=startSG.payment_menu),
        SwitchTo(Const('🔙Назад'), id='back_get_stars_amount', state=startSG.get_stars_amount),
        state=startSG.get_promo
    ),
    Window(
        Format('<b>Номер заказа</b>: <code>{uid_key}</code>\n\n<b>Сумма к оплате</b>: <code>{rub}₽ ({usdt}$)</code>\n'
               '<b>Вы покупаете</b>: <code>{amount} звезд</code>\n<b>Получатель</b>: <code>{username}</code>\n'),
        Const('<em>❗️Счет будет действителен 30 минут</em>'),
        Column(
            Url(Const('💲Crypto Bot'), id='crypto_url', url=Format('{crypto_link}')),
            Url(Const('💵Крипта / USDT'), id='oxa_url', url=Format('{oxa_link}')),
            Url(Const('💶СБП'), id='sbp_url', url=Format('{sbp_link}')),
            Url(Const('💳Карта'), id='card_url', url=Format('{card_link}'))
        ),
        Button(Const('❌Закрыть меню'), id='close_payment', on_click=getters.close_payment),
        getter=getters.payment_menu_getter,
        state=startSG.payment_menu
    ),
    Window(
        Const('Отправьте юзернейм пользователя, на который нужно отправить звезды\n\n'
              '❗️<em>Проверьте, что аккаунт существует.</em>'),
        TextInput(
            id='get_username',
            on_success=getters.get_username
        ),
        SwitchTo(Const('🔙Назад'), id='back', state=startSG.start),
        state=startSG.get_username
    ),
    Window(
        Format('{text}'),
        Column(
            Url(Const('✈️Поделиться'), id='share_url', url=Format('{url}')),
            Button(Const('💰Вывести'), id='get_derive_amount_switcher', on_click=getters.get_derive_amount_switcher),
            Button(Const('⭐️Купить звезды'), id='get_ref_amount_switcher', on_click=getters.get_ref_amount_switcher),
        ),
        SwitchTo(Const('🔙Назад'), id='back', state=startSG.start),
        getter=getters.ref_menu_getter,
        state=startSG.ref_menu
    ),
    Window(
        Const('Введите сумму для вывода <em>(в рублях)</em>'),
        TextInput(
            id='get_derive_amount',
            on_success=getters.get_derive_amount
        ),
        SwitchTo(Const('🔙Назад'), id='back_ref_menu', state=startSG.ref_menu),
        state=startSG.get_derive_amount
    ),
    Window(
        Const('<b>Укажите свой номер карты для вывода средств</b>'),
        TextInput(
            id='get_card',
            on_success=getters.get_card
        ),
        SwitchTo(Const('🔙Назад'), id='back_ref_menu', state=startSG.ref_menu),
        state=startSG.get_card
    ),
)