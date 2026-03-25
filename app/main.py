from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import api_router
from app.core.logging import setup_logging
from app.middleware.audit import AuditMiddleware

setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    yield


fastapi_app = FastAPI(
    title="Fitness API",
    version="0.1.0",
    lifespan=lifespan,
)
fastapi_app.include_router(api_router)

app = AuditMiddleware(fastapi_app)
