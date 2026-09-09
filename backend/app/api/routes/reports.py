"""Endpoints de analítica transaccional."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from pymongo.errors import ExecutionTimeout, PyMongoError

from app.api.deps import get_current_user, get_mongo_for_user
from app.db.mongo import MongoManager
from app.models.reports import ChannelReportRequest, ChannelReportResponse
from app.services.analytics import AnalyticsService, ChannelNotFound, LineAmbiguous, LineNotFound

CurrentUser = Annotated[dict, Depends(get_current_user)]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class ErrorResponse(BaseModel):
    """Cuerpo estándar de un error HTTP en esta API."""

    detail: str = Field(description="Descripción legible del error.")


_JSON = "application/json"


def _error(description: str, example_detail: str) -> dict:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {_JSON: {"example": {"detail": example_detail}}},
    }


COMMON_ERRORS: dict[int | str, dict] = {
    400: _error(
        "Payload inválido (rango vacío o excedido, filtros excluyentes, timezone desconocida).",
        "Envía exactamente uno de los filtros: 'tenant' o 'account'.",
    ),
    404: _error(
        "No existe la línea o el canal consultado.",
        "No existe ninguna línea con el número '573001234567'.",
    ),
    409: _error(
        "La línea aparece en varios tenants; se necesita más contexto.",
        (
            "El número de línea '573001234567' pertenece a varios tenants: "
            "6696761e3c8a4cfe71502bbc, 6696761e3c8a4cfe71502bcd. Filtra también por tenant."
        ),
    ),
    422: {
        "model": ErrorResponse,
        "description": "Error de validación de Pydantic (formato de campos).",
    },
    503: _error(
        "MongoDB no está disponible.",
        "No se pudo consultar la base de datos analítica.",
    ),
    504: _error(
        "La agregación superó `AGGREGATION_MAX_TIME_MS`.",
        "La consulta superó el tiempo máximo. Acorta el rango de fechas o filtra por una línea.",
    ),
}


REQUEST_BODY_EXAMPLES = {
    "por_tenant": {
        "summary": "Filtro por tenant (todos sus canales)",
        "value": {
            "tenant": "6696761e3c8a4cfe71502bbc",
            "dateFrom": "2026-08-01T00:00:00",
            "dateTo": "2026-08-31T23:59:59",
            "timezone": "America/Bogota",
        },
    },
    "por_linea": {
        "summary": "Filtro por número de línea (account)",
        "value": {
            "account": "573001234567",
            "dateFrom": "2026-08-01T00:00:00",
            "dateTo": "2026-08-08T00:00:00",
            "timezone": "America/Argentina/Buenos_Aires",
        },
    },
}


def get_service(mongo: Annotated[MongoManager, Depends(get_mongo_for_user)]) -> AnalyticsService:
    return AnalyticsService(mongo)


ServiceDep = Annotated[AnalyticsService, Depends(get_service)]


async def _run(service: AnalyticsService, request: ChannelReportRequest) -> ChannelReportResponse:
    try:
        return await service.channel_report(request)
    except (ChannelNotFound, LineNotFound) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LineAmbiguous as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ExecutionTimeout as exc:
        # La agregación superó maxTimeMS. Casi siempre es un rango demasiado amplio
        
        logger.warning("Agregación excedida por tiempo: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="La consulta superó el tiempo máximo. Acorta el rango de fechas o filtra por una línea.",
        ) from exc
    except PyMongoError as exc:
        logger.exception("Error consultando MongoDB")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo consultar la base de datos analítica.",
        ) from exc


@router.post(
    "/channels-report",
    response_model=ChannelReportResponse,
    response_model_by_alias=True,
    summary="Reporte por canal (POST)",
    description=(
        "Genera el reporte transaccional por canal para un **tenant** o una "
        "**línea** puntual. Envía exactamente uno de los dos filtros; ambos a "
        "la vez o ninguno devuelve `400`.\n\n"
        "Las fechas se interpretan en `timezone` y el rango tiene un techo de "
        "un mes."
    ),
    responses=COMMON_ERRORS,
)
async def channels_report(
    service: ServiceDep,
    _: CurrentUser,
    request: Annotated[
        ChannelReportRequest,
        Body(openapi_examples=REQUEST_BODY_EXAMPLES),
    ],
) -> ChannelReportResponse:
    return await _run(service, request)


@router.get(
    "/channels-report",
    response_model=ChannelReportResponse,
    response_model_by_alias=True,
    summary="Reporte por canal (GET)",
    description=(
        "Misma consulta que el POST, pensada para **enlaces compartibles** y "
        "**caché de navegador**. Los parámetros van en query string "
        "(`dateFrom`, `dateTo`, `tenant` o `account`, `timezone`)."
    ),
    responses=COMMON_ERRORS,
)
async def channels_report_get(
    service: ServiceDep,
    _: CurrentUser,
    date_from: Annotated[
        datetime,
        Query(alias="dateFrom", description="Inicio del rango (se interpreta en `timezone`)."),
    ],
    date_to: Annotated[
        datetime,
        Query(alias="dateTo", description="Fin exclusivo del rango (se interpreta en `timezone`)."),
    ],
    tenant: Annotated[
        str | None,
        Query(description="ObjectId del tenant. Excluyente con `account`."),
    ] = None,
    account: Annotated[
        str | None,
        Query(alias="account", description="Número de línea. Excluyente con `tenant`."),
    ] = None,
    timezone_name: Annotated[
        str | None,
        Query(alias="timezone", description="Zona horaria IANA (por defecto `America/Bogota`)."),
    ] = None,
) -> ChannelReportResponse:
    payload = {"dateFrom": date_from, "dateTo": date_to, "tenant": tenant, "account": account}
    if timezone_name:
        payload["timezone"] = timezone_name
    return await _run(service, ChannelReportRequest.model_validate(payload))
