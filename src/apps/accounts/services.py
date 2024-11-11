from decimal import Decimal
import random
import uuid

from datetime import datetime, timedelta
from typing import Annotated, Any, List, Optional
from uuid import UUID

from fastapi import BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate


from sqlalchemy import Date, cast
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from src.apps.accounts.dependencies import user_exists_check
from src.apps.accounts.enums import ActivitiyType
from src.apps.accounts.models import Activities, MatrixPool, MatrixPoolUsers, TokenMeter, User, UserStaking, UserWallet
from src.apps.accounts.schemas import AllStatisticsRead, TokenMeterCreate, TokenMeterUpdate, UserCreateOrLoginSchema, UserRead, UserUpdateSchema
from src.apps.accounts.sui_json_rpc_apis import SUI
from src.errors import InsufficientBalance, InvalidStakeAmount, InvalidTelegramAuthData, OnlyOneTokenMeterRequired, TokenMeterDoesNotExists, TokenMeterExists, UserAlreadyExists, UserBlocked, UserNotFound
from src.utils.hashing import create_access_token, createAccessToken, verifyTelegramAuthData
from src.utils.logger import LOGGER
from src.config.settings import Config
from src.db.redis import add_level_referral, get_level_referrers

from pysui.abstracts.client_keypair import SignatureScheme
from pysui import SuiConfig
from pysui.abstracts.client_keypair import KeyPair

from sui_python_sdk.wallet import SuiWallet

suiConfig = SuiConfig.user_config(
    rpc_url=Config.SUI_RPC,
)


class AdminServices:
    async def createTokenRecord(self, form_data: TokenMeterCreate, session: AsyncSession):
        db_result = await session.exec(select(TokenMeter).where(TokenMeter.tokenAddress == form_data.tokenAddress))
        existingTokenMeter = db_result.first()
        tm_result = await session.exec(select(TokenMeter))
        allTokenMeters = tm_result.all()
        
        if existingTokenMeter is not None:
            raise TokenMeterExists()
        
        if len(allTokenMeters) > 0:
            raise OnlyOneTokenMeterRequired()
        
        form_dict = form_data.model_dump()
        tokenMeter = TokenMeter(**form_dict)
        session.add(tokenMeter)
        await session.commit()
        return tokenMeter

    async def updateTokenRecord(self, token_address: str, form_data: TokenMeterUpdate, session: AsyncSession):
        db_result = await session.exec(select(TokenMeter).where(TokenMeter.tokenAddress == token_address))
        existingTokenMeter = db_result.first()
        
        if existingTokenMeter is None:
            raise TokenMeterDoesNotExists()
                
        form_dict = form_data.model_dump()
        
        for k, v in form_dict.items():
            if v is not None:
                setattr(existingTokenMeter, k, v)
        
        session.add(existingTokenMeter)
        await session.commit()
        await session.refresh(existingTokenMeter)
        return existingTokenMeter
    
    async def statRecord(self, session: AsyncSession) -> AllStatisticsRead:
        # Step 1: Group referred users by date, counting referrals per day
        daily_referrals_query = (
            select(
                cast(User.joined, Date).label("join_date"),
                func.count(User.userId).label("daily_referrals")
            )
            .where(User.referredByUserId != None)
            .group_by(cast(User.joined, Date))
        )

        # Execute the query to get daily referral counts
        daily_referrals = await session.exec(daily_referrals_query)
        daily_referrals = daily_referrals.all()

        # Step 2: Calculate the total referrals and the average referrals per day
        total_days_with_referrals = len(daily_referrals)
        total_referred_users = sum(row.daily_referrals for row in daily_referrals)
        average_daily_referrals = total_referred_users / total_days_with_referrals if total_days_with_referrals else 0


        # Query the total amount staked by summing deposits from the userStaking model
        total_staked_query = select(func.sum(UserStaking.deposit))
        total_staked_result = await session.exec(total_staked_query)
        total_staked = total_staked_result.scalar() or Decimal(0.00)
        
        # Query to get the total amount raised in the metrix pool
        total_pool_query = select(func.sum(MatrixPool.poolAmount))
        total_pool_result = await session.exec(total_pool_query)
        total_pool_generated = total_pool_result.scalar() or Decimal(0.00)
        
        AllStatisticsRead(
            averageDailyReferral=int(average_daily_referrals),
            totalAmountStaked=total_staked,
            totalMatrixPoolGenerated=total_pool_generated,
        )
                
        
