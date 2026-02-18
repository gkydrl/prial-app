from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "Prial"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@prial.app"
    email_from_name: str = "Prial"

    # Firebase
    firebase_credentials_path: str = "firebase-credentials.json"

    # Scraping
    scrape_interval_minutes: int = 30
    scrape_concurrency: int = 5
    playwright_headless: bool = True

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8081"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
