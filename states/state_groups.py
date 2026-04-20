from aiogram.fsm.state import State, StatesGroup

# Обычная группа состояний


class startSG(StatesGroup):
    start = State()

    rules_menu = State()

    pay_menu = State()
    get_username = State()
    get_promo = State()

    ref_menu = State()
    get_derive_amount = State()
    get_card = State()

    profile = State()


class GiftsSG(StatesGroup):
    choose_gift = State()
    choose_receiver = State()
    get_receiver = State()


class PaymentSG(StatesGroup):
    menu = State()
    process_payment = State()


class adminSG(StatesGroup):
    start = State()

    get_block_user = State()

    get_mail = State()
    get_time = State()
    get_keyboard = State()
    confirm_mail = State()

    deeplinks_menu = State()
    get_deeplink_name = State()
    deeplink_menu = State()

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

    application_menu = State()
    get_app_uid = State()
