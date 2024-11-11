from typing import AsyncGenerator
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker as sessionmaker
from src.config.settings import Config


engine = create_async_engine(url=Config.DATABASE_URL, pool_size=100, max_overflow=0, echo=True)

async def init_db() -> None:
    if engine is None:
        raise Exception("Database Engine is None. Please check if you have configured the database url correctly.")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
async def get_session() -> AsyncGenerator[AsyncSession,  None]:
    Session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    async with Session() as session:
        if session is None:
            raise Exception("Database session is None")
        try:
            if hasattr(Config, 'SCHEMA'):
                await session.execute(
                    text(f"SET search_path TO {Config.SCHEMA}")
                )
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


