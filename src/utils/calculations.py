from decimal import Decimal
from typing import List


from src.apps.accounts.models import MatrixPoolUsers, UserReferral
from src.db.redis import get_sui_usd_price
from src.utils.logger import LOGGER


def get_rank(tteamVolume: Decimal, tdeposit: Decimal, referrals: Decimal, usd__price):
    rank_earnings = Decimal(0.00)
    rank = None

    team_volume = tteamVolume * usd__price
    deposit = tdeposit * usd__price

    ranks = [
        {
            "name": "Leader",
            "min_volume": Decimal(1000),
            "max_volume": Decimal(5000),
            "min_deposit": Decimal(50),
            "min_referrals": 3,
            "earnings": Decimal(25),
        },
        {
            "name": "Bison King",
            "min_volume": Decimal(5000),
            "max_volume": Decimal(20000),
            "min_deposit": Decimal(100),
            "min_referrals": 5,
            "earnings": Decimal(100),
        },
        {
            "name": "Bison Hon",
            "min_volume": Decimal(20000),
            "max_volume": Decimal(100000),
            "min_deposit": Decimal(500),
            "min_referrals": 10,
            "earnings": Decimal(250),
        },
        {
            "name": "Accumulator",
            "min_volume": Decimal(100000),
            "max_volume": Decimal(250000),
            "min_deposit": Decimal(2000),
            "min_referrals": 10,
            "earnings": Decimal(1000),
        },
        {
            "name": "Bison Diamond",
            "min_volume": Decimal(250000),
            "max_volume": Decimal(500000),
            "min_deposit": Decimal(5000),
            "min_referrals": 10,
            "earnings": Decimal(3000),
        },
        {
            "name": "Bison Legend",
            "min_volume": Decimal(500000),
            "max_volume": Decimal(1000000),
            "min_deposit": Decimal(10000),
            "min_referrals": 10,
            "earnings": Decimal(5000),
        },
        {
            "name": "Supreme Bison",
            "min_volume": Decimal(1000000),
            "max_volume": None,  # No upper limit for this rank
            "min_deposit": Decimal(150000),
            "min_referrals": 10,
            "earnings": Decimal(7000),
        },
    ]

    for r in ranks:
        if (
            team_volume >= r["min_volume"]
            and (r["max_volume"] is None or team_volume < r["max_volume"])
            and deposit >= r["min_deposit"]
            and referrals >= r["min_referrals"]
        ):
            rank = r["name"]
            rank_earnings = r["earnings"]

        elif rank is not None:
            break

    if rank:
        rank_earnings = rank_earnings / usd__price

    return rank_earnings, rank

async def matrix_share(matrixUser: MatrixPoolUsers):
    percentageShare = ( matrixUser.referralsAdded / matrixUser.matrixPool.totalReferrals) * 100
    earning = matrixUser.matrixPool.raisedPoolAmount * Decimal(percentageShare / 100)
    return Decimal(percentageShare), earning
