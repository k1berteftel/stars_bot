import asyncio

from aiogram.types import CallbackQuery, User, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import ManagedTextInput
from nats.js import JetStreamContext

from utils.payments.create import (get_oxa_payment_data, get_crypto_payment_data,
                                           get_freekassa_sbp, get_freekassa_card, _get_usdt_rub)
from utils.payments.process import wait_for_payment
from utils.transactions import get_stars_price
from services.publisher import send_publisher_data
from database.action_data_class import DataInteraction
from config_data.config import load_config, Config
from states.state_groups import GiftsSG, PaymentSG




DELETED_GIFTS = [
    {"name": "Новогодняя елочка", "gift_id": "5922558454332916696", "emoji_id": "5346117566253276549", "emoji": "🎄", "price": 100},
    {"name": "Новогодний мишка", "gift_id": "5956217000635139069", "emoji_id": "5379850046122527013", "emoji": "🎁", "price": 100},
    {"name": "Мишка влюбленный", "gift_id": "5800655655995968830", "emoji_id": "5224509179334529299", "emoji": "🎁", "price": 100},
    {"name": "Сердце", "gift_id": "5801108895304779062", "emoji_id": "5224648868850863664", "emoji": "🎁", "price": 100},
    {"name": "Мишка с цветами", "gift_id": "5866352046986232958", "emoji_id": "5289670279960762852", "emoji": "🧸", "price": 100},
    {"name": "Патрик-мишка", "gift_id": "5893356958802511476", "emoji_id": "5317000922096769303", "emoji": "🎁", "price": 100},
]


def _get_gift(gift_id: str) -> dict | None:
    for gift in DELETED_GIFTS:
        if gift.get('gift_id') == gift_id:
            return gift


async def choose_gift_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    buttons = []
    for gift in DELETED_GIFTS:
        buttons.append((
            gift.get("name"),
            gift.get("gift_id"),
            gift.get("emoji_id")
        ))

    return {
        'items': buttons
    }


async def gift_selector(clb: CallbackQuery, widget: Select, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data['gift_id'] = item_id
    await dialog_manager.switch_to(GiftsSG.choose_receiver)


async def choose_receiver_getter(dialog_manager: DialogManager, **kwargs):
    session: DataInteraction = dialog_manager.middleware_data.get('session')
    gift_id = dialog_manager.dialog_data.get('gift_id')
    gift = _get_gift(gift_id)
    return {
        'emoji': f'<tg-emoji emoji-id="{gift.get("emoji_id")}">{gift.get("emoji")}</tg-emoji>',
        'gift': gift.get('name'),
        'cost': gift.get('price')
    }


async def payment_switcher(clb: CallbackQuery, widget: Button, dialog_manager: DialogManager):
    gift_id = dialog_manager.dialog_data.get('gift_id')
    gift = _get_gift(gift_id)
    data = {
        'rate': 'deleted_gift',
        'username': '@' + clb.from_user.username,
        'gift_id': gift_id,
        'gift': gift.get('name'),
        'emoji_id': gift.get('emoji_id'),
        'currency': gift.get('price')
    }
    await dialog_manager.start(PaymentSG.menu, data=data)


async def get_receiver(msg: Message, widget: ManagedTextInput, dialog_manager: DialogManager, text: str):
    import re
    username = text.strip()
    match = re.match(r"^@?([a-zA-Z0-9_]{5,32})$", username)
    if not match:
        await msg.delete()
        await msg.answer('<tg-emoji emoji-id="5467928559664242360">❗️</tg-emoji>Юзернейм должен быть в формате "@username", пожалуйста попробуйте снова')
        return
    gift_id = dialog_manager.dialog_data.get('gift_id')
    gift = _get_gift(gift_id)
    data = {
        'rate': 'deleted_gift',
        'username': username,
        'gift_id': gift_id,
        'gift': gift.get('name'),
        'emoji_id': gift.get('emoji_id'),
        'currency': gift.get('price')
    }
    await dialog_manager.start(PaymentSG.menu, data=data)
