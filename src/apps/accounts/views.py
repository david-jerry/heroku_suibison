from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Path, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, paginate

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.apps.accounts.dependencies import AccessTokenBearer, RefreshTokenBearer, TokenBearer, admin_permission_check, get_current_user
from src.apps.accounts.models import MatrixPool, MatrixPoolUsers, TokenMeter, User, UserReferral, UserWallet
from src.apps.accounts.schemas import AccessToken, ActivitiesRead, AdminLogin, AllStatisticsRead, DeleteMessage, MatrixUsersRead, Message, MatrixPoolRead, MatrixUserCreateUpdate, RegAndLoginResponse, SignedTTransactionBytesMessage, StakingCreate, SuiDollarRate, TokenMeterCreate, TokenMeterRead, TokenMeterUpdate, UserCreateOrLoginSchema, UserLoginSchema, UserRead, UserUpdateSchema, UserWithReferralsRead, WithdrawEarning, Withdrawal
from src.apps.accounts.services import AdminServices, UserServices
from src.celery_beat import TemplateScheduleSQLRepository
from src.db.engine import get_session
from src.config.settings import Config
from src.db.redis import add_jti_to_blocklist, get_level_referrers, get_sui_usd_price
from src.errors import ActivePoolNotFound, InvalidTelegramAuthData, InvalidToken, MatrixPoolNotFound, UserAlreadyExists, UserNotFound
from src.utils.hashing import createAccessToken , verifyTelegramAuthData
from src.utils.logger import LOGGER

session = Annotated[AsyncSession, Depends(get_session)]
auth_router = APIRouter()
user_router = APIRouter()
stake_router = APIRouter()
matrix_router = APIRouter()

admin_service = AdminServices()
user_service = UserServices()
celery_beat = TemplateScheduleSQLRepository()


