import datetime

from sqlalchemy import select, insert, update, column, text, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.model import (UsersTable, DeeplinksTable, OneTimeLinksIdsTable, AdminsTable, PromosTable, UserPromoTable, PricesTable)


async def setup_database(session: async_sessionmaker):
    async with session() as session:
        await session.execute(insert(PricesTable).values(
            charge=15
        ))
        await session.commit()


class DataInteraction():
    def __init__(self, session: async_sessionmaker):
        self._sessions = session

    async def check_promo(self, user_id: int, promo: str) -> bool | PromosTable:
        async with self._sessions() as session:
            promo = await session.scalar(select(PromosTable).where(PromosTable.promo == promo))
            if not promo:
                return False
            if promo.entry >= promo.limit:
                await self.del_promo(promo.id)
                return False
            user_promo = await self.get_user_promo(user_id, promo.promo)
            if user_promo:
                return False
            await self.add_user_promo(user_id, promo.promo)
            await session.execute(update(PromosTable).where(PromosTable.id == promo.id).values(
                entry=PromosTable.entry + 1
            ))
            await session.commit()
            return promo

    async def check_user(self, user_id: int) -> bool:
        async with self._sessions() as session:
            result = await session.scalar(select(UsersTable).where(UsersTable.user_id == user_id))
        return True if result else False

    async def add_user(self, user_id: int, username: str, name: str, referral: int | None):
        if await self.check_user(user_id):
            return
        async with self._sessions() as session:
            await session.execute(insert(UsersTable).values(
                user_id=user_id,
                username=username,
                name=name,
                referral=referral
            ))
            await session.commit()

    async def add_refs(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(update(UsersTable).where(UsersTable.user_id == user_id).values(
                refs=UsersTable.refs + 1,
            ))
            await session.commit()

    async def add_entry(self, link: str):
        async with self._sessions() as session:
            await session.execute(update(DeeplinksTable).where(DeeplinksTable.link == link).values(
                entry=DeeplinksTable.entry+1
            ))
            await session.commit()

    async def add_deeplink(self, link: str):
        async with self._sessions() as session:
            await session.execute(insert(DeeplinksTable).values(
                link=link
            ))
            await session.commit()

    async def add_link(self, link: str):
        async with self._sessions() as session:
            await session.execute(insert(OneTimeLinksIdsTable).values(
                link=link
            ))
            await session.commit()

    async def add_admin(self, user_id: int, name: str):
        async with self._sessions() as session:
            await session.execute(insert(AdminsTable).values(
                user_id=user_id,
                name=name
            ))
            await session.commit()

    async def add_promo(self, promo: str, limit: int, percent: int):
        async with self._sessions() as session:
            await session.execute(insert(PromosTable).values(
                promo=promo,
                limit=limit,
                percent=percent
            ))
            await session.commit()

    async def add_user_promo(self, user_id: int, promo: str):
        async with self._sessions() as session:
            await session.execute(insert(UserPromoTable).values(
                user_id=user_id,
                promo=promo
            ))
            await session.commit()

    async def get_promos(self):
        async with self._sessions() as session:
            result = await session.scalars(select(PromosTable))
        return result.fetchall()

    async def get_user_promo(self, user_id: int, promo: str):
        async with self._sessions() as session:
            result = await session.scalar(select(UserPromoTable).where(
                and_(
                    UserPromoTable.promo == promo,
                    UserPromoTable.user_id == user_id
                )
            ))
        return result if result else False

    async def get_users(self):
        async with self._sessions() as session:
            result = await session.scalars(select(UsersTable))
        return result.fetchall()

    async def get_user(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(UsersTable).where(UsersTable.user_id == user_id))
        return result

    async def get_links(self):
        async with self._sessions() as session:
            result = await session.scalars(select(OneTimeLinksIdsTable))
        return result.fetchall()

    async def get_admins(self):
        async with self._sessions() as session:
            result = await session.scalars(select(AdminsTable))
        return result.fetchall()

    async def get_deeplinks(self):
        async with self._sessions() as session:
            result = await session.scalars(select(DeeplinksTable))
        return result.fetchall()

    async def get_prices(self):
        async with self._sessions() as session:
            result = await session.scalar(select(PricesTable))
        return result

    async def set_charge(self, charge: int):
        async with self._sessions() as session:
            await session.execute(update(PricesTable).values(
                charge=charge
            ))
            await session.commit()

    async def set_activity(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(update(UsersTable).where(UsersTable.user_id == user_id).values(
                activity=datetime.datetime.today()
            ))
            await session.commit()

    async def set_active(self, user_id: int, active: int):
        async with self._sessions() as session:
            await session.execute(update(UsersTable).where(UsersTable.user_id == user_id).values(
                active=active
            ))
            await session.commit()

    async def del_deeplink(self, link: str):
        async with self._sessions() as session:
            await session.execute(delete(DeeplinksTable).where(DeeplinksTable.link == link))
            await session.commit()

    async def del_link(self, link_id: str):
        async with self._sessions() as session:
            await session.execute(delete(OneTimeLinksIdsTable).where(OneTimeLinksIdsTable.link == link_id))
            await session.commit()

    async def del_promo(self, id: int):
        async with self._sessions() as session:
            await session.execute(delete(PromosTable).where(PromosTable.id == id))
            await session.commit()

    async def del_admin(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(delete(AdminsTable).where(AdminsTable.user_id == user_id))
            await session.commit()