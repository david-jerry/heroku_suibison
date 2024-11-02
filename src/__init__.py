from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi.responses import JSONResponse
from pydantic_core import ValidationError

from src.apps.accounts.dependencies import get_ip_address
from src.db.engine import init_db
from src.utils.logger import LOGGER
from src.middleware import register_middleware
from src.config.settings import Config

from fastapi import FastAPI, Request
from fastapi_pagination import add_pagination
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi import status
from fastapi.encoders import jsonable_encoder

version = Config.VERSION
description = f"""
# SUI Bison API Documentation

* **BASE URL** https://api.sui-bison.com/{version}

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
        "url": "https://github.com/david-jerry/sui-bison-api/blob/main/LICENSE",
    },
    contact={
        "name": "Jeremiah David",
        "url": "https://github.com/david-jerry",
        "email": "jeremiahedavid@gmail.com",
    },
    terms_of_service="https://github.com/david-jerry/portfolio-api/blob/main/TERMS.md",
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}",
    redoc_url=f"{version_prefix}/docs",
)

register_all_errors(app)

register_middleware(app)

add_pagination(app)