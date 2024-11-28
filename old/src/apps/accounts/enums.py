from enum import Enum


class ActivitiyType(str, Enum):
    DEPOSIT = "Deposit"
    WITHDRAWAL = "Withdrawal"
    RANKING = "New Ranking"
    REFERRAL = "New Active Referral"
    FASTBONUS = "Fast Bonus Activated"
    MATRIXPOOL = "GMP"
    WELCOME = "WELCOME"

    @classmethod
    def from_str(cls, enum: str) -> "ActivitiyType":
        try:
            return cls(enum)
        except ValueError:
            raise ValueError(f"'{enum}' is not a valid ActivitiyType")
        