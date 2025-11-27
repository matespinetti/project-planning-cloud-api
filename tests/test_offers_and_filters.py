"""Targeted tests for project filtering and oferta creation safeguards."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.api.v1.endpoints.projects import list_projects
from app.models.oferta import EstadoOferta
from app.models.pedido import EstadoPedido
from app.schemas.oferta import OfertaCreate
from app.services.oferta_service import OfertaService
from app.services.pedido_service import PedidoService


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


class _ListResult:
    def __init__(self, values):
        self._values = values

    def unique(self):
        return self

    def scalars(self):
        return self

    def all(self):
        return self._values


class _ListSession:
    """Session stub to return a predefined list of pedidos."""

    def __init__(self, pedidos):
        self._pedidos = pedidos

    async def get(self, _model, _id):
        return SimpleNamespace(id=_id)

    async def execute(self, _stmt):
        return _ListResult(self._pedidos)


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
async def test_create_oferta_allows_if_previous_not_pending():
    """A previous oferta that is not pending should not block creation."""
    pedido = SimpleNamespace(id=uuid4(), estado=EstadoPedido.PENDIENTE)
    # Simulate no pending offer found
    session = _DummySession(pedido=pedido, existing_offer_id=None)
    oferta_data = OfertaCreate(descripcion="descripcion valida", monto_ofrecido=50.0)
    user = SimpleNamespace(id=uuid4())

    # Should not raise
    await OfertaService.create(session, pedido.id, oferta_data, user)


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


@pytest.mark.asyncio
async def test_ya_oferto_only_counts_pending_offers():
    user_id = uuid4()
    pending_offer = SimpleNamespace(user_id=user_id, estado=EstadoOferta.pendiente)
    rejected_offer = SimpleNamespace(user_id=user_id, estado=EstadoOferta.rechazada)
    other_user_offer = SimpleNamespace(user_id=uuid4(), estado=EstadoOferta.pendiente)

    pedido_with_pending = SimpleNamespace(ofertas=[pending_offer])
    pedido_with_rejected = SimpleNamespace(ofertas=[rejected_offer])
    pedido_other_user = SimpleNamespace(ofertas=[other_user_offer])

    session = _ListSession([pedido_with_pending, pedido_with_rejected, pedido_other_user])

    pedidos = await PedidoService.list_by_proyecto(
        session, uuid4(), estado_filter=None, current_user_id=user_id
    )

    assert pedidos[0].ya_oferto is True
    assert pedidos[1].ya_oferto is False
    assert pedidos[2].ya_oferto is False
