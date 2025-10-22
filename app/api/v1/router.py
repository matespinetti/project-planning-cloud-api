"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, ofertas, pedidos, projects

api_router = APIRouter()

# Include endpoints
api_router.include_router(auth.router)
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(pedidos.router, tags=["pedidos"])
api_router.include_router(ofertas.router, tags=["ofertas"])
