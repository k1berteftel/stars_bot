import asyncio
import aiohttp
import json
import logging

from config_data.config import load_config, Config


config: Config = load_config()


async def get_stars_price(amount: int) -> float:
    url = 'https://tg2.parssms.info/v1/stars/price'
    headers = {
        'Content-Type': 'application/json',
        'api-key': config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, ssl=False) as resp:
            data = await resp.json()
            per_star = float(data[0]['approx_price_usd'][1::]) / 50
    return round(amount * per_star, 2)


async def transfer_stars(username: str, stars: int) -> bool:
    url = "https://tg2.parssms.info/v1/stars/payment"
    data = {
        "query": username,
        "quantity": str(stars)
    }
    headers = {
        'Content-Type': 'application/json',
        'api-key': config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                content = await resp.content.read()
                logging.error(content)
                with open('err_trans.txt', 'a', encoding='utf-8') as f:
                    f.write(f'**Ошибка транзакции**:\nКонтент: {content}\n')
                try:
                    data = await resp.json()
                    with open('err_trans.txt', 'a', encoding='utf-8') as f:
                        f.write(f'JSON: {data}\n\n')
                except Exception:
                    ...
                return False
            data = await resp.json()
            if data['ok'] != True:
                logging.error(data)
                return False
            print(data)
    return True


async def transfer_premium(username: str, months: int):
    url = "https://tg.parssms.info/v1/premium/payment"
    data = {
        "query": username,
        "months": str(months)
    }
    headers = {
        'Content-Type': 'application/json',
        'api-key': config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                print(await resp.content.read())
                logging.error(await resp.content.read())
                try:
                    logging.error(await resp.json())
                except Exception:
                    ...
                return False
            data = await resp.json()
            if data['ok'] != True:
                logging.error(data)
                return False
            print(data)
    return True


async def transfer_ton(username: str, amount: int):
    url = 'https://tg.parssms.info/v1/ads/topup'
    data = {
        "query": username,
        "amount": str(amount)
    }
    headers = {
        'Content-Type': 'application/json',
        'api-key': config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                print(await resp.content.read())
                logging.error(await resp.content.read())
                try:
                    logging.error(await resp.json())
                except Exception:
                    ...
                return False
            data = await resp.json()
            if data['ok'] != True:
                logging.error(data)
                return False
            print(data)
    return True


async def check_user_premium(username: str, months: int):
    url = 'https://tg.parssms.info/v1/premium/search'
    data = {
        "query": username,
        "months": str(months)
    }
    headers = {
        'Content-Type': 'application/json',
        'api-key': config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                print(await resp.content.read())
                logging.error(await resp.content.read())
                try:
                    logging.error(await resp.json())
                except Exception:
                    ...
                return False
            data = await resp.json()
            print(data)
            if data['ok'] != True:
                return False
            print(data)
    return True



#print(asyncio.run(transfer_stars('farion', 50)))