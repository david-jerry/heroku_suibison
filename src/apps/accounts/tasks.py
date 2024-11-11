from datetime import datetime, timedelta
from decimal import Decimal
from celery import shared_task
from sqlmodel.ext.asyncio.session import AsyncSession

from src.apps.accounts.models import UserStaking

@shared_task
async def calculate_and_update_staked_interest_every_5_days(session: AsyncSession, stake: UserStaking):
    """
    This task calculates and updates the interest on a stake until its expiry date.

    Args:
        session: The database session object.
        stake: The UserStaking object representing the stake.
    """
    remaining_days = (stake.endingAt - datetime.now()).days
    
    # loop this task until staking expiry date has reached then stop it
    while remaining_days > 0:
        # calculate interest based on remaining days
        if remaining_days < 95 and stake.roi <= Decimal(0.04):
            new_roi = stake.roi + Decimal(0.005)
            interest_earned = stake.deposit * new_roi
             
            
