from datetime import datetime, timedelta
import hmac
import hashlib
from typing import Optional
import urllib.parse
import uuid

import jwt
from src.config.settings import Config
from src.errors import InvalidToken, TokenExpired


def verifyTelegramAuthData(telegram_init_data: str) -> bool:
    encoded_string = urllib.parse.unquote(telegram_init_data)
    array = encoded_string.split("&")
    hash_index = next((i for i, s in enumerate(array) if s.startswith("hash=")), None)
    secret = hmac.new(Config.TELEGRAM_TOKEN.encode("utf-8"), b"WebAppData", hashlib.sha256)
    
    if hash_index is None:
        return False
    
    hash_value = array.pop(hash_index).split("=")[1]
    array.sort()
    data_check_string = "\n".join(array)
    generate_hash = hmac.new(secret.digest(), data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return generate_hash == hash_value

def createAccessToken(user_data: dict, expiry: timedelta = None, refresh: bool = False) -> str:
    payload = {}
    payload["user"] = user_data
    payload["exp"] = datetime.now() + (
        expiry if expiry is not None else timedelta(seconds=Config.ACCESS_TOKEN_EXPIRY)
    )
    payload["jti"] = str(uuid.uuid4())
    token = jwt.encode(
        payload=payload, key=Config.TELEGRAM_TOKEN, algorithm=Config.ALGORITHM
    )
    return token

def decodeAccessToken(token: str) -> dict:
    try:
        token_data = jwt.decode(
            jwt=token, key=Config.TELEGRAM_TOKEN, algorithms=[Config.ALGORITHM]
        )
        return token_data
    except jwt.ExpiredSignatureError:
        raise TokenExpired()
    except jwt.PyJWTError as e:
        raise InvalidToken()
    