class UserServices:
    async def register_new_user(self, admin: bool, telegram_init_data: str, referrer: Optional[int], form_data: UserCreateOrLoginSchema, session: AsyncSession) -> User:
        if not verifyTelegramAuthData(telegram_init_data):
            raise InvalidTelegramAuthData()
        
        # check if it is a returning user
        user: Optional[User] = await user_exists_check(form_data.userId, session)
        referring_user = None
        
        # if returning user register the user and generate a unique wallet for them with a welcome ctivity attached
        if user is None:
            form_dict = form_data.model_dump()
            new_user = User(**form_dict)
            new_user.isSuperuser = admin
            
            # Add a referrer if the user was referred by someone through their link and add the level downlines as well
            if referrer is not None:
                new_user.referredByUserId = referrer
                
                db_result = await session.exec(select(User).where(User.userId == referrer))
                referring_user = db_result.first()
                
                # Save the referral level down to the 5th level in redis for improved performance
                if referring_user is not None:
                    referring_user.totalDirectReferrals += 1
                    refferal_name = f"{new_user.firstName} {new_user.lastName}" if new_user.firstName is not None and new_user.lastName else None
                    await add_level_referral(referring_user.userId, level=1, referralId=new_user.userId, balance=Decimal(0.00))
                    if referring_user.referredByUserId is not None:
                        referring_user.referreByUser.totalIndirectReferrals += 1 
                        await add_level_referral(referring_user.referreByUser.userId, level=2, referralId=new_user.userId, balance=Decimal(0.00), name=refferal_name)
                        if referring_user.referreByUser.referredByUserId is not None:
                            referring_user.referreByUser.referreByUser.totalIndirectReferrals += 1 
                            await add_level_referral(referring_user.referreByUser.referreByUser.userId, level=3, referralId=new_user.userId, balance=Decimal(0.00), name=refferal_name)
                            if referring_user.referreByUser.referreByUser.referredByUserId is not None:
                                referring_user.referreByUser.referreByUser.referreByUser.totalIndirectReferrals += 1 
                                await add_level_referral(referring_user.referreByUser.referreByUser.referreByUser.userId, level=4, referralId=new_user.userId, balance=Decimal(0.00), name=refferal_name)
                                if referring_user.referreByUser.referreByUser.referreByUser.referredByUserId is not None:
                                    referring_user.referreByUser.referreByUser.referreByUser.referreByUser.totalIndirectReferrals += 1 
                                    await add_level_referral(referring_user.referreByUser.referreByUser.referreByUser.referreByUser.userId, level=5, referralId=new_user.userId, balance=Decimal(0.00), name=refferal_name)

            # Generate a new wallet which includes the wallet address and mnemonic phrase
            _mnen_phrase, _address = suiConfig.create_new_keypair_and_address(scheme=SignatureScheme.ED25519)
            
            # Save the new wallet in the database
            new_wallet = UserWallet(address=_address, phrase=_mnen_phrase, userId=new_user.userId)
            
            # Create a new staking account for the user wallet to store their staking details
            new_staking = UserStaking(walletAddress=new_wallet.address, wallet=new_wallet)
            
            # Create an activity record for this new user
            new_activity = Activities(activityType=ActivitiyType.WELCOME, strDetail="Welcome to SUI-Bison", userId=new_user.userId)
            
            session.add(new_user)
            session.add(new_wallet)
            session.add(new_staking)
            session.add(new_activity)
            await session.commit()
        
            # generate access and refresh token so long the telegram init data is valid
            accessToken = createAccessToken(
                user_data={
                    "userId": new_user.userId,
                },
                expiry=timedelta(seconds=Config.ACCESS_TOKEN_EXPIRY)
            )
            refreshToken = createAccessToken(
                user_data={
                    "userId": new_user.userId,
                },
                refresh=True,
                expiry=timedelta(days=7)
            )
            return accessToken, refreshToken, new_user
    
        # check if the user is blocked
        if user is not None and user.isBlocked:
            raise UserBlocked()
        
        # check if the user has just joined and within 24hours to give them an extra referral boost
        if referring_user.totalDirectReferrals >= 2 and (datetime.utcnow() - referring_user.joined) < timedelta(hours=24):
            referring_user.wallet.earnings += 3
            # NOTE: Add a functionality to get sui price in usd from yahoo finance
            new_activity = Activities(activityType=ActivitiyType.FASTBONUS, strDetail="Fast start bonus", suiAmount=3, userId=referring_user.userId)
            session.add(new_activity)
            await session.commit()
        
        # update the users rank record immediately they open the webapp and the weeks match up
        if user is not None and user.rank is not None:
            user.wallet.update_ranking_details(session)
            # Calculate days since last rank earning
            days_since_last_earning = (datetime.now().date() - user.lastRankEarningAddedAt.date()).days

            # Calculate weeks using integer division (discarding remainder)
            weeks_earned = days_since_last_earning // 7

            # Check if there are weeks to be added
            if weeks_earned > 0:
                user.wallet.earnings += user.wallet.rankEarnings * weeks_earned
                user.wallet.totalReferralEarnings += user.wallet.rankEarnings * weeks_earned
                

            # Update lastRankEarningAddedAt to reflect the latest calculation
            user.lastRankEarningAddedAt = datetime.now() - timedelta(days=days_since_last_earning % 7)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        # Process active stake balances and earnings
        if user is not None and user.wallet.staking.endingAt <= datetime.now():
            active_stake = user.wallet.staking
            await self.calculate_and_update_staked_interest_every_5_days(session, active_stake)
        
        # generate access and refresh token so long the telegram init data is valid
        accessToken = createAccessToken(
            user_data={
                "userId": user.userId,
            },
            expiry=timedelta(seconds=Config.ACCESS_TOKEN_EXPIRY)
        )
        refreshToken = createAccessToken(
            user_data={
                "userId": user.userId,
            },
            refresh=True,
            expiry=timedelta(days=7)
        )
        
        return accessToken, refreshToken, user
    
    async def return_all_users(self, session: AsyncSession):
        users: Page[UserRead] = await paginate(session, select(User).order_by(User.joined, User.userId))
        return users
    
    async def return_user_by_userId(self, userId: int, session: AsyncSession):
        db_result = await session.exec(select(User).where(User.userId == userId))
        user = db_result.first()
        if user is None:
            raise UserNotFound()
        return user
    
    async def updateUserProfile(self, user: User, form_data: UserUpdateSchema, session: AsyncSession):
        form_dict = form_data.model_dump()
        
        for k, v in form_dict.items():
            if v is not None:
                setattr(user, k, v)
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def get_activities(self, user: User, session: AsyncSession):
        db_result = await session.exec(select(Activities).where(Activities.userId == user.userId).limit(30))
        activities = db_result.all()
        return activities
    
    async def stake_sui(self, amount: Decimal, user: User, session: AsyncSession):
        # user has to successfuly transfer into this wallet account then we 
        # first check for them to confirm the transfer is successful
        # NOTE: should be improved with a function that checks repeatedly for transfer success and can come from the frontend to initiate a stake if there is a confirmed sui balance
        coin_balance = await SUI.getBalance(user.wallet.address)
        token_meter = session.exec(select(TokenMeter).where(TokenMeter.address != None)).first()

        # Check if user has enough balance to stake
        if coin_balance.coinObjectCount < amount:
            raise InsufficientBalance()
        
        # Check for active staking
        if user.wallet.staking.endingAt is not None:
            active_staking = user.wallet.staking

            # Top-up active staking 
            # if deposit is not larger than current active stake balance then raise an error for insufficient balance
            if not amount > active_staking.deposit and not amount >= Decimal(coin_balance.coinObjectCount):
                # User tried to stake less than or equal to their existing amount
                raise InvalidStakeAmount()


            # if there is a active stake run the topup, update the active stake balance 
            # and then transfer the sui wallet balance to the admin user
            active_staking.deposit += amount
            await session.commit()
            await session.refresh(active_staking)
        else:
            stake = user.wallet.staking
            stake.deposit += amount
            stake.startedAt = datetime.now()
            stake.endingAt = datetime.now() + timedelta(days=100)
            await session.commit()
            await session.refresh(stake)
            
        # after successfully topping up stake sui in the user's 
        # wallet to the admin so it starts afresh from 0 while updating the 
        # actual system wallet balance
        await self.transferToAdminWallet(user, token_meter)
        return active_staking
        
    async def calculate_and_update_staked_interest_every_5_days(session: AsyncSession, stake: UserStaking):
        """
        This calculates and updates the interest on a stake until its expiry date.

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
        
    async def transferToAdminWallet(user, token_meter):
        """Transfer the current sui wallet balance of a user to the admin wallet specified in the tokenMeter"""
        coinDetail = await SUI.getCoins(user.wallet.address)
        coins = []
        for coin in coinDetail:
            if coin.coinType == "0x2::sui::SUI":
                coins.append(coin.coinObjectId)
        try:
            transResponse = await SUI.payAllSui(user.wallet.address, token_meter.address, 10000, coins)
            return transResponse.txBytes
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


    async def withdrawToUserWallet(user: User, withdrawal_wallet: str, session: AsyncSession):
        """Transfer the current sui wallet balance of a user to the admin wallet specified in the tokenMeter"""
        token_meter: Optional[TokenMeter] = await session.exec(select(TokenMeter)).first()
        
        # determine that the company's wallet address has sui tokens to transfer to withdrawing user
        coinDetail = await SUI.getCoins(token_meter.tokenAddress)
        coins = []
        for coin in coinDetail:
            if coin.coinType == "0x2::sui::SUI":
                coins.append(coin.coinObjectId)
                
        now = datetime.now()
        sevenDaysLater = now + timedelta(days=7)
        
        # perform the calculatios in the ratio 60:20:10:10
        withdawable_amount = user.wallet.earnings * Decimal(0.6)
        redepositable_amount = user.wallet.earnings * Decimal(0.2)
        token_meter_amount = user.wallet.earnings * Decimal(0.1)
        matrix_pool_amount = user.wallet.earnings * Decimal(0.1)
        
        # Top up the meter balance with the users amount and update the amount 
        # invested by the user into the token meter
        token_meter.totalAmountCollected += token_meter_amount
        user.wallet.totalTokenPurchased += token_meter_amount
        
        # redeposit 20% from the earnings amount into the user staking deposit
        user.wallet.staking.deposit += redepositable_amount
        
        # Share another 10% to the global matrix pool
        active_matrix_pool_or_new = await session.exec(select(MatrixPool).where(MatrixPool.countDownTo >= now)).first()
        
        # confirm there is an active matrix pool to add another 10% of the earning into
        if active_matrix_pool_or_new is None:
            active_matrix_pool_or_new = MatrixPool(poolAmount=matrix_pool_amount, countDownFrom=now, countDownTo=sevenDaysLater)
            
            session.add(active_matrix_pool_or_new)
            
        # if there is no active matrix pool then create one for the next 7 days and add the 10% from the withdrawal into it
        if active_matrix_pool_or_new is not None:
            active_matrix_pool_or_new.poolAmount += matrix_pool_amount
        
        await session.commit()
        await session.refresh(active_matrix_pool_or_new)

        # transfer the remaining 60% to the users external wallet address
        try:
            transResponse = await SUI.paySui(user.wallet.address, withdrawal_wallet, withdawable_amount, 10000, coins)
            return transResponse.txBytes
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
            

        