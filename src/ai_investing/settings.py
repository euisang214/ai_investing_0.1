from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_INVESTING_", extra="ignore")

    database_url: str = "sqlite+pysqlite:///:memory:"
    langgraph_checkpoint_url: str | None = None
    config_dir: Path = Path("config")
    prompts_dir: Path = Path("prompts")
    provider: str = Field(default="fake")
    allow_fake_fallback: bool = True
    log_level: str = "INFO"
    auth_enabled: bool = True
    api_keys: str = ""
    domain: str = ""
    max_tokens_per_run: int | None = None
