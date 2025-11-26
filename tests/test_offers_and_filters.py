"""Targeted tests for project filtering and oferta creation safeguards."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.api.v1.endpoints.projects import list_projects
from app.models.pedido import EstadoPedido
from app.schemas.oferta import OfertaCreate
from app.services.oferta_service import OfertaService


class _DummyResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _DummySession:
    """Lightweight async session stub to simulate duplicate offer checks."""

    def __init__(self, pedido, existing_offer_id=None):
        self._pedido = pedido
        self._existing_offer_id = existing_offer_id

    async def get(self, _model, _id):
        return self._pedido

    async def execute(self, _stmt):
        return _DummyResult(self._existing_offer_id)

    def add(self, _obj):
        # No-op for test
        return None

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None


@pytest.mark.asyncio
async def test_create_oferta_rejects_duplicate_for_same_user():
    pedido = SimpleNamespace(id=uuid4(), estado=EstadoPedido.PENDIENTE)
    session = _DummySession(pedido=pedido, existing_offer_id=uuid4())
    oferta_data = OfertaCreate(descripcion="descripcion valida", monto_ofrecido=100.0)
    user = SimpleNamespace(id=uuid4())

    with pytest.raises(HTTPException) as excinfo:
        await OfertaService.create(session, pedido.id, oferta_data, user)

    assert excinfo.value.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_list_projects_rejects_conflicting_flags():
    db = AsyncMock()
    current_user = SimpleNamespace(id=uuid4())

    with pytest.raises(HTTPException) as excinfo:
        await list_projects(
            page=1,
            page_size=20,
            estado=None,
            tipo=None,
            pais=None,
            provincia=None,
            ciudad=None,
            search=None,
            user_id=None,
            my_projects=True,
            exclude_my_projects=True,
            sort_by="created_at",
            sort_order="desc",
            db=db,
            current_user=current_user,
        )

    assert excinfo.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
