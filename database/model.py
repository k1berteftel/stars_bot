import datetime

from sqlalchemy import BigInteger, VARCHAR, ForeignKey, DateTime, Boolean, Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UsersTable(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(VARCHAR)
    name: Mapped[str] = mapped_column(VARCHAR)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    referral: Mapped[int] = mapped_column(BigInteger, default=None, nullable=True)
    refs: Mapped[int] = mapped_column(Integer, default=0)
    earn: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[int] = mapped_column(Integer, default=1)
    activity: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=datetime.datetime.now())
    entry: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), default=datetime.datetime.now())


class DeeplinksTable(Base):
    __tablename__ = 'deeplinks'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    link: Mapped[str] = mapped_column(VARCHAR)
    entry: Mapped[int] = mapped_column(BigInteger, default=0)


class AdminsTable(Base):
    __tablename__ = 'admins'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(VARCHAR)


class OneTimeLinksIdsTable(Base):
    __tablename__ = 'links'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    link: Mapped[str] = mapped_column(VARCHAR)


class PromosTable(Base):
    __tablename__ = 'promos'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    promo: Mapped[str] = mapped_column(VARCHAR, unique=True)
    limit: Mapped[int] = mapped_column(Integer)
    percent: Mapped[int] = mapped_column(Integer)
    entry: Mapped[int] = mapped_column(Integer, default=0)


class UserPromoTable(Base):
    __tablename__ = 'user-promo'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    promo: Mapped[str] = mapped_column(ForeignKey('promos.promo', ondelete='CASCADE'))


class PricesTable(Base):
    __tablename__ = 'prices'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    charge: Mapped[int] = mapped_column(Integer, default=15)
