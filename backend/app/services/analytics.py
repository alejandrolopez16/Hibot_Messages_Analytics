"""Servicio que arma el reporte por canal de comunicación."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any, Iterable

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.config import Settings, get_settings
from app.db.mongo import MongoManager
from app.models.reports import (
    ChannelReportRequest,
    ChannelReportResponse,
    ChannelReportRow,
    ConsecutiveBreakdown,
    FilterMode,
    OutboundBreakdown,
    ReportTotals,
)
from app.services import pipelines

logger = logging.getLogger(__name__)

CHANNEL_PROJECTION = {"account": 1, "name": 1, "type": 1, "tenant": 1}
# El reporte solo cubre WhatsApp: cualquier otro tipo de canal se descarta
# tanto del scope inicial como de los canales que aparezcan por tráfico.
WHATSAPP_TYPE = "WhatsApp"


class ChannelNotFound(Exception):
    def __init__(self, channel_id: str) -> None:
        super().__init__(f"No existe el canal '{channel_id}'.")
        self.channel_id = channel_id


class LineNotFound(Exception):
    def __init__(self, account: str) -> None:
        super().__init__(f"No existe ninguna línea con el número '{account}'.")
        self.account = account


class LineAmbiguous(Exception):
    def __init__(self, account: str, tenants: list[str]) -> None:
        super().__init__(
            f"El número de línea '{account}' pertenece a varios tenants: "
            f"{', '.join(tenants)}. Filtra también por tenant."
        )
        self.account = account
        self.tenants = tenants


class _TTLCache:
    """Caché en memoria por proceso, con TTL y tamaño acotado.

    Suficiente para absorber recargas de pantalla y navegación de ida y vuelta
    entre filtros. En despliegue multi-instancia cada réplica mantiene su propia
    copia; si eso importa, cambiar por Redis sin tocar el resto del servicio.
    """

    def __init__(self, ttl_seconds: int, max_entries: int) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._data: OrderedDict[str, tuple[float, ChannelReportResponse]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ChannelReportResponse | None:
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            if time.monotonic() - stored_at > self._ttl:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    async def set(self, key: str, value: ChannelReportResponse) -> None:
        async with self._lock:
            self._data[key] = (time.monotonic(), value)
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)


class AnalyticsService:
    def __init__(self, mongo: MongoManager, settings: Settings | None = None) -> None:
        self._mongo = mongo
        self._settings = settings or get_settings()
        self._cache = _TTLCache(
            self._settings.report_cache_ttl_seconds,
            self._settings.report_cache_max_entries,
        )

    # --- Colecciones ---------------------------------------------------------

    @property
    def _channels(self) -> AsyncIOMotorCollection:
        return self._mongo.channels_db.get_collection("channelData")

    @property
    def _conversations(self) -> AsyncIOMotorCollection:
        return self._mongo.interactions_db.get_collection("conversationData")

    @property
    def _messages(self) -> AsyncIOMotorCollection:
        return self._mongo.interactions_db.get_collection("messageData")

    # --- API pública ---------------------------------------------------------

    async def channel_report(self, request: ChannelReportRequest) -> ChannelReportResponse:
        cache_key = request.cache_key()
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cached": True})

        started = time.perf_counter()

        tenant, metadata = await self._resolve_scope(request)

        # En modo línea el scope ya contiene solo los canales de esa línea; en
        # modo tenant se pasa `None` para no restringir por `channelId`.
        channel_ids = list(metadata) if request.mode is FilterMode.LINE else None

        match = pipelines.build_match(
            tenant=tenant,
            date_from=request.date_from,
            date_to=request.date_to,
            channel_ids=channel_ids,
        )

        # Las tres agregaciones son independientes y golpean nodos secundarios
        # distintos del replica set, así que corren en paralelo. El tiempo total
        # es el de la más lenta y no la suma de las tres.
        conversations, messages, consecutive = await asyncio.gather(
            self._aggregate(self._conversations, pipelines.conversations_pipeline(match), "conversations"),
            self._aggregate(self._messages, pipelines.messages_pipeline(match), "messages"),
            self._aggregate(self._messages, pipelines.consecutive_pipeline(match), "consecutive"),
        )

        conv_by_channel = {doc["_id"]: doc for doc in conversations if doc.get("_id")}
        msg_by_channel = {doc["_id"]: doc for doc in messages if doc.get("_id")}
        cons_by_channel = {doc["_id"]: doc for doc in consecutive if doc.get("_id")}

        # Canales con tráfico que no estaban en el scope inicial (por ejemplo,
        # canales eliminados que aún tienen histórico de mensajes).
        seen = set(conv_by_channel) | set(msg_by_channel)
        faltantes = seen - set(metadata)
        if faltantes:
            metadata.update(await self._load_channels_by_ids(faltantes))

        # Solo se reportan canales WhatsApp: los que aparecen por tráfico pero
        # no están en `metadata` son de otro tipo y quedan fuera del cálculo.
        rows = [
            self._build_row(
                channel_id,
                metadata[channel_id],
                conv_by_channel.get(channel_id),
                msg_by_channel.get(channel_id),
                cons_by_channel.get(channel_id),
            )
            for channel_id in metadata
        ]
        rows.sort(key=lambda r: (r.incoming + r.outbound.total, r.conversations), reverse=True)

        response = ChannelReportResponse(
            mode=request.mode,
            tenant=tenant,
            account=request.account,
            dateFrom=request.date_from,
            dateTo=request.date_to,
            totals=self._build_totals(rows),
            rows=rows,
            elapsedMs=int((time.perf_counter() - started) * 1000),
            cached=False,
        )

        await self._cache.set(cache_key, response)
        return response

    # --- Internos ------------------------------------------------------------

    async def _resolve_scope(self, request: ChannelReportRequest) -> tuple[str, dict[str, dict[str, Any]]]:
        """Devuelve el tenant efectivo y los metadatos de canal del scope.

        En modo línea el tenant se deriva del canal (o canales) que tienen ese
        `account`: es lo que permite que el `$match` entre por
        `{ tenant: 1, created: 1 }` en vez de escanear.
        """
        if request.mode is FilterMode.LINE:
            account = request.account or ""
            cursor = self._channels.find(
                {"account": account, "type": WHATSAPP_TYPE},
                projection=CHANNEL_PROJECTION,
            )
            channels = [doc async for doc in cursor]
            if not channels:
                raise LineNotFound(account)

            tenants = sorted({str(doc["tenant"]) for doc in channels})
            if len(tenants) > 1:
                raise LineAmbiguous(account, tenants)

            metadata = {str(doc["_id"]): doc for doc in channels}
            return tenants[0], metadata

        # En modo tenant se precargan todos sus canales para que los que no
        # tuvieron tráfico en el rango aparezcan en cero en vez de desaparecer
        # de la tabla.
        metadata = await self._load_channels_by_tenant(request.tenant or "")
        return request.tenant or "", metadata

    async def _load_channels_by_tenant(self, tenant: str) -> dict[str, dict[str, Any]]:
        cursor = self._channels.find(
            {"tenant": tenant, "type": WHATSAPP_TYPE},
            projection=CHANNEL_PROJECTION,
        )
        return {str(doc["_id"]): doc async for doc in cursor}

    async def _load_channels_by_ids(self, channel_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
        object_ids = []
        for raw in channel_ids:
            try:
                object_ids.append(ObjectId(raw))
            except (InvalidId, TypeError):
                logger.debug("channelId no convertible a ObjectId: %s", raw)
        if not object_ids:
            return {}
        cursor = self._channels.find(
            {"_id": {"$in": object_ids}, "type": WHATSAPP_TYPE},
            projection=CHANNEL_PROJECTION,
        )
        return {str(doc["_id"]): doc async for doc in cursor}

    async def _aggregate(
        self, collection: AsyncIOMotorCollection, pipeline: list[dict[str, Any]], label: str
    ) -> list[dict[str, Any]]:
        hint = pipelines.TENANT_CREATED_HINT if self._mongo.use_index_hint else None
        cursor = collection.aggregate(
            pipeline,
            allowDiskUse=True,
            **({"hint": hint} if hint else {}),
            maxTimeMS=self._settings.aggregation_max_time_ms,
            # Etiqueta visible en currentOp y en el profiler de Atlas: permite
            # identificar y matar una consulta analítica sin adivinar cuál es.
            comment=f"hibot-analytics:{label}",
        )
        return await cursor.to_list(length=None)

    @staticmethod
    def _build_row(
        channel_id: str,
        meta: dict[str, Any] | None,
        conversation_doc: dict[str, Any] | None,
        message_doc: dict[str, Any] | None,
        consecutive_doc: dict[str, Any] | None,
    ) -> ChannelReportRow:
        message_doc = message_doc or {}
        total = int(message_doc.get("outbound_total", 0))
        template = int(message_doc.get("outbound_template", 0))
        bot = int(message_doc.get("outbound_bot", 0))
        agent = int(message_doc.get("outbound_agent", 0))
        external = int(message_doc.get("outbound_external", 0))

        consecutive_doc = consecutive_doc or {}

        return ChannelReportRow(
            channelId=channel_id,
            account=(meta or {}).get("account"),
            name=(meta or {}).get("name"),
            type=(meta or {}).get("type"),
            conversations=int((conversation_doc or {}).get("conversations", 0)),
            incoming=int(message_doc.get("incoming", 0)),
            outbound=OutboundBreakdown(
                total=total,
                template=template,
                bot=bot,
                agent=agent,
                external=external,
                other=max(total - (template + bot + agent + external), 0),
            ),
            consecutive=ConsecutiveBreakdown(
                total=int(consecutive_doc.get("consecutive_total", 0)),
                bot=int(consecutive_doc.get("consecutive_bot", 0)),
                agent=int(consecutive_doc.get("consecutive_agent", 0)),
            ),
        )

    @staticmethod
    def _build_totals(rows: list[ChannelReportRow]) -> ReportTotals:
        totals = ReportTotals(channels=len(rows))
        for row in rows:
            totals.conversations += row.conversations
            totals.incoming += row.incoming
            totals.outbound.total += row.outbound.total
            totals.outbound.template += row.outbound.template
            totals.outbound.bot += row.outbound.bot
            totals.outbound.agent += row.outbound.agent
            totals.outbound.external += row.outbound.external
            totals.outbound.other += row.outbound.other
            totals.consecutive.total += row.consecutive.total
            totals.consecutive.bot += row.consecutive.bot
            totals.consecutive.agent += row.consecutive.agent
        return totals
