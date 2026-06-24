"""Application configuration loaded from environment variables."""
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Application
    app_name: str = "coffee-roast-api"
    app_env: Literal["development", "production", "test"] = "development"
    app_version: str = "0.3.0"
    debug: bool = True
    sql_echo: bool = False  # Log every SQL statement — big perf hit, keep off.
    secret_key: str = "change-me"
    # Git commit SHA — injected at deploy/dev-start time via env.
    app_git_sha: str = "unknown"

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

    # Auth
    allow_first_user_registration: bool = True

    # Timezone — naive timestamps from CSV / filenames / forms are assumed to be
    # in this zone and converted to UTC before persisting.
    app_timezone: str = "Asia/Shanghai"

    # Bulk upload limits
    bulk_upload_max_files: int = 20
    bulk_upload_max_total_bytes: int = 104_857_600  # 100 MB

    # Spacing between consecutive pots when assigning roast times by upload/pot
    # order (minutes). No CookDate, same-day filenames get first-pot time +
    # (pot_order - 1) * this spacing.
    roast_spacing_minutes: int = 45

    # Bulk job expiry (seconds)
    bulk_job_expiry_seconds: int = 86400  # 24 hours

    # Public evaluation rate limit
    public_evaluation_rate_limit_per_minute: int = 10
    public_evaluation_repeat_window_seconds: int = 300

    # Public frontend URL for share links
    public_frontend_base_url: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _validate_production_settings(self):
        if self.app_env != "production":
            return self
        if self.secret_key in ("change-me", "dev-secret-key-change-before-production"):
            raise ValueError("生产环境必须设置一个安全的 SECRET_KEY")
        if self.jwt_secret_key in ("change-me-jwt-secret", "dev-jwt-secret-change-before-production"):
            raise ValueError("生产环境必须设置一个安全的 JWT_SECRET_KEY")
        if self.database_url and "coffee123" in self.database_url:
            raise ValueError("生产环境必须设置一个安全的数据库密码")
        if any("localhost" in o for o in self.cors_origins):
            raise ValueError("生产环境不能使用 localhost CORS 来源")
        return self

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
