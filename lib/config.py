"""
Configuración centralizada con pydantic-settings.
Carga y valida variables de entorno al arrancar. Falla rápido si falta algo requerido.
"""
from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Claude (requerido)
    anthropic_api_key: str

    # Telegram (requerido)
    telegram_bot_token: str
    telegram_chat_id: str

    # Mistral (opcional)
    mistral_api_key: Optional[str] = None

    # General
    log_level: str = "INFO"
    data_dir: str = "data"

    # Tarea menu
    menu_source_url: str = (
        "https://www.maisonslaffitte.fr/restauration-scolaire/10166/"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL debe ser uno de: {valid}")
        return upper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la instancia singleton de configuración."""
    return Settings()
