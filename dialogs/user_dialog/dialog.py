from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.user_dialog import getters

from states.state_groups import startSG, adminSG, GiftsSG

user_dialog = Dialog(
    Window(
        DynamicMedia('media'),
        Format('<b><tg-emoji emoji-id="5897920748101571572">🌟</tg-emoji> Добро пожаловать!</b>\n\n'
               'Здесь можно приобрести Премиум и Telegram звезды без верификации KYC и дешевле чем в приложении.'
               '\n\n<tg-emoji emoji-id="4985783828892091847">☝️</tg-emoji>Через наш сервис уже куплено:\n<b>{stars} звезд (~{usdt} $)</b>'),
        Button(Const('Купить звезды'), id='stars_pay_choose', on_click=getters.buy_choose, style=Style(emoji_id="5463289097336405244")),
        Row(
            Button(Const('TON'), id='ton_pay_choose', on_click=getters.buy_choose, style=Style(emoji_id="")),
            Button(Const('Премиум'), id='premium_pay_choose', on_click=getters.buy_choose, style=Style(emoji_id="6190484269513586305"))
        ),
        Column(
            Start(Const('Удаленные подарки'), id='gift_dialog', state=GiftsSG.choose_gift, style=Style(emoji_id="5203996991054432397")),
            SwitchTo(Const('Партнерская программа'), id='ref_menu_switcher', state=startSG.ref_menu, style=Style(emoji_id="5377548235709619284")),
            SwitchTo(Const('Профиль'), id='profile_switcher', state=startSG.profile, style=Style(emoji_id="5467730450002746997")),
        ),
        Row(
            Url(Const('Поддержка'), id='support_url', url=Const('https://t.me/TrustStarsHelp'), style=Style(emoji_id="5411563083908797492")),
            Url(Const('Наш VPN'), id='vpn_url', url=Const('https://t.me/SolaVpBot'), style=Style(emoji_id="5447410659077661506")),
        ),
        Column(
            Url(Const('Создать своего бота'), id='partner_url', url=Const('https://t.me/TrustPartnersBot'), style=Style(emoji_id="5309832892262654231")),
            Start(Const('Админ панель'), id='admin', state=adminSG.start, when='admin'),
        ),
        getter=getters.start_getter,
        state=startSG.start
    ),
    Window(
        Const('Выберите способ получения TON'),
        Column(
            Button(Const('На кошелек'), id='address_ton_choose', on_click=getters.choose_ton_method),
            Button(Const('Юзернейм'), id='username_ton_choose', on_click=getters.choose_ton_method)
        ),
        SwitchTo(Const('Назад'), id='back', state=startSG.start, style=Style(emoji_id="5388584622328131561")),
        state=startSG.choose_ton_method
    ),
    Window(
        Const('Укажите адрес кошелька, на который вы хотели бы приобрести TON'),
        TextInput(
            id='get_ton_address',
            on_success=getters.get_ton_address
        ),
        SwitchTo(Const('Назад'), id='back_choose_ton_method', state=startSG.choose_ton_method, style=Style(emoji_id="5388584622328131561")),
        state=startSG.get_ton_address
    ),
    Window(
        Format('{text}'),
        TextInput(
            id='get_currency_amount',
            on_success=getters.get_currency_amount
        ),
        Group(
            Select(
                Format('{item[0]}'),
                id='pay_menu_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.pay_menu_selector
            ),
            width=4
        ),
        Column(
            SwitchTo(Format('Получатель: {username}'), id='get_username_switcher', state=startSG.get_username,
                     style=Style(emoji_id="5472239203590888751"), when='not_address')
        ),
        SwitchTo(Const('Назад'), id='back', state=startSG.start, style=Style(emoji_id="5388584622328131561")),
        getter=getters.pay_menu_getter,
        state=startSG.pay_menu
    ),
    Window(
        Const('<tg-emoji emoji-id="5467730450002746997">🔍</tg-emoji><b>Укажите имя пользователя</b>\n<em>Н-р: @username</em>'),
        TextInput(
            id='get_username',
            on_success=getters.get_username
        ),
        SwitchTo(Const('Назад'), id='back_pay_menu', state=startSG.pay_menu, style=Style(emoji_id="5388584622328131561")),
        state=startSG.get_username
    ),
    Window(
        Const('Введите промокод или нажмите "➡️Пропустить", чтобы продолжить покупку звезд'),
        TextInput(
            id='get_promo',
            on_success=getters.get_promo
        ),
        Column(
            Button(Const('➡️Пропустить'), id='skip_promo', on_click=getters.skip_promo),
        ),
        SwitchTo(Const('Назад'), id='back_pay_menu', state=startSG.pay_menu, style=Style(emoji_id="5388584622328131561")),
        state=startSG.get_promo
    ),
    Window(
        Format('{text}'),
        Column(
            Url(Const('Поделиться'), id='share_url', url=Format('{url}'), style=Style(emoji_id="5372849966689566579")),
            #Button(Const('💰Вывести'), id='get_derive_amount_switcher', on_click=getters.get_derive_amount_switcher),
            Button(Const('Купить звезды'), id='stars_pay_choose', on_click=getters.buy_choose, style=Style(emoji_id="5463289097336405244")),
        ),
        SwitchTo(Const('Назад'), id='back', state=startSG.start, style=Style(emoji_id="5388584622328131561")),
        getter=getters.ref_menu_getter,
        state=startSG.ref_menu
    ),
    Window(
        Const('Введите сумму для вывода <em>(в ⭐)</em>'),
        TextInput(
            id='get_derive_amount',
            on_success=getters.get_derive_amount
        ),
        SwitchTo(Const('Назад'), id='back_ref_menu', state=startSG.ref_menu, style=Style(emoji_id="5388584622328131561")),
        state=startSG.get_derive_amount
    ),
    Window(
        Format('{text}'),
        Column(
    SwitchTo(Const('Партнерская программа'), id='ref_menu_switcher', state=startSG.ref_menu, style=Style(emoji_id="5377548235709619284")),
            Url(Const('Правила'), id='rules_url', url=Const('https://telegra.ph/Politika-konfidencialnosti-12-29-42'), style=Style(emoji_id="5197269100878907942")),
        ),
        SwitchTo(Const('Назад'), id='back', state=startSG.start, style=Style(emoji_id="5388584622328131561")),
        getter=getters.profile_getter,
        state=startSG.profile
    ),
)