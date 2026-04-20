from aiogram.types import ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo, Column, Row, Button, Group, Select, Start, Url, Cancel
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia

from dialogs.admin_dialog import getters
from states.state_groups import adminSG


admin_dialog = Dialog(
    Window(
        Const('Админ панель'),
        Column(
            Button(Const('📊 Получить статистику'), id='get_static', on_click=getters.get_static),
            SwitchTo(Const('🛫Сделать рассылку'), id='mailing_menu_switcher', state=adminSG.get_mail),
            SwitchTo(Const('Блокировка пользователей'), id='get_block_user', state=adminSG.get_block_user),
            SwitchTo(Const('Найти заказ'), id='get_app_uid_switcher', state=adminSG.get_app_uid),
            SwitchTo(Const('🔗 Управление диплинками'), id='deeplinks_menu_switcher', state=adminSG.deeplinks_menu),
            SwitchTo(Const('Управление промокодами'), id='promos_menu_switcher', state=adminSG.promos_menu),
            SwitchTo(Const('👥 Управление админами'), id='admin_menu_switcher', state=adminSG.admin_menu),
            SwitchTo(Const('Управление наценкой'), id='charge_menu_switcher', state=adminSG.charge_menu),
            #SwitchTo(Const('Управление ОП'), id='op_menu_switcher', state=adminSG.op_menu),
            Button(Const('📋Выгрузка базы пользователей'), id='get_users_txt', on_click=getters.get_users_txt),
            Button(Const('Выгрузка реф. участников'), id='get_ref_table', on_click=getters.get_ref_table),
            Button(Const('Проверить активность'), id='check_activity', on_click=getters.check_activity),
            Button(Const('Распределить средства'), id='send_distribute_action', on_click=getters.send_distribute),
        ),
        Cancel(Const('Назад'), id='close_admin'),
        state=adminSG.start
    ),
    Window(
        Const('Введите user_id или @username пользователя, которого надо заблокировать'),
        TextInput(
            id='get_block_user',
            on_success=getters.get_block_user
        ),
        SwitchTo(Const('🔙 Назад'), id='back', state=adminSG.start),
        state=adminSG.get_block_user
    ),
    Window(
        Const('Введите номер заказа'),
        TextInput(
            id='get_app_uid',
            on_success=getters.get_app_uid
        ),
        SwitchTo(Const('🔙 Назад'), id='back', state=adminSG.start),
        state=adminSG.get_app_uid
    ),
    Window(
        Format('<b>Данные по заказу</b>\n\n{text}'),
        SwitchTo(Const('🔙 Назад'), id='back_get_app_uid', state=adminSG.get_app_uid),
        getter=getters.application_menu_getter,
        state=adminSG.application_menu
    ),
    Window(
        Format('<b>Действующие наценки</b>\n - Для звезд: {stars_charge}%'
               '\n - Для премиума: {premium_charge}%\n - Для TON: {ton_charge}\n\n'
               '<em>Чтобы поменять наценку выберите курс для смены</em>'),
        Column(
            Button(Const('Звезды'), id='stars_choose', on_click=getters.charge_choose_switcher),
            Button(Const('Премиум'), id='premium_choose', on_click=getters.charge_choose_switcher),
            Button(Const('TON'), id='ton_choose', on_click=getters.charge_choose_switcher),
        ),
        SwitchTo(Const('🔙 Назад'), id='back', state=adminSG.start),
        getter=getters.charge_menu_getter,
        state=adminSG.charge_menu
    ),
    Window(
        Const('Введите новое значение для наценки в %'),
        TextInput(
            id='get_charge',
            on_success=getters.get_charge
        ),
        SwitchTo(Const('🔙 Назад'), id='back_charge_menu', state=adminSG.charge_menu),
        state=adminSG.get_charge
    ),
    Window(
        Format('<b>Меню управления промокодами</b>\n\n'
               '🎯 Имеющиеся Промокоды:\n{promos}'),
        Column(
            SwitchTo(Const('➕ Добавить Промокод'), id='add_promo_switcher', state=adminSG.get_promo),
            SwitchTo(Const('❌ Удалить промокод'), id='del_deeplinks_switcher', state=adminSG.del_promo),
        ),
        SwitchTo(Const('🔙 Назад'), id='back', state=adminSG.start),
        getter=getters.promo_menu_getter,
        state=adminSG.promos_menu
    ),
    Window(
        Const('Введите новый промокод'),
        TextInput(
            id='get_promo',
            on_success=getters.get_promo
        ),
        SwitchTo(Const('🔙 Назад'), id='promos_back', state=adminSG.promos_menu),
        state=adminSG.get_promo
    ),
    Window(
        Const('Введите лимит вводов для данного промокода'),
        TextInput(
            id='get_limit',
            on_success=getters.get_limit
        ),
        SwitchTo(Const('🔙 Назад'), id='get_promo_back', state=adminSG.get_promo),
        state=adminSG.get_limit
    ),
    Window(
        Const('Введите процент скидки для данного промокода\n<em>Пример ввода: 5, 7, 15</em>'),
        TextInput(
            id='get_percent',
            on_success=getters.get_percent
        ),
        SwitchTo(Const('🔙 Назад'), id='get_limit_back', state=adminSG.get_limit),
        state=adminSG.get_percent
    ),
    Window(
        Const('❌ Выберите промокод для удаления'),
        Group(
            Select(
                Format('🔗 {item[0]}'),
                id='promos_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.del_promo
            ),
            width=1
        ),
        SwitchTo(Const('🔙 Назад'), id='promos_back', state=adminSG.promos_menu),
        getter=getters.del_promo_getter,
        state=adminSG.del_promo
    ),
    Window(
        Format('🔗 *Меню управления диплинками*'),
        Column(
            Select(
                Format('{item[0]}'),
                id='deeplinks_menu_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.deeplink_choose
            ),
        ),
        Row(
            Button(Const('◀️'), id='back_deeplinks_pager', on_click=getters.deeplinks_pager, when='not_first'),
            Button(Format('{page}'), id='deeplinks_pager', when='deeplinks'),
            Button(Const('▶️'), id='next_deeplinks_pager', on_click=getters.deeplinks_pager, when='not_last')
        ),
        SwitchTo(Const('➕ Добавить диплинк'), id='add_deeplink', state=adminSG.get_deeplink_name),
        SwitchTo(Const('🔙 Назад'), id='back', state=adminSG.start),
        getter=getters.deeplinks_menu_getter,
        state=adminSG.deeplinks_menu
    ),
    Window(
        Const('Введите название для данной ссылки'),
        TextInput(
            id='get_link_name',
            on_success=getters.get_deeplink_name
        ),
        SwitchTo(Const('🔙 Назад'), id='back_deeplinks_menu', state=adminSG.deeplink_menu),
        state=adminSG.get_deeplink_name
    ),
    Window(
        Format('{text}'),
        Column(
            Button(Const('🗑Удалить диплинк'), id='del_deeplink', on_click=getters.del_deeplink),
        ),
        SwitchTo(Const('🔙 Назад'), id='back_deeplinks_menu', state=adminSG.deeplinks_menu),
        getter=getters.deeplink_menu_getter,
        state=adminSG.deeplink_menu
    ),
    Window(
        Format('👥 *Меню управления администраторами*\n\n {admins}'),
        Column(
            SwitchTo(Const('➕ Добавить админа'), id='add_admin_switcher', state=adminSG.admin_add),
            SwitchTo(Const('❌ Удалить админа'), id='del_admin_switcher', state=adminSG.admin_del)
        ),
        SwitchTo(Const('🔙 Назад'), id='back', state=adminSG.start),
        getter=getters.admin_menu_getter,
        state=adminSG.admin_menu
    ),
    Window(
        Const('👤 Выберите пользователя, которого хотите сделать админом\n'
              '⚠️ Ссылка одноразовая и предназначена для добавления только одного админа'),
        Column(
            Url(Const('🔗 Добавить админа (ссылка)'), id='add_admin',
                url=Format('http://t.me/share/url?url=https://t.me/TrustStarsBot?start={id}')),  # поменять ссылку
            Button(Const('🔄 Создать новую ссылку'), id='new_link_create', on_click=getters.refresh_url),
            SwitchTo(Const('🔙 Назад'), id='back_admin_menu', state=adminSG.admin_menu)
        ),
        getter=getters.admin_add_getter,
        state=adminSG.admin_add
    ),
    Window(
        Const('❌ Выберите админа для удаления'),
        Group(
            Select(
                Format('👤 {item[0]}'),
                id='admin_del_builder',
                item_id_getter=lambda x: x[1],
                items='items',
                on_click=getters.del_admin
            ),
            width=1
        ),
        SwitchTo(Const('🔙 Назад'), id='back_admin_menu', state=adminSG.admin_menu),
        getter=getters.admin_del_getter,
        state=adminSG.admin_del
    ),
    Window(
        Const('Введите сообщение которое вы хотели бы разослать\n\n<b>Предлагаемый макросы</b>:'
              '\n{name} - <em>полное имя пользователя</em>'),
        MessageInput(
            content_types=ContentType.ANY,
            func=getters.get_mail
        ),
        SwitchTo(Const('Назад'), id='back', state=adminSG.start),
        state=adminSG.get_mail
    ),
    Window(
        Const('Введите дату и время в которое сообщение должно отправиться всем юзерам в формате '
              'час:минута:день:месяц\n Например: 18:00 10.02 (18:00 10-ое февраля)'),
        TextInput(
            id='get_time',
            on_success=getters.get_time
        ),
        SwitchTo(Const('Продолжить без отложки'), id='get_keyboard_switcher', state=adminSG.get_keyboard),
        SwitchTo(Const('Назад'), id='back_get_mail', state=adminSG.get_mail),
        state=adminSG.get_time
    ),
    Window(
        Const('Введите кнопки которые будут крепиться к рассылаемому сообщению\n'
              'Введите кнопки в формате:\n кнопка1 - ссылка1\nкнопка2 - ссылка2'),
        TextInput(
            id='get_mail_keyboard',
            on_success=getters.get_mail_keyboard
        ),
        SwitchTo(Const('Продолжить без кнопок'), id='confirm_mail_switcher', state=adminSG.confirm_mail),
        SwitchTo(Const('Назад'), id='back_get_time', state=adminSG.get_time),
        state=adminSG.get_keyboard
    ),
    Window(
        Const('Вы подтверждаете рассылку сообщения'),
        Row(
            Button(Const('Да'), id='start_malling', on_click=getters.start_malling),
            Button(Const('Нет'), id='cancel_malling', on_click=getters.cancel_malling),
        ),
        SwitchTo(Const('Назад'), id='back_get_keyboard', state=adminSG.get_keyboard),
        state=adminSG.confirm_mail
    ),
)