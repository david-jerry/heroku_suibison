from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_URL = Path(__file__).resolve().parent.parent.parent

class BaseConfig(BaseSettings):
    ENVIRONMENT: str
    SECRET_KEY: str
    WEBAPP_URL: str
    ALGORITHM: Optional[str] = "HS256"
    ROLLBACK_ACCESS_TOKEN: str = "2574e01d16c14665916305eae9694244"
    BASE_DIR: Optional[Path] = BASE_URL
    TELEGRAM_TOKEN: str
    APP_DIR: Optional[Path] = BASE_DIR / 'src/apps'
    VERSION: Optional[str] = "v1"
    ACCESS_TOKEN_EXPIRY: Optional[int] = 1800
    DOMAIN: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding='utf-8'
    )


BaseConfigSettings = BaseConfig()
