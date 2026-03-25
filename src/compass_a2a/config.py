from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "compass_a2a"
    host: str = "127.0.0.1"
    port: int = 8000
    public_url: str = "http://127.0.0.1:8000"
    log_level: str = "INFO"

    auth_username: str = "compass"
    auth_password: str = "compass"

    compass_base_url: str = "http://127.0.0.1:8080"
    protocol_version: str = "0.3.0"
    adapter_version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="COMPASS_A2A_",
        extra="ignore",
    )
