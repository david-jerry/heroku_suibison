from enum import Enum


class ActivityType(str, Enum):
    DEPOSIT = "Deposit"
    WITHDRAWAL = "Withdrawal"
    RANKING = "New Ranking"
    REFERRAL = "New Active Referral"
    FASTBONUS = "Fast Bonus Activated"
    MATRIXPOOL = "GMP Payout"
    MATRIXPOOLTOPUP = "GMP Top Up"
    TOKENPURCHASE = "Purchased Token"
    WELCOME = "WELCOME"
    REFERRALBONUS = "Referral Bonus"

    @classmethod
    def from_str(cls, enum: str) -> "ActivityType":
        try:
            return cls(enum)
        except ValueError:
            raise ValueError(f"'{enum}' is not a valid ActivityType")
