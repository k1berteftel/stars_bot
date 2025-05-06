import asyncio
import aiohttp
import json

from ton_fragment.helpers import scraper

from config_data.config import load_config, Config


config: Config = load_config()


async def transfer_stars(username: str, stars: int) -> bool:
    url = "https://tg.parssms.info/v1/stars/payment"
    data = {
        "query": username,
        "quantity": stars
    }
    headers = {
        'Content-Type': 'application/json',
        'api-key': config.fragment.api_key
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            if resp.status != 200:
                print(resp.content)
                return False
            data = await resp.json()
            content = await resp.text()
            print(data)
    return True



#asyncio.run(transfer_stars())