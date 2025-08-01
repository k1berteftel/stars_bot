import asyncio
import datetime
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


def _get_signature(data: dict, api_key: str):
    print('data before', data)
    sorted_data = dict(sorted(data.items(), key=lambda item: item[0]))
    print('data after ', sorted_data)
    message = '|'.join(str(v) for v in sorted_data.values())
    print(message)
    signature = hmac.new(
        key=api_key.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    sorted_data['signature'] = signature
    return sorted_data


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
            print(data)
            print(type(data['status']), data['status'])
            if data['status'] == 429:
                print('status', data['status'])
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


async def get_freekassa_card(user_id: int, amount: float):
    url = 'https://api.fk.life/v1/orders/create'
    data = {
        'shopId': 32219,
        'nonce': int(datetime.datetime.today().timestamp()),
        'us_userId': str(user_id),
        'i': 36,
        'email': f'{user_id}@stars-bot.ru',
        'ip': '80.80.116.211',
        'amount': str(float),
        'currency': 'RUB'
    }
    data = _get_signature(data, config.freekassa.api_key)
    async with ClientSession() as session:
        async with session.post(url, json=data) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'url': data['location'],
    }


async def get_freekassa_sbp(user_id: int, amount: float):
    url = 'https://api.fk.life/v1/orders/create'
    data = {
        'shopId': 32219,
        'nonce': int(datetime.datetime.today().timestamp()),
        'us_userId': str(user_id),
        'i': 44,
        'email': f'{user_id}@stars-bot.ru',
        'ip': '80.80.116.211',
        'amount': str(amount),
        'currency': 'RUB'
    }
    data = _get_signature(data, config.freekassa.api_key)
    async with ClientSession() as session:
        async with session.post(url, json=data) as resp:
            if resp.status != 200:
                print(await resp.json())
                print(resp.status)
                return False
            data = await resp.json()
    return {
        'url': data['location'],
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


async def check_oxa_payment(track_id: str, counter: int = 1) -> bool:
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
            try:
                data = await resp.json()
            except Exception:
                if counter >= 5:
                    return False
                return await check_oxa_payment(track_id, counter+1)
    if data['data']['status'] == 'paid':
        return True
    return False


async def check_crypto_payment(invoice_id: int) -> bool:
    invoice = await crypto_bot.get_invoices(invoice_ids=invoice_id)
    if invoice.status == 'paid':
        return True
    return False


async def _get_usdt_rub() -> float:
    url = 'https://open.er-api.com/v6/latest/USD'
    async with ClientSession() as session:
        async with session.get(url) as res:
            data = await res.json()
            rub = data['rates']['RUB']
    return float(rub)


async def _get_ton_usdt() -> float:
    url = 'https://api.coingecko.com/api/v3/coins/the-open-network'
    async with ClientSession() as session:
        async with session.get(url) as res:
            resp = await res.json()
            ton = float(resp['market_data']['current_price']['usd'])
    return ton



#print(asyncio.run(get_freekassa_sbp(48472347, 100)))
