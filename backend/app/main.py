"""Entrypoint del módulo de analítica transaccional."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, reports
from app.core.config import get_settings
from app.db.mongo import mongo, mongo_tp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo.connect()
    if settings.mongo_uri_tp:
        await mongo_tp.connect(uri=settings.mongo_uri_tp)
        mongo_tp.use_index_hint = False
    try:
        yield
    finally:
        await mongo.close()
        await mongo_tp.close()


settings = get_settings()

API_DESCRIPTION = """
Servicio HTTP que expone el **reporte de tráfico por canal** para el
tablero interno de Hibot.

### Alcance
* Filtra por **tenant** (todos sus canales) o por **número de línea**
  (`account`) puntual.
* Rango máximo de un mes por consulta.
* Interpreta las fechas en la zona horaria enviada (`timezone`);
  internamente todo se resuelve en UTC.

### Rendimiento
* Las agregaciones sobre `conversationData` y `messageData` corren en
  paralelo, con `hint` fijo sobre `{ tenant: 1, created: 1 }` y
  `maxTimeMS` acotado.
* Hay caché en memoria por proceso con TTL corto: recargas y navegación
  ida y vuelta no cuestan una segunda agregación.

### Errores
| Código | Situación                                                                 |
| ------ | ------------------------------------------------------------------------- |
| 400    | Payload inválido (fechas, rango, timezone, tenant/account excluyentes).   |
| 404    | No existe el canal / línea consultada.                                    |
| 409    | La línea aparece en varios tenants; ambigua.                              |
| 422    | Errores de validación de Pydantic (formato de campos).                    |
| 503    | Fallo de conexión con MongoDB.                                            |
| 504    | La agregación superó `AGGREGATION_MAX_TIME_MS`.                           |
"""

OPENAPI_TAGS = [
    {
        "name": "analytics",
        "description": (
            "Reporte transaccional por canal. Filtra por tenant o por línea "
            "y devuelve totales, desglose de salientes y detalle por canal."
        ),
    },
    {
        "name": "infra",
        "description": "Endpoints operacionales: health-check contra MongoDB.",
    },
]

app = FastAPI(
    title="Hibot · Analítica transaccional",
    version="1.0.0",
    summary="Reporte de tráfico por canal para el tablero interno de Hibot.",
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    contact={"name": "Equipo Analytics · Hibot", "email": "analytics@hibot.us"},
    license_info={"name": "Uso interno · Hibot"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reports.router)


@app.get(
    "/health",
    tags=["infra"],
    summary="Health-check",
    description="Verifica que la aplicación puede alcanzar MongoDB (`admin.ping`).",
    responses={
        200: {
            "description": "El servicio responde y MongoDB está accesible.",
            "content": {"application/json": {"example": {"status": "ok"}}},
        },
        503: {"description": "MongoDB no responde."},
    },
)
async def health() -> JSONResponse:
    await mongo.client.admin.command("ping")
    return JSONResponse({"status": "ok"})
