"""Configuración central de la aplicación."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- MongoDB -------------------------------------------------------------
    # La URI DEBE apuntar al replica set (mongodb+srv://...). Si no trae
    # readPreference, el cliente lo inyecta en tiempo de arranque.
    mongo_uri: str = Field(..., alias="MONGO_URI")
    mongo_db_channels: str = Field("channels", alias="MONGO_DB_CHANNELS")
    mongo_db_interactions: str = Field("interactions", alias="MONGO_DB_INTERACTIONS")

    mongo_max_pool_size: int = Field(20, alias="MONGO_MAX_POOL_SIZE")
    mongo_min_pool_size: int = Field(2, alias="MONGO_MIN_POOL_SIZE")
    mongo_server_selection_timeout_ms: int = Field(8_000, alias="MONGO_SERVER_SELECTION_TIMEOUT_MS")

    # Corta la agregación del lado del servidor si se pasa del presupuesto.
    # Evita que una consulta mal filtrada mantenga ocupado un secundario.
    aggregation_max_time_ms: int = Field(120_000, alias="AGGREGATION_MAX_TIME_MS")

    # --- Reglas de negocio ---------------------------------------------------
    # Rango máximo por consulta (aplica a tenant y a línea): 1 mes.
    max_range_days_channel: int = Field(31, alias="MAX_RANGE_DAYS_CHANNEL")
    max_range_days_tenant: int = Field(31, alias="MAX_RANGE_DAYS_TENANT")
    default_timezone: str = Field("America/Bogota", alias="DEFAULT_TIMEZONE")

    # --- Caché ---------------------------------------------------------------
    # Estas consultas son caras y los datos históricos no cambian. Un TTL corto
    # absorbe recargas de pantalla y cambios de filtro de ida y vuelta.
    report_cache_ttl_seconds: int = Field(300, alias="REPORT_CACHE_TTL_SECONDS")
    report_cache_max_entries: int = Field(128, alias="REPORT_CACHE_MAX_ENTRIES")

    # --- API -----------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"], alias="CORS_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
