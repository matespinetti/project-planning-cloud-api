"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import projects, auth

api_router = APIRouter()

# Include project endpoints
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(auth.router)
