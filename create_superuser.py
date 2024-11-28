import asyncio
from datetime import datetime, timedelta
import uuid
from fastapi import Request
from passlib.context import CryptContext
from sqlmodel import select
from src.apps.accounts.enum import ActivityType
from src.apps.accounts.models import Activities, User
from src.apps.accounts.services import UserServices
from src.db.engine import get_session
from src.errors import ReferrerNotFound
from src.utils.hashing import createAccessToken
from src.utils.logger import LOGGER

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

user_services = UserServices()

# Function to get user input asynchronously
async def get_input(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)

# Function to hash password asynchronously
async def hash_password(password: str) -> str:
    return await asyncio.to_thread(pwd_context.hash, password)

async def create_superuser():
    async for session in get_session():
        # Get user input asynchronously
        userId = await get_input("Enter userId for superuser: ")
        password = await get_input("Enter password for superuser: ")

        # Check if user already exists
        result = await session.exec(
            select(User).where(User.userId == userId)
        )
        existing_user = result.first()

        if existing_user:
            LOGGER.info(f"User with userId {userId} already exists.")
            return

        # Hash password asynchronously
        hashed_password = await hash_password(password)

        # Create superuser
        superuser = User(
            uid=uuid.uuid4(),
            userId=userId,
            passwordHash=hashed_password,
            isSuperuser=True,
            isAdmin=True,
        )

        session.add(superuser)
        
        stake = await user_services.create_staking_account(superuser, session)
        LOGGER.debug(f"Stake:: {stake}")
        # Create an activity record for this new user
        new_activity = Activities(activityType=ActivityType.WELCOME, strDetail="Welcome to SUI-Bison", userUid=superuser.uid)
        session.add(new_activity)
        
        new_wallet = await user_services.create_wallet(superuser, session)
        LOGGER.debug(f"NEW WALLET:: {new_wallet}")
        
        try:
            await user_services.create_referrer("6773082668", superuser, session)
            LOGGER.debug("Created Referral")
        except ReferrerNotFound:
            pass
        # generate access and refresh token so long the telegram init data is valid
        await session.commit()
        await session.refresh(superuser)
        LOGGER.info(f"Superuser {userId} created successfully.")

if __name__ == "__main__":
    asyncio.run(create_superuser())