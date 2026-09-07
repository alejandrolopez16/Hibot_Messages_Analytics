"""Pipelines de agregación.

Diseño: no hay `$lookup` en ninguno de los dos pipelines.

- `channelData` está en otra base de datos y `$lookup` no cruza bases, así que
  los metadatos del canal se resuelven en una consulta aparte.
- `conversationData` y `messageData` sí comparten base, pero unirlas con
  `$lookup` sobre cientos de millones de documentos ejecutaría una subconsulta
  por documento. Como ambas colecciones tienen `channelId`, se agregan por
  separado y se cruzan en memoria sobre las decenas de filas del resultado.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

# --- Expresiones de clasificación -------------------------------------------

IS_CONTACT: dict[str, Any] = {"$eq": ["$from", "CONTACT"]}
IS_OUTBOUND: dict[str, Any] = {"$ne": ["$from", "CONTACT"]}

# `template` puede venir ausente, null o "". `$ifNull` normaliza los tres casos
# a "" para que la comparación sea una sola.
TEMPLATE_VALUE: dict[str, Any] = {"$ifNull": ["$template", ""]}
HAS_TEMPLATE: dict[str, Any] = {"$ne": [TEMPLATE_VALUE, ""]}
NO_TEMPLATE: dict[str, Any] = {"$eq": [TEMPLATE_VALUE, ""]}

# Orden de los índices del $match, para pasarlo como hint.
TENANT_CREATED_HINT: dict[str, int] = {"tenant": 1, "created": 1}


def _count_if(condition: dict[str, Any]) -> dict[str, Any]:
    return {"$sum": {"$cond": [condition, 1, 0]}}


def build_match(
    *,
    tenant: str,
    date_from: datetime,
    date_to: datetime,
    channel_ids: list[str] | None = None,
) -> dict[str, Any]:
    """`$match` inicial, ordenado para caer sobre `{ tenant: 1, created: 1 }`.

    `tenant` siempre está presente, incluso cuando el usuario filtró por línea:
    no existe índice por `channelId`, así que el tenant se resuelve antes de
    consultar (a partir de la línea) y los `channelId` de esa línea quedan como
    filtro residual sobre un conjunto que ya redujo el índice.
    """
    match: dict[str, Any] = {
        "tenant": tenant,
        # `$gte` / `$lt` deja el límite superior exclusivo: dos rangos contiguos
        # no cuentan dos veces el mensaje que cae justo en la frontera.
        "created": {"$gte": date_from, "$lt": date_to},
    }
    if channel_ids:
        # Una línea puede estar asociada a más de un canal (por ejemplo, un
        # canal reemplazado que conserva histórico): se filtra con `$in` para
        # sumar el tráfico de todos.
        match["channelId"] = channel_ids[0] if len(channel_ids) == 1 else {"$in": channel_ids}
    return match


def conversations_pipeline(match: dict[str, Any]) -> list[dict[str, Any]]:
    """Total de conversaciones por canal."""
    return [
        {"$match": match},
        {"$group": {"_id": "$channelId", "conversations": {"$sum": 1}}},
    ]


def messages_pipeline(match: dict[str, Any]) -> list[dict[str, Any]]:
    """Entrantes y desglose de salientes por canal, en una sola pasada.

    Todos los contadores salen del mismo `$group` con acumuladores condicionales.
    Contar cada categoría con su propia consulta significaría releer el mismo
    rango cinco veces.

    Regla del enunciado: un saliente con `template` no vacío suma solo a
    `outbound_template`; los contadores de bot / agent / external exigen
    `template` vacío, así que ninguna categoría se solapa.
    """
    return [
        {"$match": match},
        {
            "$group": {
                "_id": "$channelId",
                "incoming": _count_if(IS_CONTACT),
                "outbound_total": _count_if(IS_OUTBOUND),
                "outbound_template": _count_if({"$and": [IS_OUTBOUND, HAS_TEMPLATE]}),
                "outbound_bot": _count_if({"$and": [{"$eq": ["$from", "BOT"]}, NO_TEMPLATE]}),
                "outbound_agent": _count_if({"$and": [{"$eq": ["$from", "AGENT"]}, NO_TEMPLATE]}),
                "outbound_external": _count_if({"$and": [{"$eq": ["$from", "EXTERNAL"]}, NO_TEMPLATE]}),
            }
        },
    ]
