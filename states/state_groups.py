from aiogram.fsm.state import State, StatesGroup

# Обычная группа состояний


class startSG(StatesGroup):
    start = State()
    rules_menu = State()
    get_username = State()
    ton_receipt_menu = State()
    get_address = State()
    get_stars_amount = State()
    get_promo = State()
    get_premium_rate = State()
    get_ton_amount = State()
    payment_menu = State()
    ref_menu = State()
    get_derive_amount = State()
    get_card = State()


class adminSG(StatesGroup):
    start = State()
    get_mail = State()
    get_time = State()
    get_keyboard = State()
    confirm_mail = State()
    deeplink_menu = State()
    deeplink_del = State()
    admin_menu = State()
    admin_del = State()
    admin_add = State()
    promos_menu = State()
    del_promo = State()
    get_promo = State()
    get_limit = State()
    get_percent = State()
    charge_menu = State()
    get_charge = State()
    get_app_uid = State()
    application_menu = State()
