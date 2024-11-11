from datetime import datetime, timedelta
from typing import Annotated, List, Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Path, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.apps.accounts.dependencies import AccessTokenBearer, RefreshTokenBearer, admin_permission_check, get_current_user
from src.apps.accounts.models import MatrixPool, MatrixPoolUsers, TokenMeter, User
from src.apps.accounts.schemas import AccessToken, ActivitiesRead, AllStatisticsRead, DeleteMessage, Message, MatrixPoolUsersCreate, RegAndLoginResponse, StakingCreate, TokenMeterCreate, TokenMeterRead, TokenMeterUpdate, UserCreateOrLoginSchema, UserLevelReferral, UserRead, UserUpdateSchema, UserWithReferralsRead, WithdrawEarning
from src.apps.accounts.services import AdminServices, UserServices
from src.db.engine import get_session
from src.config.settings import Config
from src.db.redis import add_jti_to_blocklist, get_level_referrers
from src.errors import ActivePoolNotFound, InvalidTelegramAuthData, InvalidToken, UserAlreadyExists
from src.utils.hashing import createAccessToken, verifyTelegramAuthData

session = Annotated[AsyncSession, Depends(get_session)]
auth_router = APIRouter()
user_router = APIRouter()
stake_router = APIRouter()
matrix_router = APIRouter()

admin_service = AdminServices()
user_service = UserServices()


@auth_router.post(
    "start",
    status_code=status.HTTP_201_CREATED,
    response_model=RegAndLoginResponse,
    description="Initialize a new webapp instance for a user passing a `telegram_init_data` for authorization check and an `*optional* referrerId` to create the level authorization. Within this endpoint is the function tto auto generate a unique wallet address and an initial activity record for the new user if it is their first time initializing the webapp else it automatically generates an accesstoken and refreshToken when the user is a returning user."
)
async def start(referrer: Optional[int], telegram_init_data: str, form_data: Annotated[UserCreateOrLoginSchema, Body()], session: session, admin: bool = False):
    accessToken, refershToken, user = await user_service.register_new_user(admin, telegram_init_data, referrer, form_data, session)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Authorization Successful", 
            "accessToken": accessToken, 
            "refereshToken": refershToken, 
            "user": user
        }
    )

@auth_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=AccessToken,
    description="Returns a specific user by providing their userId"
)
async def refresh_access_token(token: Annotated[User, Depends(RefreshTokenBearer())], session: session):
    expiry_timestamp = token["exp"]
    userId = token["user"]["userId"]
    
    if datetime.fromtimestamp(expiry_timestamp).date() < datetime.now().date():
        raise InvalidToken()
    
    res_user = await user_service.return_user_by_userId(userId, session)
    new_access_token = createAccessToken(user_data=token["user"])
    return {
        "message": "AccessToken generated successfully",
        "access_token": new_access_token,
        "user": res_user
    }

@auth_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserRead],
    description="This is an admin only endpoint that returns a paginated list of user datas"
)
async def get_users(user: Annotated[User, Depends(admin_permission_check)], session: session):
    users = await user_service.return_all_users(session)
    return users

@auth_router.patch(
    "block-user",
    status_code=status.HTTP_200_OK,
    response_model=DeleteMessage,
    description="Blocks a specific user"
)
async def block_a_user(userId: int, user: Annotated[User, Depends(admin_permission_check)], session: session):
    res_user = await user_service.return_user_by_userId(userId, session)
    res_user.isBlocked = True
    session.add(res_user)
    await session.commit()
    await session.refresh(res_user)
    return {
        "message": f"{res_user.userId} has been blocked",
    }

@auth_router.post(
    "create-token-meter",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenMeterRead,
    description="Create the token meter total capital, add an admin wallet address to transfer sui from individual user generated wallets into to show the meter bar."
)
async def create_token_meter(form_data: Annotated[TokenMeterCreate, Body()], user: Annotated[User, Depends(admin_permission_check)], session: session):
    tokenMeter = await admin_service.createTokenRecord(form_data, session)
    return tokenMeter

@auth_router.post(
    "add-new-matrix-pool-user",
    status_code=status.HTTP_201_CREATED,
    response_model=DeleteMessage,
    description="Adds a new user into the matrix pool user list for shares in the global matrix pool information."
)
async def add_new_pool_user(form_data: Annotated[MatrixPoolUsersCreate, Body()], user: Annotated[User, Depends(admin_permission_check)], session: session):
    active_pool: Optional[MatrixPool] = await session.exec(select(MatrixPool).where(MatrixPool.countDownTo >= datetime.now())).first()
    if active_pool is not None:
        new_matrix_pool_user_or_existing_one: Optional[MatrixPoolUsers] = await session.exec(select(MatrixPoolUsers).where(MatrixPoolUsers.matrixPoolUid == active_pool.uid)).first()
        if new_matrix_pool_user_or_existing_one is not None:
            new_matrix_pool_user_or_existing_one.referralsAdded += form_data.referralsAdded
        else:
            new_matrix_pool_user_or_existing_one = MatrixPoolUsers(userId=form_data.userId, referralsAdded=form_data.referralsAdded, matrixPoolUid=active_pool.uid)
            session.add(new_matrix_pool_user_or_existing_one)
            
        await session.commit()
        await session.refresh(active_pool)
        
        return {
            "message": "Successfully added a new matrix pool user"
        }
    raise ActivePoolNotFound()

@auth_router.patch(
    "update-token-meter",
    status_code=status.HTTP_200_OK,
    response_model=TokenMeterRead,
    description="update the token meter."
)
async def update_token_meter(form_data: Annotated[TokenMeterUpdate, Body()], user: Annotated[User, Depends(admin_permission_check)], session: session):
    tokenMeter = await admin_service.updateTokenRecord(form_data, session)
    return tokenMeter

