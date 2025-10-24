"""Oferta endpoints."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.errors import OWNERSHIP_RESPONSES, ErrorDetail, ValidationErrorDetail
from app.schemas.oferta import (
    OfertaCreate,
    OfertaResponse,
    OfertaWithUserResponse,
    OfertaWithPedidoResponse,
    OfertaConfirmacionResponse,
)
from app.services.oferta_service import OfertaService

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post(
    "/pedidos/{pedido_id}/ofertas",
    response_model=OfertaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Pedido does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Pedido with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid oferta data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "descripcion"],
                                "msg": "field required",
                                "type": "value_error.missing",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def create_oferta(
    pedido_id: UUID,
    oferta_data: OfertaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OfertaResponse:
    """
    Crear una nueva oferta para un pedido.
    Cualquier usuario autenticado puede enviar una oferta.

    **Restricciones:**
    - Solo se pueden enviar ofertas a pedidos en estado 'PENDIENTE'
    - No se pueden enviar ofertas a pedidos que ya están 'COMPROMETIDO' o 'COMPLETADO'
    """
    logger.info(f"User {current_user.id} creating oferta for pedido {pedido_id}")

    oferta = await OfertaService.create(db, pedido_id, oferta_data, current_user)

    logger.info(f"Successfully created oferta {oferta.id}")
    return OfertaResponse.model_validate(oferta)


@router.get(
    "/pedidos/{pedido_id}/ofertas",
    response_model=List[OfertaWithUserResponse],
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of the project",
            "content": {
                "application/json": {
                    "example": {"detail": "You are not the owner of this project"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Pedido does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Pedido with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
    },
)
async def list_ofertas_for_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[OfertaWithUserResponse]:
    """
    Obtener todas las ofertas de un pedido específico.
    Solo el dueño del proyecto puede ver las ofertas de sus pedidos.
    """
    logger.info(f"User {current_user.id} fetching ofertas for pedido {pedido_id}")

    ofertas = await OfertaService.get_by_pedido(db, pedido_id, current_user)

    # Convert to response schema with user info
    response_ofertas = []
    for oferta in ofertas:
        oferta_dict = OfertaWithUserResponse.model_validate(oferta).model_dump()
        oferta_dict["user_email"] = oferta.user.email
        oferta_dict["user_ong"] = oferta.user.ong
        oferta_dict["user_nombre"] = oferta.user.nombre
        oferta_dict["user_apellido"] = oferta.user.apellido
        response_ofertas.append(OfertaWithUserResponse(**oferta_dict))

    return response_ofertas


@router.post(
    "/ofertas/{oferta_id}/accept",
    response_model=OfertaResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of the project",
            "content": {
                "application/json": {
                    "example": {"detail": "You are not the owner of this project"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Oferta does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Oferta with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Cannot accept oferta due to business rules",
            "content": {
                "application/json": {
                    "examples": {
                        "already_completed": {
                            "summary": "Pedido already completed",
                            "value": {"detail": "Cannot accept oferta for completed pedido"},
                        },
                        "already_committed": {
                            "summary": "Pedido already committed",
                            "value": {"detail": "Cannot accept oferta for committed pedido"},
                        },
                    }
                }
            },
        },
    },
)
async def accept_oferta(
    oferta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OfertaResponse:
    """
    Aceptar una oferta.
    Solo el dueño del proyecto puede aceptar ofertas para su proyecto.

    **Restricciones:**
    - Solo se pueden aceptar ofertas de pedidos en estado 'PENDIENTE'
    - No se pueden aceptar ofertas de pedidos que ya están 'COMPROMETIDO' o 'COMPLETADO'

    **Cuando se acepta una oferta:**
    - La oferta seleccionada pasa a estado 'aceptada'
    - **Todas las demás ofertas pendientes para el mismo pedido son rechazadas automáticamente**
    - El pedido pasa a estado 'comprometido' (pendiente de confirmación del oferente)
    """
    logger.info(f"User {current_user.id} accepting oferta {oferta_id}")

    oferta = await OfertaService.accept(db, oferta_id, current_user)

    logger.info(f"Successfully accepted oferta {oferta_id}")
    return OfertaResponse.model_validate(oferta)


@router.post(
    "/ofertas/{oferta_id}/reject",
    response_model=OfertaResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the owner of the project",
            "content": {
                "application/json": {
                    "example": {"detail": "You are not the owner of this project"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Oferta does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Oferta with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
    },
)
async def reject_oferta(
    oferta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OfertaResponse:
    """
    Rechazar una oferta.
    Solo el dueño del proyecto puede rechazar ofertas para su proyecto.
    """
    logger.info(f"User {current_user.id} rejecting oferta {oferta_id}")

    oferta = await OfertaService.reject(db, oferta_id, current_user)

    logger.info(f"Successfully rejected oferta {oferta_id}")
    return OfertaResponse.model_validate(oferta)


@router.post(
    "/ofertas/{oferta_id}/confirmar-realizacion",
    response_model=OfertaConfirmacionResponse,
    responses={
        401: OWNERSHIP_RESPONSES[401],
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - User is not the creator of the oferta",
            "content": {
                "application/json": {
                    "example": {"detail": "You are not the creator of this oferta"}
                }
            },
        },
        404: {
            "model": ErrorDetail,
            "description": "Not Found - Oferta does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Oferta with id 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
        400: {
            "model": ErrorDetail,
            "description": "Bad Request - Cannot confirm realization due to business rules",
            "content": {
                "application/json": {
                    "examples": {
                        "already_completed": {
                            "summary": "Commitment already confirmed",
                            "value": {
                                "detail": "This commitment has already been confirmed and marked as completado"
                            },
                        },
                        "wrong_state": {
                            "summary": "Wrong pedido state",
                            "value": {
                                "detail": "Cannot confirm realization. Pedido is in state pendiente, expected comprometido"
                            },
                        },
                    }
                }
            },
        },
    },
)
async def confirmar_realizacion_oferta(
    oferta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OfertaConfirmacionResponse:
    """
    Confirmar que se ha cumplido el compromiso de una oferta aceptada.
    Solo el usuario que creó la oferta puede confirmar su realización.

    **Requisitos:**
    - La oferta debe estar en estado 'ACEPTADA'
    - El pedido debe estar en estado 'COMPROMETIDO'

    **Resultado:**
    - El pedido pasa de estado 'COMPROMETIDO' a 'COMPLETADO'
    - Se devuelve un mensaje claro con la transición de estados
    - Incluye timestamp de confirmación

    **Errores comunes:**
    - Si el pedido ya está 'COMPLETADO': "This commitment has already been confirmed..."
    - Si el pedido no está 'COMPROMETIDO': "Cannot confirm realization. Pedido is in state..."
    """
    logger.info(f"User {current_user.id} confirming realization of oferta {oferta_id}")

    result = await OfertaService.confirm_realizacion(db, oferta_id, current_user)

    logger.info(f"Successfully confirmed realization of oferta {oferta_id}")
    return OfertaConfirmacionResponse(**result)


@router.get(
    "/ofertas/mis-compromisos",
    response_model=List[OfertaWithPedidoResponse],
    responses={
        401: OWNERSHIP_RESPONSES[401],
        422: {
            "model": ValidationErrorDetail,
            "description": "Validation Error - Invalid estado_pedido filter value",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "estado_pedido"],
                                "msg": "value is not a valid enumeration member",
                                "type": "type_error.enum",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def get_my_commitments(
    estado_pedido: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[OfertaWithPedidoResponse]:
    """
    Obtener todas las ofertas aceptadas del usuario actual (sus compromisos).
    Opcionalmente filtrar por estado del pedido: 'comprometido' o 'completado'.

    - **estado_pedido**: Filtro opcional por estado del pedido (comprometido o completado)
    """
    logger.info(f"User {current_user.id} fetching their commitments")

    ofertas = await OfertaService.get_my_commitments(db, current_user, estado_pedido)

    # Convert to response schema with pedido info
    response_ofertas = []
    for oferta in ofertas:
        oferta_dict = OfertaWithPedidoResponse.model_validate(oferta).model_dump()
        oferta_dict["pedido_tipo"] = oferta.pedido.tipo.value
        oferta_dict["pedido_descripcion"] = oferta.pedido.descripcion
        oferta_dict["pedido_estado"] = oferta.pedido.estado.value
        oferta_dict["pedido_monto"] = oferta.pedido.monto
        oferta_dict["pedido_moneda"] = oferta.pedido.moneda
        oferta_dict["pedido_cantidad"] = oferta.pedido.cantidad
        oferta_dict["pedido_unidad"] = oferta.pedido.unidad
        response_ofertas.append(OfertaWithPedidoResponse(**oferta_dict))

    return response_ofertas
