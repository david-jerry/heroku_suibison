import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
import pprint
from typing import Annotated, List, Optional
from celery import shared_task
from fastapi import Depends

from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

import ast

from src.apps.accounts.models import MatrixPool, MatrixPoolUsers, TokenMeter, User, UserReferral, UserStaking, UserWallet
import yfinance as yf

from src.apps.accounts.services import UserServices
from src.celery_tasks import celery_app
from src.db import engine
from src.db.engine import get_session, get_session_context
from src.db.redis import redis_client
from src.utils.calculations import get_rank, matrix_share
from src.utils.logger import LOGGER
from sqlmodel import select

user_services = UserServices()

async def run_cncurrent_tasks():
    await create_matrix_pool()
    await calculate_daily_tasks()

async def calculate_daily_tasks():
    async with get_session_context() as session:
        session: AsyncSession = session
        try:
            now = datetime.now()
            user_db = await session.exec(select(User).where(User.isBlocked == False).where(User.isAdmin == False))
            users: List[User] = user_db.all()

            LOGGER.info("running daily task calculation logic")

            for user in users:
                stake = user.staking

                if stake is None:
                    return

                if stake.start:
                    if stake.roi < Decimal(0.04) and stake.nextRoiIncrease > now:
                        # Increase ROI and set the next increase date
                        stake.roi += Decimal(0.005)
                        stake.nextRoiIncrease = now + timedelta(days=5)

                    if stake.roi == Decimal(0.04):
                        stake.end = now + timedelta(days=100)


                    if stake.lastEarningTime + timedelta(days=1) > now:
                        interest_earned = stake.deposit * stake.roi
                        user.wallet.earnings += interest_earned

                        # Todo: add activity here to notify user about earning topup

                if stake.end and stake.end.date() == now.date():
                    stake.roi = Decimal(0.01)
                    stake.end = None
                    stake.nextRoiIncrease = None

                await session.commit()
                await session.refresh(user)
            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()

async def create_matrix_pool():
    async with get_session_context() as session:
        session: AsyncSession = session
        try:
            now = datetime.now()
            matrix_db = await session.exec(select(MatrixPool).where(MatrixPool.endDate >= now))
            active_matrix_pool_or_new: Optional[MatrixPool] = matrix_db.first()
            sevenDaysLater = now + timedelta(days=7)

            if active_matrix_pool_or_new is None:
                new_pool = MatrixPool(
                    raisedPoolAmount=Decimal(0), startDate=now, endDate=sevenDaysLater
                )
                session.add(new_pool)
                await session.commit()
            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()

if __name__ == "__main__":
    asyncio.run(run_cncurrent_tasks())


















































































# @celery_app.task(name="five_day_stake_interest")
# def five_day_stake_interest():
#     # fetch dollar rate from oe sui to check agaist the entire website

#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(calculate_and_update_staked_interest_every_5_days())
#     loop.close()

# async def calculate_and_update_staked_interest_every_5_days():
#     now = datetime.now()
#     async with get_session_context() as session:
#         user_db = await session.exec(select(User).where(User.isBlocked == False))
#         users = user_db.all()

#         for user in users:
#             stake = user.staking

#             remaining_days = (stake.end - now).days

#             # loop this task until staking expiry date has reached then stop it
#             if stake.end > now:
#                 # accrue interest until it reaches 4% then create the end date to be 100 days in the future

#                 # calculate interest based on remaining days and ensure the roi is less than 4%
#                 if (stake.roi < Decimal(0.04)) and (stake.nextRoiIncrease == now):
#                     new_roi = stake.roi + Decimal(0.005)
#                     stake.roi = new_roi
#                     stake.nextRoiIncrease = now + timedelta(days=5)
#                 elif stake.roi == Decimal(0.04):
#                     stake.end = now + timedelta(days=100)

#                 interest_earned = stake.deposit * new_roi
#                 user.wallet.earnings += interest_earned
#                 user.wallet.earnings += (stake.deposit * stake.roi)

#             if stake.end < now:
#                 stake.roi = 0.01
#                 stake.nextRoiIncrease = None

#             await session.commit()
#             await session.refresh(stake)
#             return None



