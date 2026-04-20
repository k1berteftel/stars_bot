from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url, Cancel, ListGroup
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from custom_widgets.style import DynamicStyle
from dialogs.gifts_dialog import getters

from states.state_groups import startSG, GiftsSG


gift_dialog = Dialog(
    Window(
        Const('<b>Покупка подарка</b>\n\n<em>Выберите подарок из списка ниже</em>'),
        Group(
            Select(
                Format('{item[0]}'),
                id='choose_gift_builder',
                item_id_getter=lambda x: x[1],
                style=DynamicStyle(emoji_id=Format('{item[2]}')),
                items='items',
                on_click=getters.gift_selector
            ),
            width=1
        ),
        Cancel(Const('Назад'), id='close_dialog', style=Style(emoji_id="5388584622328131561")),
        getter=getters.choose_gift_getter,
        state=GiftsSG.choose_gift
    ),
    Window(
        Format('<b>Подарок:</b> {emoji}<u>{gift}</u>\n<b>Стоимость:</b> {cost}₽'
               '\n<em>Кому вы покупаете подарок?</em>'),
        Column(
            Button(Const('Себе'), id='payment_switcher', on_click=getters.payment_switcher),
            SwitchTo(Format('Другому'), id='get_receiver_switcher', state=GiftsSG.get_receiver, style=Style(emoji_id="5472239203590888751")),
        ),
        SwitchTo(Const('Назад'), id='back_choose_gift', state=GiftsSG.choose_gift, style=Style(emoji_id="5388584622328131561")),
        getter=getters.choose_receiver_getter,
        state=GiftsSG.choose_receiver
    ),
    Window(
        Const('<tg-emoji emoji-id="5467730450002746997">🔍</tg-emoji><b>Укажите имя пользователя, которому вы хотели бы купить подарок</b>\n<em>Н-р: @username</em>'),
        TextInput(
            id='get_receiver',
            on_success=getters.get_receiver
        ),
        SwitchTo(Const('Назад'), id='back_choose_receiver', state=GiftsSG.choose_receiver, style=Style(emoji_id="5388584622328131561")),
        state=GiftsSG.get_receiver
    )
)