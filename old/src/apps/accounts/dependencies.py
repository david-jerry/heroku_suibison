from typing import Annotated, Optional

from sqlmodel import select

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, OAuth2PasswordBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from src.apps.accounts.models import User
from src.db.engine import get_session
from src.db.redis import token_in_blocklist
from src.utils.hashing import decodeAccessToken
from src.errors import AccessTokenRequired, InsufficientPermission, InvalidAuthenticationScheme, RefreshTokenRequired, RevokedToken, UnAuthorizedAccess, UserBlocked, UserNotFound
from src.utils.logger import LOGGER
from src.config.settings import Config

# oauth2_bearer = OAuth2PasswordBearer(tokenUrl=f"/{Config.VERSION}/auth/start")
# oauth2_bearer_dependency = Annotated[str, Depends(oauth2_bearer)]
db_dependency = Annotated[AsyncSession, Depends(get_session)]


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        creds: HTTPAuthorizationCredentials = await super().__call__(request)
        if creds.scheme != "Bearer":
            raise InvalidAuthenticationScheme()

        token = creds.credentials

        token_data = decodeAccessToken(token)

        blocked = await token_in_blocklist(token_data["jti"])
        if blocked:
            raise RevokedToken()

        return token_data


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data["refresh"]:
            raise AccessTokenRequired()
        return None


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and not token_data["refresh"]:
            raise RefreshTokenRequired()
        return None


async def get_current_user(token_data: Annotated[dict, Depends(AccessTokenBearer())], session: db_dependency) -> Optional[User]:
    userId = token_data["user"]["userId"]
    if userId is None:
        raise UnAuthorizedAccess()

    db_result = await session.exec(select(User).where(User.userId == str(userId)))
    user = db_result.first()

    if user is None:
        raise UserNotFound()

    if user.isBlocked:
        raise UserBlocked()

    return user


async def user_exists_check(userId: str, session: db_dependency) -> Optional[User]:
    db_result = await session.exec(select(User).where(User.userId == str(userId)))
    user = db_result.first()
    return user


async def admin_permission_check(auth_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not auth_user.isAdmin or not auth_user.isSuperuser:
        raise InsufficientPermission()
    if auth_user.isBlocked:
        raise UserBlocked()
    return auth_user