@auth_router.get(
    "stats",
    status_code=status.HTTP_200_OK,
    response_model=AllStatisticsRead,
    description="Get stats for the project"
)
async def get_project_stats(user: Annotated[User, Depends(admin_permission_check)], session: session):
    return await admin_service.statRecord(session)
    

# User Endpoints
@user_router.get(
    "token-meter",
    status_code=status.HTTP_200_OK,
    response_model=Optional[TokenMeterRead],
    description="Get token meter."
)
async def get_token_meter(user: Annotated[User, Depends(get_current_user)], session: session):
    db_result = await session.exec(select(TokenMeter))
    return db_result.first()

@user_router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserWithReferralsRead,
    description="Returns an authenticated user"
)
async def me(user: Annotated[User, Depends(get_current_user)], session: session):
    referralsLv1List = await get_level_referrers(user.userId, 1)
    referralsLv2List = await get_level_referrers(user.userId, 2)
    referralsLv3List = await get_level_referrers(user.userId, 3)
    referralsLv4List = await get_level_referrers(user.userId, 4)
    referralsLv5List = await get_level_referrers(user.userId, 5)
    
    referralsLv1 = [UserLevelReferral(userId=user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv1List] if len(referralsLv1List) > 0 else []
    referralsLv2 = [UserLevelReferral(userId=user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv2List] if len(referralsLv2List) > 0 else []
    referralsLv3 = [UserLevelReferral(userId=user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv3List] if len(referralsLv3List) > 0 else []
    referralsLv4 = [UserLevelReferral(userId=user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv4List] if len(referralsLv4List) > 0 else []
    referralsLv5 = [UserLevelReferral(userId=user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv5List] if len(referralsLv5List) > 0 else []
    
    return {
        "user": user, 
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5,
    }

@user_router.get(
    "/{userId}",
    status_code=status.HTTP_200_OK,
    response_model=UserWithReferralsRead,
    description="Returns a specific user by providing their userId"
)
async def get_user(userId: int, user: Annotated[User, Depends(admin_permission_check)], session: session):
    res_user = await user_service.return_user_by_userId(userId, session)
    referralsLv1List = await get_level_referrers(res_user.userId, 1)
    referralsLv2List = await get_level_referrers(res_user.userId, 2)
    referralsLv3List = await get_level_referrers(res_user.userId, 3)
    referralsLv4List = await get_level_referrers(res_user.userId, 4)
    referralsLv5List = await get_level_referrers(res_user.userId, 5)
    
    referralsLv1 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv1List] if len(referralsLv1List) > 0 else []
    referralsLv2 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv2List] if len(referralsLv2List) > 0 else []
    referralsLv3 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv3List] if len(referralsLv3List) > 0 else []
    referralsLv4 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv4List] if len(referralsLv4List) > 0 else []
    referralsLv5 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv5List] if len(referralsLv5List) > 0 else []
    
    return {
        "user": res_user, 
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5,
    }

@user_router.patch(
    "me",
    status_code=status.HTTP_200_OK,
    response_model=UserWithReferralsRead,
    description="Returns a specific user by providing their userId"
)
async def update_profile(user: Annotated[User, Depends(get_current_user)], form_data: Annotated[UserUpdateSchema, Body()], session: session):
    res_user = await user_service.updateUserProfile(user, form_data, session)
    referralsLv1List = await get_level_referrers(res_user.userId, 1)
    referralsLv2List = await get_level_referrers(res_user.userId, 2)
    referralsLv3List = await get_level_referrers(res_user.userId, 3)
    referralsLv4List = await get_level_referrers(res_user.userId, 4)
    referralsLv5List = await get_level_referrers(res_user.userId, 5)
    
    referralsLv1 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv1List] if len(referralsLv1List) > 0 else []
    referralsLv2 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv2List] if len(referralsLv2List) > 0 else []
    referralsLv3 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv3List] if len(referralsLv3List) > 0 else []
    referralsLv4 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv4List] if len(referralsLv4List) > 0 else []
    referralsLv5 = [UserLevelReferral(userId=res_user.userId, level=1, referralName=ref["name"], referralId=ref["referralId"], totalStake=ref["balance"]) for ref in referralsLv5List] if len(referralsLv5List) > 0 else []
    
    return {
        "user": res_user, 
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5,
    }

@user_router.post(
    "withdraw",
    status_code=status.HTTP_201_CREATED,
    response_model=DeleteMessage,
    description="Initiates the withdrawals and distributes the payout as required from the platform while returning the transfer tx"
)
async def withdraw_earning(user: Annotated[User, Depends(get_current_user)], form_data: Annotated[WithdrawEarning, Body()], session: session):
    transfer_tx = await user_service.withdrawToUserWallet(user, form_data.wallet_address, session)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": f"Withdrawal successful. WithdrawalTX: {transfer_tx}"})

@user_router.post(
    "stake-sui",
    status_code=status.HTTP_201_CREATED,
    response_model=DeleteMessage,
    description="Stakes sui coins"
)
async def initialize_a_staking(user: Annotated[User, Depends(get_current_user)], form_data: Annotated[StakingCreate, Body()], session: session):
    active_stake = await user_service.stake_sui(form_data.deposit, user, session)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": f"You successfully staked: {form_data.deposit} SUI and your current active stake deposit is {active_stake.deposit}"})

@user_router.get(
    "activities",
    status_code=status.HTTP_200_OK,
    response_model=List[ActivitiesRead],
    description="Activities for a specific user"
)
async def get_user_activities(user: Annotated[User, Depends(get_current_user)], session: session):
    return await user_service.get_activities(user, session)