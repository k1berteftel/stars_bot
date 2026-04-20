from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


async def get_sub_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Наш канал', url='https://t.me/TrustStarsNews', icon_custom_emoji_id="4985577743476327819")],
        ]
    )
    return keyboard