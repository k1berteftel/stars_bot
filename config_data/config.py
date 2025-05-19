from dataclasses import dataclass

from environs import Env

'''
    При необходимости конфиг базы данных или других сторонних сервисов
'''


@dataclass
class tg_bot:
    token: str
    admin_ids: list[int]


@dataclass
class DB:
    dns: str


@dataclass
class NatsConfig:
    servers: list[str]


@dataclass
class CryptoBot:
    token: str


@dataclass
class Lava:
    secret_key: str


@dataclass
class Fragment:
    api_key: str


@dataclass
class Oxa:
    api_key: str


@dataclass
class Wata:
    api_key: str


@dataclass
class Config:
    bot: tg_bot
    db: DB
    nats: NatsConfig
    crypto_bot: CryptoBot
    fragment: Fragment
    oxa: Oxa
    lava: Lava
    wata: Wata


def load_config(path: str | None = None) -> Config:
    env: Env = Env()
    env.read_env(path)

    return Config(
        bot=tg_bot(
            token=env('token'),
            admin_ids=list(map(int, env.list('admins')))
            ),
        db=DB(
            dns=env('dns')
        ),
        nats=NatsConfig(
            servers=env.list('nats')
        ),
        crypto_bot=CryptoBot(
            token=env('crypto_token')
        ),
        fragment=Fragment(
            api_key=env('fragment_api_key')
        ),
        oxa=Oxa(
            api_key=env('oxa_api_key')
        ),
        lava=Lava(
            secret_key=env('secret_key')
        ),
        wata=Wata(
            api_key=env('wata_api_key')
        )
    )
