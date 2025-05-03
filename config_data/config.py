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
class YooKassa:
    account_id: str
    secret_key: str


@dataclass
class Config:
    bot: tg_bot
    db: DB
    nats: NatsConfig
    crypto_bot: CryptoBot
    yookassa: YooKassa


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
        yookassa=YooKassa(
            account_id=env('account_id'),
            secret_key=env('secret_key')
        )
    )
