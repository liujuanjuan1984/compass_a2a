from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "compass_a2a"
    host: str = "127.0.0.1"
    port: int = 8000
    public_url: str = "http://127.0.0.1:8000"
    log_level: str = "INFO"

    compass_api_base_url: str = "http://127.0.0.1:8000/api/v1"
    default_locale: str = "zh-CN"
    protocol_version: str = "0.3.0"
    adapter_version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="COMPASS_A2A_",
        extra="ignore",
    )
