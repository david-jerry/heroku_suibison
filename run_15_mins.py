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
    await fetch_sui_price()
    await add_fast_bonus()
    await fetch_sui_balance()
    await check_ranking()

async def fetch_sui_price():
    try:
        sui = yf.Ticker("SUI20947-USD")
        rate = sui.fast_info.last_price
        LOGGER.debug(f"SUI Price: {rate}")
        await redis_client.set("sui_price", rate)
    except Exception as e:
        LOGGER.error(e)

async def add_fast_bonus():
    async with get_session_context() as session:
        session: AsyncSession = session
        try:
            user_db = await session.exec(select(User).where(User.isBlocked == False))
            users = user_db.all()

            LOGGER.debug(f"FASTBONUSTASK: {users}")

            for user in users:
                LOGGER.debug(user.userId)
                ref_db = await session.exec(select(UserReferral).where(UserReferral.userId == user.userId).where(UserReferral.level == 1))
                refs = ref_db.all()

                # the has made first deposit is a means to know if the user has gained the fastadd bonus to not give them again
                if len(refs) > 0 and not user.hasMadeFirstDeposit:
                    fast_boost_time = user.joined + timedelta(hours=24)
                    # db_referrals = await session.exec(select(UserReferral).where(UserReferral.userId == referring_user.userId).where(UserReferral.level == 1))
                    # referrals = db_referrals.all()

                    paid_users = []
                    for u in refs:
                        ref_db = await session.exec(select(User).where(User.userId == u.userId))
                        referrer = ref_db.first()
                        if referrer and referrer.staking.deposit >= Decimal(1):
                            paid_users.append(u)

                    if user.joined < fast_boost_time and len(paid_users) >= 2:
                        user.wallet.totalFastBonus += Decimal(1.00)
                        user.staking.deposit += Decimal(1.00)
                        user.hasMadeFirstDeposit = True

                    await session.commit()
                    await session.refresh(user)

                # ###### CHECK IF THE REFERRING USER HAS A REFERRER THEN REPEAT THE PROCESS AGAIN
            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()

async def fetch_sui_balance():
    async with get_session_context() as session:
        session: AsyncSession = session
        try:
            now = datetime.now()
            user_db = await session.exec(select(User).where(User.isBlocked == False))
            users = user_db.all()

            for user in users:
                LOGGER.debug(f"checking here stake: {user}")
                await user_services.stake_sui(user, session)
                LOGGER.debug(f"finished stake check ------------------------------------")
            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()

async def check_ranking():
    async with get_session_context() as session:
        session: AsyncSession = session
        now = datetime.now()

        user_db = await session.exec(select(User).where(User.isBlocked == False))
        users = user_db.all()

        for user in users:
            if user.wallet:
                rankErning, rank = await get_rank(user.totalTeamVolume, user.wallet.totalDeposit, user.totalReferrals)
                LOGGER.debug(f"{user.firstName}:- Ranking: {rankErning} | Rank: {rank}")
                user.rank = rank
                user.wallet.weeklyRankEarnings = rankErning
                LOGGER.debug(f"confirm lastEarning date: {user.lastRankEarningAddedAt}")
                LOGGER.debug(f"confirm user rank: {user.rank}")
                LOGGER.debug(f"confirm weekly rank earning: {user.wallet.weeklyRankEarnings}")
                await session.commit()

                if user.lastRankEarningAddedAt and now.date() == user.lastRankEarningAddedAt.date():
                    LOGGER.debug("confirm dates")
                    user.wallet.earnings += Decimal(user.wallet.weeklyRankEarnings)
                    user.wallet.totalRankBonus += Decimal(user.wallet.weeklyRankEarnings)
                    user.wallet.expectedRankBonus += Decimal(user.wallet.weeklyRankEarnings)
                    # Update lastRankEarningAddedAt to reflect the latest calculation
                    user.lastRankEarningAddedAt = now + timedelta(days=7)

                await session.commit()
                await session.refresh(user)

if __name__ == "__main__":
    asyncio.run(run_cncurrent_tasks())
