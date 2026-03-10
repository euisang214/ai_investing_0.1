from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_INVESTING_", extra="ignore")

    database_url: str = "sqlite+pysqlite:///:memory:"
    config_dir: Path = Path("config")
    prompts_dir: Path = Path("prompts")
    provider: str = Field(default="fake")
