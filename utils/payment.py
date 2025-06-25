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

merchant_api_key = config.oxa.api_key
crypto_bot = AioCryptoPay(token=config.crypto_bot.token, network=Networks.MAIN_NET)


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
    if not data['status'] != 200:
        return await get_oxa_payment_data(amount)
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


async def get_p2p_sbp(amount: int):
    url = 'https://p2pkassa.live/api/v1/acquiring'
    order_id = get_random_id()
    data = {
        'project_id': 386,
        'order_id': order_id,
        'amount': float(amount),
        'currency': 'RUB',
        'method': 'sbp',
    }
    join_string = f"{config.p2p.api_key}{order_id}{386}{float(amount):.2f}RUB"
    auth_token = hashlib.sha512(join_string.encode('utf-8')).hexdigest()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}'
    }
    async with ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.content.read()
            data = json.loads(data.decode('utf-8'))
    return {
        'url': data['link'],
        'id': data['id'],
        'order_id': order_id
    }


async def check_p2p_sbp(order_id: str, id: str):
    async with ClientSession() as session:
        url = 'https://p2pkassa.live/api/v1/getpayAcquiring'
        join_string = f"{config.p2p.api_key}{id}{order_id}{386}"
        data = {
            'id': id,
            'order_id': order_id,
            'project_id': 386
        }
        auth_token = hashlib.sha512(join_string.encode('utf-8')).hexdigest()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }
        async with session.post(url, json=data, headers=headers) as resp:
            if resp.status != 200:
                return False
            data = await resp.json()
            if data['status'] == 'PAID':
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


async def _get_usdt_rub() -> float:
    async with ClientSession() as session:
        async with session.get('https://www.rbc.ru/crypto/currency/usdtrub') as res:
            resp = await res.text()
            soup = BeautifulSoup(resp, 'lxml')
            price = soup.find('div', class_='chart__subtitle').text.strip()
            value = re.search(r'\d+,\d+', price)
            return float(price[value.start():value.end():].replace(',', '.'))


#print(asyncio.run(check_p2p_sbp('ONSvMYlT', '51f77da9-5280-4fcc-88c1-dd6c1c1a8afe')))
