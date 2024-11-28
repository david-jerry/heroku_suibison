from decimal import Decimal
from typing import List


from src.apps.accounts.models import MatrixPoolUsers, UserReferral
from src.db.redis import get_sui_usd_price
from src.utils.logger import LOGGER


async def get_rank(tteamVolume: Decimal, tdeposit: Decimal, referrals: List[UserReferral]):
    usd__price = await get_sui_usd_price()
    rankEarnings = Decimal(0.00)
    rank = None
    
    teamVolume = tteamVolume * usd__price
    deposit = tdeposit * usd__price
    
    LOGGER.debug(f"teamVolume: {teamVolume}")
    LOGGER.debug(f"deposit: {deposit}")
    
    if teamVolume >= Decimal(1000) and teamVolume < Decimal(5000) and deposit >= Decimal(50) and len(referrals) >= 3:
        rankEarnings = Decimal(25)
        rank = "Leader"
    elif teamVolume >= Decimal(5000) and teamVolume < Decimal(20000) and deposit >= Decimal(100) and len(referrals) >= 5:
        rankEarnings = Decimal(100)
        rank = "Bison King"
    elif teamVolume >= Decimal(20000) and teamVolume < Decimal(100000) and deposit >= Decimal(500) and len(referrals) >= 10:
        rankEarnings = Decimal(250)
        rank = "Bison Hon"
    elif teamVolume >= Decimal(100000) and teamVolume < Decimal(250000) and deposit >= Decimal(2000) and len(referrals) >= 10:
        rankEarnings = Decimal(1000)
        rank = "Accumulator"
    elif teamVolume >= Decimal(250000) and teamVolume < Decimal(500000) and deposit >= Decimal(5000) and len(referrals) >= 10:
        rankEarnings = Decimal(3000)
        rank = "Bison Diamond"
    elif teamVolume >= Decimal(500000) and teamVolume < Decimal(1000000) and deposit >= Decimal(10000) and len(referrals) >= 10:
        rankEarnings = Decimal(5000)
        rank = "Bison Legend"
    elif teamVolume >= Decimal(1000000) and deposit >= Decimal(150000) and len(referrals) >= 10:
        rankEarnings = Decimal(7000)
        rank = "Supreme Bison"

    return rankEarnings, rank

async def matrix_share(matrixUser: MatrixPoolUsers):
    percentageShare = (matrixUser.matrixPool.totalReferrals / matrixUser.referralsAdded) * 100
    earning = matrixUser.matrixPool.raisedPoolAmount * Decimal(percentageShare / 100)
    return Decimal(percentageShare), earning