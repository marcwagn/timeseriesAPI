# how to run the server --> uv run uvicorn src.main:app --reload
from src.core.logging_config import setup_logging

setup_logging()

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.db.schema import Base, engine
from src.core.config import config
from src.api.v1 import timeseries

import src.db.init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=config.app_name, lifespan=lifespan)


app.include_router(timeseries.router)
