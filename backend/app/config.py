from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://databot:databot@localhost:5432/databot"

    # PostgreSQL SSL (Google Cloud SQL)
    db_pg_ssl_root_cert_content: str = ""
    db_pg_ssl_cert_content: str = ""
    db_pg_ssl_key_content: str = ""

    # ON24 API
    on24_base_url: str = "https://apiqa.on24.com"
    on24_client_id: str = ""
    on24_access_token_key: str = ""
    on24_access_token_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # App
    app_name: str = "DataBot"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

    # Sync
    sync_interval_hours: int = 4
    active_event_sync_minutes: int = 15

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
