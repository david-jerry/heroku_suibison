from decimal import Decimal
import uuid
from fastapi import File, UploadFile
from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, FileUrl, IPvAnyAddress, constr, model_validator, root_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_extra_types.routing_number import ABARoutingNumber
from pydantic_extra_types.payment import PaymentCardBrand, PaymentCardNumber
from pydantic_extra_types.country import CountryInfo

from datetime import date, datetime
from typing import Optional, List, Annotated

from src.apps.accounts.enums import ActivitiyType


class Message(BaseModel):
    message: str
    error_code: str


class DeleteMessage(BaseModel):
    message: str

class AccessToken(BaseModel):
    message: str
    access_token: str
    user: Optional["UserRead"] = None
    
class RegAndLoginResponse(BaseModel):
    meessage: str
    accessToken: str
    refreshToken: str
    user: "UserRead"

class Coin(BaseModel):
    coinType: str
    coinObjectId: str
    version: str
    digest: str
    balance: str
    previousTransaction: str
    
    
class CoinBalance(BaseModel):
    coinType: str
    coinObjectCount: int
    totalBalance: str
    lockedBalance: any
    
    
class MetaData(BaseModel):
    decimals: int
    name: str
    symbol: str
    description: str
    iconUrl: List[str]
    id: Optional[str]
    
    
class WithdrawEarning(BaseModel):
    wallet_address: str
    
    
class SuiTransferResponse(BaseModel):
    gas: List[any]
    inputObjects: List[any]
    txBytes: any
    

class UserBaseSchema(BaseModel):
    firstName: Annotated[Optional[str], constr(max_length=255)] = None  # First name with max length constraint
    lastName: Annotated[Optional[str], constr(max_length=255)] = None  # Last name with max length constraint
    phoneNumber: Annotated[Optional[str], constr(min_length=10, max_length=14)] = None  # Phone number with length constraints
    email: Optional[EmailStr]  = None # Email with validation

    class Config:
        from_attributes = True  # Allows loading from ORM models like SQLModel


class UserRead(UserBaseSchema):    
    userIId: int
    image: Optional[str] = None
    dob: Optional[date] = None
    rank: Optional[str]
    
    joined: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    lastRankEarningAddedAt: Optional[datetime] = None
    
    totalDirectReferrals: int = 0
    totalIndirectReferrals: int = 0

    isBlocked: bool = False
    isSuperuser: bool = False

    age: Optional[int] = None
    
    wallet: Optional["WalletRead"] = None
    referrals: List["UserRead"]
    
    referredByUserId: Optional[int] = None
    
    @staticmethod
    def get_rank_from_wallet(wallet: "WalletRead"):
        return wallet.rankTitle if wallet is not None else None
        
    @staticmethod
    def calculate_age(dob: Optional[datetime]) -> int:
        if dob:
            today = datetime.today().date()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
            return age
        return 0

    @classmethod
    def from_orm(cls, user: "UserRead"):
        user_dict = user.model_dump()
        user_dict["age"] = cls.calculate_age(user.dob)
        user_dict["rank"] = cls.get_rank_from_wallet(user.wallet)
        return cls(**user_dict)

    class Config:
        from_attributes = True  # Allows loading from ORM models like SQLModel


class UserCreateOrLoginSchema(BaseModel):
    userId: int
    firstName: Annotated[Optional[str], constr(max_length=255)] = None  # First name with max length constraint
    lastName: Annotated[Optional[str], constr(max_length=255)] = None  # Last name with max length constraint
    phoneNumber: Annotated[Optional[str], constr(min_length=10, max_length=14)] = None  # Phone number with length constraints
    image: Optional[str] = None


class UserUpdateSchema(UserBaseSchema):
    dob: Optional[date] = None


class UserLevelReferral(BaseModel):
    userId: int
    referralName: str
    referralId: int
    totalStake: Decimal = 0.00
    level: int
    reward: Decimal
    
    @staticmethod
    def calculate_bonus(level: int, totalStake: Decimal) -> Decimal:
        if level == 1:
            bonus = totalStake * 0.1
            return bonus
        elif level == 2:
            bonus = totalStake * 0.05
            return bonus
        elif level == 3:
            bonus = totalStake * 0.03
            return bonus
        elif level == 4:
            bonus = totalStake * 0.02
            return bonus
        elif level == 5:
            bonus = totalStake * 0.01
            return bonus
        return 0

    @classmethod
    def from_orm(cls, user: "UserLevelReferral"):
        user_dict = user.model_dump()
        user_dict["reward"] = cls.calculate_bonus(user.level, user.totalStake)
        return cls(**user_dict)


class UserWithReferralsRead(BaseModel):
    user: UserRead
    referralsLv1: List[UserLevelReferral]
    referralsLv2: List[UserLevelReferral]
    referralsLv3: List[UserLevelReferral]
    referralsLv4: List[UserLevelReferral]
    referralsLv5: List[UserLevelReferral]
    
    
class WalletBaseSchema(BaseModel):
    address: str
    phrase: str
    
    earnings: Decimal = 0.00
    
    rankEarnings: Decimal = 0.00
    totalDeposit: Decimal = 0.00
    totalWithdrawn: Decimal = 0.00
    totalTokenPurchased: Decimal = 0.00
    totalTeamVolume: Decimal = 0.00
    totalReferralEarnings: Decimal = 0.00
    
    
