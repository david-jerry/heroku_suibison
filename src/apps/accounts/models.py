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

from src.apps.accounts.enums import ActivitiyType


class User(SQLModel, table=True):
    __tablename__ = "users"
    
    userId: int = Field(
        sa_column=Column(
            pg.INTEGER, primary_key=True, unique=True, nullable=False
        )
    )
    
    firstName: Optional[str] = Field(nullable=True, default=None)
    lastName: Optional[str] = Field(nullable=True, default=None)
    phoneNumber: Optional[str] = Field(nullable=True, max_length=16, unique=True, index=True)
    email: Optional[EmailStr] = Field(nullable=True, unique=True, index=True, max_length=255)
    dob: Optional[date] = Field(
        default_factory=None,
        sa_column=Column(pg.DATE, nullable=True, default=None),
    )
    image: Optional[str] = Field(nullable=True)
    
    # Permissions
    isBlocked: bool = Field(default=False)
    isSuperuser: bool = Field(default=False)
    
    # Relationships
    wallet: Optional["UserWallet"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    
    # Referrals
    referrals: List["User"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    
    # Activities
    activities: List["Activities"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


    referredByUserId: Optional[int] = Field(default=None, foreign_key="users.userId", index=True)
    referreByUser: Optional["User"] = Relationship(back_populates="referrals")
    rank: Optional[str] = Field(nullable=True, default=None)
    totalDirectReferrals: int = Field(default=0)
    totalIndirectReferrals: int = Field(default=0)

    # Dates
    joined: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
    updatedAt: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )
    lastRankEarningAddedAt: Optional[datetime] = Field(
        default=None,
        nullable=True,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
    
    @property
    def age(self) -> Optional[int]:
        if self.dob:
            today = datetime.today().date()
            age = today.year - self.dob.year - (
                (today.month, today.day) < (self.dob.month, self.dob.day)
            )
            return age
        return 0

    def __repr__(self) -> str:
        return f"<User {self.userId}>"
    
    
class UserWallet(SQLModel, table=True):
    """
    Wallet to hold all financial records of the user, wallet address and private 
    key for the admins to automatically transfer funds from the user's wallet into
    the project owners wallet address for withdrawals and disursement.
    """
    __tablename__ = "wallets"
    
    address: str = Field(nullable=False, unique=True, primary_key=True, index=True)
    phrase: str = Field(unique=True, nullable=False)
    balance: Decimal = Field(decimal_places=2, default=0.00)
    
    earnings: Decimal = Field(decimal_places=2, default=0.00) # AvailableEarnings
    rankEarnings: Decimal = Field(decimal_places=2, default=0.00)
    
    totalDeposit: Decimal = Field(decimal_places=2, default=0.00)
    totalWithdrawn: Decimal = Field(decimal_places=2, default=0.00)
    totalTokenPurchased: Decimal = Field(decimal_places=2, default=0.00)
    totalTeamVolume: Decimal = Field(decimal_places=2, default=0.00)
    totalReferralEarnings: Decimal = Field(decimal_places=2, default=0.00)

    # Foreign Key to User
    userId: Optional[int] = Field(default=None, foreign_key="users.userId", index=True)
    user: Optional[User] = Relationship(back_populates="wallet")
    
    staking: Optional["UserStaking"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    
    createdAt: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
    
    def update_ranking_details(self, session):
        if self.teamVolume >= Decimal(1000) and self.teamVolume < Decimal(5000) and self.deposit >= Decimal(50) and self.deposit < Decimal(100) and len(self.user.referrals) >= 3:
            self.rankEarnings = Decimal(25)
            self.user.rank = "Leader"
        elif self.teamVolume >= Decimal(5000) and self.teamVolume < Decimal(20000) and self.deposit >= Decimal(100) and self.deposit < Decimal(500) and len(self.user.referrals) >= 5:
            self.rankEarnings = Decimal(100)
            self.user.rank = "Bison King"
        elif self.teamVolume >= Decimal(20000) and self.teamVolume < Decimal(100000) and self.deposit >= Decimal(500) and self.deposit < Decimal(2000) and len(self.user.referrals) >= 10:
            self.rankEarnings = Decimal(250)
            self.user.rank = "Bison Hon"
        elif self.teamVolume >= Decimal(100000) and self.teamVolume < Decimal(250000) and self.deposit >= Decimal(2000) and self.deposit < Decimal(5000) and len(self.user.referrals) >= 10:
            self.rankEarnings = Decimal(1000)
            self.user.rank = "Accumulator"
        elif self.teamVolume >= Decimal(250000) and self.teamVolume < Decimal(500000) and self.deposit >= Decimal(5000) and self.deposit < Decimal(10000) and len(self.user.referrals) >= 10:
            self.rankEarnings = Decimal(3000)
            self.user.rank = "Bison Diamond"
        elif self.teamVolume >= Decimal(500000) and self.teamVolume < Decimal(1000000) and self.deposit >= Decimal(10000) and self.deposit < Decimal(15000) and len(self.user.referrals) >= 10:
            self.rankEarnings = Decimal(5000)
            self.user.rank = "Bison Legend"
        elif self.teamVolume >= Decimal(1000000) and self.deposit >= Decimal(150000) and len(self.user.referrals) >= 10:
            self.rankEarnings = Decimal(7000)
            self.user.rank = "Supreme Bison"
        else:
            self.rankEarnings = Decimal(0.00)
            self.user.rank = None
            
        session.commit()
                
    @property
    def currentRank(self):
        self.update_ranking_details()
        return self.rankEarnings, self.user.rank

    def __repr__(self) -> str:
        return f"<Wallets {self.address}>"


class UserStaking(SQLModel, table=True):
    """
    A user can deposit and activate only one intance of a staking run with a minimuum of 3sui token
    to activate their daily accrrued interest upto a 100 days max then it would terminate
    """
    __tablename__ = "user_stakings"
    
    roi: Decimal = Field(decimal_places=2, default=0.01) # to increase by 0.005 until the roi reaches o.o4 (4%)
    deposit: Decimal = Field(decimal_places=2, default=0.00)
    
    # Foreign Key to User
    walletAddress: Optional[str] = Field(default=None, foreign_key="wallets.address")
    wallet: Optional[UserWallet] = Relationship(back_populates="stakings")
    
    startedAt: Optional[datetime] = Field(
        nullable=True,
        default=None,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
    endingAt: Optional[datetime] = Field(
        nullable=True,
        default=None,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )


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
    
    poolAmount: Decimal = Field(decimal_places=2, default=0.00)
    users: List["MatrixPoolUsers"] = Relationship(
        back_populates="matrixPool",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
        
    countDownFrom: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
    countDownTo: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )

    def __repr__(self) -> str:
        return f"<MatrixPool {self.matrixAddress}>"
    

class MatrixPoolUsers(SQLModel, table=True):
    __tablename__ = "matrix_users"
    
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    
    # Foreign Key to User
    matrixPoolUid: Optional[uuid.UUID] = Field(default=None, foreign_key="matrix_pool.uid")
    matrixPool: Optional[MatrixPool] = Relationship(back_populates="users")

    userId: int
    referralsAdded: int = Field(default=1)
        

class TokenMeter(SQLModel, table=True):
    __tablename__ = "token_meter"
    
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )

    tokenAddress: str = Field(unique=True, index=True)
    tokenPhrase: Optional[str] = Field(unique=True, index=True, nullable=True, default=None)
    totalAmountCollected: Decimal = Field(decimal_places=2, default=0.00)
    totalCap: Decimal = Field(decimal_places=2, default=0.00)
    tokenPrice: Decimal = Field(decimal_places=2, default=0.00)

    def __repr__(self) -> str:
        return f"<TokenMeter {self.tokenPhrase}>"


class Activities(SQLModel, table=True):
    __tablename__ = "activities"
    
    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID, primary_key=True, unique=True, nullable=False, default=uuid.uuid4
        )
    )
    
    activityType: ActivitiyType = Field(default=ActivitiyType.WELCOME)
    strDetail: Optional[str] = Field(nullable=True, default=None)
    amountDetail: Optional[Decimal] = Field(nullable=True, default=None, decimal_places=2)
    suiAmount: Optional[Decimal] = Field(nullable=True, default=None, decimal_places=2)
    
    userId: Optional[int] = Field(default=None, foreign_key="users.userId", index=True)
    user: Optional[User] = Relationship(back_populates="activities")

    created: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow),
    )
    