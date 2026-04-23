import datetime
from typing import Literal

from sqlalchemy import select, insert, update, column, text, delete, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.model import (UsersTable, DeeplinksTable, OneTimeLinksIdsTable, AdminsTable, PromosTable,
                            UserPromoTable, PricesTable, ApplicationsTable, StaticsTable, BlockUsersTable, CashFlowTable)
from database.cache import invalidates, cached, CacheManager


async def setup_database(session: async_sessionmaker):
    async with session() as session:
        if not await session.scalar(select(PromosTable)):
            await session.execute(insert(PricesTable).values())
        if not await session.scalar(select(StaticsTable)):
            await session.execute(insert(StaticsTable).values())
        if not await session.scalar(select(CashFlowTable)):
            await session.execute(insert(CashFlowTable).values())
        await session.commit()


class DataInteraction():
    def __init__(self, session: async_sessionmaker, cache_manager: CacheManager = None):
        self._sessions = session
        self.cache_manager: CacheManager = cache_manager

    @cached(ttl=3600, prefix="user")
    async def get_user(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalar(
                select(UsersTable).where(UsersTable.user_id == user_id)
            )
        return result

    @cached(ttl=3600, prefix="user_by_username")
    async def get_user_by_username(self, username: str):
        async with self._sessions() as session:
            result = await session.scalar(
                select(UsersTable).where(UsersTable.username == username)
            )
        return result

    @cached(ttl=300, prefix="blocked_users")
    async def get_block_users(self):
        async with self._sessions() as session:
            result = await session.scalars(select(BlockUsersTable))
        return result.fetchall()

    @cached(ttl=3600, prefix="admins")
    async def get_admins(self):
        async with self._sessions() as session:
            result = await session.scalars(select(AdminsTable))
        return result.fetchall()

    @cached(ttl=1800, prefix="promos")
    async def get_promos(self):
        async with self._sessions() as session:
            result = await session.scalars(select(PromosTable))
        return result.fetchall()

    @cached(ttl=1800, prefix="promo")
    async def get_promo(self, promo: str):
        async with self._sessions() as session:
            result = await session.scalar(
                select(PromosTable).where(PromosTable.promo == promo)
            )
        return result

    @cached(ttl=300, prefix="user_promo")
    async def get_user_promo(self, user_id: int, promo: str):
        async with self._sessions() as session:
            result = await session.scalar(
                select(UserPromoTable).where(
                    and_(
                        UserPromoTable.promo == promo,
                        UserPromoTable.user_id == user_id
                    )
                )
            )
        return result if result else False

    @cached(ttl=60, prefix="statistics")
    async def get_statistics(self):
        async with self._sessions() as session:
            result = await session.scalar(select(StaticsTable))
        return result

    @cached(ttl=300, prefix="users_list")
    async def get_users(self):
        async with self._sessions() as session:
            result = await session.scalars(select(UsersTable))
        return result.fetchall()

    @cached(ttl=300, prefix="ref_users")
    async def get_ref_users(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalars(
                select(UsersTable).where(UsersTable.referral == user_id)
            )
        return result.fetchall()

    @cached(ttl=300, prefix="sub_ref_users")
    async def get_sub_ref_users(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalars(
                select(UsersTable).where(UsersTable.sub_referral == user_id)
            )
        return result.fetchall()

    @cached(ttl=300, prefix="applications_list")
    async def get_applications(self):
        async with self._sessions() as session:
            result = await session.scalars(
                select(ApplicationsTable).order_by(ApplicationsTable.uid_key)
            )
        return result.fetchall()

    @cached(ttl=300, prefix="application")
    async def get_application(self, uid_key: int):
        async with self._sessions() as session:
            result = await session.scalar(
                select(ApplicationsTable).where(ApplicationsTable.uid_key == uid_key)
            )
        return result

    @cached(ttl=300, prefix="receiver_applications")
    async def get_receiver_applications(self, receiver: str):
        async with self._sessions() as session:
            result = await session.scalars(
                select(ApplicationsTable).where(ApplicationsTable.receiver == receiver)
            )
        return result.fetchall()

    @cached(ttl=300, prefix="last_application")
    async def get_last_application(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalar(
                select(ApplicationsTable)
                .where(ApplicationsTable.user_id == user_id)
                .order_by(ApplicationsTable.create.desc())
            )
        return result

    @cached(ttl=300, prefix="user_applications")
    async def get_user_applications(self, user_id: int):
        async with self._sessions() as session:
            result = await session.scalars(
                select(ApplicationsTable).where(ApplicationsTable.user_id == user_id)
            )
        return result.fetchall()

    @cached(ttl=300, prefix="links")
    async def get_links(self):
        async with self._sessions() as session:
            result = await session.scalars(select(OneTimeLinksIdsTable))
        return result.fetchall()

    @cached(ttl=300, prefix="deeplink")
    async def get_deeplink(self, id: int):
        async with self._sessions() as session:
            result = await session.scalar(select(DeeplinksTable).where(DeeplinksTable.id == id))
        return result

    @cached(ttl=300, prefix="deeplinks")
    async def get_deeplinks(self):
        async with self._sessions() as session:
            result = await session.scalars(select(DeeplinksTable))
        return result.fetchall()

    @cached(ttl=3600, prefix="prices")
    async def get_prices(self):
        async with self._sessions() as session:
            result = await session.scalar(select(PricesTable))
        return result

    # ==================== UPDATE методы (инвалидируют кэш) ====================

    @invalidates("deeplink:{deeplink_id}", "deeplinks")
    async def set_deeplink_value(self, deeplink_id: int, **kwargs):
        async with self._sessions() as session:
            await session.execute(
                update(DeeplinksTable)
                .where(DeeplinksTable.id == deeplink_id)
                .values(**kwargs)
            )
            await session.commit()

    @invalidates("deeplink:{deeplink_id}", "deeplinks")
    async def update_deeplink_earn(self, deeplink_id: int, earn: int):
        async with self._sessions() as session:
            await session.execute(
                update(DeeplinksTable)
                .where(DeeplinksTable.id == deeplink_id)
                .values(
                    earned=DeeplinksTable.earned + earn,
                    today=DeeplinksTable.today + earn,
                    week=DeeplinksTable.week + earn
                )
            )
            await session.commit()

    @invalidates("user:{user_id}", "users_list")
    async def update_username(self, user_id: int, username: str):
        async with self._sessions() as session:
            await session.execute(
                update(UsersTable)
                .where(UsersTable.user_id == user_id)
                .values(username=username)
            )
            await session.commit()

    @invalidates("application:{uid_key}", "applications_list", "user_applications:{user_id}")
    async def update_application(self, uid_key: int, status: int, payment: str | None, tx_hash: str | None = None):
        async with self._sessions() as session:
            await session.execute(
                update(ApplicationsTable)
                .where(ApplicationsTable.uid_key == uid_key)
                .values(
                    status=status,
                    tx_hash=tx_hash,
                    payment=payment
                )
            )
            await session.commit()

    @invalidates("user:{user_id}", "users_list")
    async def update_buys(self, user_id: int, stars: int):
        user = await self.get_user(user_id)
        async with self._sessions() as session:
            if user and user.buys is None:
                await session.execute(
                    update(UsersTable)
                    .where(UsersTable.user_id == user_id)
                    .values(buys=stars)
                )
            else:
                await session.execute(
                    update(UsersTable)
                    .where(UsersTable.user_id == user_id)
                    .values(buys=UsersTable.buys + stars)
                )
            await session.commit()

    @invalidates("user:{user_id}", "users_list")
    async def update_earn(self, user_id: int, earn: int):
        async with self._sessions() as session:
            await session.execute(
                update(UsersTable)
                .where(UsersTable.user_id == user_id)
                .values(earn=UsersTable.earn + earn)
            )
            await session.commit()

    @invalidates("prices")
    async def set_charge(self, **kwargs):
        async with self._sessions() as session:
            await session.execute(update(PricesTable).values(kwargs))
            await session.commit()

    @invalidates("user:{user_id}", "users_list")
    async def set_activity(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(
                update(UsersTable)
                .where(UsersTable.user_id == user_id)
                .values(activity=datetime.datetime.today())
            )
            await session.commit()

    @invalidates("user:{user_id}", "users_list")
    async def set_active(self, user_id: int, active: int):
        async with self._sessions() as session:
            await session.execute(
                update(UsersTable)
                .where(UsersTable.user_id == user_id)
                .values(active=active)
            )
            await session.commit()

    # ==================== ADD методы (инвалидируют кэш) ====================

    @invalidates("user:{user_id}", "users_list")
    async def add_user(self, user_id: int, username: str, name: str,
                       referral: int | None, sub_referral: int | None, join: str | None = None):
        if await self.check_user(user_id):
            return

        async with self._sessions() as session:
            await session.execute(
                insert(UsersTable).values(
                    user_id=user_id,
                    username=username,
                    name=name,
                    referral=referral,
                    sub_referral=sub_referral,
                    join=join,
                    entry=datetime.datetime.now()
                )
            )
            await session.commit()

    @invalidates("blocked_users")
    async def add_block(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(insert(BlockUsersTable).values(user_id=user_id))
            await session.commit()

    @invalidates("statistics")
    async def add_payment(self):
        async with self._sessions() as session:
            await session.execute(
                update(StaticsTable).values(payments=StaticsTable.payments + 1)
            )
            await session.commit()

    @invalidates("statistics")
    async def add_buys(self, sum: int):
        async with self._sessions() as session:
            await session.execute(
                update(StaticsTable).values(buys=StaticsTable.buys + sum)
            )
            await session.commit()

    @invalidates("user:{user_id}", "ref_users:{user_id}", "users_list")
    async def add_refs(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(
                update(UsersTable)
                .where(UsersTable.user_id == user_id)
                .values(refs=UsersTable.refs + 1)
            )
            await session.commit()

    @invalidates("user:{user_id}", "sub_ref_users:{user_id}", "users_list")
    async def add_sub_refs(self, user_id: int):
        user = await self.get_user(user_id)
        async with self._sessions() as session:
            if user and user.sub_refs:
                await session.execute(
                    update(UsersTable)
                    .where(UsersTable.user_id == user_id)
                    .values(
                        sub_refs=UsersTable.sub_refs + 1,
                        earn=UsersTable.earn + 2
                    )
                )
            else:
                await session.execute(
                    update(UsersTable)
                    .where(UsersTable.user_id == user_id)
                    .values(
                        sub_refs=1,
                        earn=UsersTable.earn + 2
                    )
                )
            await session.commit()

    @invalidates("deeplink:{id}", "deeplinks")
    async def add_entry(self, id: int):
        async with self._sessions() as session:
            await session.execute(
                update(DeeplinksTable)
                .where(DeeplinksTable.id == id)
                .values(entry=DeeplinksTable.entry + 1)
            )
            await session.commit()

    @invalidates("deeplinks")
    async def add_deeplink(self, link: str, name: str):
        async with self._sessions() as session:
            await session.execute(
                insert(DeeplinksTable).values(link=link, name=name)
            )
            await session.commit()

    @invalidates("links")
    async def add_link(self, link: str):
        async with self._sessions() as session:
            await session.execute(insert(OneTimeLinksIdsTable).values(link=link))
            await session.commit()

    @invalidates("admins")
    async def add_admin(self, user_id: int, name: str):
        async with self._sessions() as session:
            await session.execute(insert(AdminsTable).values(user_id=user_id, name=name))
            await session.commit()

    @invalidates("applications_list", "user_applications:{user_id}", "receiver_applications:{receiver}")
    async def add_application(self, user_id: int, receiver: str,
                              amount: int, rub: int, usdt: float,
                              buy: Literal['deleted_gift', 'stars', 'premium', 'ton'], count=1) -> ApplicationsTable:
        applications = await self.get_applications()
        uid_key = applications[-1].uid_key + count if applications else 1000

        async with self._sessions() as session:
            try:
                await session.execute(
                    insert(ApplicationsTable).values(
                        uid_key=uid_key,
                        user_id=user_id,
                        receiver=receiver,
                        amount=amount,
                        rub=rub,
                        usdt=usdt,
                        type=buy
                    )
                )
                await session.commit()
            except Exception:
                return await self.add_application(user_id, receiver, amount, rub, usdt, buy, count + 1)

            return await self.get_application(uid_key)

    @invalidates("promos", "promo:{promo}")
    async def add_promo(self, promo: str, limit: int, percent: int):
        async with self._sessions() as session:
            await session.execute(
                insert(PromosTable).values(promo=promo, limit=limit, percent=percent)
            )
            await session.commit()

    @invalidates("user_promo:{user_id}:{promo}")
    async def add_user_promo(self, user_id: int, promo: str):
        async with self._sessions() as session:
            await session.execute(
                insert(UserPromoTable).values(user_id=user_id, promo=promo)
            )
            await session.commit()

    # ==================== DELETE методы (инвалидируют кэш) ====================

    @invalidates("blocked_users")
    async def del_block_user(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(
                delete(BlockUsersTable).where(BlockUsersTable.user_id == user_id)
            )
            await session.commit()

    @invalidates("deeplink:{id}", "deeplinks")
    async def del_deeplink(self, id: int):
        async with self._sessions() as session:
            await session.execute(delete(DeeplinksTable).where(DeeplinksTable.id == id))
            await session.commit()

    @invalidates("links")
    async def del_link(self, link_id: str):
        async with self._sessions() as session:
            await session.execute(
                delete(OneTimeLinksIdsTable).where(OneTimeLinksIdsTable.link == link_id)
            )
            await session.commit()

    @invalidates("promos", "promo:{promo}")
    async def del_promo(self, id: int):
        promo = await self.get_promo_by_id(id)
        async with self._sessions() as session:
            await session.execute(delete(PromosTable).where(PromosTable.id == id))
            await session.commit()

    @invalidates("applications_list", "application:{uid_key}", "user_applications:{user_id}")
    async def del_application(self, uid_key: int):
        app = await self.get_application(uid_key)
        if not app:
            return

        async with self._sessions() as session:
            await session.execute(
                delete(ApplicationsTable).where(ApplicationsTable.uid_key == uid_key)
            )
            await session.commit()

    @invalidates("admins")
    async def del_admin(self, user_id: int):
        async with self._sessions() as session:
            await session.execute(
                delete(AdminsTable).where(AdminsTable.user_id == user_id)
            )
            await session.commit()

    # ==================== Вспомогательные методы (без кэша) ====================

    async def add_cashflow(self, sum: int):
        async with self._sessions() as session:
            await session.execute(update(CashFlowTable).values(
                earn=CashFlowTable.earn + sum,
                today=CashFlowTable.today + sum,
                week=CashFlowTable.week + sum,
                month=CashFlowTable.month + sum
            ))
            await session.commit()

    async def set_cashflow_value(self, **kwargs):
        async with self._sessions() as session:
            await session.execute(update(CashFlowTable).values(
                kwargs
            ))
            await session.commit()

    async def check_promo(self, user_id: int, promo: str) -> bool | PromosTable:
        async with self._sessions() as session:
            promo_obj = await session.scalar(
                select(PromosTable).where(PromosTable.promo == promo)
            )

            if not promo_obj:
                return False

            if promo_obj.entry >= promo_obj.limit:
                await self.del_promo(promo_obj.id)
                return False

            user_promo = await self.get_user_promo(user_id, promo_obj.promo)
            if user_promo:
                return False

            await self.add_user_promo(user_id, promo_obj.promo)

            await session.execute(
                update(PromosTable)
                .where(PromosTable.id == promo_obj.id)
                .values(entry=PromosTable.entry + 1)
            )
            await session.commit()

            return promo_obj

    async def check_user(self, user_id: int) -> bool:
        async with self._sessions() as session:
            result = await session.scalar(
                select(UsersTable).where(UsersTable.user_id == user_id)
            )
        return result is not None

    async def get_promo_by_id(self, id: int):
        async with self._sessions() as session:
            result = await session.scalar(
                select(PromosTable).where(PromosTable.id == id)
            )
        return result

    async def get_cashflow(self):
        async with self._sessions() as session:
            result = await session.scalar(select(CashFlowTable))
        return result

    async def get_deeplink_by_link(self, link: str):
        async with self._sessions() as session:
            result = await session.scalar(
                select(DeeplinksTable).where(DeeplinksTable.link == link)
            )
        return result