class WalletRead(WalletBaseSchema):
    created: datetime
    rankTitle: Optional[str] = None
    
    userId: int = None
    user: Optional[UserRead] = None
    staking: Optional["StakingRead"]
    
    createdAt: datetime

    @staticmethod
    def get_rank(teamVolume: Decimal, deposit: Decimal, referrals: List[UserRead]):
        rankEarnings = Decimal(0.00)
        rank = None
        if teamVolume >= Decimal(1000) and teamVolume < Decimal(5000) and deposit >= Decimal(50) and deposit < Decimal(100) and len(referrals) >= 3:
            rankEarnings = Decimal(25)
            rank = "Leader"
        elif teamVolume >= Decimal(5000) and teamVolume < Decimal(20000) and deposit >= Decimal(100) and deposit < Decimal(500) and len(referrals) >= 5:
            rankEarnings = Decimal(100)
            rank = "Bison King"
        elif teamVolume >= Decimal(20000) and teamVolume < Decimal(100000) and deposit >= Decimal(500) and deposit < Decimal(2000) and len(referrals) >= 10:
            rankEarnings = Decimal(250)
            rank = "Bison Hon"
        elif teamVolume >= Decimal(100000) and teamVolume < Decimal(250000) and deposit >= Decimal(2000) and deposit < Decimal(5000) and len(referrals) >= 10:
            rankEarnings = Decimal(1000)
            rank = "Accumulator"
        elif teamVolume >= Decimal(250000) and teamVolume < Decimal(500000) and deposit >= Decimal(5000) and deposit < Decimal(10000) and len(referrals) >= 10:
            rankEarnings = Decimal(3000)
            rank = "Bison Diamond"
        elif teamVolume >= Decimal(500000) and teamVolume < Decimal(1000000) and deposit >= Decimal(10000) and deposit < Decimal(15000) and len(referrals) >= 10:
            rankEarnings = Decimal(5000)
            rank = "Bison Legend"
        elif teamVolume >= Decimal(1000000) and deposit >= Decimal(150000) and len(referrals) >= 10:
            rankEarnings = Decimal(7000)
            rank = "Supreme Bison"
        
        return rankEarnings, rank
        
    @classmethod
    def from_orm(cls, wallet: "WalletRead"):
        wallet_dict = wallet.model_dump()
        rankDetail = cls.get_rank(wallet.teamVolume, wallet.totalDeposit, wallet.user.referrals)
        wallet_dict["rankEarnings"] = rankDetail[0]
        wallet_dict["rankTitle"] = rankDetail[1]
        return cls(**wallet_dict)

    class Config:
        from_attributes = True  # Allows loading from ORM models like SQLModel


class StakingBaseSchema(BaseModel):
    roi: Decimal = 0.00
    deposit: Decimal = 0.00
    

class StakingCreate(BaseModel):
    deposit: Decimal
    
    
class StakingRead(StakingBaseSchema):
    walletAddress: str
    
    startedAt: datetime
    andingAt: datetime
    
    class Config:
        from_attributes = True  # Allows loading from ORM models like SQLModel


class AllStatisticsRead(BaseModel):
    totalAmountStaked: Decimal = 0.00
    totalMatrixPoolGenerated: Decimal = 0.00
    averageDailyReferral: int = 0
    

class MatrixPoolBaseSchema(BaseModel):
    poolAmount: Decimal = 0.00
    countDownFrom: datetime
    countDownTo: datetime
    active: bool = False
    
    
class MatrixPoolRead(MatrixPoolBaseSchema):
    uid: uuid.UUID
    users: List["MatrixPoolUsersRead"]
    
    @staticmethod
    def is_active(countDownTo: datetime):
        return countDownTo <= datetime.now()
    
    @classmethod
    def fro_orm(cls, pool: "MatrixPoolRead"):
        pool_dict = pool.model_dump()
        pool_dict["active"] = cls.is_active(pool.countDownTo)
        return cls(**pool_dict)
    

    class Config:
        from_attributes = True  # Allows loading from ORM models like SQLModel


class MatrixPoolUsersCreate(BaseModel):
    userId: int
    referralsAdded: int = 1

    
class MatrixPoolUsersRead(BaseModel):
    uid: uuid.UUID
    matrixPoolUid: uuid.UUID
    userId: int
    referralsAdded: int = 1

    class Config:
        from_attributes = True  # Allows loading from ORM models like SQLModel


class TokenMeterCreate(BaseModel):
    tokenAddress: str
    totalCap: Decimal = 0.00
    
    
class TokenMeterUpdate(BaseModel):
    tokenAddress: Optional[str]
    totalCap: Optional[Decimal]
    

class TokenMeterRead(BaseModel):
    uid: uuid.UUID
    
    tokenAddress: str
    tokenPrase: str
    totalAmountCollected: Decimal = 0.00

    totalCap: Decimal = 0.00
    tokenPrice: Decimal = 0.00
    percent_raised: Decimal = 0.00
    
    @staticmethod
    def percentage_raised(token: "TokenMeterRead"):
        percentage = (token.tokenPrice / token.totalCap) * 100
        return percentage
    
    @classmethod
    def fro_orm(cls, token: "TokenMeterRead"):
        token_dict = token.model_dump()
        token_dict["percent_raised"] = cls.percentage_raised(token)
        return cls(**token_dict)


class ActivitiesRead(BaseModel):
    uid: uuid.UUID
    
    activityType: ActivitiyType
    strDetail: Optional[str]
    amountDetail: Optional[Decimal]
    suiAmount: Optional[Decimal]
    userId: int
    
    created: datetime