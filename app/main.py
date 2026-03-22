from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import api_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title="Fitness API",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router)
