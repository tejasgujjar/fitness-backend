from __future__ import annotations

from fastapi import APIRouter

from . import auth, diet, health, sync, users, workouts

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(diet.router, prefix="/diet", tags=["diet"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])

__all__ = ["api_router"]
