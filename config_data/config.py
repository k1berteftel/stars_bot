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
class P2P:
    api_key: str


@dataclass
class Fragment:
    api_key: str


@dataclass
class Oxa:
    api_key: str


@dataclass
class Wata:
    card_key: str
    sbp_key: str


@dataclass
class Config:
    bot: tg_bot
    db: DB
    nats: NatsConfig
    crypto_bot: CryptoBot
    fragment: Fragment
    oxa: Oxa
    p2p: P2P
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
        p2p=P2P(
            api_key=env('p2p_api_token')
        ),
        wata=Wata(
            card_key=env('wata_card_key'),
            sbp_key=env('wata_sbp_key')
        )
    )
