# how to run the server --> uv run uvicorn src.main:app --reload
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.db.schema import Base, engine
from src.api.v1 import timeseries, auth
from src.core.config import config
from src.core.logging_config import setup_logging, redirect_uvicorn_loggers

setup_logging(config.log_level)

import src.db.init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    redirect_uvicorn_loggers()

    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=config.app_name, lifespan=lifespan)


app.include_router(auth.router)
app.include_router(timeseries.router)
