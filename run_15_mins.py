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
    await calculate_users_matrix_pool_share()
    await check_ranking()


async def calculate_users_matrix_pool_share():
    async with get_session_context() as session:
        session: AsyncSession = session
        try:
            now = datetime.now()
            # ###### CALCULATE USERS SHARE TO AN ACTIVE POOL
            matrix_db = await session.exec(select(MatrixPool).where(MatrixPool.endDate >= now))
            active_matrix_pool_or_new = matrix_db.first()

            if active_matrix_pool_or_new:
                payoutTime = active_matrix_pool_or_new.endDate - timedelta(minutes=4)
                mp_users_db = await session.exec(select(MatrixPoolUsers).where(MatrixPoolUsers.matrixPoolUid == active_matrix_pool_or_new.uid).order_by(MatrixPoolUsers.referralsAdded))
                mp_users = mp_users_db.all()

                position = len(mp_users) + 1
                for mp_user in mp_users:
                    position -= 1
                    mp_user.position = position

                    mpu_db = await session.exec(select(User).where(User.userId == mp_user.userId))
                    mpu: Optional[User] = mpu_db.first()
                    name = mp_user.userId
                    if mpu.firstName:
                        name = mpu.firstName
                    elif mpu.lastName:
                        name = mpu.lastName

                    if mp_user.name is None:
                        mp_user.name = name

                    percentage, earning = await matrix_share(mp_user)
                    # mp_user.matrixShare = percentage
                    mp_user.matrixEarninig = earning
                    if now >= payoutTime:
                        mpu.wallet.earnings += earning
                        mpu.wallet.availableReferralEarning += earning
                        mpu.wallet.totalReferralEarnings += earning

                        sevenDaysLater = now + timedelta(days=7)

                        new_pool = MatrixPool(
                            raisedPoolAmount=Decimal(0), startDate=now, endDate=sevenDaysLater
                        )
                        session.add(new_pool)

                    await session.commit()
                    await session.refresh(mp_user)
            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()

async def fetch_sui_price():
    try:
        sui = yf.Ticker("SUI20947-USD")
        rate = sui.fast_info.last_price
        LOGGER.debug(f"SUI Price: {rate}")
        await redis_client.set("sui_price", rate)
    except Exception as e:
        LOGGER.error(e)

def find_original_deposit(deposit: Decimal):
    percentage = Decimal(0.1)
    number = deposit / (1 - percentage)
    return number

async def add_fast_bonus():
    async with get_session_context() as session:
        session: AsyncSession = session
        try:
            user_db = await session.exec(select(User).where(User.isBlocked == False).where(User.isAdmin == False).where(User.hasMadeFirstDeposit == False))
            users = user_db.all()

            for user in users:
                LOGGER.info(f"FASTBONUSTASK: {user.userId}")

                deducted_token_purchase_amount = find_original_deposit(user.staking.deposit)
                fast_bonus_deadline = user.joined + timedelta(hours=24)
                has_minimum_deposit = deducted_token_purchase_amount >= Decimal(1)
                now = datetime.now()

                LOGGER.debug(f'Looking hererererererrer: 1:: {fast_bonus_deadline} {has_minimum_deposit} {deducted_token_purchase_amount}')
                if now > fast_bonus_deadline or not has_minimum_deposit:
                    continue

                ref_db = await session.exec(select(UserReferral).where(UserReferral.userId == user.userId).where(UserReferral.level == 1))
                refs = ref_db.all()

                LOGGER.debug("Looking herererer: 2")
                if len(refs) < 2:
                    continue

                active_referrals = []
                for u in refs:
                    ref_db = await session.exec(select(User).where(User.userId == u.userId))
                    referral = ref_db.first()
                    if referral and find_original_deposit(referral.staking.deposit) >= Decimal(1):
                        active_referrals.append(u)

                LOGGER.debug(f"Looking herererer: 3: {active_referrals}")

                if len(active_referrals) < 2:
                    continue

                user.wallet.totalFastBonus += Decimal(1.00)
                user.staking.deposit += Decimal(1.00)
                user.hasMadeFirstDeposit = True

                await session.commit()
                await session.refresh(user)

            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()

async def fetch_sui_balance():
    async with get_session_context() as session:
        session: AsyncSession = session
        try:
            now = datetime.now()
            user_db = await session.exec(select(User).where(User.isBlocked == False).where(User.isAdmin == False))
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

        user_db = await session.exec(select(User).where(User.isBlocked == False).where(User.isAdmin == False))
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
