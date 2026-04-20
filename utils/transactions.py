import asyncio
import aiohttp
import json
import logging

from aiogram import Bot

from config_data.config import load_config, Config


config: Config = load_config()


async def get_stars_price(amount: int) -> float:
    url = 'https://tg.parssms.info/v1/stars/price'
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
    url = "http://localhost:8090/buy"
    data = {
        'currency': stars,
        'username': username,
        'type': 'stars'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                return False
            data = await resp.json()
            if not data['ok']:
                logging.error(f'{data.get("message")}')
                return False
    return True


async def transfer_premium(username: str, months: int):
    url = "http://localhost:8090/buy"
    data = {
        'currency': months,
        'username': username,
        'type': 'premium'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                return False
            data = await resp.json()
            if not data['ok']:
                logging.error(f'{data.get("message")}')
                return False
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


async def distribute_ton():
    url = "http://localhost:8090/distribute"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, ssl=False) as resp:
            #print(resp.status)
            if resp.status not in [200, 201]:
                return False
            data = await resp.json()
            if not data['ok']:
                return False
    return True


async def transfer_gift(username: int, gift_id: int) -> bool:
    url = "http://localhost:8090/buy"
    data = {
        'currency': int(gift_id),
        'username': username,
        'type': 'deleted_gift'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, ssl=False) as resp:
            print(resp.status)
            if resp.status not in [200, 201]:
                return False
            data = await resp.json()
            if not data['ok']:
                logging.error(f'{data.get("message")}')
                return False
    return True





#print(asyncio.run(transfer_stars('Leggit_dev', 50)))
