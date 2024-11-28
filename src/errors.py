from typing import Any, Callable, Optional
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi import FastAPI, status
from pydantic_core import ValidationError


class SuiBisonException(Exception):
    """Next exceptions class for all SuiBison Errors."""

    def __init__(self, name: Optional[str] = None):
        self.name = name


# Token and Authentication Errors
class InvalidToken(SuiBisonException):
    """User has provided an invalid."""
    pass


class IncorrectScheduleDuration(SuiBisonException):
    """Incorrect scheduling value"""
    pass


class InvalidRefreshToken(SuiBisonException):
    """Refresh token is invaliid"""
    pass


class ActivePoolNotFound(SuiBisonException):
    """Active pool not available ro existing"""
    pass


class InsufficientBalance(SuiBisonException):
    """Insufficient amount to start a stake for 100days."""
    pass


class InvalidStakeAmount(SuiBisonException):
    """
    Updating the staked amount requires the user to top up with an amount greater 
    than the previous amount initilizing the active stake
    """
    pass


class TokenExpired(SuiBisonException):
    """Token has expired"""
    pass


class TelegramAuthDataTokenExpired(SuiBisonException):
    """Telegram mini app token expired"""
    pass


class UnAuthorizedTelegramAccess(SuiBisonException):
    """Unauthorized telegram auth string used for the wrong user"""
    pass


class InvalidAuthenticationScheme(SuiBisonException):
    """Invalid authentication scheme not Bearer"""
    pass


class InvalidTelegramAuthData(SuiBisonException):
    """Invalid tlegram auth data"""
    pass


class RevokedToken(SuiBisonException):
    """User has provided a token that has been revoked."""
    pass


class AccessTokenRequired(SuiBisonException):
    """User has provided a refresh token when an access token is needed."""
    pass


class RefreshTokenRequired(SuiBisonException):
    """User has provided an access token when a refresh token is needed."""
    pass


# User-related Errors
class UserAlreadyExists(SuiBisonException):
    """User has provided an email for a user who exists during sign up."""
    pass


class UserNotFound(SuiBisonException):
    """User not found."""
    pass


class ReferrerNotFound(SuiBisonException):
    """Referrer not found"""
    pass


class UserBlocked(SuiBisonException):
    """This user has been blocked due to suspicious attempts or activities on their account."""
    pass


class UnAuthorizedAccess(SuiBisonException):
    """Please provide an authorized header key: userId."""
    pass


class InvalidCredentials(SuiBisonException):
    """User has provided wrong email or password during log in."""
    pass


class InsufficientPermission(SuiBisonException):
    """User does not have the necessary permissions to perform an action."""
    pass


class AccountNotVerified(SuiBisonException):
    """Account not yet verified."""
    pass


class FormDataRequired(SuiBisonException):
    """Form Data Required."""
    pass


class TokenMeterExists(SuiBisonException):
    """Token Meter already exists."""
    pass


class OnlyOneTokenMeterRequired(SuiBisonException):
    """Only one token meter record should exists."""
    pass


class TokenMeterDoesNotExists(SuiBisonException):
    """Token Meter does not exist"""
    pass


class StakingExpired(SuiBisonException):
    """The staking has expired its session"""
    pass


# Exception handler generator
# def create_exception_handler(
#     status_code: int, initial_detail: Any
# ) -> Callable[[Request, Exception], JSONResponse]:
#     async def exception_handler(exc: SuiBisonException):
#         return JSONResponse(content=initial_detail, status_code=status_code)

#     return exception_handler


