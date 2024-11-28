from datetime import date, datetime
from decimal import Decimal
from pydantic import AnyHttpUrl, EmailStr, FileUrl, IPvAnyAddress
from pydantic_extra_types.payment import PaymentCardBrand, PaymentCardNumber
from sqlmodel import SQLModel, Field, Relationship, Column
import sqlalchemy.dialects.postgresql as pg
import uuid
from typing import List, Optional
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.country import CountryInfo

from src.apps.accounts.enum import ActivityType


class CeleryBeat(SQLModel, table=True):
    __tablename__ = "celery_beat"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, primary_key=True, unique=True, nullable=False)
    )

    task_name: str = Field(max_length=500, nullable=False, description="Name of the task")
    # task_sig: str = Field(max_length=500, nullable=True, description="Signature for the task")
    task_args: Optional[str] = Field(default="{}", max_length=500, description="JSON-formatted task arguments")
    task_kwargs: Optional[str] = Field(default="{}", max_length=500, description="JSON-formatted task keyword arguments")
    crontab: str = Field(max_length=200, nullable=False, description="Cron expression for scheduling")
    schedule_type: str = Field(max_length=50, nullable=False, description="Type of schedule (e.g., daily, weekly)")

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(
        pg.TIMESTAMP, nullable=False, onupdate=datetime.utcnow), description="Record last update timestamp")

    def __repr__(self) -> str:
        return f"<CeleryBeat uid={self.uid}, task_name={self.task_name}, schedule_type={self.schedule_type}>"


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, primary_key=True, unique=True, nullable=False)
    )

    userId: str = Field(max_length=12, nullable=False, description="Telegram user ID", index=True)
    firstName: Optional[str] = Field(max_length=255, nullable=True, default=None,
                                     description="Telegram user saved First Name")
    lastName: Optional[str] = Field(max_length=255, nullable=True, default=None,
                                    description="Telegram user saved Last Name")
    phoneNumber: Optional[str] = Field(max_length=14, nullable=True, default=None,
                                       description="Telegram user saved Phone Nmber")
    dob: Optional[date] = Field(
        default_factory=None,
        sa_column=Column(pg.DATE, nullable=True, default=None),
        description="Telegram user saved date of birth"
    )
    image: Optional[str] = Field(nullable=True, default=None, description="Telegram user saved Image")
    passwordHash: str = Field(nullable=True)

    # Permissions
    isBlocked: bool = Field(default=False, description="When a user violates the rules of the project they get banned")
    usedSpeedBoost: bool = Field(default=False, nullable=True,
                                 description="If a user has enabled their speed boost then they would no longer need it")
    isAdmin: bool = Field(default=False)
    isSuperuser: bool = Field(default=False, description="A superuser permission")
    hasMadeFirstDeposit: bool = Field(
        default=False, nullable=False, description="Checks if the user being a referral in this case has made an initial deposit to credit the ")
    isMakingFirstDeposit: bool = Field(nullable=True, default=True)
    
    # rank
    rank: Optional[str] = Field(max_length=150, nullable=True, default=None)
    # totalTeamVolume will be returnd in the schema instead of storing on the database
    totalTeamVolume: Decimal = Field(default=Decimal(0), decimal_places=9)
    # totalReferrals will also be stored in the schema instead of in the database
    totalReferrals: Decimal = Field(default=Decimal(0), decimal_places=9)
    totalReferralsStakes: Decimal = Field(default=Decimal(0), decimal_places=9, nullable=True)
    # totalNetwork likewise
    totalNetwork: int = Field(default=Decimal(0), sa_column=Column(pg.BIGINT, nullable=False))

    # referral
    referrer: Optional["UserReferral"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    referrer_id: uuid.UUID = Field(nullable=True, foreign_key="users.uid")

    # Activities
    activities: List["Activities"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    # Wallet
    wallet: Optional["UserWallet"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    # user staking
    staking: Optional["UserStaking"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    # failed transactions
    pendingTransactions: List["PendingTransactions"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    joined: datetime = Field(default_factory=datetime.utcnow, nullable=False, description="Record creation timestamp")
    lastRankEarningAddedAt: datetime = Field(default_factory=datetime.utcnow,
                                             nullable=False, description="Last earning calculation timestamp")
    updatedAt: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(
        pg.TIMESTAMP, nullable=False, onupdate=datetime.utcnow), description="Record last update timestamp")

    def __repr__(self) -> str:
        return f"<User {self.userId}>"


class UserReferral(SQLModel, table=True):
    """Get the referring user and store the referral of a new user into this model with their level to determine who was addded"""
    __tablename__ = "referrals"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, primary_key=True, unique=True, nullable=False)
    )

    level: int = Field(default=1, nullable=True)

    theirUserId: str = Field(nullable=True)
    userId: Optional[str] = Field(default=None, nullable=True)
    name: Optional[str] = Field(default=None, nullable=True, max_length=255)
    reward: Decimal = Field(default=Decimal(0.00), decimal_places=9, nullable=True)
    stake: Decimal = Field(default=Decimal(0.00), decimal_places=9, nullable=True)
    userUid: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional["User"] = Relationship(back_populates="referrer")
    created: datetime = Field(default_factory=datetime.utcnow, nullable=True, description="Record creation timestamp")

    def __repr__(self) -> str:
        return f"<UserReferral {self.userUid}>"


class UserWallet(SQLModel, table=True):
    """
    Wallet to hold all financial records of the user, wallet address and private
    key for the admins to automatically transfer funds from the user's wallet into
    the project owners wallet address for withdrawals and disursement.
    """
    __tablename__ = "wallets"

    uid: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, primary_key=True, unique=True, nullable=False)
    )

    address: str = Field(nullable=False, unique=True, index=True)
    phrase: str = Field(unique=True, nullable=False)
    privateKey: str = Field(unique=True, nullable=False)

    balance: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    pendingBalance: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    earnings: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    availableReferralEarning: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    expectedRankBonus: Decimal = Field(decimal_places=9, default=Decimal(0.00))

    weeklyRankEarnings: Decimal = Field(decimal_places=9, default=Decimal(0.00))

    totalDeposit: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalTokenPurchased: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalRankBonus: Decimal = Field(decimal_places=9, default=Decimal(0))
    totalFastBonus: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalWithdrawn: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalReferralBonus: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalReferralEarnings: Decimal = Field(decimal_places=9, default=Decimal(0), nullable=True)

    # Foreign Key to User
    userUid: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional[User] = Relationship(back_populates="wallet")

    createdAt: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )

    def __repr__(self) -> str:
        return f"<Wallets {self.address}>"


