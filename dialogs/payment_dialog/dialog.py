from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url, Cancel
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.payment_dialog import getters

from states.state_groups import startSG, PaymentSG


payment_dialog = Dialog(
    Window(
        Const('<tg-emoji emoji-id="5380025207773741278">🏦</tg-emoji><b>Выберите способ оплаты</b>\n'),
        Format('{text}'),
        Column(
            Button(Const('СБП 1'), id='sbp1_payment_choose', on_click=getters.payment_choose, style=Style(emoji_id="5265074015868822600")),
            Button(Const('СБП 2'), id='sbp2_payment_choose', on_click=getters.payment_choose, style=Style(emoji_id="5265074015868822600")),
            Button(Const('Карта'), id='card_payment_choose', on_click=getters.payment_choose, style=Style(emoji_id="5801180866071760635")),
            Button(Const('CryptoBot'), id='cb_payment_choose', on_click=getters.payment_choose, style=Style(emoji_id="5361836987642815474")),
            #Button(Const('💲Крипта'), id='crypto_payment_choose', on_click=getters.payment_choose),
            Button(Const('С баланса'), id='ref_balance_buy', on_click=getters.from_balance, style=Style(emoji_id="5264713049637409446")),
        ),
        Cancel(Const('Назад'), id='close_dialog', style=Style(emoji_id="5388584622328131561")),
        getter=getters.menu_getter,
        state=PaymentSG.menu
    ),
    Window(
        Const('<b><tg-emoji emoji-id="5990109364956958958">⌛️</tg-emoji>Ожидание оплаты</b>'),
        Format('{text}'),
        Column(
            Url(Const('Оплатить'), id='url', url=Format('{url}'), style=Style(emoji_id="5256057883082107781")),
        ),
        Button(Const('Назад'), id='back', on_click=getters.close_payment, style=Style(emoji_id="5388584622328131561")),
        getter=getters.process_payment_getter,
        state=PaymentSG.process_payment
    ),
)