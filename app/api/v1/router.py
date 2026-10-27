"""Central router registering all API v1 domain endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router

v1_router = APIRouter()

v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
