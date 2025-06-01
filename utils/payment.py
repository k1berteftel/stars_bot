import asyncio
import json
import uuid
import re
import lxml
import hashlib
import hmac

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from aiocryptopay import AioCryptoPay, Networks

from utils.build_ids import get_random_id
from config_data.config import Config, load_config


config: Config = load_config()

secret_key = config.lava.secret_key
merchant_api_key = config.oxa.api_key
crypto_bot = AioCryptoPay(token=config.crypto_bot.token, network=Networks.MAIN_NET)


def _add_signature(data: dict) -> str:
    data = dict(sorted(data.items(), key=lambda x: x[0]))
    sign = hmac.new(bytes(secret_key, 'utf-8'), json.dumps(data).encode('utf-8'), hashlib.sha256).hexdigest()
    return sign


async def get_wata_card_data(user_id: int, price: int) -> dict | bool:
    headers = {
        'Authorization': f'Bearer {config.wata.card_key}',
        'Content-Type': 'application/json'
    }
    data = {
        "amount": float(price),
        "currency": "RUB",
        "orderId": str(user_id)
    }
    async with ClientSession() as session:
        async with session.post('https://api.wata.pro/api/h2h/links', json=data, headers=headers) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'id': data['id'],
        'url': data['url']
    }


async def get_wata_sbp_data(user_id: int, price: int) -> dict | bool:
    headers = {
        'Authorization': f'Bearer {config.wata.sbp_key}',
        'Content-Type': 'application/json'
    }
    data = {
        "amount": float(price),
        "currency": "RUB",
        "orderId": str(user_id)
    }
    async with ClientSession() as session:
        async with session.post('https://api.wata.pro/api/h2h/links', json=data, headers=headers) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'id': data['id'],
        'url': data['url']
    }


async def get_card_payment_data(price: int) -> dict | bool:
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'sum': float(price),
        'orderId': get_random_id(),
        'shopId': '9262f0d1-9aa6-4a7b-b4fb-38fe93779454',
        'includeService': ['sbp']
    }
    data = dict(sorted(data.items(), key=lambda x: x[0]))
    sign = _add_signature(data)
    headers['Signature'] = sign
    async with ClientSession() as session:
        async with session.post('https://api.lava.ru/business/invoice/create', json=data, headers=headers) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'id': data['data']['id'],
        'url': data['data']['url']
    }


async def get_oxa_payment_data(amount: int | float):
    url = 'https://api.oxapay.com/v1/payment/invoice'
    headers = {
        'merchant_api_key': merchant_api_key,
        'Content-Type': 'application/json'
    }
    data = {
        'amount': float(amount),
        'mixed_payment': False
    }
    async with ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
            data = await resp.json()
    return {
        'url': data['data']['payment_url'],
        'id': data['data']['track_id']
    }


async def get_crypto_payment_data(amount: int | float):
    invoice = await crypto_bot.create_invoice(asset='USDT', amount=amount)
    return {
        'url': invoice.mini_app_invoice_url,
        'id': invoice.invoice_id
    }


async def check_card_payment(id: str) -> bool:
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'shopId': '9262f0d1-9aa6-4a7b-b4fb-38fe93779454',
        'orderId': get_random_id(),
        'invoiceId': id
    }
    data = dict(sorted(data.items(), key=lambda x: x[0]))
    sign = _add_signature(data)
    headers['Signature'] = sign
    async with ClientSession() as session:
        async with session.post('https://api.lava.ru/business/invoice/status', json=data, headers=headers) as resp:
            if resp.status != 200:
                print('card check error', await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    if data['data']['status'] == 'success':
        return True
    return False


async def check_oxa_payment(track_id: str) -> bool:
    url = 'https://api.oxapay.com/v1/payment/' + track_id
    headers = {
        'merchant_api_key': merchant_api_key,
        'Content-Type': 'application/json'
    }
    async with ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print('oxa check error', await resp.json())
                return False
            data = await resp.json()
    if data['data']['status'] == 'paid':
        return True
    return False


async def check_crypto_payment(invoice_id: int) -> bool:
    invoice = await crypto_bot.get_invoices(invoice_ids=invoice_id)
    if invoice.status == 'paid':
        return True
    return False


async def check_wata_payment(id: str):
    url = f'https://api.wata.pro/api/h2h/links/{id}'
    print(url)
    headers = {
        'Authorization': f'Bearer {config.wata.card_key}',
        'Content-Type': 'application/json'
    }
    async with ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                print(resp.status)
                print('wata check error', await resp.json())
                return False
            data = await resp.json()
    if data['status'] == 'Closed':
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


#print(asyncio.run(check_wata_payment('3a19f00f-819b-71cc-799f-c57af7076efb')))