@auth_router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    response_model=RegAndLoginResponse,
    description="Initialize a new webapp instance for a user passing a `telegram_init_data` for authorization check and an `*optional* referrerId`(telegram userId) to create the level authorization. Within this endpoint is the function tto auto generate a unique wallet address and an initial activity record for the new user if it is their first time initializing the webapp else it automatically generates an accesstoken and refreshToken when the user is a returning user."
)
async def start(form_data: Annotated[UserCreateOrLoginSchema, Body()], session: session, referrer: Optional[str] = None):
    accessToken, refershToken, user = await user_service.register_new_user(referrer, form_data, session)
    referralsLv1List = await session.exec(select(UserReferral).where(UserReferral.level == 1).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv2List = await session.exec(select(UserReferral).where(UserReferral.level == 2).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv3List = await session.exec(select(UserReferral).where(UserReferral.level == 3).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv4List = await session.exec(select(UserReferral).where(UserReferral.level == 4).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv5List = await session.exec(select(UserReferral).where(UserReferral.level == 5).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    LOGGER.debug(referralsLv2List.all())

    referralsLv1 = referralsLv1List.all()
    referralsLv2 = referralsLv2List.all()
    referralsLv3 = referralsLv3List.all()
    referralsLv4 = referralsLv4List.all()
    referralsLv5 = referralsLv5List.all()

    userResp = {
        "user": user,
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5
    }
    return {
        "message": "Authorization Successful",
        "accessToken": accessToken,
        "refreshToken": refershToken,
        "user": userResp
    }

@auth_router.post(
    "/start-without-ref",
    status_code=status.HTTP_200_OK,
    response_model=RegAndLoginResponse,
    description="Telegram auth login."
)
async def login(form_data: Annotated[UserLoginSchema, Body()], session: session):
    accessToken, refershToken, user = await user_service.login_user(form_data, session)
    referralsLv1List = await session.exec(select(UserReferral).where(UserReferral.level == 1).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv2List = await session.exec(select(UserReferral).where(UserReferral.level == 2).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv3List = await session.exec(select(UserReferral).where(UserReferral.level == 3).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv4List = await session.exec(select(UserReferral).where(UserReferral.level == 4).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv5List = await session.exec(select(UserReferral).where(UserReferral.level == 5).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    LOGGER.debug(referralsLv2List.all())

    referralsLv1 = referralsLv1List.all()
    referralsLv2 = referralsLv2List.all()
    referralsLv3 = referralsLv3List.all()
    referralsLv4 = referralsLv4List.all()
    referralsLv5 = referralsLv5List.all()

    userResp = {
        "user": user,
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5
    }
    return {
        "message": "Authorization Successful",
        "accessToken": accessToken,
        "refreshToken": refershToken,
        "user": userResp
    }

@auth_router.post(
    "/admin-login",
    status_code=status.HTTP_200_OK,
    response_model=RegAndLoginResponse,
    description="Admin login endpoint to log an admin in without telegram auth string"
)
async def admin_login(request: Request, form_data: Annotated[AdminLogin, Body(...)], session: session):
    accessToken, refershToken, user = await user_service.authenticate_user(form_data, session)
    referralsLv1List = await session.exec(select(UserReferral).where(UserReferral.level == 1).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv2List = await session.exec(select(UserReferral).where(UserReferral.level == 2).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv3List = await session.exec(select(UserReferral).where(UserReferral.level == 3).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv4List = await session.exec(select(UserReferral).where(UserReferral.level == 4).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv5List = await session.exec(select(UserReferral).where(UserReferral.level == 5).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))

    referralsLv1 = referralsLv1List.all()
    referralsLv2 = referralsLv2List.all()
    referralsLv3 = referralsLv3List.all()
    referralsLv4 = referralsLv4List.all()
    referralsLv5 = referralsLv5List.all()

    userResp = {
        "user": user,
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5
    }
    return {
        "message": "Authorization Successful",
        "accessToken": accessToken,
        "refreshToken": refershToken,
        "user": userResp
    }

@auth_router.get(
    "/refresh-token",
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
    "/get-users",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserRead],
    dependencies=[Depends(admin_permission_check)],
    description="This is an admin only endpoint that returns a paginated list of user datas"
)
async def get_users(session: session, date: Optional[date] = None):
    users = await admin_service.getAllUsers(date, session)
    return users

@auth_router.get(
    "/get-transactions",
    status_code=status.HTTP_200_OK,
    response_model=Page[ActivitiesRead],
    dependencies=[Depends(admin_permission_check)],
    description="Returns a paginated list of filtered actvities to an admin"
)
async def get_transactions(session: session, date: Optional[date] = None):
    transactions = await admin_service.getAllTransactions(date, session)
    return paginate(transactions)

@auth_router.get(
    "/get-activities",
    status_code=status.HTTP_200_OK,
    response_model=Page[ActivitiesRead],
    dependencies=[Depends(admin_permission_check)],
    description="Returns a paginated list of all actvities to an admin"
)
async def get_activities(session: session, date: Optional[date] = None):
    activities = await admin_service.getAllActivities(date, session)
    return paginate(activities)

@auth_router.patch(
    "/ban-user/{userId}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteMessage,
    dependencies=[Depends(admin_permission_check)],
    description="Ban a specific user"
)
async def ban_a_user(userId: str, session: session):
    isBanned = await admin_service.banUser(userId, session)
    return {
        "message": f"{userId} has been {'banned' if isBanned else 'unbanned'}",
    }

@auth_router.post(
    "/create-token-meter",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenMeterRead,
    dependencies=[Depends(admin_permission_check)],
    description="Create the token meter total capital, add an admin wallet address to transfer sui from individual user generated wallets into to show the meter bar."
)
async def create_token_meter(form_data: Annotated[TokenMeterCreate, Body()], session: session):
    tokenMeter = await admin_service.createTokenRecord(form_data, session)
    return tokenMeter

@auth_router.post(
    "/add-new-matrix-pool-user",
    status_code=status.HTTP_201_CREATED,
    response_model=DeleteMessage,
    dependencies=[Depends(admin_permission_check)],
    description="Adds a new user into the matrix pool user list for shares in the global matrix pool information."
)
async def add_new_pool_user(form_data: Annotated[MatrixUserCreateUpdate, Body()], session: session):
    matrix_user = await admin_service.addNewPoolUser(form_data, session)
    return {
            "message": f"Successfully added {matrix_user.userId} to matrix pool users"
        }

@auth_router.patch(
    "/update-token-meter",
    status_code=status.HTTP_200_OK,
    response_model=TokenMeterRead,
    dependencies=[Depends(admin_permission_check)],
    description="update the token meter."
)
async def update_token_meter(form_data: Annotated[TokenMeterUpdate, Body()], session: session):
    tokenMeter = await admin_service.updateTokenRecord(form_data, session)
    return tokenMeter

@auth_router.get(
    "/{userId}",
    status_code=status.HTTP_200_OK,
    response_model=UserWithReferralsRead,
    dependencies=[Depends(admin_permission_check)],
    description="Returns a specific user to an admin"
)
async def get_a_user(userId: str, session: session):
    db_user = await session.exec(select(User).where(User.userId == userId))
    user = db_user.first()
    referralsLv1List = await session.exec(select(UserReferral).where(UserReferral.level == 1).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv2List = await session.exec(select(UserReferral).where(UserReferral.level == 2).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv3List = await session.exec(select(UserReferral).where(UserReferral.level == 3).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv4List = await session.exec(select(UserReferral).where(UserReferral.level == 4).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv5List = await session.exec(select(UserReferral).where(UserReferral.level == 5).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))

    referralsLv1 = referralsLv1List.all()
    referralsLv2 = referralsLv2List.all()
    referralsLv3 = referralsLv3List.all()
    referralsLv4 = referralsLv4List.all()
    referralsLv5 = referralsLv5List.all()

    return {
        "user": user,
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5,
    }

@auth_router.delete(
    "/{userId}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteMessage,
    dependencies=[Depends(admin_permission_check)],
    description="Returns a specific user to an admin"
)
async def delete_a_user(userId: str, session: session):
    db_user = await session.exec(select(User).where(User.userId == userId))
    user = db_user.first()
    db_pool_users = await session.exec(select(MatrixPoolUsers).where(MatrixPoolUsers.userId == userId))
    all_pool = db_pool_users.all()
    ref_db = await session.exec(select(User).where(User.userId == user.referrer.userId))
    referrer = ref_db.first()

    if referrer is not None:
        referrer.totalNetwork -= 1
        referrer.totalReferrals -= 1

    if user.wallet:
        await session.delete(user.wallet)

    if user.staking:
        await session.delete(user.staking)

    if user.referrer:
        await session.delete(user.referrer)

    for ctivity in user.activities:
        await session.delete(ctivity)

    for pu in all_pool:
        await session.delete(pu)

    for pt in user.pendingTransactions:
        await session.delete(pt)

    await session.delete(user)
    await session.commit()

    return {
        "message": "Successfully Deleted",
    }

@auth_router.patch(
    "/{userId}",
    status_code=status.HTTP_200_OK,
    response_model=UserWithReferralsRead,
    dependencies=[Depends(admin_permission_check)],
    description="Update records for a specific user by providing their userId as a required field ad then the body form data to update with"
)
async def update_profile(userId: str, form_data: Annotated[UserUpdateSchema, Body()], session: session):
    db_user = await session.exec(select(User).where(User.userId == userId))
    user = db_user.first()

    res_user = await user_service.updateUserProfile(user, form_data, session)
    referralsLv1List = await session.exec(select(UserReferral).where(UserReferral.level == 1).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv2List = await session.exec(select(UserReferral).where(UserReferral.level == 2).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv3List = await session.exec(select(UserReferral).where(UserReferral.level == 3).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv4List = await session.exec(select(UserReferral).where(UserReferral.level == 4).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv5List = await session.exec(select(UserReferral).where(UserReferral.level == 5).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))

    referralsLv1 = referralsLv1List.all()
    referralsLv2 = referralsLv2List.all()
    referralsLv3 = referralsLv3List.all()
    referralsLv4 = referralsLv4List.all()
    referralsLv5 = referralsLv5List.all()

    return {
        "user": res_user,
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5,
    }




# User Endpoints
@user_router.get(
    "/get-sui-rate",
    status_code=status.HTTP_200_OK,
    response_model=SuiDollarRate,
    description="Get the rate of sui in dollars form yfinance"
)
async def get_sui_rate():
    rate = await get_sui_usd_price()
    return {
        "rate": rate
    }

@user_router.get(
    "/token-meter",
    status_code=status.HTTP_200_OK,
    response_model=Optional[TokenMeterRead],
    description="Get token meter."
)
async def get_token_meter(session: session):
    db_result = await session.exec(select(TokenMeter))
    return db_result.first()

@user_router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserWithReferralsRead,
    # dependencies=[Depends(get_current_user)],
    description="Returns a paginated list of all actvities to an admin"
)
async def me(user: Annotated[User, Depends(get_current_user)], session: session):
    LOGGER.debug(f"user: {user}")

    referralsLv1List = await session.exec(statement = select(UserReferral).where(UserReferral.level == 1).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv2List = await session.exec(statement = select(UserReferral).where(UserReferral.level == 2).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv3List = await session.exec(statement = select(UserReferral).where(UserReferral.level == 3).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv4List = await session.exec(statement = select(UserReferral).where(UserReferral.level == 4).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv5List = await session.exec(statement = select(UserReferral).where(UserReferral.level == 5).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))

    referralsLv1 = referralsLv1List.all()
    referralsLv2 = referralsLv2List.all()
    referralsLv3 = referralsLv3List.all()
    referralsLv4 = referralsLv4List.all()
    referralsLv5 = referralsLv5List.all()

    return {
        "user": user,
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5,
    }

@user_router.get(
    "/referrals",
    status_code=status.HTTP_200_OK,
    response_model=Page[UserRead],
    dependencies=[Depends(get_current_user)],
    description="Returns a paginated list of all referrals to an admin"
)
async def user_referrals(user: Annotated[User, Depends(get_current_user)], session: session, level: int):
    LOGGER.debug(f"user: {user}")
    referrals = await user_service.get_user_downlines(user, level, session)

    return paginate(referrals)

@user_router.post(
    "/me/stake",
    status_code=status.HTTP_201_CREATED,
    response_model=SignedTTransactionBytesMessage,
    dependencies=[Depends(get_current_user)],
    description="Initiates a stake and staarts the countdown to a 100days"
)
async def initiate_a_stake(user: Annotated[User, Depends(get_current_user)], session: session):
    await user_service.stake_sui(user, session)

    # staked = await user_service.stake_sui(user, session)
    # message = "Initialized/Toppped a Stake"
    message = "Please go about your activity and whenever the stake has reflected in your wallet balance we shall reflect it."
    # if not staked:
    return {
        "message": message
    }

@user_router.post(
    "/me/withdraw",
    status_code=status.HTTP_201_CREATED,
    response_model=SignedTTransactionBytesMessage,
    dependencies=[Depends(get_current_user)],
    description="Initiates a withdrawal from the users earning"
)
async def withdraw_from_earning(wallet: Annotated[Withdrawal, Body(...)], user: Annotated[User, Depends(get_current_user)], session: session):
    await user_service.withdrawToUserWallet(user, wallet, session)
    return {
        "message": "Withdrawal successful"
    }

@user_router.get(
    "/me/activities",
    status_code=status.HTTP_200_OK,
    response_model=Page[ActivitiesRead],
    dependencies=[Depends(get_current_user)],
    description="Returns a paginated list of all actvities to an admin"
)
async def get_my_activities(user: Annotated[User, Depends(get_current_user)], session: session):
    activities = await user_service.getUserActivities(user, session)
    return paginate(activities)

@user_router.patch(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserWithReferralsRead,
    dependencies=[Depends(get_current_user)],
    description="Update records for a specific user by providing their userId as a required field ad then the body form data to update with"
)
async def update_profile(user: Annotated[User, Depends(get_current_user)], form_data: Annotated[UserUpdateSchema, Body()], session: session):
    res_user = await user_service.updateUserProfile(user, form_data, session)
    referralsLv1List = await session.exec(select(UserReferral).where(UserReferral.level == 1).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv2List = await session.exec(select(UserReferral).where(UserReferral.level == 2).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv3List = await session.exec(select(UserReferral).where(UserReferral.level == 3).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv4List = await session.exec(select(UserReferral).where(UserReferral.level == 4).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))
    referralsLv5List = await session.exec(select(UserReferral).where(UserReferral.level == 5).where(UserReferral.userId == user.userId).order_by(UserReferral.created).limit(50))

    referralsLv1 = referralsLv1List.all()
    referralsLv2 = referralsLv2List.all()
    referralsLv3 = referralsLv3List.all()
    referralsLv4 = referralsLv4List.all()
    referralsLv5 = referralsLv5List.all()

    return {
        "user": res_user,
        "referralsLv1": referralsLv1,
        "referralsLv2": referralsLv2,
        "referralsLv3": referralsLv3,
        "referralsLv4": referralsLv4,
        "referralsLv5": referralsLv5,
    }

@user_router.get(
    "/matrix-pool",
    status_code=status.HTTP_200_OK,
    response_model=Optional[MatrixPoolRead],
    dependencies=[Depends(get_current_user)],
    description="Returns the current matrix pool"
)
async def get_active_matrix_pool(user: Annotated[User, Depends(get_current_user)], session: session):
    now = datetime.now()
    mp_db = await session.exec(select(MatrixPool).where(MatrixPool.endDate >= now))
    matrix = mp_db.first()
    return matrix

@user_router.get(
    "/my-pool-position",
    status_code=status.HTTP_200_OK,
    response_model=Optional[MatrixUsersRead],
    dependencies=[Depends(get_current_user)],
    description="Returns the current user matrix pool position"
)
async def get_active_matrix_pool(user: Annotated[User, Depends(get_current_user)], session: session):
    now = datetime.now()
    mp_db = await session.exec(select(MatrixPool).where(MatrixPool.endDate >= now))
    matrix = mp_db.first()
    
    if matrix is None:
        raise MatrixPoolNotFound()
    
    mp_db = await session.exec(select(MatrixPoolUsers).where(MatrixPoolUsers.userId == user.userId).where(MatrixPoolUsers.matrixPoolUid == matrix.uid))
    matrix_user = mp_db.first()
    return matrix_user



