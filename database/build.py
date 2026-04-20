from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from database.model import Base


class PostgresBuild:
    def __init__(self, url: str):
        self.engine = create_async_engine(
            url,
            pool_size=50,  # Увеличили с 25
            max_overflow=50,  # Увеличили с 10
            pool_timeout=30,  # Таймаут ожидания соединения
            pool_pre_ping=True,  # Проверка соединения перед использованием
            pool_recycle=3600,
            pool_use_lifo=True
        )

    async def create_tables(self, base):
        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)

    async def drop_tables(self, base):
        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.drop_all)

    async def clear(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS deeplinks CASCADE"))

    def session(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(self.engine, expire_on_commit=False)