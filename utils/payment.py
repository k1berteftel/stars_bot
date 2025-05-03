import uuid
import re
import lxml

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from yookassa import Configuration, Payment
from yookassa.payment import PaymentResponse
from aiocryptopay import AioCryptoPay, Networks

from config_data.config import Config, load_config


config: Config = load_config()

Configuration.account_id = config.yookassa.account_id
Configuration.secret_key = config.yookassa.secret_key

crypto_bot = AioCryptoPay(token=config.crypto_bot.token, network=Networks.MAIN_NET)


async def get_yookassa_payment_data(price: int) -> dict:
    payment = await Payment.create({
        "amount": {
            "value": str(float(price)),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/AidaLook_bot"
        },
        "receipt": {
            "customer": {
                "email": "kkulis985@gmail.com"
            },
            'items': [
                {
                    'description': "Покупка звезд",
                    "amount": {
                        "value": str(float(price)),
                        "currency": "RUB"
                    },
                    'vat_code': 1,
                    'quantity': 1
                }
            ]
        },
        "capture": True,
        "description": "Покупка звезд"
    }, uuid.uuid4())
    url = payment.confirmation.confirmation_url
    return {
        'url': url,
        'id': payment.id
    }


async def get_crypto_payment_data(price: int):
    course = await _get_usdt_rub()
    price = round(price / course, 2)
    invoice = await crypto_bot.create_invoice(asset='USDT', amount=price)
    return {
        'url': invoice.mini_app_invoice_url,
        'id': invoice.invoice_id
    }


async def check_yookassa_payment(payment_id: int):
    payment: PaymentResponse = await Payment.find_one(payment_id)
    if payment.paid:
        return True
    return False


async def check_crypto_payment(invoice_id: int):
    invoice = await crypto_bot.get_invoices(invoice_ids=invoice_id)
    if invoice.status == 'paid':
        return True
    return False


async def _get_usdt_rub() -> float:
    async with ClientSession() as session:
        async with session.get('https://www.rbc.ru/crypto/currency/usdtrub') as res:
            resp = await res.text()
            soup = BeautifulSoup(resp, 'lxml')
            price = soup.find('div', class_='chart__subtitle').text.strip()
            value = re.search(r'\d+,\d+', price)
            return float(price[value.start():value.end():].replace(',', '.'))
