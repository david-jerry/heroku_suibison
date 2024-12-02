import pprint
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from src.config.settings import Config
import time
import logging
import rollbar
from rollbar.contrib.fastapi import ReporterMiddleware as RollbarMiddleware

from src.utils.logger import LOGGER

logger = logging.getLogger("uvicorn.access")
logger.disabled = True

rollbar.init(
    Config.ROLLBACK_ACCESS_TOKEN,
    handler='async',
)

def register_middleware(app: FastAPI):

    app.middleware(
        RollbarMiddleware
    )
    
    @app.middleware("http")
    async def custom_logging(request: Request, call_next):
        start_time = time.time()
        
        # Check if the request URL is the root "/"
        if request.url.path == "/":
            # Redirect to /api/v1/redocs
            return RedirectResponse(url=f"/{Config.VERSION}")

        response = await call_next(request)
        # LOGGER.debug(pprint.pprint(response, indent=4, depth=4))
        processing_time = time.time() - start_time

        host = request.client.host
        port = request.client.port
        method = request.method
        path = request.url.path

        message = f"""
{host}:{port} - {method} - {path} - {response.status_code} \n[msg: {response}] \ncompleted after {processing_time}s
        """

        LOGGER.info(message)
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "sui-bison.netlify.app",
            "t.me/sui_bison_bot",
            "t.me/sui_bison_bot/app",
            "localhost",
            "localhost:3000",
            "127.0.0.1",
            "0.0.0.0",
            "api.sui-bison.live",   
            "*",
            "sui-bison-be-188876f9767b.herokuapp.com",   
        ],
    )