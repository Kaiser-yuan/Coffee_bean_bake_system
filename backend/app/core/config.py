"""Application configuration loaded from environment variables."""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Application
    app_name: str = "coffee-roast-api"
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = True
    secret_key: str = "change-me"

    # Database
    database_url: str = "postgresql+asyncpg://coffee:coffee123@localhost:5432/coffee_roast"

    # JWT
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # File Upload
    upload_max_size_bytes: int = 20_971_520  # 20MB
    upload_dir: str = "data/uploads"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def upload_path(self) -> Path:
        p = PROJECT_ROOT / self.upload_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
