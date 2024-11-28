from decimal import Decimal
import json
from typing import Optional
import uuid
import redis.asyncio as aioredis
from src.apps.accounts.models import User
from src.config.settings import (
    broker_url,
)
from src.utils.logger import LOGGER

# Redis connection pool settings
REDIS_POOL_SIZE = 10
REDIS_TIMEOUT = 5
JTI_EXPIRY = 3600
VERIFICATION_CODE_EXPIRY = 900  # 15 minutes
SECURITY_EXPIRY = 2592000  # 1 month

# Initialize Redis with connection pooling
redis_pool = aioredis.ConnectionPool.from_url(
    broker_url, max_connections=REDIS_POOL_SIZE, socket_timeout=REDIS_TIMEOUT
)
redis_client = aioredis.Redis(connection_pool=redis_pool)


# Blacklisting
async def add_jti_to_blocklist(jti: str) -> None:
    """Adds a JTI (JWT ID) to the Redis blocklist with an expiry."""
    # Use the 'set' command with an expiry to add the JTI to the blocklist
    await redis_client.set(jti, "", ex=JTI_EXPIRY)

async def token_in_blocklist(jti: str) -> bool:
    """Checks if a JTI (JWT ID) is in the Redis blocklist."""
    
    # Use 'exists' instead of 'get' for better performance
    is_blocked = await redis_client.exists(jti)
    LOGGER.debug(f"Token is blocked: {is_blocked == 1}")
    return is_blocked == 1

async def add_level_referral(userId: str, level: int, referralId: str, balance: Decimal, name: Optional[str]):
    key = f"user:{userId}:level:{level}"
    
    # get current referrer list, decode and deserialize it
    referrers = await get_level_referrers(userId, level)
        
    # Find the referrer to update or add a new one
    found = False
    for referrer in referrers:
        if referrer['referralId'] == referralId:
            referrer['balance'] = balance
            referrer['name'] = name
            found = True
            break

    if not found:
        referrers.append({
            "referralId": referralId,
            "name": name,
            "balance": balance
        })
        
    await redis_client.set(key, json.dumps(referrers))
    return None
        
async def get_level_referrers(userId: str, level: int):
    key = f"user:{userId}:level:{level}"
    
    # get current referrer list, decode and deserialize it
    referrer_data = await redis_client.exists(key)
    if referrer_data == 1:
        referrals = await redis_client.get(key)
        return json.loads(referrals.decode("utf-8"))
    return []
    
    
async def get_sui_usd_price():
    price = await redis_client.get("sui_price")
    return Decimal(json.loads(price.decode("utf-8")))

# async def save_addresses(user: User):
#     key = f"wallet"
#     data = {
#         "userId": user.userId,
#         "address": user.wallet.address
#     }
#     old_datas = await redis_client.get("wallet")
    
#     await redis_client.set(key, json.dumps(data))
#     return None

# async def get_address(user: User):
#     key = f"wallet"
#     address = await redis_client.get(key)
#     return json.loads(address.decode("utf-8"))

# async def get_all_addresses():
#     addresses = []
#     match = "wallets"
#     # res = redis_client.scan_iter(match)
#     redis_client.get(match):
#         value = await redis_client.get(key)
#         addresses.append(json.loads(value.decode("utf=8")))
#     return addresses
    