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
class ConsumerConfig:
    subject: str
    stream: str
    durable_name: str


@dataclass
class Redis:
    password: str


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
class FreeKassa:
    api_key: str


@dataclass
class Paypear:
    shop_id: int
    secret_key: str


@dataclass
class Platega:
    merchant_id: str
    secret_key: str


@dataclass
class Config:
    bot: tg_bot
    db: DB
    nats: NatsConfig
    consumer: ConsumerConfig
    redis: Redis
    crypto_bot: CryptoBot
    fragment: Fragment
    oxa: Oxa
    p2p: P2P
    freekassa: FreeKassa
    paypear: Paypear
    platega: Platega


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
        consumer=ConsumerConfig(
            subject=env('NATS_CONSUMER_SUBJECT'),
            stream=env('NATS_CONSUMER_STREAM'),
            durable_name=env('NATS_CONSUMER_DURABLE_NAME')
        ),
        redis=Redis(
            password=env('redis_password')
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
        freekassa=FreeKassa(
            api_key=env('freekassa_api_key')
        ),
        paypear=Paypear(
            shop_id=int(env('paypear_shop_id')),
            secret_key=env('paypear_secret_key')
        ),
        platega=Platega(
            merchant_id=env('platega_merchant_id'),
            secret_key=env('platega_secret_key')
        )
    )
