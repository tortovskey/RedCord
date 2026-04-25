from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    app_data_dir: Path = Field(default=Path("./data"), alias="APP_DATA_DIR")
    backup_dir: Path = Field(default=Path("./data/backups"), alias="BACKUP_DIR")
    log_dir: Path = Field(default=Path("./logs"), alias="LOG_DIR")
    autosave_interval_seconds: int = Field(default=10, alias="AUTOSAVE_INTERVAL_SECONDS")
    ai_provider: str = Field(default="mock", alias="AI_PROVIDER")
    default_theme: str = Field(default="RedCord", alias="DEFAULT_THEME")


class HealthStatus(BaseModel):
    database: str
    autosave: str
    backup_last_run: str
    integrity: str
    ai_assistant: str
    watchdog: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings()
