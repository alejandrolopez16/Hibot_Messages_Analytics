"""Contratos de entrada y salida del endpoint de reportes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import get_settings


class FilterMode(str, Enum):
    TENANT = "tenant"
    LINE = "line"


class ChannelReportRequest(BaseModel):
    """Filtro del reporte: por tenant o por número de línea, nunca ambos."""

    _EX_DATE_FROM = "2026-08-01T00:00:00"
    _EX_DATE_TO_MONTH = "2026-08-31T23:59:59"

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "tenant": "6696761e3c8a4cfe71502bbc",
                    "dateFrom": _EX_DATE_FROM,
                    "dateTo": _EX_DATE_TO_MONTH,
                    "timezone": "America/Bogota",
                },
                {
                    "account": "573001234567",
                    "dateFrom": _EX_DATE_FROM,
                    "dateTo": "2026-08-08T00:00:00",
                    "timezone": "America/Argentina/Buenos_Aires",
                },
            ]
        },
    )

    tenant: str | None = Field(
        default=None,
        description="ObjectId del tenant en formato string (24 hex).",
        examples=["6696761e3c8a4cfe71502bbc"],
    )
    account: str | None = Field(
        default=None,
        alias="account",
        description="Número de línea del canal (campo `account` en `channelData`).",
        examples=["573001234567"],
    )
    date_from: datetime = Field(
        alias="dateFrom",
        description="Inicio del rango sobre el campo `created`. Se interpreta en `timezone`.",
        examples=[_EX_DATE_FROM],
    )
    date_to: datetime = Field(
        alias="dateTo",
        description="Fin del rango (exclusivo) sobre `created`. Se interpreta en `timezone`.",
        examples=[_EX_DATE_TO_MONTH],
    )
    timezone_name: str = Field(
        default_factory=lambda: get_settings().default_timezone,
        alias="timezone",
        description="Zona horaria IANA usada para interpretar el rango (por ejemplo `America/Bogota`).",
        examples=["America/Bogota"],
    )

    @field_validator("tenant")
    @classmethod
    def _validate_object_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        try:
            ObjectId(value)
        except (InvalidId, TypeError) as exc:
            raise ValueError(f"'{value}' no es un ObjectId válido.") from exc
        return value

    @field_validator("account")
    @classmethod
    def _normalize_account(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("timezone_name")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Zona horaria desconocida: '{value}'.") from exc
        return value

    @model_validator(mode="after")
    def _validate_filter(self) -> "ChannelReportRequest":
        settings = get_settings()

        if bool(self.tenant) == bool(self.account):
            raise ValueError("Envía exactamente uno de los filtros: 'tenant' o 'account'.")

        tz = ZoneInfo(self.timezone_name)
        # Una fecha sin offset se interpreta en la zona del tenant (America/Bogota
        # por defecto) y no en UTC: el usuario piensa el rango en hora local, y
        # tratarlo como UTC correría el reporte 5 horas.
        if self.date_from.tzinfo is None:
            self.date_from = self.date_from.replace(tzinfo=tz)
        if self.date_to.tzinfo is None:
            self.date_to = self.date_to.replace(tzinfo=tz)

        self.date_from = self.date_from.astimezone(timezone.utc)
        self.date_to = self.date_to.astimezone(timezone.utc)

        if self.date_to <= self.date_from:
            raise ValueError("'dateTo' debe ser posterior a 'dateFrom'.")

        span = self.date_to - self.date_from
        limit_days = (
            settings.max_range_days_channel if self.account else settings.max_range_days_tenant
        )
        if span > timedelta(days=limit_days):
            raise ValueError(
                f"El rango es de {span.days} días y el máximo permitido es {limit_days}. "
                "Acorta el rango y vuelve a consultar."
            )

        return self

    @property
    def mode(self) -> FilterMode:
        return FilterMode.LINE if self.account else FilterMode.TENANT

    def cache_key(self) -> str:
        return "|".join(
            [
                self.mode.value,
                self.tenant or self.account or "",
                self.date_from.isoformat(),
                self.date_to.isoformat(),
            ]
        )


class OutboundBreakdown(BaseModel):
    """Desglose de los mensajes salientes (todo lo que no es `from == CONTACT`)."""

    total: int = Field(0, description="Suma total de mensajes salientes.")
    template: int = Field(0, description="Salientes con `template` no vacío (HSM).")
    bot: int = Field(0, description="Salientes con `from == BOT` y sin template.")
    agent: int = Field(0, description="Salientes con `from == AGENT` y sin template.")
    external: int = Field(0, description="Salientes con `from == EXTERNAL` y sin template.")
    # Salientes con un `from` fuera de {BOT, AGENT, EXTERNAL} y sin template.
    # No es un KPI de negocio: existe para que total == suma de las partes y
    # cualquier valor nuevo en `from` se vea en vez de perderse.
    other: int = Field(
        0,
        description="Salientes sin template cuyo `from` no cae en {BOT, AGENT, EXTERNAL}.",
    )


class ChannelReportRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    channel_id: str = Field(alias="channelId", description="ObjectId del canal.")
    account: str | None = Field(default=None, description="Número de línea del canal.")
    name: str | None = Field(default=None, description="Nombre visible del canal.")
    type: str | None = Field(default=None, description="Tipo del canal (por ejemplo `whatsapp`).")
    conversations: int = Field(0, description="Conversaciones creadas en el rango.")
    incoming: int = Field(0, description="Mensajes entrantes (`from == CONTACT`) en el rango.")
    outbound: OutboundBreakdown = Field(default_factory=OutboundBreakdown)


class ReportTotals(BaseModel):
    channels: int = Field(0, description="Cantidad de canales incluidos en el resultado.")
    conversations: int = Field(0, description="Suma de conversaciones del periodo.")
    incoming: int = Field(0, description="Suma de mensajes entrantes del periodo.")
    outbound: OutboundBreakdown = Field(default_factory=OutboundBreakdown)


class ChannelReportResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "mode": "tenant",
                    "tenant": "6696761e3c8a4cfe71502bbc",
                    "account": None,
                    "dateFrom": "2026-08-01T05:00:00+00:00",
                    "dateTo": "2026-09-01T04:59:59+00:00",
                    "totals": {
                        "channels": 3,
                        "conversations": 1240,
                        "incoming": 8125,
                        "outbound": {
                            "total": 12980,
                            "template": 4102,
                            "bot": 5220,
                            "agent": 3200,
                            "external": 400,
                            "other": 58,
                        },
                    },
                    "rows": [
                        {
                            "channelId": "6a85c38d30dd311dd7ce7b8b",
                            "account": "573001234567",
                            "name": "Ventas WhatsApp",
                            "type": "whatsapp",
                            "conversations": 820,
                            "incoming": 5320,
                            "outbound": {
                                "total": 8410,
                                "template": 2650,
                                "bot": 3400,
                                "agent": 2100,
                                "external": 240,
                                "other": 20,
                            },
                        }
                    ],
                    "elapsedMs": 842,
                    "cached": False,
                }
            ]
        },
    )

    mode: FilterMode = Field(description="Filtro efectivo aplicado (`tenant` o `line`).")
    tenant: str | None = Field(default=None, description="Tenant al que se restringió la consulta.")
    account: str | None = Field(
        default=None,
        alias="account",
        description="Número de línea al que se restringió la consulta.",
    )
    date_from: datetime = Field(alias="dateFrom", description="Inicio efectivo en UTC.")
    date_to: datetime = Field(alias="dateTo", description="Fin efectivo (exclusivo) en UTC.")
    totals: ReportTotals
    rows: list[ChannelReportRow] = Field(
        description="Detalle por canal, ordenado por tráfico descendente."
    )
    elapsed_ms: int = Field(alias="elapsedMs", description="Tiempo de servicio en milisegundos.")
    cached: bool = Field(default=False, description="`true` si la respuesta viene del caché en memoria.")
