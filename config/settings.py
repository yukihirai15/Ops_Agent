"""
OpsAgent configuration — loaded from environment / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Anthropic (optional now)
    anthropic_api_key: Optional[str] = None

    # Groq
    groq_api_key: str

    # Prometheus
    prometheus_url: str = "http://prometheus:9090"

    # Loki (optional — falls back to Docker logs)
    loki_url: Optional[str] = None

    # Slack
    slack_webhook_url: Optional[str] = None

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"

    # Agent behaviour
    max_iterations: int = 10
    dry_run: bool = False  # If True, skips Slack + external mutations


settings = Settings()
