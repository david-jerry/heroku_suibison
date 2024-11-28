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
    async with asyncio.TaskGroup() as group:
        group.create_task(fetch_sui_price())
        group.create_task(add_fast_bonus())
        group.create_task(fetch_sui_balance())

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
        try:
            now = datetime.now()
            user_db = await session.exec(select(User).where(User.isBlocked == False))
            users: List[User] = user_db.all()
            
            LOGGER.debug(f"FASTBONUSTASK: {users}")

            for user in users:
                LOGGER.debug(user.userId)
                ref_db = await session.exec(select(UserReferral).where(UserReferral.userId == user.userId).where(UserReferral.level == 1))
                refs: List[UserReferral] = ref_db.all()

                if len(refs) > 0:
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
                        
                    await session.commit()
                    await session.refresh(user)

                # ###### CHECK IF THE REFERRING USER HAS A REFERRER THEN REPEAT THE PROCESS AGAIN
            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()

async def fetch_sui_balance():
    async with get_session_context() as session:
        try:
            now = datetime.now()
            user_db = await session.exec(select(User).where(User.isBlocked == False))
            users = user_db.all()

            for user in users:
                LOGGER.debug(f"checking here: {user}")
                await user_services.stake_sui(user, session)
            await session.close()
        except Exception as e:
            LOGGER.error(e)
            await session.close()


if __name__ == "__main__":
    asyncio.run(run_cncurrent_tasks())