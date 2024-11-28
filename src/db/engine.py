import pprint
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlmodel import SQLModel  # , create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

from src.config.settings import Config
from src.utils.logger import LOGGER

db_url = str(Config.DATABASE_URL).strip()
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
engine = create_async_engine(url=db_url, echo=False, pool_size=5, max_overflow=10)
Session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

async def init_db() -> None:
    if engine is None:
        raise Exception("Database Engine is None. Please check if you have configured the database url correctly.")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession,  None]:
    async with Session() as session:
        if session is None:
            raise Exception("Database session is None")
        try:
            if hasattr(Config, 'SCHEMA'):
                await session.execute(
                    text(f"SET search_path TO {Config.SCHEMA}")
                )
            yield session
        except Exception as e:
            LOGGER.debug("Database session error")
            LOGGER.error(pprint.pprint(e, indent=4, depth=4))
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_session_context() -> AsyncSession: # type: ignore
    async with Session() as session:
        if session is None:
            raise Exception("Database session is None")
        try:
            if hasattr(Config, 'SCHEMA'):
                await session.execute(
                    text(f"SET search_path TO {Config.SCHEMA}")
                )
            yield session
        except Exception as e:
            LOGGER.debug("Database session error")
            LOGGER.error(pprint.pprint(e, indent=4, depth=4))
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session_context():
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception as e:
            LOGGER.debug("Database session error")
            LOGGER.error(pprint.pprint(e, indent=4, depth=4))
            await session.rollback()
            raise
        finally:
            await session.close()
