"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, etapas, metrics, observaciones, ofertas, pedidos, projects, users

api_router = APIRouter()

# Include endpoints
api_router.include_router(auth.router)
api_router.include_router(users.router, tags=["users"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(etapas.router, tags=["etapas"])
api_router.include_router(pedidos.router, tags=["pedidos"])
api_router.include_router(ofertas.router, tags=["ofertas"])
api_router.include_router(observaciones.router, tags=["observaciones"])
api_router.include_router(metrics.router, tags=["metrics"])