class PendingTransactions(SQLModel, table=True):
    __tablename__ = "peending_transactions"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    amount: Decimal = Field(decimal_places=9, default=0.00)
    # Foreign Key to User
    userUid: Optional[uuid.UUID] = Field(default=None, nullable=True, foreign_key="users.uid")
    user: Optional[User] = Relationship(back_populates="pendingTransactions")
    commpleted: bool = Field(default=False)



class UserStaking(SQLModel, table=True):
    """
    A user can deposit and activate only one intance of a staking run with a minimuum of 3sui token
    to activate their daily accrrued interest upto a 100 days max then it would terminate
    """
    __tablename__ = "user_stakings"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    roi: Decimal = Field(decimal_places=2, default=Decimal(0.01))
    deposit: Decimal = Field(decimal_places=9, default=Decimal(0))

    # Foreign Key to User
    userUid: Optional[uuid.UUID] = Field(default=None, foreign_key="users.uid")
    user: Optional[User] = Relationship(back_populates="staking")

    start: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, default=None, nullable=True),
    )

    end: Optional[datetime] = Field(
        sa_column=Column(pg.TIMESTAMP, default=None, nullable=True),
    )
    nextRoiIncrease: Optional[datetime] = Field(
        sa_column=Column(pg.TIMESTAMP, default=None, nullable=True),
    )

    def __repr__(self) -> str:
        return f"<Stakes {self.user}>"


class MatrixPool(SQLModel, table=True):
    """
    This takes from the user withdrawals and only when the user has made a direct
    referral before they qualify to have a share in the matrix pool and based on
    their share the money would be withdrawn into their earnings balance for them
    to withdraw whenever they desire.
    """
    __tablename__ = "matrix_pool"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    raisedPoolAmount: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalReferrals: int = 0

    users: List["MatrixPoolUsers"] = Relationship(
        back_populates="matrixPool",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    startDate: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
    endDate: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )

    def __repr__(self) -> str:
        return f"<MatrixPool {self.matrixAddress}>"


class MatrixPoolUsers(SQLModel, table=True):
    """
    For every matrix pool run users who purchase the share by adding their referrals
    gets instant stakes to the claims here
    """
    __tablename__ = "matrix_users"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    # Foreign Key to active matrixPool
    matrixPoolUid: Optional[uuid.UUID] = Field(default=None, foreign_key="matrix_pool.uid")
    matrixPool: Optional[MatrixPool] = Relationship(back_populates="users")
    position: Optional[int] = Field(nullable=True, default=0)
    name: Optional[str] = Field(nullable=True, default=None)

    userId: str
    referralsAdded: int = Field(default=1)

    matrixEarninig: Decimal = Field(decimal_places=9, default=Decimal(0))
    matrixShare: Decimal = Field(decimal_places=2, default=Decimal(0))

    def __repr__(self) -> str:
        return f"<MatrixPoolUser {self.matrixPool} - {self.endDate}>"


class TokenMeter(SQLModel, table=True):
    __tablename__ = "token_meter"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    tokenAddress: Optional[str] = Field(unique=True, index=True, nullable=True, default=None)
    tokenPhrase: Optional[str] = Field(unique=True, index=True, nullable=True, default=None)
    tokenPrivateKey: Optional[str] = Field(unique=True, index=True, nullable=True, default=None)
    totalAmountCollected: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalCap: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    tokenPrice: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    suiUsdPrice: Decimal = Field(decimal_places=9, default=Decimal(0.00))
    totalDeposited: Decimal = Field(decimal_places=9, default=Decimal(0))
    totalWithdrawn: Decimal = Field(decimal_places=9, default=Decimal(0))
    totalSentToGMP: Decimal = Field(decimal_places=9, default=Decimal(0))
    totalDistributedByGMP: Decimal = Field(decimal_places=9, default=Decimal(0))

    def __repr__(self) -> str:
        return f"<TokenMeter {self.tokenAddress}>"


class Activities(SQLModel, table=True):
    __tablename__ = "activities"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    activityType: ActivityType = Field(default=ActivityType.WELCOME)
    strDetail: Optional[str] = Field(nullable=True, default=None,
                                     description="This is to store the ranking information which is a string")
    amountDetail: Optional[Decimal] = Field(nullable=True, default=None, decimal_places=9,
                                            description="This stores the dollar equivalent of the sui value if the activity type is not a welcome, ranking, new referral")
    suiAmount: Optional[Decimal] = Field(nullable=True, default=None, decimal_places=9)

    userUid: uuid.UUID = Field(foreign_key="users.uid")
    user: User = Relationship(back_populates="activities")

    created: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
