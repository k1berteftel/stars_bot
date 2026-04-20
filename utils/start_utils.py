from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.action_data_class import DataInteraction


async def wrapper_today(session: DataInteraction):
    for link in await session.get_deeplinks():
        await session.set_deeplink_value(deeplink_id=link.id, today=0)
    cashflow = await session.get_cashflow()
    await session.set_cashflow_value(today=0, yesterday=cashflow.today, before_yesterday=cashflow.yesterday)


async def wrapper_week(session: DataInteraction):
    for link in await session.get_deeplinks():
        await session.set_deeplink_value(deeplink_id=link.id, week=0)
    await session.set_cashflow_value(week=0)


async def wrapper_month(session: DataInteraction):
    await session.set_cashflow_value(month=0)


async def start_schedulers(scheduler: AsyncIOScheduler, session: DataInteraction):
    """Запуск всех планировщиков"""
    # Ежедневный сброс в 00:00
    scheduler.add_job(
        wrapper_today,
        'cron',
        args=[session],
        hour=0,
        minute=0,
        id='reset_daily_profit'
    )
    scheduler.add_job(
        wrapper_week,
        'cron',
        args=[session],
        day_of_week='mon',
        hour=0,
        minute=0,
        id='reset_weekly_profit'
    )
    scheduler.add_job(
        wrapper_month,
        'cron',
        args=[session],
        day=1,
        hour=0,
        minute=0,
        id='reset_monthly_profit'
    )

