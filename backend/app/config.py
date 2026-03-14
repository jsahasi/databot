from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App database (local PostgreSQL in Docker)
    database_url: str = "postgresql+asyncpg://databot:databot@localhost:5432/databot"

    # ON24 master database (direct read-only access)
    on24_db_url: str = ""
    on24_db_url_qa: str = ""

    # PostgreSQL SSL (Google Cloud SQL)
    db_pg_ssl_root_cert_content: str = ""
    db_pg_ssl_cert_content: str = ""
    db_pg_ssl_key_content: str = ""

    # ON24 QA database SSL (separate certs if different)
    db_pg_ssl_cert_content_qa: str = ""
    db_pg_ssl_key_content_qa: str = ""
    postgres_password_qa: str = ""

    # ON24 API
    on24_base_url: str = "https://apiqa.on24.com"
    on24_client_id: str = ""
    on24_access_token_key: str = ""
    on24_access_token_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # OpenAI (embeddings)
    openai_api_key: str = ""

    # Brand voice — company website for blog scraping (optional)
    company_website_url: str = ""

    # App
    app_name: str = "DataBot"
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Sync
    sync_interval_hours: int = 4
    active_event_sync_minutes: int = 15

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
