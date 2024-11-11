from decimal import Decimal
import json
from typing import Optional
import uuid
import redis.asyncio as aioredis
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
    LOGGER.debug(f"Token is locked: {is_blocked == 1}")
    return is_blocked == 1

async def add_level_referral(userId: int, level: int, referralId: int, balance: Decimal, name: Optional[str]):
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
        
async def get_level_referrers(userId: int, level: int):
    key = f"user:{userId}:level:{level}"
    
    # get current referrer list, decode and deserialize it
    referrer_data = await redis_client.exists(key)
    if referrer_data == 1:
        return json.loads(referrer_data.decode("utf-8"))
    return []
    