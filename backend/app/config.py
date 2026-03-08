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

    # Email (Resend)
    resend_api_key: str = ""
    from_email: str = "noreply@prial.com"
    from_email_name: str = "Prial"

    # Password reset
    password_reset_token_expire_minutes: int = 60

    # Firebase
    firebase_credentials_path: str = "firebase-credentials.json"
    firebase_credentials_json: str = ""  # JSON içeriği (Railway env var)

    # Scraping
    scrape_interval_minutes: int = 30
    scrape_concurrency: int = 5
    playwright_headless: bool = True
    scraper_api_key: str = ""

    # Admin
    admin_api_key: str = "change-me-in-production"

    # Anthropic (LLM matching)
    anthropic_api_key: str = ""

    # Catalog crawler
    crawler_search_concurrency: int = 3   # kaç variant aynı anda aransın
    crawler_results_per_store: int = 5    # site başına kaç arama sonucu kontrol edilsin

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8081"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
