import asyncio
from contextlib import asynccontextmanager
import pprint

from telegram import Update
from celery.schedules import crontab

from src.apps.accounts.tasks import fetch_sui_price, fetch_sui_usd_price_hourly
from src.db.engine import init_db
from src.celery_tasks import celery_app
from src.utils.logger import LOGGER
from src.middleware import register_middleware
from src.config.settings import Config
from src.errors import register_all_errors
from src.apps.accounts.views import auth_router, user_router
import rollbar
from rollbar.contrib.fastapi import add_to as rollbar_add_to

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi_pagination import add_pagination
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi import status
from fastapi.encoders import jsonable_encoder
from telegram_bot import telegramApp
import uvicorn

version = Config.VERSION
description = f"""
# SUI Bison API Documentation

* **BASE URL** https://api.sui-bison.live/{version}

## OVERVIEW

Sui-Bison is the first of its kind community driven smart contract project on the sui blockchain, with expert computer engineers and mathematicians, working to ensure that we earn and grow our sui portfolio.

## Why Accumulate the SUI Tken with SUI Bison Smart Contract

The SUI Token is the native cryptocurrency of the Sui Blockchain, which is designed to facilitate transactions, incentivize network peticipants, and enable governance. Sui Token and its blockchain are one of the fastest, smooth and reliable crypto projects of our time. Many has predicted it to be next Solana. What better way to accumulate Sui than participating on the staking opportunity o Sui bison

## History of SUI

Sui is a layer-1 blockchai optimizing for low-latency blockchain transfers. Its focused on instant transaction finality and high-speed transaction to make Sui a suitable platform for on-chain use cases like games, finance ad other real-time applicatios.


### Request/Response Format

* **Request:** JSON
* **Response:** JSON

### Error Handling

* **HTTP Status Codes:** The API will return appropriate HTTP status codes (e.g., 200 for success, 400 for bad requests, 500 for server errors).
* **Error Messages:** Error messages will be provided in the JSON response body.

### Rate Limiting

* **None
The API may have rate limits to prevent abuse. Please refer to the official Next Stocks API documentation for specific rate limits.

"""

@asynccontextmanager
async def life_span(app: FastAPI):
    LOGGER.info("Server is running")
    await init_db()
    yield
    LOGGER.info("Server has stopped")


app = FastAPI(
    title="SUI BISON API",
    description=description,
    version=version,
    lifespan=life_span,
    license_info={
        "name": "MIT License",
        "url": "https://github.com/david-jerry/sui-bison/blob/main/LICENSE",
    },
    contact={
        "name": "Jeremiah David",
        "url": "https://github.com/david-jerry",
        "email": "jeremiahedavid@gmail.com",
    },
    terms_of_service="https://github.com/david-jerry/sui-bison/blob/main/TERMS.md",
    openapi_url=f"/{version}/openapi.json",
    docs_url=f"/{version}/docs",
    redoc_url=f"/{version}",
)
rollbar.init('2574e01d16c14665916305eae9694244')
rollbar_add_to(app)

# # Add an /error endpoint to cause an uncaught exception
# async def localfunc(arg1, arg2, arg3):
#     # Both local variables and function arguments will be sent to Rollbar
#     # and available in the UI
#     localvar = 'local variable'
#     cause_error_with_local_variables

# @app.get('/v2/error')
# async def read_error():
#     await localfunc('func_arg1', 'func_arg2', 1)
    
register_all_errors(app)

register_middleware(app)

add_pagination(app)

app.include_router(auth_router, prefix=f"/{version}/auth", tags=["auth"])
app.include_router(user_router, prefix=f"/{version}/users", tags=["users"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
