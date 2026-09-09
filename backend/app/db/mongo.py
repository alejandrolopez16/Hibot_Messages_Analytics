"""Conexión a MongoDB Atlas.

Un solo AsyncIOMotorClient para todo el proceso: el driver mantiene el pool de
conexiones y el monitoreo de topología del replica set. Abrir un cliente por
base de datos duplicaría ambos sin ganar nada, porque las BD viven en el mismo
clúster. El ruteo se hace con client.get_database(...).
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ReadPreference

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

REQUIRED_READ_PREFERENCE = "secondaryPreferred"


def ensure_read_preference(uri: str) -> str:
    """Garantiza `readPreference=secondaryPreferred` en la URI.

    Es la restricción de infraestructura del proyecto: estas agregaciones barren
    cientos de millones de documentos y no pueden competir por el primario, que
    atiende la mensajería en tiempo real. La validación va en código y no solo en
    el .env para que un despliegue con la variable mal copiada no mande carga
    analítica al primario en silencio.
    """
    parts = urlsplit(uri)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))

    current = params.get("readPreference")
    if current != REQUIRED_READ_PREFERENCE:
        if current:
            logger.warning(
                "MONGO_URI traía readPreference=%s; se fuerza a %s.", current, REQUIRED_READ_PREFERENCE
            )
        params["readPreference"] = REQUIRED_READ_PREFERENCE

    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))


class MongoManager:
    """Ciclo de vida del cliente, atado al lifespan de FastAPI."""

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None

    async def connect(self, settings: Settings | None = None, uri: str | None = None) -> None:
        settings = settings or get_settings()
        uri = ensure_read_preference(uri or settings.mongo_uri)

        self._client = AsyncIOMotorClient(
            uri,
            maxPoolSize=settings.mongo_max_pool_size,
            minPoolSize=settings.mongo_min_pool_size,
            serverSelectionTimeoutMS=settings.mongo_server_selection_timeout_ms,
            # 'local' evita el costo de esperar confirmación de mayoría en lecturas
            # analíticas, donde unos segundos de lag de replicación son aceptables.
            readConcernLevel="local",
            retryReads=True,
            appname="hibot-analytics",
            tz_aware=True,
        )

        info = await self._client.admin.command("ping")
        logger.info("MongoDB conectado (readPreference=%s, ping=%s)", REQUIRED_READ_PREFERENCE, info.get("ok"))

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            raise RuntimeError("El cliente de MongoDB no está inicializado.")
        return self._client

    def database(self, name: str) -> AsyncIOMotorDatabase:
        return self.client.get_database(name, read_preference=ReadPreference.SECONDARY_PREFERRED)

    @property
    def channels_db(self) -> AsyncIOMotorDatabase:
        return self.database(get_settings().mongo_db_channels)

    @property
    def interactions_db(self) -> AsyncIOMotorDatabase:
        return self.database(get_settings().mongo_db_interactions)


mongo = MongoManager()
mongo_tp = MongoManager()


def get_mongo() -> MongoManager:
    """Dependencia de FastAPI — base de datos principal."""
    return mongo


def get_mongo_tp() -> MongoManager:
    """Dependencia de FastAPI — base de datos TP."""
    return mongo_tp