# Register all error handlers
def register_all_errors(app: FastAPI):
    # User-related Error Handlers
    @app.exception_handler(ValidationError)
    async def validation_error(request: Request, exc: ValidationError):
        error_messages = []
        for error in exc.errors():
            message = error["msg"]
            input = error["input"][0] or error["input"]
            error_messages.append({f"{input}": f"{message}"})

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "model field errors",
                "source_errors": jsonable_encoder(error_messages),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(request: Request, exc: RequestValidationError):
        error_messages = []
        for error in exc.errors():
            field = error["loc"][-1]  # Get the field name
            message = error["msg"]
            error_messages.append({f"{field}": f"{message}"})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": jsonable_encoder(error_messages),
                "source_errors": jsonable_encoder(exc.errors()),
            },
        )

    @app.exception_handler(ResponseValidationError)
    async def response_validation_error(request: Request, exc: ResponseValidationError):
        error_messages = []
        for error in exc.errors():
            field = error["loc"][-1]  # Get the field name
            message = error["msg"]
            error_messages.append({f"{field}": f"{message}"})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": "Response errors",
                "source_errors": jsonable_encoder(error_messages),
            },
        )

    @app.exception_handler(InvalidToken)
    async def InvalidTokenError(request: Request, exc: InvalidToken):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Token is invalid.", "error_code": "invalid_token"}
        )

    @app.exception_handler(UnAuthorizedTelegramAccess)
    async def UnAuthorizedTelegramAccessError(request: Request, exc: UnAuthorizedTelegramAccess):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Telegram auth string used for the wrong userId.",
                     "error_code": "invalid_telegram_auth_string"}
        )

    @app.exception_handler(StakingExpired)
    async def StakingExpiredError(request: Request, exc: StakingExpired):
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content={"message": "The staking balance toping has expired. Please do not be troubled and whatever has been deposited within your wallet would be reflected.", "error_code": "timed_out"}
        )

    @app.exception_handler(IncorrectScheduleDuration)
    async def IncorrectScheduleDurationError(request: Request, exc: IncorrectScheduleDuration):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Incorrect Scheduling task value.", "error_code": "incorrect_scheduling_time"}
        )

    @app.exception_handler(ReferrerNotFound)
    async def ReferrerNotFoundError(request: Request, exc: ReferrerNotFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "We could not find a user with that userId.", "error_code": "referrer_not_found"}
        )

    @app.exception_handler(InvalidRefreshToken)
    async def InvalidRefreshTokenError(request: Request, exc: InvalidRefreshToken):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Refresh Token is invalid.", "error_code": "invalid_refresh_token"}
        )

    @app.exception_handler(ActivePoolNotFound)
    async def ActivePoolNotFoundError(request: Request, exc: ActivePoolNotFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "There is no active pool for the weeek.", "error_code": "active_pool_not_found"}
        )

    @app.exception_handler(InsufficientBalance)
    async def InsufficientBalanceError(request: Request, exc: InsufficientBalance):
        return JSONResponse(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            content={"message": "You do not have enough SUI to initiate a stake.", "error_code": "insufficient_balanc"}
        )

    @app.exception_handler(InvalidStakeAmount)
    async def InvalidStakeAmountError(exc: InvalidStakeAmount):
        return JSONResponse(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            content={"message": "You are required to top up your account with an amount greater than your initial staking amount.",
                     "error_code": "Invalid_stake_amount"}
        )

    @app.exception_handler(InvalidTelegramAuthData)
    async def InvalidTelegramAuthDataError(request: Request, exc: InvalidTelegramAuthData):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Telegram initiialization data is invalid.", "error_code": "invalid_telegram_init_data"}
        )

    @app.exception_handler(TokenExpired)
    async def TokenExpiredError(request: Request, exc: TokenExpired):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Token has expired.", "error_code": "expired_token"}
        )

    @app.exception_handler(TelegramAuthDataTokenExpired)
    async def TelegramAuthDataTokenExpiredError(request: Request, exc: TelegramAuthDataTokenExpired):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Telegran MiniAPP Token has expired.", "error_code": "mini_app_expired_token"}
        )

    @app.exception_handler(TokenMeterExists)
    async def TokenMeterExistsError(request: Request, exc: TokenMeterExists):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "An exisitng token meter with similar records exists.", "error_code": "token_meter_exists"}
        )

    @app.exception_handler(TokenMeterDoesNotExists)
    async def TokenMeterDoesNotExistsError(request: Request, exc: TokenMeterDoesNotExists):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "No record of this token meter exists.", "error_code": "token_meter_does_not_exists"}
        )

    @app.exception_handler(OnlyOneTokenMeterRequired)
    async def OnlyOneTokenMeterRequiredError(request: Request, exc: OnlyOneTokenMeterRequired):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "There can only be one token record per project.",
                     "error_code": "multiple_token_meter_record"}
        )

    @app.exception_handler(InvalidAuthenticationScheme)
    async def InvalidAuthenticationSchemeError(request: Request, exc: InvalidAuthenticationScheme):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Invalid Authentication Scheme", "error_code": "invalid_auth_scheme"}
        )

    @app.exception_handler(RevokedToken)
    async def RevokedTokenError(request: Request, exc: RevokedToken):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Token has been revoked.", "error_code": "token_revoked"}
        )

    @app.exception_handler(AccessTokenRequired)
    async def AccessTokenRequiredError(request: Request, exc: AccessTokenRequired):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Please provide a valid access token.", "error_code": "access_token_required"}
        )

    @app.exception_handler(RefreshTokenRequired)
    async def RefreshTokenRequiredError(request: Request, exc: RefreshTokenRequired):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Please provide a valid refresh token.", "error_code": "refresh_token_required"}
        )

    @app.exception_handler(FormDataRequired)
    async def FormDataRequiredError(request: Request, exc: FormDataRequired):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Please provide a body/data to submit into the form.", "error_code": "account_not_verified"}
        )

    @app.exception_handler(InsufficientPermission)
    async def InsufficientPermissionError(request: Request, exc: InsufficientPermission):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Unauthorized access restricted.", "error_code": "unauthorized_access"}
        )

    @app.exception_handler(InvalidCredentials)
    async def InvalidCredentialsError(request: Request, exc: InvalidCredentials):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid email or password.", "error_code": "invalid_email_or_password"}
        )

    @app.exception_handler(UnAuthorizedAccess)
    async def UnAuthorizedAccessError(request: Request, exc: InvalidCredentials):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "UnAuthorized access. Please provide the correct header key.",
                     "error_code": "unauthorized_access"}
        )

    @app.exception_handler(UserBlocked)
    async def UserBlockedError(request: Request, exc: UserBlocked):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "This account has been blocked.", "error_code": "user_blocked"}
        )

    @app.exception_handler(UserAlreadyExists)
    async def UserAlreadyExistsError(request: Request, exc: UserAlreadyExists):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "User with this email already exists", "error_code": "user_already_exist"}
        )

    @app.exception_handler(UserNotFound)
    async def UserNotFoundError(request: Request, exc: UserNotFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "User does not exist", "error_code": "user_not_found"}
        )
